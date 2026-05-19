from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from altrasia.domain.presence import PERSONA_ID
from altrasia.orchestrator.single_speaker import trigger_invites_ensemble

ClaimStrength = Literal["high", "medium", "low"]
ClaimReason = Literal[
    "operator_question",
    "cast_attention",
    "cast_directed",
    "cast_room_question",
    "ensemble_cue",
    "explicit_floor",
]


@dataclass
class FloorClaim:
    claimed_by: str
    strength: ClaimStrength
    reason: ClaimReason
    awaiting_addressees: list[str] | None = None


_EXPLICIT_FLOOR = re.compile(
    r"\b(give me the floor|may i have the floor|hear me out|listen up|"
    r"everyone listen|hold on|one moment|need your attention|"
    r"need everyone'?s attention|can i ask the room)\b",
    re.I,
)

_ROOM_QUESTION = re.compile(
    r"\b(anyone|you all|everyone|the team|the room)\b",
    re.I,
)

_RELEASE = re.compile(r"\b(carry on|as you were|continue|go ahead)\b", re.I)


def detect_floor_release(text: str) -> bool:
    return bool(_RELEASE.search(text or ""))


def detect_floor_claim_from_addressing(
    addressing: Any,
    *,
    speaker_id: str,
) -> FloorClaim | None:
    from altrasia.orchestrator.speaker_selection import addressee_ids_for

    if addressing.mode == "directed":
        ids = addressee_ids_for(addressing)
        if ids:
            return FloorClaim(
                claimed_by=speaker_id,
                strength="high",
                reason="cast_directed",
                awaiting_addressees=list(ids),
            )
    if addressing.mode == "ensemble":
        return FloorClaim(
            claimed_by=speaker_id,
            strength="high",
            reason="ensemble_cue",
        )
    return None


def detect_floor_claim(
    text: str,
    *,
    role: str,
    speaker_id: str,
    cast: list[str] | None = None,
    chars: dict[str, dict] | None = None,
    addressing: Any | None = None,
) -> FloorClaim | None:
    t = (text or "").strip()
    if not t:
        return None
    if addressing is not None and role != "operator":
        directed = detect_floor_claim_from_addressing(addressing, speaker_id=speaker_id)
        if directed:
            return directed
    if trigger_invites_ensemble(t):
        return FloorClaim(
            claimed_by=speaker_id,
            strength="high",
            reason="ensemble_cue",
        )
    if _EXPLICIT_FLOOR.search(t):
        return FloorClaim(
            claimed_by=speaker_id,
            strength="high",
            reason="explicit_floor" if role != "operator" else "cast_attention",
        )
    if role == "operator" and "?" in t:
        return FloorClaim(
            claimed_by=PERSONA_ID,
            strength="medium",
            reason="operator_question",
        )
    if role != "operator" and "?" in t and _ROOM_QUESTION.search(t):
        return FloorClaim(
            claimed_by=speaker_id,
            strength="medium",
            reason="cast_room_question",
        )
    return None


def apply_floor_claim(
    svc: Any,
    scene_id: str,
    claim: FloorClaim,
    *,
    source_message_id: str | None = None,
) -> None:
    from altrasia.banter_runner import clear_banter_and_cancel_jobs
    from altrasia.orchestrator.idle_social_state import set_floor_hold
    from altrasia.world_config import get_idle_social_config

    scene = svc.store.get_scene(scene_id)
    if not scene:
        return
    world_id = scene["worldId"]
    cfg = get_idle_social_config(svc.store, world_id)
    if not cfg.get("floorHoldEnabled", True):
        return
    clear_banter_and_cancel_jobs(svc, scene_id)
    ttl = int(cfg.get("floorHoldClearAfterSeconds", 90))
    set_floor_hold(
        svc.store,
        scene_id,
        claimed_by=claim.claimed_by,
        reason=claim.reason,
        source_message_id=source_message_id,
        awaiting_addressees=claim.awaiting_addressees,
        clear_after_seconds=ttl,
    )
