from __future__ import annotations

import json
from typing import Any

from altrasia.domain.position3d import collect_reference_points, derive_position3d
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
        plan_pos = hints.get("planPosition") or hints.get("mapPosition") or layout
        if plan_pos:
            node["planPosition"] = plan_pos
        if scene.get("locationDescription"):
            node["locationDescription"] = scene["locationDescription"]
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
        node["position3d"] = derive_position3d(node, hints)
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

    world_map = None
    if world.get("worldMapJson"):
        world_map = json.loads(world["worldMapJson"])

    vertical_kinds = {"stairs", "ladder", "elevator", "shaft"}
    vertical_edges: list[dict[str, Any]] = []
    node_by_id = {n["sceneId"]: n for n in nodes}
    for edge in edges:
        kind = (edge.get("kind") or "").lower()
        if kind not in vertical_kinds:
            continue
        src = node_by_id.get(edge["sourceSceneId"])
        tgt = node_by_id.get(edge["targetSceneId"])
        if not src or not tgt:
            continue
        src_lvl = src.get("levelIndex") if src.get("levelIndex") is not None else src.get("mapLevel", 0)
        tgt_lvl = tgt.get("levelIndex") if tgt.get("levelIndex") is not None else tgt.get("mapLevel", 0)
        if src_lvl == tgt_lvl:
            continue
        vertical_edges.append(
            {
                "exitId": edge["exitId"],
                "sourceSceneId": edge["sourceSceneId"],
                "targetSceneId": edge["targetSceneId"],
                "kind": edge.get("kind"),
                "sourceLevel": src_lvl,
                "targetLevel": tgt_lvl,
                "structureId": src.get("structureId") or tgt.get("structureId"),
            }
        )

    layout_status = _layout_status(nodes)
    has_authored_3d = any(
        _layout_hints(s).get("position3d")
        for s in scenes
    )
    layout_3d_status = "complete" if has_authored_3d else "derived"
    ref_points = collect_reference_points(None, world_map)

    return {
        "activeSceneId": active,
        "nodes": nodes,
        "structures": struct_out,
        "edges": edges,
        "verticalEdges": vertical_edges,
        "worldMap": world_map,
        "referencePoints": ref_points,
        "siteLayoutApplied": bool(world_map and world_map.get("structurePlacements")),
        "layoutStatus": layout_status,
        "layout3dStatus": layout_3d_status,
        "layout": {
            "coordinateSpace": "normalized-0-100",
            "algorithm": "layered-bfs-v1",
            "architectureStyle": arch_style,
        },
    }


def _layout_status(nodes: list[dict]) -> str:
    if len(nodes) < 2:
        return "missing"
    authored = sum(1 for n in nodes if n.get("mapPositionAuthor"))
    if authored >= max(2, len(nodes) - 1):
        return "complete"
    if authored >= 1:
        return "partial"
    default_only = all(
        n.get("layout", {}).get("x") == 30 + (i * 40) % 60
        and n.get("layout", {}).get("y") == 30 + (i * 25) % 50
        for i, n in enumerate(nodes)
        if not n.get("mapPositionAuthor")
    )
    if default_only and authored == 0:
        return "missing"
    return "partial"


def _auto_position(scene_id: str, scenes: list[dict]) -> dict[str, float]:
    idx = next((i for i, s in enumerate(scenes) if s["sceneId"] == scene_id), 0)
    n = max(len(scenes), 1)
    return {"x": 30 + (idx * 40) % 60, "y": 30 + (idx * 25) % 50}
