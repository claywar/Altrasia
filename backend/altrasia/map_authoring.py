from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.services import AppServices

ISO = lambda: datetime.now(timezone.utc).isoformat()

MAP_DRAFT_SYSTEM = (
    "You are a map layout assistant. Respond with ONLY a JSON object (no markdown) "
    'with keys: schemaVersion (1), scope ("mini"), nodes (array of '
    "{sceneId, mapPosition: {x, y}} with x,y 0-100), edges (optional array)."
)


def _parse_proposed(raw: str, graph: dict[str, Any]) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    nodes = data.get("nodes")
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
    return {
        "schemaVersion": 1,
        "scope": data.get("scope") or "mini",
        "nodes": nodes,
        "edges": data.get("edges") or [],
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
    if scope not in ("mini", "site", "stack"):
        raise ValueError("scope must be mini, site, or stack")
    world = svc.store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
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
        messages = [
            {"role": "system", "content": MAP_DRAFT_SYSTEM},
            {
                "role": "user",
                "content": f"Brief: {brief}\n\nCurrent scenes:\n"
                + json.dumps(
                    [
                        {"sceneId": n["sceneId"], "name": n["locationName"]}
                        for n in graph.get("nodes", [])
                    ]
                ),
            },
        ]
        result = await svc.llm.chat(messages, tools=None)
        content = result["choices"][0]["message"].get("content") or "{}"
        return _parse_proposed(content, graph)

    try:
        proposed = await svc.gpu_queue.run(draft_id, "map_layout_draft", _run)
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
    return _serialize_draft(row)  # type: ignore[arg-type]


def get_layout_draft(svc: AppServices, draft_id: str) -> dict[str, Any] | None:
    row = svc.store.get_layout_draft(draft_id)
    return _serialize_draft(row) if row else None


def _serialize_draft(row: dict[str, Any]) -> dict[str, Any]:
    proposed = None
    if row.get("proposedJson"):
        try:
            proposed = json.loads(row["proposedJson"])
        except json.JSONDecodeError:
            proposed = None
    return {
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
    world_id = row["worldId"]
    scenes = {s["sceneId"]: s for s in svc.store.list_scenes(world_id)}
    applied: list[str] = []
    conflicts: list[dict[str, str]] = []
    for node in proposed.get("nodes") or []:
        sid = node.get("sceneId")
        pos = node.get("mapPosition")
        if not sid or not pos:
            continue
        if sid not in scenes:
            conflicts.append({"sceneId": sid, "reason": "unknown scene"})
            continue
        scene = scenes[sid]
        hints = SqlitePersistence.json_loads(scene.get("layoutHintsJson"), {})
        hints["mapPosition"] = {"x": float(pos.get("x", 50)), "y": float(pos.get("y", 50))}
        svc.store.update_scene(
            sid,
            layoutHintsJson=json.dumps(hints),
            updatedAt=ISO(),
        )
        applied.append(sid)
    svc.store.update_layout_draft(
        draft_id, status="committed", updatedAt=ISO()
    )
    return {"layoutDraftId": draft_id, "applied": applied, "conflicts": conflicts}
