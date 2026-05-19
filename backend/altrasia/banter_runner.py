from __future__ import annotations

import json
from typing import Any

from altrasia.debate_activity import (
    activity_current_speaker,
    banter_exhausted,
    clear_banter,
    get_active_banter,
    parse_activity,
    start_banter,
    topic_exhausted_recent_lines,
)
from altrasia.domain.presence import PERSONA_ID
from altrasia.orchestrator.banter_gates import should_start_idle_banter
from altrasia.orchestrator.idle_social_state import append_banter_session
from altrasia.orchestrator.social_selection import pick_idle_dyad
from altrasia.world_config import get_idle_social_config


def clear_banter_and_cancel_jobs(svc: Any, scene_id: str) -> None:
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return
    activity = get_active_banter(scene) if scene else None
    if activity:
        cfg = get_idle_social_config(svc.store, scene["worldId"])
        append_banter_session(
            svc.store,
            scene_id,
            session_id=str(activity.get("sessionId") or ""),
            participants=list(activity.get("participants") or []),
            line_count=int(activity.get("lineCount") or 0),
            window=int(cfg.get("idleSocialVarietyWindow", 8)),
        )
    clear_banter(svc.store, scene_id)
    world_id = scene["worldId"]
    for job in svc.store.list_queued_jobs(world_id):
        if job.get("sceneId") != scene_id:
            continue
        trig = job.get("trigger")
        if trig in ("banter_turn", "idle_continue"):
            svc.orchestrator.cancel_job(job["jobId"])


async def enqueue_banter_turn(
    svc: Any,
    scene_id: str,
    *,
    character_id: str | None = None,
    continue_depth: int = 0,
    rationale: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return None
    activity = get_active_banter(scene)
    if not activity:
        return None
    speaker = character_id or activity_current_speaker(activity)
    if not speaker:
        return None
    present = json.loads(scene.get("presentJson") or "[]")
    if speaker not in present:
        return None
    if scene_id in svc.orchestrator._scene_chain_active and continue_depth == 0:
        pass
    orch = svc.orchestrator
    if continue_depth == 0:
        orch._scene_chain_active.add(scene_id)
    trig = "idle_continue" if continue_depth > 0 else "banter_turn"
    rat = dict(rationale or {})
    rat.setdefault("banterSessionId", activity.get("sessionId"))
    rat.setdefault("participants", activity.get("participants"))
    rat["socialIdle"] = True
    rat["continueDepth"] = continue_depth
    return await orch.enqueue_generation(
        world_id=scene["worldId"],
        scene_id=scene_id,
        character_id=speaker,
        trigger=trig,
        continue_depth=continue_depth,
        selection_rationale_json=json.dumps(rat),
    )


async def try_start_banter(svc: Any, world_id: str, scene_id: str) -> dict[str, Any] | None:
    ok, _ = should_start_idle_banter(
        svc, world_id, scene_id, orchestrator=svc.orchestrator
    )
    if not ok:
        return None
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return None
    cast = [
        c for c in json.loads(scene.get("presentJson") or "[]") if c not in (PERSONA_ID,)
    ]
    pick = pick_idle_dyad(svc, world_id=world_id, scene=scene, cast=cast)
    if not pick:
        return None
    cfg = get_idle_social_config(svc.store, world_id)
    max_depth = int(cfg.get("idleSocialMaxDepth", 3))
    start_banter(
        svc.store,
        scene_id,
        speaking_order=pick.speaking_order,
        session_id=pick.session_id,
        turns_remaining=max_depth,
    )
    return await enqueue_banter_turn(
        svc,
        scene_id,
        character_id=pick.speaking_order[0],
        continue_depth=0,
        rationale=pick.rationale,
    )


async def tick_banter_scenes(svc: Any, world_id: str) -> dict[str, Any] | None:
    if world_id in svc.paused_worlds:
        return None
    if svc.gpu_queue.busy:
        return None
    if svc.store.list_queued_jobs(world_id):
        return None
    cfg = get_idle_social_config(svc.store, world_id)
    if not cfg.get("idleBanterEnabled", True):
        for scene in svc.store.list_scenes(world_id):
            if get_active_banter(scene):
                clear_banter_and_cancel_jobs(svc, scene["sceneId"])
        return None
    for scene in svc.store.list_scenes(world_id):
        scene_id = scene["sceneId"]
        if scene_id in svc.orchestrator._scene_chain_active:
            activity = get_active_banter(scene)
            if not activity:
                continue
        activity = get_active_banter(scene)
        if activity:
            from altrasia.orchestrator.idle_social_state import scene_operator_quiet_active

            if scene_operator_quiet_active(svc, world_id, scene_id):
                continue
            speaker = activity_current_speaker(activity)
            if speaker:
                return await enqueue_banter_turn(svc, scene_id, character_id=speaker)
            continue
        ok, _ = should_start_idle_banter(
            svc, world_id, scene_id, orchestrator=svc.orchestrator
        )
        if ok:
            return await try_start_banter(svc, world_id, scene_id)
    return None


def finish_banter_session_if_done(
    svc: Any,
    scene_id: str,
    activity: dict[str, Any],
    *,
    recent_line_texts: list[str] | None = None,
) -> bool:
    if not banter_exhausted(activity) and not (
        recent_line_texts and topic_exhausted_recent_lines(recent_line_texts)
    ):
        return False
    clear_banter_and_cancel_jobs(svc, scene_id)
    svc.orchestrator._scene_chain_active.discard(scene_id)
    return True
