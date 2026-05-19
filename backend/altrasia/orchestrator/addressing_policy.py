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


def prior_operator_message(
    store: Any,
    world_id: str,
    scene_id: str,
    *,
    before_message_id: str | None = None,
) -> dict[str, Any] | None:
    found_current = before_message_id is None
    for m in reversed(store.list_messages(world_id, scene_id=scene_id)):
        if m.get("role") == "assistant":
            continue
        text = (m.get("outputText") or "").strip()
        if not text:
            continue
        if not found_current:
            if m.get("messageId") == before_message_id:
                found_current = True
            continue
        return m
    return None


def pending_directed_followup_for_reply(
    store: Any,
    world_id: str,
    scene_id: str,
    current_message_id: str,
) -> tuple[AddressingResult, str] | None:
    """Prior operator line was directed and not all named addressees have spoken."""
    prior = prior_operator_message(
        store, world_id, scene_id, before_message_id=current_message_id
    )
    if not prior:
        return None
    prior_id = prior.get("messageId")
    if not prior_id:
        return None
    addressing = addressing_from_message_row(prior)
    if not addressing or addressing.mode != "directed":
        return None
    ids = addressee_ids_for(addressing)
    spoke = cast_spoke_on_trigger(store, world_id, scene_id, prior_id)
    missing = [cid for cid in ids if cid not in spoke]
    if not missing and not addressing.unresolved_name_tokens:
        return None
    return addressing, prior_id


def pending_clarification_for_reply(
    store: Any,
    world_id: str,
    scene_id: str,
    current_message_id: str,
) -> AddressingResult | None:
    """Prior operator line was clarification; current line may resolve it."""
    prior = prior_operator_message(
        store, world_id, scene_id, before_message_id=current_message_id
    )
    if not prior:
        return None
    addressing = addressing_from_message_row(prior)
    if addressing and addressing.mode == "clarification":
        return addressing
    return None


def latest_operator_addressing(
    store: Any, world_id: str, scene_id: str
) -> tuple[AddressingResult | None, str | None]:
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


def clarifier_replied_to_trigger(
    store: Any,
    world_id: str,
    scene_id: str,
    operator_message_id: str,
    clarifier_id: str | None,
) -> bool:
    if not clarifier_id:
        return False
    return primary_replied_to_trigger(
        store, world_id, scene_id, operator_message_id, clarifier_id
    )


def scene_has_pending_addressing(
    store: Any, world_id: str, scene_id: str
) -> bool:
    """Directed addressee unanswered or clarification awaiting operator follow-up."""
    addressing, op_id = latest_operator_addressing(store, world_id, scene_id)
    if not addressing or not op_id:
        return False
    if addressing.mode == "clarification":
        if clarifier_replied_to_trigger(
            store, world_id, scene_id, op_id, addressing.clarifier_id
        ):
            return True
        return True
    if addressing.mode != "directed":
        return False
    ids = addressee_ids_for(addressing)
    if not ids:
        return False
    return any(
        not primary_replied_to_trigger(store, world_id, scene_id, op_id, aid)
        for aid in ids
    )


def scene_has_unanswered_directed(
    store: Any, world_id: str, scene_id: str
) -> bool:
    return scene_has_pending_addressing(store, world_id, scene_id)


def may_character_generate(
    svc: Any,
    job: dict[str, Any],
    cfg: dict[str, Any],
) -> tuple[bool, str]:
    """
    Generic gate: every scene generation job must pass this before speaking.
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

    if not addressing:
        return True, "no_addressing"

    if addressing.mode == "clarification":
        if trigger == "idle_timer":
            return False, "clarification_blocks_idle"
        clarifier = addressing.clarifier_id
        if not clarifier:
            return False, "clarification_no_clarifier"
        if character_id != clarifier:
            return False, "not_clarifier"
        if depth > 0:
            return False, "clarification_no_continue"
        spoke = cast_spoke_on_trigger(svc.store, world_id, scene_id, op_id)
        if character_id in spoke:
            return False, "clarifier_already_spoke"
        return True, "clarification"

    if addressing.mode != "directed":
        return True, "not_directed"

    addressees = addressee_ids_for(addressing)
    if not addressees:
        return True, "directed_no_primary"

    if trigger == "idle_timer":
        return False, "directed_blocks_idle"

    spoke = cast_spoke_on_trigger(svc.store, world_id, scene_id, op_id)
    if character_id in spoke:
        try:
            rationale = json.loads(job.get("selectionRationaleJson") or "{}")
            if rationale.get("generation_recovery"):
                return True, "generation_recovery"
        except json.JSONDecodeError:
            pass
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
