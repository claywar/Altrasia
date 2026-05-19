from __future__ import annotations

import json
from typing import Any

from altrasia.domain.presence import PERSONA_ID
from altrasia.orchestrator.speaker_selection import (
    AddressingResult,
    addressee_ids_for,
    addressing_from_dict,
    is_multi_directed,
    pick_directed_witness,
)

_EXPLICIT_TARGET_TRIGGERS = frozenset(
    {"whisper_target", "knock_answered", "phone_target", "discussion_deliverable"}
)
def addressing_from_message_row(row: dict[str, Any] | None) -> AddressingResult | None:
    if not row:
        return None
    try:
        meta = json.loads(row.get("metaJson") or "{}")
    except json.JSONDecodeError:
        return None
    orch = meta.get("orchestration") or {}
    return addressing_from_dict(orch.get("addressing"))


def latest_operator_message(
    store: Any, world_id: str, scene_id: str
) -> dict[str, Any] | None:
    for m in reversed(store.list_messages(world_id, scene_id=scene_id)):
        if m.get("role") == "assistant":
            continue
        if (m.get("outputText") or "").strip():
            return m
    return None


def latest_operator_addressing(
    store: Any, world_id: str, scene_id: str
) -> tuple[AddressingResult | None, str | None]:
    """Most recent operator line and its persisted addressing (if any)."""
    op = latest_operator_message(store, world_id, scene_id)
    if not op:
        return None, None
    return addressing_from_message_row(op), op.get("messageId")


def cast_spoke_on_trigger(
    store: Any, world_id: str, scene_id: str, operator_message_id: str | None
) -> set[str]:
    if not operator_message_id:
        return set()
    rows = store.conn.execute(
        """SELECT characterId FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ?
             AND status = 'done' AND characterId IS NOT NULL""",
        (world_id, scene_id, operator_message_id),
    ).fetchall()
    return {row[0] for row in rows}


def primary_replied_to_trigger(
    store: Any,
    world_id: str,
    scene_id: str,
    operator_message_id: str,
    primary_id: str,
) -> bool:
    row = store.fetchone(
        """SELECT 1 FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ?
             AND characterId = ? AND status = 'done' LIMIT 1""",
        (world_id, scene_id, operator_message_id, primary_id),
    )
    return row is not None


def scene_has_unanswered_directed(
    store: Any, world_id: str, scene_id: str
) -> bool:
    """True when the latest operator line is directed and an addressee has not replied yet."""
    addressing, op_id = latest_operator_addressing(store, world_id, scene_id)
    if not addressing or addressing.mode != "directed":
        return False
    ids = addressee_ids_for(addressing)
    if not ids or not op_id:
        return False
    return any(
        not primary_replied_to_trigger(store, world_id, scene_id, op_id, aid)
        for aid in ids
    )


def may_character_generate(
    svc: Any,
    job: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[bool, str]:
    """
    Generic gate: every scene generation job must pass this before speaking.

    Enforces directed threads regardless of trigger (persona, continue, idle).
    """
    trigger = str(job.get("trigger") or "")
    if trigger in _EXPLICIT_TARGET_TRIGGERS:
        return True, "explicit_target"
    if trigger.startswith("commission"):
        return True, "commission"
    if trigger == "debate_turn":
        return True, "debate"

    world_id = job["worldId"]
    scene_id = job["sceneId"]
    character_id = job["characterId"]
    depth = int(job.get("continueDepth") or 0)
    op_id = job.get("triggerMessageId")

    addressing = addressing_from_message_row(
        svc.store.fetchone(
            "SELECT metaJson FROM Message WHERE messageId = ?",
            (op_id,),
        )
        if op_id
        else None
    )
    if addressing is None:
        addressing, latest_op_id = latest_operator_addressing(svc.store, world_id, scene_id)
        if op_id is None and latest_op_id:
            op_id = latest_op_id

    if not addressing or addressing.mode != "directed":
        return True, "not_directed"

    addressees = addressee_ids_for(addressing)
    if not addressees:
        return True, "directed_no_primary"

    if trigger == "idle_timer":
        return False, "directed_blocks_idle"

    spoke = cast_spoke_on_trigger(svc.store, world_id, scene_id, op_id)
    if character_id in spoke:
        return False, "already_spoke_on_operator_line"

    if is_multi_directed(addressing):
        if character_id not in addressees:
            return False, "not_named_addressee"
        if depth >= len(addressees):
            return False, "directed_multi_depth_exceeded"
        if character_id != addressees[depth]:
            return False, "directed_multi_wrong_order"
        return True, "directed_multi_addressee"

    primary = addressees[0]
    if depth == 0:
        if character_id == primary:
            return True, "directed_primary"
        return False, "directed_wrong_speaker_at_depth_0"

    directed_max = max(0, int(cfg.get("directedReplyMaxDepth", 1)))
    if depth > directed_max:
        return False, "directed_depth_exceeded"

    if character_id == primary:
        return False, "directed_primary_cannot_continue"

    if depth == 1 and directed_max >= 1:
        op_row = (
            svc.store.fetchone(
                "SELECT outputText FROM Message WHERE messageId = ?",
                (op_id,),
            )
            if op_id
            else None
        )
        op_text = (op_row.get("outputText") or "").strip() if op_row else ""
        scene = svc.store.get_scene(scene_id)
        present = [
            c
            for c in json.loads(scene["presentJson"])
            if c not in (PERSONA_ID,)
        ]
        rel_min = float(cfg.get("directedWitnessRelevanceMin", 0.55))
        witness = pick_directed_witness(
            svc,
            world_id=world_id,
            scene_id=scene_id,
            trigger_text=op_text,
            primary_id=primary,
            eligible=present,
            exclude_ids=spoke,
            trigger_message_id=op_id,
            relevance_min=rel_min,
        )
        if witness and witness.character_id == character_id:
            return True, "directed_witness"
        return False, "not_qualified_witness"

    return False, "directed_denied"


def list_scene_jobs(store: Any, world_id: str, scene_id: str) -> list[dict[str, Any]]:
    rows = store.conn.execute(
        """SELECT jobId, characterId, trigger, continueDepth, triggerMessageId, status
           FROM GenerationJob
           WHERE worldId = ? AND sceneId = ?
             AND status IN ('queued', 'running')""",
        (world_id, scene_id),
    ).fetchall()
    keys = ["jobId", "characterId", "trigger", "continueDepth", "triggerMessageId", "status"]
    return [dict(zip(keys, row, strict=True)) for row in rows]
