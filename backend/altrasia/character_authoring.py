from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.services import AppServices

ISO = lambda: datetime.now(timezone.utc).isoformat()

DRAFT_SYSTEM = (
    "You are a character authoring assistant for a narrative world. "
    "Respond with ONLY a single JSON object (no markdown) with keys: "
    "persona, instructions, focusTags (array), speechWeight (0-1 number), modelProfile."
)


def _display_name(defn: dict[str, Any], brief: str) -> str:
    persona = (defn.get("persona") or "").strip()
    if persona:
        first = persona.split(".")[0].strip()
        if len(first) > 48:
            return first[:45] + "…"
        return first or "New character"
    return (brief[:48] + "…") if len(brief) > 48 else (brief or "New character")


def _parse_definition(raw: str, brief: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    persona = data.get("persona") or f"A thoughtful NPC inspired by: {brief[:200]}"
    instructions = data.get("instructions") or (
        "Stay in character. Use memory tools when uncertain about past events."
    )
    return {
        "persona": persona,
        "instructions": instructions,
        "focusTags": data.get("focusTags") or [],
        "speechWeight": float(data.get("speechWeight", 0.5)),
        "modelProfile": data.get("modelProfile") or "qwen3.6-35b-a3b",
    }


async def create_character_draft(svc: AppServices, brief: str) -> dict[str, Any]:
    """CHAR-1/CHAR-4: meta-channel draft via GpuResourceQueue (not scene play)."""
    draft_id = str(uuid.uuid4())
    now = ISO()
    svc.store.insert_character_draft(
        {
            "draftId": draft_id,
            "operatorBrief": brief,
            "definitionJson": None,
            "status": "drafting",
            "errorMessage": None,
            "createdAt": now,
            "updatedAt": now,
        }
    )

    async def _run() -> dict[str, Any]:
        messages = [
            {"role": "system", "content": DRAFT_SYSTEM},
            {"role": "user", "content": brief},
        ]
        result = await svc.llm.chat(messages, tools=None)
        content = result["choices"][0]["message"].get("content") or "{}"
        return _parse_definition(content, brief)

    try:
        definition = await svc.gpu_queue.run(draft_id, "character_draft", _run)
        svc.store.update_character_draft(
            draft_id,
            definitionJson=json.dumps(definition),
            status="ready",
            updatedAt=ISO(),
        )
    except Exception as exc:  # noqa: BLE001 — persist draft failure for operator
        svc.store.update_character_draft(
            draft_id,
            status="error",
            errorMessage=str(exc),
            updatedAt=ISO(),
        )
        raise

    row = svc.store.get_character_draft(draft_id)
    return _draft_response(row)


def _draft_response(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        raise ValueError("draft not found")
    defn = None
    if row.get("definitionJson"):
        defn = json.loads(row["definitionJson"])
    return {
        "draftId": row["draftId"],
        "status": row["status"],
        "operatorBrief": row["operatorBrief"],
        "definitionJson": defn,
        "errorMessage": row.get("errorMessage"),
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
    }


def get_character_draft(svc: AppServices, draft_id: str) -> dict[str, Any] | None:
    row = svc.store.get_character_draft(draft_id)
    if not row:
        return None
    return _draft_response(row)


def discard_character_draft(svc: AppServices, draft_id: str) -> bool:
    row = svc.store.get_character_draft(draft_id)
    if not row:
        return False
    if row["status"] == "approved":
        return False
    svc.store.update_character_draft(
        draft_id, status="discarded", updatedAt=ISO()
    )
    return True


def approve_character_draft(
    svc: AppServices,
    draft_id: str,
    *,
    definition_override: dict[str, Any] | None = None,
    display_name: str | None = None,
    world_id: str | None = None,
) -> dict[str, Any]:
    """CHAR-2/CHAR-3: persist Character + optional world membership."""
    row = svc.store.get_character_draft(draft_id)
    if not row:
        raise ValueError("draft not found")
    if row["status"] not in ("ready", "drafting"):
        raise ValueError(f"draft not approvable: {row['status']}")
    if not row.get("definitionJson"):
        raise ValueError("draft has no definition yet")

    base = json.loads(row["definitionJson"])
    if definition_override:
        base = {**base, **definition_override}
    brief = row["operatorBrief"]
    character_id = f"char-{uuid.uuid4().hex[:12]}"
    now = ISO()
    model_profile = base.get("modelProfile") or "qwen3.6-35b-a3b"
    if isinstance(model_profile, dict):
        model_profile = model_profile.get("id") or "qwen3.6-35b-a3b"
    model_profile = str(model_profile)
    svc.store.insert_character(
        {
            "characterId": character_id,
            "displayName": display_name or _display_name(base, brief),
            "definitionJson": json.dumps(base),
            "modelProfile": model_profile,
            "speechWeight": base.get("speechWeight", 0.5),
            "createdAt": now,
        }
    )
    if world_id:
        world = svc.store.get_world(world_id)
        if not world:
            raise ValueError("world not found")
        svc.store.add_world_member(world_id, character_id)

    svc.store.update_character_draft(
        draft_id, status="approved", updatedAt=ISO()
    )
    return {
        "characterId": character_id,
        "draftId": draft_id,
        "displayName": display_name or _display_name(base, brief),
        "definitionJson": base,
        "worldId": world_id,
    }
