from __future__ import annotations

from typing import Any

from altrasia.debate_activity import activity_current_speaker, parse_activity


async def enqueue_conversation_turn(svc: Any, scene_id: str) -> dict[str, Any] | None:
    """Schedule the current conversation speaker (AO-22-1)."""
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return None
    activity = parse_activity(scene)
    if not activity or activity.get("kind") != "conversation":
        return None
    speaker = activity_current_speaker(activity)
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
        trigger="conversation_turn",
    )
