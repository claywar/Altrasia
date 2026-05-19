from __future__ import annotations

from typing import Any


async def presence_join(
    services: Any,
    *,
    world_id: str,
    scene_id: str,
    character_id: str,
    action: str = "join",
) -> None:
    """LP-1 join via shared service path (API, tools, narrative presence)."""
    from altrasia.commission_notify import refresh_commissions

    services.presence.join(scene_id, character_id)
    services.event_bus.emit(
        services.store,
        world_id,
        "presence.changed",
        {"sceneId": scene_id, "characterId": character_id, "action": action},
    )
    await refresh_commissions(services, world_id)


async def presence_summon_batch(
    services: Any,
    *,
    world_id: str,
    target_scene_id: str,
    character_ids: list[str],
    summoner_id: str | None = None,
    source_scene_id: str | None = None,
    source: str = "tool",
    related_message_id: str | None = None,
    announce: bool = True,
) -> dict[str, Any]:
    """Batch summon to target scene."""
    for cid in character_ids:
        await presence_join(
            services,
            world_id=world_id,
            scene_id=target_scene_id,
            character_id=cid,
            action="summon",
        )
    if announce:
        from altrasia.domain.presence_announce import announce_summon

        await announce_summon(
            services,
            world_id=world_id,
            target_scene_id=target_scene_id,
            summoned_ids=character_ids,
            summoner_id=summoner_id,
            source_scene_id=source_scene_id,
            source=source,  # type: ignore[arg-type]
            related_message_id=related_message_id,
        )
    return {"ok": True, "targetSceneId": target_scene_id, "characterIds": character_ids}
