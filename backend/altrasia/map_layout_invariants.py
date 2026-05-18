from __future__ import annotations

import json
from typing import Any

VERTICAL_KINDS = {"stairs", "ladder", "elevator", "shaft"}
SCOPE_REF_IDS = {
    "mini": {"mini_envelope", "mini_shapes"},
    "site": {"site_overlay"},
    "stack": {"level_stack"},
    "floor": {"mini_envelope", "mini_shapes"},
}
MIN_SITE_SEPARATION = 8.0


def _hints(scene: dict) -> dict:
    from altrasia.persistence.sqlite_store import SqlitePersistence

    return SqlitePersistence.json_loads(scene.get("layoutHintsJson"), {})


def _pos(item: dict) -> dict[str, float] | None:
    raw = item.get("planPosition") or item.get("layout") or item.get("mapPosition")
    if not raw:
        return None
    if "planX" in raw or "planY" in raw:
        return {
            "x": float(raw.get("planX", raw.get("x", 50))),
            "y": float(raw.get("planY", raw.get("y", 50))),
        }
    if raw.get("x") is not None and raw.get("y") is not None:
        return {"x": float(raw["x"]), "y": float(raw["y"])}
    return None


def _point_in_boundary(x: float, y: float, boundary: dict | None) -> bool:
    if not boundary:
        return True
    if boundary.get("shape") == "circle":
        cx = boundary.get("cx", 0)
        cy = boundary.get("cy", 0)
        r = boundary.get("r", 0)
        return (x - cx) ** 2 + (y - cy) ** 2 <= (r + 2) ** 2
    verts = boundary.get("vertices")
    if verts and len(verts) >= 3:
        xs = [v["x"] for v in verts]
        ys = [v["y"] for v in verts]
        return min(xs) - 2 <= x <= max(xs) + 2 and min(ys) - 2 <= y <= max(ys) + 2
    if boundary.get("x") is not None and boundary.get("w") is not None:
        return (
            boundary["x"] - 2 <= x <= boundary["x"] + boundary["w"] + 2
            and boundary.get("y", 0) - 2 <= y <= boundary.get("y", 0) + boundary.get("h", 0) + 2
        )
    return True


def check_invariants(
    layout: dict[str, Any],
    store: Any,
    world_id: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    scope = layout.get("scope") or "mini"
    ref = layout.get("referenceDiagramId")
    allowed_refs = SCOPE_REF_IDS.get(scope, set())
    if ref and ref not in allowed_refs:
        warnings.append(f"referenceDiagramId {ref} unusual for scope {scope}")

    scenes_db = {s["sceneId"]: s for s in store.list_scenes(world_id)}
    structs_db = {s["structureId"]: s for s in store.list_structures(world_id)}
    scene_items = layout.get("scenes") or layout.get("nodes") or []

    if scope in ("mini", "site"):
        by_struct: dict[str, list[dict]] = {}
        for item in scene_items:
            sid = item.get("structureId")
            if not sid and item.get("sceneId") in scenes_db:
                sid = _hints(scenes_db[item["sceneId"]]).get("structureId")
            if not sid:
                continue
            by_struct.setdefault(sid, []).append(item)
        for st_id, items in by_struct.items():
            boundary = None
            for st in layout.get("structures") or []:
                if st.get("structureId") == st_id:
                    boundary = st.get("boundary")
                    break
            if not boundary and st_id in structs_db:
                raw = structs_db[st_id].get("boundaryJson")
                boundary = json.loads(raw) if raw else None
            for item in items:
                pos = _pos(item)
                if pos and not _point_in_boundary(pos["x"], pos["y"], boundary):
                    errors.append(
                        f"{item.get('sceneId')}: position outside structure {st_id} envelope"
                    )

    if scope == "site":
        wm = layout.get("worldMap") or {}
        placements = wm.get("structurePlacements") or []
        origins: list[tuple[str, float, float]] = []
        for pl in placements:
            oid = pl.get("structureId")
            origin = pl.get("origin") or {}
            if oid and origin.get("x") is not None:
                origins.append((oid, float(origin["x"]), float(origin["y"])))
        if len(origins) < 2:
            errors.append("site scope: need >= 2 structurePlacements in worldMap")
        for i, a in enumerate(origins):
            for b in origins[i + 1 :]:
                dist = ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
                if dist < MIN_SITE_SEPARATION:
                    errors.append(
                        f"structures {a[0]} and {b[0]} placements too close ({dist:.1f})"
                    )

    if scope == "stack":
        vertical_positions: dict[str, dict[str, float]] = {}
        for edge in layout.get("edges") or []:
            kind = (edge.get("kind") or "").lower()
            if kind not in VERTICAL_KINDS:
                continue
            src = edge.get("sourceSceneId")
            tgt = edge.get("targetSceneId")
            for sid in (src, tgt):
                if not sid:
                    continue
                item = next((x for x in scene_items if x.get("sceneId") == sid), None)
                if item:
                    pos = _pos(item)
                    if pos:
                        vertical_positions[sid] = pos
        pos_values = list(vertical_positions.values())
        if len(pos_values) >= 2:
            xs = [p["x"] for p in pos_values]
            if max(xs) - min(xs) > 3:
                warnings.append("vertical link scenes should share planPosition.x")

        for edge in layout.get("edges") or []:
            kind = (edge.get("kind") or "").lower()
            if kind not in VERTICAL_KINDS:
                continue
            src = edge.get("sourceSceneId")
            tgt = edge.get("targetSceneId")
            if not src or not tgt:
                continue
            src_item = next((x for x in scene_items if x.get("sceneId") == src), None)
            tgt_item = next((x for x in scene_items if x.get("sceneId") == tgt), None)
            if not src_item or not tgt_item:
                continue
            sl = src_item.get("levelIndex", src_item.get("mapLevel", 0))
            tl = tgt_item.get("levelIndex", tgt_item.get("mapLevel", 0))
            if sl == tl:
                errors.append(f"vertical edge {edge.get('exitId')} connects same level")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "referenceDiagramId": ref,
    }
