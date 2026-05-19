from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.orchestrator.discussion_judgement import (
    ISO,
    ensure_ensemble_discussion,
    get_ensemble_discussion,
)

_DELIVERABLE_KINDS = frozenset({"report", "summary", "brief", "update"})

# Name, … (when finished|when done|after …) … (expect|want|need) … (report|summary|…)
_OBLIGATION_CLAUSE = re.compile(
    r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,\s*"
    r"(?:(?:when|once|after)\s+(?:your\s+team\s+is\s+)?(?:finished|done)|"
    r"when\s+(?:you(?:'re| are)\s+)?finished)\s*[,]?\s*"
    r"(?:I\s+)?(?:expect|want|need|would\s+like)\s+"
    r"(?:a\s+)?(?P<kind>report|summary|brief|update)\s+from\s+you",
    re.I,
)

_ALT_OBLIGATION = re.compile(
    r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,\s*"
    r".{0,120}?"
    r"(?P<kind>report|summary|brief|update)\s+from\s+you",
    re.I,
)


def _roster_index(roster: list[dict[str, Any]]) -> dict[str, str]:
    """Map lowercase name tokens -> characterId."""
    index: dict[str, str] = {}
    for m in roster:
        cid = m.get("characterId")
        display = (m.get("displayName") or "").strip()
        if not cid or not display:
            continue
        index[display.lower()] = cid
        parts = display.split()
        if parts:
            index[parts[0].lower()] = cid
    return index


def resolve_character_name(name: str, roster_index: dict[str, str]) -> str | None:
    token = (name or "").strip().lower().rstrip(",")
    if not token:
        return None
    if token in roster_index:
        return roster_index[token]
    for key, cid in roster_index.items():
        if key.startswith(token) or token.startswith(key.split()[0]):
            return cid
    return None


def parse_operator_deliverables(
    text: str,
    roster: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract post-discussion obligations directed at named cast members."""
    if not (text or "").strip():
        return []
    index = _roster_index(roster)
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pattern in (_OBLIGATION_CLAUSE, _ALT_OBLIGATION):
        for match in pattern.finditer(text):
            name = match.group("name")
            kind = (match.group("kind") or "report").lower()
            if kind not in _DELIVERABLE_KINDS:
                kind = "report"
            cid = resolve_character_name(name, index)
            if not cid or cid in seen:
                continue
            seen.add(cid)
            clause = match.group(0).strip()
            found.append(
                {
                    "deliverableId": str(uuid.uuid4()),
                    "characterId": cid,
                    "kind": kind,
                    "instruction": clause[:500],
                    "status": "pending",
                    "operatorMessageId": None,
                    "fulfillmentMessageId": None,
                    "commissionId": None,
                }
            )
    return found


def merge_deliverables_into_activity(
    activity: dict[str, Any],
    deliverables: list[dict[str, Any]],
    *,
    operator_message_id: str | None = None,
    max_count: int = 3,
) -> dict[str, Any]:
    existing = list(activity.get("deliverables") or [])
    pending_ids = {
        d.get("characterId")
        for d in existing
        if d.get("status") == "pending"
    }
    for d in deliverables[:max_count]:
        if d.get("characterId") in pending_ids:
            continue
        if operator_message_id:
            d = {**d, "operatorMessageId": operator_message_id}
        existing.append(d)
        pending_ids.add(d["characterId"])
    activity["deliverables"] = existing[-max_count:]
    return activity


def bootstrap_ensemble_discussion(
    store: Any,
    scene_id: str,
    *,
    operator_text: str,
    operator_message_id: str | None,
    world_id: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Start ensemble_discussion activity and attach parsed operator deliverables."""
    activity = ensure_ensemble_discussion(
        store, scene_id, operator_message_id=operator_message_id
    )
    if not cfg.get("discussionDeliverablesEnabled", True):
        return activity
    roster = store.list_world_characters(world_id)
    parsed = parse_operator_deliverables(operator_text, roster)
    if not parsed:
        return activity
    max_n = int(cfg.get("maxDeliverablesPerDiscussion", 3))
    activity = merge_deliverables_into_activity(
        activity,
        parsed,
        operator_message_id=operator_message_id,
        max_count=max_n,
    )
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def pending_deliverables(activity: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not activity:
        return []
    return [
        d
        for d in (activity.get("deliverables") or [])
        if d.get("status") == "pending"
    ]


def all_deliverables_done(activity: dict[str, Any] | None) -> bool:
    deliverables = (activity or {}).get("deliverables") or []
    if not deliverables:
        return True
    return all(d.get("status") == "done" for d in deliverables)


def mark_deliverable_done(
    store: Any,
    scene_id: str,
    deliverable_id: str,
    *,
    fulfillment_message_id: str,
    commission_id: str | None = None,
) -> dict[str, Any] | None:
    scene = store.get_scene(scene_id)
    activity = get_ensemble_discussion(scene)
    if not activity:
        return None
    updated = None
    deliverables: list[dict[str, Any]] = []
    for d in activity.get("deliverables") or []:
        if d.get("deliverableId") == deliverable_id:
            d = {
                **d,
                "status": "done",
                "fulfillmentMessageId": fulfillment_message_id,
                "commissionId": commission_id,
                "completedAt": ISO(),
            }
            updated = d
        deliverables.append(d)
    activity["deliverables"] = deliverables
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return updated


def deliverables_summary_for_judge(activity: dict[str, Any] | None) -> str:
    pending = pending_deliverables(activity)
    if not pending:
        return "No post-discussion deliverables pending."
    lines = []
    for d in pending:
        lines.append(
            f"- {d.get('characterId')}: {d.get('kind', 'report')} — {d.get('instruction', '')[:200]}"
        )
    return "Operator deliverables still outstanding:\n" + "\n".join(lines)


def mind_locus_for_deliverable(scene_id: str, character_id: str, kind: str) -> str:
    return f"discussion:{scene_id}:{character_id}:{kind}"


def save_activity(store: Any, scene_id: str, activity: dict[str, Any]) -> None:
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())


def get_activity(store: Any, scene_id: str) -> dict[str, Any] | None:
    scene = store.get_scene(scene_id)
    return get_ensemble_discussion(scene)


_CHAIN_STOP_SCHEDULE_DELIVERABLES = frozenset(
    {"conversation_resolved", "max_continue_depth", "depth_cap_unresolved"}
)


async def enqueue_pending_deliverables(
    orch: Any,
    job: dict[str, Any],
    stop_reason: str | None,
) -> list[dict[str, Any]]:
    """After the cast chain stops, schedule one generation per pending deliverable."""
    if not stop_reason or stop_reason not in _CHAIN_STOP_SCHEDULE_DELIVERABLES:
        return []
    cfg = orch._world_config(job["worldId"])
    if not cfg.get("discussionDeliverablesEnabled", True):
        return []
    activity = get_activity(orch.svc.store, job["sceneId"])
    pending = pending_deliverables(activity)
    if not pending:
        return []
    scheduled: list[dict[str, Any]] = []
    for d in pending:
        result = await orch.enqueue_generation(
            world_id=job["worldId"],
            scene_id=job["sceneId"],
            character_id=d["characterId"],
            trigger="discussion_deliverable",
            continue_depth=0,
            trigger_message_id=job.get("triggerMessageId"),
            deliverable_id=d.get("deliverableId"),
            deliverable_kind=d.get("kind", "report"),
            deliverable_instruction=d.get("instruction"),
        )
        if result:
            scheduled.append({**d, "jobId": result.get("jobId")})
    if scheduled:
        orch._emit(
            job["worldId"],
            "conversation.deliverables_scheduled",
            {
                "sceneId": job["sceneId"],
                "deliverables": [
                    {"characterId": s["characterId"], "kind": s.get("kind"), "jobId": s.get("jobId")}
                    for s in scheduled
                ],
            },
        )
    return scheduled


def maybe_clear_ensemble_if_complete(store: Any, scene_id: str) -> bool:
    activity = get_activity(store, scene_id)
    if activity and all_deliverables_done(activity):
        from altrasia.orchestrator.discussion_judgement import clear_ensemble_discussion

        clear_ensemble_discussion(store, scene_id)
        return True
    return False
