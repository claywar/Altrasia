from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.map_apply import apply_layout_json
from altrasia.map_layout_invariants import check_invariants
from altrasia.map_layout_validator import check_readiness, strip_unknown_keys, validate_layout
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.services import AppServices

ISO = lambda: datetime.now(timezone.utc).isoformat()

MAP_DRAFT_SYSTEM = (
    "You are a map layout assistant for Altrasia. Respond with ONLY a JSON object (no markdown). "
    "schemaVersion: 1. Include scope, nodes or scenes (sceneId, mapPosition {x,y} 0-100), "
    "optional structures (structureId, displayName, boundary with vertices), edges (exitId, "
    "sourceSceneId, targetSceneId, kind, travelSteps, direction, exitAnchor). "
    "referenceDiagramId: mini_envelope | mini_shapes | site_overlay | level_stack. "
    "scope site: MUST include worldMap.structurePlacements (>=2 structures). "
    "scope stack: scenes MUST include mapLevel/levelIndex and planPosition {x,y} aligned for vertical exits. "
    "No reasoning fields."
)


def _parse_proposed(raw: str, graph: dict[str, Any], scope: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data = strip_unknown_keys(data)
    nodes = data.get("nodes") or data.get("scenes")
    if not isinstance(nodes, list) or not nodes:
        nodes = []
        for i, n in enumerate(graph.get("nodes") or []):
            layout = n.get("layout") or {"x": 20 + (i % 4) * 20, "y": 30 + (i // 4) * 25}
            nodes.append(
                {
                    "sceneId": n["sceneId"],
                    "mapPosition": {"x": layout.get("x", 50), "y": layout.get("y", 50)},
                }
            )
        data["nodes"] = nodes
    return {
        "schemaVersion": 1,
        "scope": data.get("scope") or scope,
        "nodes": nodes,
        "scenes": data.get("scenes") or nodes,
        "structures": data.get("structures") or [],
        "edges": data.get("edges") or [],
        "worldMap": data.get("worldMap"),
        "referenceDiagramId": data.get("referenceDiagramId"),
    }


def _discard_active_drafts(store: Any, world_id: str, except_id: str | None = None) -> None:
    cur = store.conn.execute(
        "SELECT layoutDraftId FROM LayoutDraft WHERE worldId = ? AND status IN ('drafting', 'ready')",
        (world_id,),
    )
    for row in cur.fetchall():
        did = row[0]
        if except_id and did == except_id:
            continue
        store.update_layout_draft(did, status="discarded", updatedAt=ISO())


async def create_layout_draft(
    svc: AppServices, world_id: str, brief: str, scope: str = "mini"
) -> dict[str, Any]:
    if scope not in ("mini", "site", "stack", "floor"):
        raise ValueError("scope must be mini, site, stack, or floor")
    world = svc.store.get_world(world_id)
    if not world:
        raise ValueError("world not found")

    readiness = check_readiness(svc.store, world_id, scope, brief)
    if not readiness.get("ready"):
        raise ValueError(
            json.dumps(
                {
                    "code": readiness.get("code", "insufficient_framing"),
                    "missing": readiness.get("missing", []),
                }
            )
        )

    graph = build_spatial_graph(svc.store, world_id)
    draft_id = str(uuid.uuid4())
    now = ISO()
    svc.store.insert_layout_draft(
        {
            "layoutDraftId": draft_id,
            "worldId": world_id,
            "operatorBrief": brief,
            "scope": scope,
            "proposedJson": None,
            "status": "drafting",
            "errorMessage": None,
            "revision": 0,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    _discard_active_drafts(svc.store, world_id, except_id=draft_id)

    async def _run() -> dict[str, Any]:
        scene_ctx = [
            {
                "sceneId": n["sceneId"],
                "locationName": n["locationName"],
                "structureId": n.get("structureId"),
            }
            for n in graph.get("nodes", [])
        ]
        messages = [
            {"role": "system", "content": MAP_DRAFT_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Brief: {brief}\nScope: {scope}\n"
                    f"Scenes:\n{json.dumps(scene_ctx)}\n"
                    f"Structures:\n{json.dumps(graph.get('structures') or [])}"
                ),
            },
        ]
        result = await svc.llm.chat(messages, tools=None)
        content = result["choices"][0]["message"].get("content") or "{}"
        return _parse_proposed(content, graph, scope)

    try:
        proposed = await svc.gpu_queue.run(draft_id, "map_layout_draft", _run)
        proposed = strip_unknown_keys(proposed)
        validation = validate_layout(proposed, svc.store, world_id)
        svc.store.update_layout_draft(
            draft_id,
            proposedJson=json.dumps(proposed),
            status="ready",
            updatedAt=ISO(),
        )
    except Exception as exc:
        svc.store.update_layout_draft(
            draft_id,
            status="failed",
            errorMessage=str(exc)[:500],
            updatedAt=ISO(),
        )
        raise
    row = svc.store.get_layout_draft(draft_id)
    validation = validate_layout(proposed, svc.store, world_id)
    return _serialize_draft(row, validation=validation)  # type: ignore[arg-type]


async def repair_layout_draft(
    svc: AppServices, draft_id: str, feedback: str, mode: str = "describe-change"
) -> dict[str, Any]:
    row = svc.store.get_layout_draft(draft_id)
    if not row:
        raise ValueError("draft not found")
    if row["status"] not in ("ready", "failed"):
        raise ValueError(f"cannot repair draft in status {row['status']}")
    try:
        current = json.loads(row["proposedJson"] or "{}")
    except json.JSONDecodeError:
        current = {}
    world_id = row["worldId"]
    scope = row["scope"]
    graph = build_spatial_graph(svc.store, world_id)
    revision = int(row.get("revision") or 0) + 1

    async def _run() -> dict[str, Any]:
        prompt = (
            f"Mode: {mode}\nFeedback: {feedback}\n"
            f"Current layout:\n{json.dumps(current)}\n"
            "Apply only the requested changes. Return full updated JSON."
        )
        messages = [
            {"role": "system", "content": MAP_DRAFT_SYSTEM},
            {"role": "user", "content": prompt},
        ]
        result = await svc.llm.chat(messages, tools=None)
        content = result["choices"][0]["message"].get("content") or "{}"
        return _parse_proposed(content, graph, scope)

    proposed = await svc.gpu_queue.run(draft_id, "map_layout_repair", _run)
    proposed = strip_unknown_keys(proposed)
    validation = validate_layout(proposed, svc.store, world_id)
    svc.store.update_layout_draft(
        draft_id,
        proposedJson=json.dumps(proposed),
        status="ready",
        revision=revision,
        updatedAt=ISO(),
    )
    updated = svc.store.get_layout_draft(draft_id)
    return _serialize_draft(updated)  # type: ignore[arg-type]


def update_draft_proposed(svc: AppServices, draft_id: str, proposed: dict[str, Any]) -> dict[str, Any]:
    row = svc.store.get_layout_draft(draft_id)
    if not row:
        raise ValueError("draft not found")
    if row["status"] != "ready":
        raise ValueError(f"cannot edit draft in status {row['status']}")
    proposed = strip_unknown_keys(proposed)
    validation = validate_layout(proposed, svc.store, row["worldId"])
    svc.store.update_layout_draft(
        draft_id,
        proposedJson=json.dumps(proposed),
        updatedAt=ISO(),
    )
    out = _serialize_draft(svc.store.get_layout_draft(draft_id))  # type: ignore[arg-type]
    out["validation"] = validation
    return out


def get_layout_draft(svc: AppServices, draft_id: str) -> dict[str, Any] | None:
    row = svc.store.get_layout_draft(draft_id)
    return _serialize_draft(row) if row else None


def _serialize_draft(
    row: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proposed = None
    if row.get("proposedJson"):
        try:
            proposed = json.loads(row["proposedJson"])
        except json.JSONDecodeError:
            proposed = None
    out: dict[str, Any] = {
        "layoutDraftId": row["layoutDraftId"],
        "worldId": row["worldId"],
        "operatorBrief": row["operatorBrief"],
        "scope": row["scope"],
        "proposed": proposed,
        "status": row["status"],
        "errorMessage": row.get("errorMessage"),
        "revision": int(row.get("revision") or 0),
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
    }
    if validation is not None:
        out["validation"] = validation
    return out


def commit_layout_draft(svc: AppServices, draft_id: str) -> dict[str, Any]:
    row = svc.store.get_layout_draft(draft_id)
    if not row:
        raise ValueError("draft not found")
    if row["status"] != "ready":
        raise ValueError(f"cannot commit draft in status {row['status']}")
    try:
        proposed = json.loads(row["proposedJson"] or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("invalid proposedJson") from exc
    validation = validate_layout(proposed, svc.store, row["worldId"])
    if not validation["valid"]:
        raise ValueError(json.dumps({"validationErrors": validation["errors"]}))
    inv = check_invariants(proposed, svc.store, row["worldId"])
    if not inv["valid"]:
        raise ValueError(json.dumps({"invariantErrors": inv["errors"]}))
    result = apply_layout_json(svc.store, row["worldId"], proposed)
    build_spatial_graph(svc.store, row["worldId"])
    svc.store.update_layout_draft(draft_id, status="committed", updatedAt=ISO())
    return {
        "layoutDraftId": draft_id,
        "applied": result["applied"],
        "conflicts": result["conflicts"],
        "scope": row["scope"],
    }


def patch_layout_safe(
    svc: AppServices, world_id: str, patch: dict[str, Any]
) -> dict[str, Any]:
    """Apply safe single-scene position or exit hint without full draft."""
    applied: list[str] = []
    conflicts: list[dict[str, str]] = []
    scenes = {s["sceneId"]: s for s in svc.store.list_scenes(world_id)}

    for node in patch.get("nodes") or []:
        sid = node.get("sceneId")
        pos = node.get("mapPosition")
        if not sid or not pos or sid not in scenes:
            conflicts.append({"sceneId": sid or "?", "reason": "unknown or missing"})
            continue
        scene = scenes[sid]
        hints = SqlitePersistence.json_loads(scene.get("layoutHintsJson"), {})
        hints["mapPosition"] = {"x": float(pos.get("x", 50)), "y": float(pos.get("y", 50))}
        svc.store.update_scene(sid, layoutHintsJson=json.dumps(hints), updatedAt=ISO())
        applied.append(sid)

    if patch.get("edges"):
        apply_layout_json(svc.store, world_id, {"edges": patch["edges"]})

    return {"applied": applied, "conflicts": conflicts, "autoApplied": len(conflicts) == 0}
