from __future__ import annotations

import json
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence


def _layout_hints(scene: dict) -> dict:
    return SqlitePersistence.json_loads(scene.get("layoutHintsJson"), {})


def build_spatial_graph(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    scenes = store.list_scenes(world_id)
    structures = store.list_structures(world_id)
    active = world.get("activeSceneId")
    nodes: list[dict] = []
    edges: list[dict] = []
    for scene in scenes:
        hints = _layout_hints(scene)
        present = json.loads(scene.get("presentJson") or "[]")
        pos = hints.get("mapPosition") or hints.get("layout")
        layout = pos or _auto_position(scene["sceneId"], scenes)
        node: dict[str, Any] = {
            "sceneId": scene["sceneId"],
            "locationName": scene["locationName"],
            "isActive": scene["sceneId"] == active,
            "presentCount": len(present),
            "layout": layout,
        }
        if hints.get("mapPosition"):
            node["mapPositionAuthor"] = hints["mapPosition"]
        for key in (
            "structureId",
            "mapZone",
            "mapShape",
            "mapSize",
            "levelIndex",
            "mapLevel",
            "levelLabel",
            "exitAnchor",
        ):
            if hints.get(key) is not None or scene.get(key) is not None:
                node[key] = hints.get(key) if hints.get(key) is not None else scene.get(key)
        if node.get("levelIndex") is None and scene.get("mapLevel") is not None:
            node["levelIndex"] = scene.get("mapLevel")
        nodes.append(node)
        src_struct = hints.get("structureId") or scene.get("structureId")
        for ex in json.loads(scene.get("exitsJson") or "[]"):
            tgt = ex.get("targetSceneId")
            tgt_scene = next((s for s in scenes if s["sceneId"] == tgt), None)
            tgt_hints = _layout_hints(tgt_scene) if tgt_scene else {}
            tgt_struct = tgt_hints.get("structureId") or (
                tgt_scene.get("structureId") if tgt_scene else None
            )
            crosses = bool(
                src_struct and tgt_struct and src_struct != tgt_struct
            ) or bool(src_struct and not tgt_struct)
            edge: dict[str, Any] = {
                "exitId": ex.get("exitId"),
                "sourceSceneId": scene["sceneId"],
                "targetSceneId": tgt,
                "label": ex.get("label"),
                "kind": ex.get("kind", "door"),
                "travelSteps": ex.get("travelSteps", 1),
                "direction": ex.get("direction"),
                "doorState": ex.get("doorState"),
                "exitAnchor": ex.get("exitAnchor"),
                "crossesStructure": ex.get("crossesStructure", crosses),
            }
            edges.append(edge)
    struct_out = []
    for s in structures:
        struct_out.append(
            {
                "structureId": s["structureId"],
                "displayName": s["displayName"],
                "kind": s.get("kind", "building"),
                "containsActiveScene": any(
                    n.get("structureId") == s["structureId"] and n.get("isActive") for n in nodes
                ),
                "boundary": json.loads(s["boundaryJson"]) if s.get("boundaryJson") else None,
            }
        )
    config = json.loads(world.get("configJson") or "{}")
    arch_style = config.get("architectureStyle", "diagram")
    if arch_style not in ("diagram", "blueprint", "minimal"):
        arch_style = "diagram"

    return {
        "activeSceneId": active,
        "nodes": nodes,
        "structures": struct_out,
        "edges": edges,
        "layout": {
            "coordinateSpace": "normalized-0-100",
            "algorithm": "layered-bfs-v1",
            "architectureStyle": arch_style,
        },
    }


def _auto_position(scene_id: str, scenes: list[dict]) -> dict[str, float]:
    idx = next((i for i, s in enumerate(scenes) if s["sceneId"] == scene_id), 0)
    n = max(len(scenes), 1)
    return {"x": 30 + (idx * 40) % 60, "y": 30 + (idx * 25) % 50}
