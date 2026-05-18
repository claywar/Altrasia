from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def apply_layout_json(store: SqlitePersistence, world_id: str, layout: dict[str, Any]) -> dict[str, Any]:
    """Apply validated layout to scenes, structures, exits, worldMapJson."""
    scenes_db = {s["sceneId"]: s for s in store.list_scenes(world_id)}
    applied_scenes: list[str] = []
    conflicts: list[dict[str, str]] = []

    scene_items = layout.get("scenes") or layout.get("nodes") or []
    for item in scene_items:
        sid = item.get("sceneId")
        if not sid or sid not in scenes_db:
            if sid:
                conflicts.append({"sceneId": sid, "reason": "unknown scene"})
            continue
        scene = scenes_db[sid]
        hints = SqlitePersistence.json_loads(scene.get("layoutHintsJson"), {})
        pos = item.get("layout") or item.get("mapPosition")
        if pos:
            hints["mapPosition"] = {
                "x": float(pos.get("x", 50)),
                "y": float(pos.get("y", 50)),
            }
        for key in (
            "structureId",
            "mapZone",
            "mapShape",
            "mapSize",
            "levelIndex",
            "mapLevel",
            "levelLabel",
            "exitAnchor",
            "planPosition",
        ):
            if item.get(key) is not None:
                hints[key] = item[key]
        store.update_scene(
            sid,
            layoutHintsJson=json.dumps(hints),
            updatedAt=ISO(),
        )
        applied_scenes.append(sid)

    for st in layout.get("structures") or []:
        sid = st.get("structureId")
        if not sid:
            continue
        boundary = st.get("boundary")
        existing = next(
            (s for s in store.list_structures(world_id) if s["structureId"] == sid),
            None,
        )
        payload = {
            "structureId": sid,
            "worldId": world_id,
            "displayName": st.get("displayName") or sid,
            "kind": st.get("kind", "building"),
            "boundaryJson": json.dumps(boundary) if boundary else None,
            "updatedAt": ISO(),
        }
        if existing:
            store.conn.execute(
                """UPDATE Structure SET displayName = ?, kind = ?, boundaryJson = ?, updatedAt = ?
                   WHERE worldId = ? AND structureId = ?""",
                (
                    payload["displayName"],
                    payload["kind"],
                    payload["boundaryJson"],
                    payload["updatedAt"],
                    world_id,
                    sid,
                ),
            )
            store.conn.commit()
        else:
            store.insert_structure(payload)

    for edge in layout.get("edges") or []:
        src = edge.get("sourceSceneId")
        eid = edge.get("exitId")
        if not src or not eid or src not in scenes_db:
            continue
        scene = scenes_db[src]
        exits = json.loads(scene.get("exitsJson") or "[]")
        updated = False
        for ex in exits:
            if ex.get("exitId") == eid:
                for key in (
                    "travelSteps",
                    "direction",
                    "doorState",
                    "exitAnchor",
                    "crossesStructure",
                    "label",
                ):
                    if edge.get(key) is not None:
                        ex[key] = edge[key]
                updated = True
                break
        if updated:
            store.update_scene(
                src,
                exitsJson=json.dumps(exits),
                updatedAt=ISO(),
            )

    world_map = layout.get("worldMap")
    if world_map:
        store.update_world(world_id, worldMapJson=json.dumps(world_map), updatedAt=ISO())

    return {"applied": applied_scenes, "conflicts": conflicts}
