"""3D position derivation and layout upgrade (v1 → v2)."""

from __future__ import annotations

from typing import Any

LEVEL_SPACING = 3.0
COORD_SCALE = 0.02  # map 0-100 → roughly -1..1 world units


def norm_xy(pos: dict[str, Any] | None) -> tuple[float, float]:
    if not pos:
        return 0.0, 0.0
    if "planX" in pos or "planY" in pos:
        x = float(pos.get("planX", pos.get("x", 50)))
        y = float(pos.get("planY", pos.get("y", 50)))
    else:
        x = float(pos.get("x", 50))
        y = float(pos.get("y", 50))
    return (x - 50) * COORD_SCALE, (y - 50) * COORD_SCALE


def level_z(node: dict[str, Any]) -> float:
    lvl = node.get("levelIndex")
    if lvl is None:
        lvl = node.get("mapLevel", 0)
    try:
        return float(lvl) * LEVEL_SPACING
    except (TypeError, ValueError):
        return 0.0


def derive_position3d(node: dict[str, Any], hints: dict[str, Any] | None = None) -> dict[str, float]:
    """Build position3d from hints or node layout fields."""
    hints = hints or {}
    if hints.get("position3d"):
        p = hints["position3d"]
        return {
            "x": float(p.get("x", 0)),
            "y": float(p.get("y", 0)),
            "z": float(p.get("z", 0)),
        }
    pos = hints.get("planPosition") or hints.get("mapPosition") or node.get("planPosition") or node.get("layout")
    x, y = norm_xy(pos)
    z = level_z({**node, **hints})
    return {"x": x, "y": y, "z": z}


def upgrade_layout_v1(layout: dict[str, Any]) -> dict[str, Any]:
    """Ensure layout has schemaVersion 2 and position3d on scenes."""
    out = dict(layout)
    ver = out.get("schemaVersion", 1)
    if ver < 2:
        out["schemaVersion"] = 2
    items = out.get("scenes") or out.get("nodes") or []
    upgraded: list[dict[str, Any]] = []
    for item in items:
        it = dict(item)
        if not it.get("position3d"):
            it["position3d"] = derive_position3d(it, it)
        upgraded.append(it)
    if out.get("scenes") is not None:
        out["scenes"] = upgraded
    else:
        out["nodes"] = upgraded
    return out


def collect_reference_points(
    layout: dict[str, Any] | None,
    world_map: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    if layout:
        for rp in layout.get("referencePoints") or []:
            if rp.get("id") and rp.get("position3d"):
                points.append(rp)
    if world_map:
        for rp in world_map.get("referencePoints") or []:
            if rp.get("id") and rp.get("position3d"):
                points.append(rp)
    return points
