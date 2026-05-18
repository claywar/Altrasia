from __future__ import annotations

from typing import Any

from altrasia.debate_activity import debate_current_speaker, parse_activity


async def enqueue_debate_turn(svc: Any, scene_id: str) -> dict[str, Any] | None:
    """Schedule the current debate speaker (DEB-2)."""
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return None
    activity = parse_activity(scene)
    if not activity:
        return None
    speaker = debate_current_speaker(activity)
    if not speaker:
        return None
    if scene_id in svc.orchestrator._scene_chain_active:
        return None
    if svc.gpu_queue.busy:
        return None
    if svc.store.list_queued_jobs(scene["worldId"]):
        return None
    return await svc.orchestrator.enqueue_generation(
        world_id=scene["worldId"],
        scene_id=scene_id,
        character_id=speaker,
        trigger="debate_turn",
    )


async def tick_debate_scenes(svc: Any, world_id: str) -> dict[str, Any] | None:
    """Idle poll: one debate turn when scene has active debate and GPU idle."""
    if world_id in svc.paused_worlds:
        return None
    for scene in svc.store.list_scenes(world_id):
        activity = parse_activity(scene)
        if not activity:
            continue
        return await enqueue_debate_turn(svc, scene["sceneId"])
    return None
