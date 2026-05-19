from __future__ import annotations

import json
import random
from typing import Any

from altrasia.debate_activity import get_active_banter, parse_activity
from altrasia.domain.presence import PERSONA_ID
from altrasia.orchestrator.addressing_policy import (
    scene_has_pending_addressing,
    scene_has_pending_cast_directed,
)
from altrasia.orchestrator.conversation_resolution import is_scene_conversation_unresolved
from altrasia.orchestrator.discussion_judgement import get_ensemble_discussion
from altrasia.orchestrator.idle_social_state import (
    scene_digest_window_active,
    scene_has_floor_hold,
    seconds_since_last_banter,
)
from altrasia.world_config import get_idle_social_config


def should_start_idle_banter(
    svc: Any,
    world_id: str,
    scene_id: str,
    *,
    orchestrator: Any | None = None,
) -> tuple[bool, str]:
    cfg = get_idle_social_config(svc.store, world_id)
    if not cfg.get("idleBanterEnabled", True):
        return False, "idle_banter_disabled"
    if not cfg.get("idleSocialEnabled", True):
        return False, "idle_social_disabled"
    from altrasia.orchestrator.idle_social_state import scene_operator_quiet_active

    if scene_operator_quiet_active(svc, world_id, scene_id):
        return False, "operator_quiet_period"
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return False, "scene_not_found"
    present = [
        c
        for c in json.loads(scene.get("presentJson") or "[]")
        if c not in (PERSONA_ID,)
    ]
    if len(present) < int(cfg.get("idleSocialMinCast", 2)):
        return False, "cast_too_small"
    if scene_has_pending_addressing(svc.store, world_id, scene_id):
        return False, "operator_directed_or_clarification_pending"
    if scene_has_pending_cast_directed(svc.store, world_id, scene_id):
        return False, "cast_directed_awaiting_reply"
    orch = orchestrator or getattr(svc, "orchestrator", None)
    if orch and scene_id in orch._scene_chain_active:
        return False, "continue_chain_active"
    unresolved, reason = is_scene_conversation_unresolved(svc.store, world_id, scene_id)
    if unresolved:
        return False, f"open_discussion_unresolved:{reason}"
    activity = parse_activity(scene)
    if activity and activity.get("kind") == "debate":
        return False, "debate_active"
    if get_ensemble_discussion(scene):
        return False, "ensemble_discussion_active"
    if get_active_banter(scene):
        return False, "banter_already_active"
    if scene_has_floor_hold(svc.store, scene_id):
        return False, "floor_hold_active"
    cooldown = float(cfg.get("idleSocialSessionCooldownSeconds", 180))
    if cooldown > 0:
        since = seconds_since_last_banter(scene)
        if since is not None and since < cooldown:
            return False, "session_cooldown"
    digest_sec = float(cfg.get("idleSocialDigestWindowSeconds", 300))
    if scene_digest_window_active(
        svc, world_id, scene_id, window_seconds=digest_sec
    ):
        return False, "digest_window_active"
    prob = float(cfg.get("idleSocialStartProbability", 0.4))
    if prob < 1.0 and random.random() >= prob:
        return False, "start_probability_skip"
    return True, "ok"
