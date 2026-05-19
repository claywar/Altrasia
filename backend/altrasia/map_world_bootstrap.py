"""LLM world bootstrap: create scenes + layout from a description."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.position3d import upgrade_layout_v1
from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.map_apply import apply_layout_json
from altrasia.map_layout_invariants import check_invariants
from altrasia.map_layout_validator import strip_unknown_keys, validate_layout
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.services import AppServices
from altrasia.world_geography import create_scene

ISO = lambda: datetime.now(timezone.utc).isoformat()

WORLD_BOOTSTRAP_SYSTEM = (
    "You are a world bootstrap assistant for Altrasia. Respond with ONLY JSON (no markdown). "
    "schemaVersion: 2. Given a place description, propose newScenes[] with tempId, locationName, "
    "locationDescription, connectFromSceneId (existing sceneId), exitLabel, reverseExitLabel. "
    "Include layout object (schemaVersion 2, scope mini) with scenes using tempId as sceneId, "
    "mapPosition 0-100, position3d, structures/edges as needed. Do not invent reasoning fields."
)


def _parse_bootstrap(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("bootstrap must be a JSON object")
    return data


def _remap_layout_ids(layout: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    layout = upgrade_layout_v1(dict(layout))
    items = layout.get("scenes") or layout.get("nodes") or []
    for item in items:
        sid = item.get("sceneId")
        if sid in id_map:
            item["sceneId"] = id_map[sid]
    for edge in layout.get("edges") or []:
        for key in ("sourceSceneId", "targetSceneId"):
            if edge.get(key) in id_map:
                edge[key] = id_map[edge[key]]
    for rp in layout.get("referencePoints") or []:
        if rp.get("sceneId") in id_map:
            rp["sceneId"] = id_map[rp["sceneId"]]
    return layout


async def create_world_bootstrap_draft(
    svc: AppServices,
    world_id: str,
    description: str,
    *,
    connect_from_scene_id: str | None = None,
) -> dict[str, Any]:
    world = svc.store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    if not description.strip():
        raise ValueError("description required")

    graph = build_spatial_graph(svc.store, world_id)
    active = connect_from_scene_id or graph.get("activeSceneId")
    draft_id = str(uuid.uuid4())
    now = ISO()
    svc.store.insert_layout_draft(
        {
            "layoutDraftId": draft_id,
            "worldId": world_id,
            "operatorBrief": description,
            "scope": "bootstrap",
            "proposedJson": None,
            "status": "drafting",
            "errorMessage": None,
            "revision": 0,
            "createdAt": now,
            "updatedAt": now,
        }
    )

    async def _run() -> dict[str, Any]:
        messages = [
            {"role": "system", "content": WORLD_BOOTSTRAP_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Description: {description}\n"
                    f"Connect new locations from sceneId: {active}\n"
                    f"Existing scenes: {json.dumps([n['sceneId'] for n in graph.get('nodes', [])])}"
                ),
            },
        ]
        result = await svc.llm.chat(messages, tools=None)
        content = result["choices"][0]["message"].get("content") or "{}"
        return _parse_bootstrap(content)

    proposed = await svc.gpu_queue.run(draft_id, "map_world_bootstrap", _run)
    svc.store.update_layout_draft(
        draft_id,
        proposedJson=json.dumps(proposed),
        status="ready",
        updatedAt=ISO(),
    )
    row = svc.store.get_layout_draft(draft_id)
    from altrasia.map_authoring import _serialize_draft

    return _serialize_draft(row)  # type: ignore[arg-type]


def apply_world_bootstrap(
    store: SqlitePersistence,
    world_id: str,
    bootstrap: dict[str, Any],
) -> dict[str, Any]:
    """Create scenes from bootstrap.newScenes then apply layout."""
    world = store.get_world(world_id)
    default_connect = world.get("activeSceneId") if world else None
    id_map: dict[str, str] = {}
    created: list[str] = []

    for spec in bootstrap.get("newScenes") or []:
        temp_id = spec.get("tempId") or spec.get("sceneId")
        if not temp_id:
            continue
        connect = spec.get("connectFromSceneId") or default_connect
        if connect and connect in id_map:
            connect = id_map[connect]
        scene = create_scene(
            store,
            world_id,
            location_name=spec.get("locationName") or "New place",
            location_description=spec.get("locationDescription") or "",
            connect_from_scene_id=connect,
            exit_label=spec.get("exitLabel") or "Enter",
            reverse_exit_label=spec.get("reverseExitLabel"),
        )
        id_map[temp_id] = scene["sceneId"]
        created.append(scene["sceneId"])

    layout = bootstrap.get("layout") or {}
    layout = _remap_layout_ids(layout, id_map)
    layout = strip_unknown_keys(layout)
    validation = validate_layout(layout, store, world_id)
    if not validation["valid"]:
        raise ValueError(json.dumps({"validationErrors": validation["errors"]}))
    inv = check_invariants(layout, store, world_id)
    if not inv["valid"]:
        raise ValueError(json.dumps({"invariantErrors": inv["errors"]}))
    result = apply_layout_json(store, world_id, layout)
    return {"createdScenes": created, "idMap": id_map, **result}


def commit_world_bootstrap_draft(svc: AppServices, draft_id: str) -> dict[str, Any]:
    row = svc.store.get_layout_draft(draft_id)
    if not row:
        raise ValueError("draft not found")
    if row["status"] != "ready":
        raise ValueError(f"cannot commit draft in status {row['status']}")
    bootstrap = json.loads(row["proposedJson"] or "{}")
    result = apply_world_bootstrap(svc.store, row["worldId"], bootstrap)
    svc.store.update_layout_draft(draft_id, status="committed", updatedAt=ISO())
    build_spatial_graph(svc.store, row["worldId"])
    return {"layoutDraftId": draft_id, **result}
