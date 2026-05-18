from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BRIEF_MIN_CHARS = 12


def _schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "schemas"
        / "map-layout-v1.schema.json"
    )


def check_readiness(
    store: Any,
    world_id: str,
    scope: str,
    brief: str | None = None,
) -> dict[str, Any]:
    """Return { ready: bool, code?, missing? } before LLM call."""
    scenes = store.list_scenes(world_id)
    structures = store.list_structures(world_id)
    missing: list[str] = []

    brief_ok = bool(brief and len(brief.strip()) >= BRIEF_MIN_CHARS)
    named = [s for s in scenes if (s.get("locationName") or "").strip()]

    if scope == "mini":
        if len(named) >= 2 or brief_ok:
            return {"ready": True}
        missing.append("at least 2 scenes with locationName or a brief >= 12 chars")
    elif scope == "site":
        if len(structures) >= 2 or brief_ok:
            return {"ready": True}
        missing.append("at least 2 structures or a descriptive brief")
    elif scope in ("stack", "floor"):
        multi_level = any(
            (_hints(s).get("levelIndex") is not None or s.get("levelIndex") is not None)
            for s in scenes
        )
        if multi_level or brief_ok:
            return {"ready": True}
        missing.append("scenes with mapLevel/levelIndex or a descriptive brief")
    else:
        missing.append(f"unknown scope {scope}")

    return {
        "ready": False,
        "code": "insufficient_framing",
        "missing": missing,
    }


def _hints(scene: dict) -> dict:
    from altrasia.persistence.sqlite_store import SqlitePersistence

    return SqlitePersistence.json_loads(scene.get("layoutHintsJson"), {})


def validate_layout(
    layout: dict[str, Any],
    store: Any,
    world_id: str,
) -> dict[str, Any]:
    """Validate layout JSON; return { valid, errors[], warnings[] }."""
    errors: list[str] = []
    warnings: list[str] = []

    if layout.get("schemaVersion") not in (1, "1", None):
        errors.append("schemaVersion must be 1")
    scope = layout.get("scope")
    if scope not in ("mini", "site", "stack", "floor", None):
        errors.append(f"invalid scope: {scope}")

    scenes_db = {s["sceneId"]: s for s in store.list_scenes(world_id)}
    structs_db = {s["structureId"]: s for s in store.list_structures(world_id)}

    scene_items = layout.get("scenes") or layout.get("nodes") or []
    for item in scene_items:
        sid = item.get("sceneId")
        if not sid:
            errors.append("scene entry missing sceneId")
            continue
        if sid not in scenes_db:
            errors.append(f"unknown sceneId: {sid}")
        pos = item.get("layout") or item.get("mapPosition")
        if pos:
            for k in ("x", "y"):
                v = pos.get(k)
                if v is not None and not (0 <= float(v) <= 100):
                    errors.append(f"{sid}: {k} out of 0-100 range")

    for st in layout.get("structures") or []:
        sid = st.get("structureId")
        if sid and sid not in structs_db:
            warnings.append(f"structure {sid} not in DB (will be created on commit if allowed)")

    seen_exits: set[str] = set()
    for edge in layout.get("edges") or []:
        eid = edge.get("exitId")
        if eid:
            if eid in seen_exits:
                errors.append(f"duplicate exitId: {eid}")
            seen_exits.add(eid)
        tgt = edge.get("targetSceneId")
        if tgt and tgt not in scenes_db:
            errors.append(f"edge target unknown scene: {tgt}")

    for key in ("reasoning", "think", "analysis"):
        if key in layout:
            errors.append(f"forbidden field: {key}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def strip_unknown_keys(layout: dict[str, Any]) -> dict[str, Any]:
    allowed_top = {
        "schemaVersion",
        "scope",
        "architectureStyle",
        "referenceDiagramId",
        "structures",
        "scenes",
        "nodes",
        "edges",
        "worldMap",
    }
    out = {k: v for k, v in layout.items() if k in allowed_top}
    return out
