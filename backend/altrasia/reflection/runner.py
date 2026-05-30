from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.evidence import record_evidence
from altrasia.memory.strip_reasoning import is_durable_value_ok, strip_reasoning
from altrasia.reflection.graph import neighbors_for_recall, write_links
from altrasia.reflection.prompts import REFLECTION_SYSTEM
from altrasia.world_config import get_world_config

log = logging.getLogger(__name__)

ISO = lambda: datetime.now(timezone.utc).isoformat()

_REFLECTION_DEFAULTS: dict[str, Any] = {
    "reflectionEnabled": False,
    "reflectionNightlyHourUtc": 3,
    "reflectionMaxCharsPerRun": 6000,
    "reflectionAutoApproveLoci": True,
    "reflectionLocusMaxChars": 2000,
    "reflectionPersonaProposalsEnabled": True,
}


def reflection_config(store: Any, world_id: str | None) -> dict[str, Any]:
    if not world_id:
        return dict(_REFLECTION_DEFAULTS)
    cfg = get_world_config(store, world_id)
    return {**_REFLECTION_DEFAULTS, **{k: cfg[k] for k in _REFLECTION_DEFAULTS if k in cfg}}


def character_has_reflection_input(store: Any, character_id: str) -> bool:
    last_at = store.get_last_reflection_at(character_id)
    diary = store.list_diary_since(character_id, last_at, limit=1)
    return len(diary) > 0


def list_eligible_characters(store: Any, world_id: str) -> list[str]:
    members = store.list_world_characters(world_id)
    return [
        m["characterId"]
        for m in members
        if not m.get("disabled") and character_has_reflection_input(store, m["characterId"])
    ]


def _parse_reflection_json(raw: str) -> dict[str, Any] | None:
    text = strip_reasoning(raw).strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _assemble_context(
    store: Any,
    *,
    character_id: str,
    world_id: str | None,
    max_chars: int,
) -> tuple[str, list[str], int]:
    last_at = store.get_last_reflection_at(character_id)
    diary = store.list_diary_since(character_id, last_at, limit=100)
    segment_ids = [d["segmentId"] for d in diary]

    ch = store.get_character(character_id) or {}
    display_name = ch.get("displayName") or character_id
    try:
        definition = json.loads(ch.get("definitionJson") or "{}")
    except json.JSONDecodeError:
        definition = {}

    parts: list[str] = [
        f"# Character: {display_name}",
        f"Persona: {(definition.get('persona') or '')[:800]}",
        f"Instructions: {(definition.get('instructions') or '')[:800]}",
    ]

    if world_id:
        cast = store.list_world_characters(world_id)
        if cast:
            parts.append("## Cast context")
            for m in cast[:20]:
                parts.append(f"- {m['characterId']}: {m.get('displayName', m['characterId'])}")

    reflection_loci = store.fetchall(
        """SELECT locusKey, value FROM Locus
           WHERE pool = 'mind' AND ownerId = ?
           AND (locusKey LIKE 'reflection:%' OR locusKey LIKE 'relationship:%')
           ORDER BY updatedAt DESC LIMIT 15""",
        (character_id,),
    )
    if reflection_loci:
        parts.append("## Existing reflection notes")
        for row in reflection_loci:
            parts.append(f"- {row['locusKey']}: {(row['value'] or '')[:400]}")

    if diary:
        parts.append("## New diary since last reflection")
        for seg in diary:
            parts.append(f"[{seg.get('createdAt', '')}] {seg.get('text', '')[:600]}")

    text = "\n".join(parts)
    return text[:max_chars], segment_ids, len(diary)


async def run_reflection(
    svc: Any,
    *,
    character_id: str,
    world_id: str | None,
    trigger: str = "on_demand",
) -> dict[str, Any]:
    cfg = reflection_config(svc.store, world_id)
    if not cfg.get("reflectionEnabled") and trigger not in ("manual", "on_demand"):
        return {"status": "skipped", "reason": "reflection_disabled"}

    if not character_has_reflection_input(svc.store, character_id):
        return {"status": "skipped", "reason": "no_new_diary"}

    run_id = str(uuid.uuid4())
    now = ISO()
    max_chars = int(cfg.get("reflectionMaxCharsPerRun", 6000))
    context, segment_ids, diary_count = _assemble_context(
        svc.store, character_id=character_id, world_id=world_id, max_chars=max_chars
    )

    svc.store.insert_reflection_run(
        {
            "runId": run_id,
            "characterId": character_id,
            "worldId": world_id,
            "trigger": trigger,
            "inputSegmentIdsJson": json.dumps(segment_ids),
            "inputMessageCount": diary_count,
            "outputLociJson": None,
            "outputLinkCount": 0,
            "status": "running",
            "errorText": None,
            "startedAt": now,
            "completedAt": None,
        }
    )

    timeout = 180.0
    if world_id:
        timeout = float(get_world_config(svc.store, world_id).get("inferenceTimeoutSeconds", 180))

    user = f"Today's date: {datetime.now(timezone.utc).date().isoformat()}\n\n{context}"

    async def work() -> dict[str, Any]:
        resp = await svc.llm.chat(
            [{"role": "system", "content": REFLECTION_SYSTEM}, {"role": "user", "content": user}],
            None,
            timeout=timeout,
        )
        raw = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
        parsed = _parse_reflection_json(str(raw))
        if not parsed:
            raise ValueError("reflection LLM returned invalid JSON")
        return parsed

    try:
        parsed = await svc.gpu_queue.run(run_id, "chat", work)
    except Exception as exc:
        log.warning("reflection failed character=%s: %s", character_id, exc)
        svc.store.update_reflection_run(
            run_id,
            status="failed",
            errorText=str(exc)[:500],
            completedAt=ISO(),
        )
        return {"status": "failed", "runId": run_id, "error": str(exc)[:200]}

    locus_max = int(cfg.get("reflectionLocusMaxChars", 2000))
    auto_approve = bool(cfg.get("reflectionAutoApproveLoci", True))
    written_loci: list[str] = []

    for item in parsed.get("loci") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        value = strip_reasoning(str(item.get("value") or ""))
        if not key or not is_durable_value_ok(value):
            continue
        if not auto_approve:
            continue
        value = value[:locus_max]
        svc.memory.memory_store(
            pool="mind",
            owner_id=character_id,
            locus_key=key,
            value=value,
        )
        record_evidence(
            svc.store,
            locus_key=key,
            pool="mind",
            owner_id=character_id,
            source_kind="reflection",
            source_ref=run_id,
        )
        svc.embeddings.schedule_embed(
            owner_scope="mind",
            owner_id=character_id,
            source_type="locus",
            source_ref=key,
            text=value,
        )
        written_loci.append(key)

    link_count = write_links(
        svc.store,
        character_id=character_id,
        reflection_run_id=run_id,
        links=[l for l in (parsed.get("links") or []) if isinstance(l, dict)],
    )

    for link in parsed.get("links") or []:
        if not isinstance(link, dict):
            continue
        summary = (link.get("summary") or "").strip()
        if summary:
            svc.embeddings.schedule_embed(
                owner_scope="mind",
                owner_id=character_id,
                source_type="link",
                source_ref=str(link.get("fromRef") or run_id),
                text=summary[:2000],
            )

    proposal_ids: list[str] = []
    if cfg.get("reflectionPersonaProposalsEnabled", True):
        for prop in parsed.get("persona_proposals") or []:
            if not isinstance(prop, dict):
                continue
            field = str(prop.get("field") or "").strip()
            if field not in ("persona", "instructions", "focusTags"):
                continue
            proposed = strip_reasoning(str(prop.get("proposedValue") or ""))
            if not is_durable_value_ok(proposed):
                continue
            pid = str(uuid.uuid4())
            svc.store.insert_persona_proposal(
                {
                    "proposalId": pid,
                    "characterId": character_id,
                    "reflectionRunId": run_id,
                    "field": field,
                    "proposedValue": proposed[:4000],
                    "rationale": strip_reasoning(str(prop.get("rationale") or ""))[:1000],
                    "status": "pending",
                    "createdAt": ISO(),
                    "resolvedAt": None,
                }
            )
            proposal_ids.append(pid)

    svc.store.update_reflection_run(
        run_id,
        status="completed",
        outputLociJson=json.dumps(written_loci),
        outputLinkCount=link_count,
        completedAt=ISO(),
    )

    return {
        "status": "completed",
        "runId": run_id,
        "lociWritten": len(written_loci),
        "linksWritten": link_count,
        "personaProposals": len(proposal_ids),
        "summary": (parsed.get("summary") or "")[:500],
    }


async def enqueue_reflection_for_world(
    svc: Any,
    world_id: str,
    *,
    trigger: str = "on_demand",
) -> list[dict[str, Any]]:
    cfg = reflection_config(svc.store, world_id)
    if not cfg.get("reflectionEnabled") and trigger not in ("manual", "on_demand"):
        return []
    if svc.gpu_queue.busy:
        return [{"status": "skipped", "reason": "gpu_busy"}]
    results: list[dict[str, Any]] = []
    for cid in list_eligible_characters(svc.store, world_id):
        if svc.gpu_queue.busy:
            break
        result = await run_reflection(
            svc, character_id=cid, world_id=world_id, trigger=trigger
        )
        results.append({"characterId": cid, **result})
        if result.get("status") == "completed":
            break
    return results
