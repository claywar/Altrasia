from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def parse_world_config(world: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(world.get("configJson") or "{}")
    except json.JSONDecodeError:
        return {}


def layout_design_mode(store: SqlitePersistence, world_id: str) -> bool:
    world = store.get_world(world_id)
    if not world:
        return False
    cfg = parse_world_config(world)
    return bool(cfg.get("layoutDesignMode", False))


def geography_status(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    cfg = parse_world_config(world)
    scenes = store.list_scenes(world_id)
    return {
        "worldId": world_id,
        "layoutDesignMode": bool(cfg.get("layoutDesignMode", False)),
        "geographyLockedAt": cfg.get("geographyLockedAt"),
        "sceneCount": len(scenes),
    }


def lock_geography(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    cfg = parse_world_config(world)
    cfg["layoutDesignMode"] = False
    cfg["geographyLockedAt"] = cfg.get("geographyLockedAt") or ISO()
    store.update_world(world_id, configJson=json.dumps(cfg), updatedAt=ISO())
    return geography_status(store, world_id)


def lock_geography_on_first_play(store: SqlitePersistence, world_id: str) -> None:
    """MAP-AUTH-LOCK-1: first persona message ends layout design mode."""
    world = store.get_world(world_id)
    if not world:
        return
    cfg = parse_world_config(world)
    if not cfg.get("layoutDesignMode"):
        return
    cfg["layoutDesignMode"] = False
    cfg["geographyLockedAt"] = ISO()
    store.update_world(world_id, configJson=json.dumps(cfg), updatedAt=ISO())


def _load_exits(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return json.loads(scene.get("exitsJson") or "[]")


def _save_exits(store: SqlitePersistence, scene_id: str, exits: list[dict[str, Any]]) -> None:
    store.update_scene(scene_id, exitsJson=json.dumps(exits), updatedAt=ISO())


def add_exit(
    store: SqlitePersistence,
    source_scene_id: str,
    target_scene_id: str,
    label: str,
) -> str:
    scene = store.get_scene(source_scene_id)
    if not scene:
        raise ValueError("source scene not found")
    exits = _load_exits(scene)
    exit_id = f"exit-{uuid.uuid4().hex[:10]}"
    exits.append(
        {
            "exitId": exit_id,
            "targetSceneId": target_scene_id,
            "label": label,
            "kind": "door",
            "travelSteps": 1,
        }
    )
    _save_exits(store, source_scene_id, exits)
    return exit_id


def create_scene(
    store: SqlitePersistence,
    world_id: str,
    *,
    location_name: str,
    location_description: str = "",
    connect_from_scene_id: str | None = None,
    exit_label: str = "Door",
    reverse_exit_label: str | None = None,
) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    scenes = store.list_scenes(world_id)
    scene_id = str(uuid.uuid4())
    now = ISO()
    n = len(scenes)
    x = 15 + (n % 4) * 22
    y = 25 + (n // 4) * 18
    store.insert_scene(
        {
            "sceneId": scene_id,
            "worldId": world_id,
            "structureId": None,
            "mapLevel": 0,
            "levelLabel": None,
            "planPositionJson": None,
            "mapArtifactJson": None,
            "locationName": location_name,
            "locationDescription": location_description,
            "presentJson": "[]",
            "fixturesJson": "{}",
            "exitsJson": "[]",
            "activityJson": None,
            "roundRobinIndex": 0,
            "layoutHintsJson": json.dumps({"mapPosition": {"x": x, "y": y}}),
            "updatedAt": now,
        }
    )
    if connect_from_scene_id:
        from_scene = store.get_scene(connect_from_scene_id)
        if not from_scene or from_scene["worldId"] != world_id:
            raise ValueError("connectFromSceneId invalid")
        add_exit(store, connect_from_scene_id, scene_id, exit_label)
        back = reverse_exit_label
        if back is None:
            back = f"To {from_scene['locationName']}"
        add_exit(store, scene_id, connect_from_scene_id, back)
    return store.get_scene(scene_id)  # type: ignore[return-value]
