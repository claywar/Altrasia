"""Pathfinding and travel over the spatial exit graph."""

from __future__ import annotations

import heapq
import json
from typing import Any

from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.world_geography import layout_design_mode

BLOCKED_DOOR_STATES = frozenset({"locked", "sealed", "blocked"})


def _edge_weight(edge: dict[str, Any]) -> float:
    steps = edge.get("travelSteps")
    if steps is None:
        return 1.0
    try:
        return max(1.0, float(steps))
    except (TypeError, ValueError):
        return 1.0


def _is_traversable(edge: dict[str, Any]) -> bool:
    state = (edge.get("doorState") or "").lower()
    return state not in BLOCKED_DOOR_STATES


def _adjacency(graph: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    adj: dict[str, list[dict[str, Any]]] = {}
    for edge in graph.get("edges") or []:
        if not _is_traversable(edge):
            continue
        src = edge.get("sourceSceneId")
        tgt = edge.get("targetSceneId")
        if not src or not tgt:
            continue
        adj.setdefault(src, []).append(edge)
        # Bidirectional travel along exits unless explicitly one-way (future flag)
        rev = {
            **edge,
            "sourceSceneId": tgt,
            "targetSceneId": src,
            "exitId": edge.get("exitId"),
            "_reversed": True,
        }
        adj.setdefault(tgt, []).append(rev)
    return adj


def reachable_from(graph: dict[str, Any], from_scene_id: str) -> set[str]:
    """All scene IDs reachable via traversable exits (BFS)."""
    if from_scene_id not in {n["sceneId"] for n in graph.get("nodes") or []}:
        return set()
    adj = _adjacency(graph)
    seen = {from_scene_id}
    queue = [from_scene_id]
    while queue:
        cur = queue.pop(0)
        for edge in adj.get(cur, []):
            nxt = edge["targetSceneId"]
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    seen.discard(from_scene_id)
    return seen


def plan_route(
    graph: dict[str, Any],
    from_scene_id: str,
    to_scene_id: str,
) -> dict[str, Any]:
    """Dijkstra shortest path weighted by travelSteps."""
    nodes = {n["sceneId"] for n in graph.get("nodes") or []}
    if from_scene_id not in nodes or to_scene_id not in nodes:
        return {
            "fromSceneId": from_scene_id,
            "toSceneId": to_scene_id,
            "reachable": False,
            "steps": [],
            "sceneIds": [],
            "totalTravelSteps": 0,
        }
    if from_scene_id == to_scene_id:
        return {
            "fromSceneId": from_scene_id,
            "toSceneId": to_scene_id,
            "reachable": True,
            "steps": [],
            "sceneIds": [from_scene_id],
            "totalTravelSteps": 0,
        }

    adj = _adjacency(graph)
    dist: dict[str, float] = {from_scene_id: 0.0}
    prev: dict[str, tuple[str, dict[str, Any]]] = {}
    heap: list[tuple[float, str]] = [(0.0, from_scene_id)]

    while heap:
        d, cur = heapq.heappop(heap)
        if d > dist.get(cur, float("inf")):
            continue
        if cur == to_scene_id:
            break
        for edge in adj.get(cur, []):
            nxt = edge["targetSceneId"]
            nd = d + _edge_weight(edge)
            if nd < dist.get(nxt, float("inf")):
                dist[nxt] = nd
                prev[nxt] = (cur, edge)
                heapq.heappush(heap, (nd, nxt))

    if to_scene_id not in dist:
        return {
            "fromSceneId": from_scene_id,
            "toSceneId": to_scene_id,
            "reachable": False,
            "steps": [],
            "sceneIds": [],
            "totalTravelSteps": 0,
        }

    path_scenes = [to_scene_id]
    path_steps: list[dict[str, Any]] = []
    cur = to_scene_id
    while cur != from_scene_id:
        p, edge = prev[cur]
        path_steps.append(
            {
                "exitId": edge.get("exitId"),
                "fromSceneId": p,
                "toSceneId": cur,
                "label": edge.get("label"),
                "kind": edge.get("kind"),
                "travelSteps": edge.get("travelSteps", 1),
            }
        )
        path_scenes.append(p)
        cur = p
    path_steps.reverse()
    path_scenes.reverse()

    return {
        "fromSceneId": from_scene_id,
        "toSceneId": to_scene_id,
        "reachable": True,
        "steps": path_steps,
        "sceneIds": path_scenes,
        "totalTravelSteps": int(dist[to_scene_id]),
    }


def are_adjacent(graph: dict[str, Any], a: str, b: str) -> bool:
    return b in reachable_from(graph, a)


def navigation_summary(
    store: SqlitePersistence,
    world_id: str,
    from_scene_id: str | None = None,
) -> dict[str, Any]:
    graph = build_spatial_graph(store, world_id)
    active = from_scene_id or graph.get("activeSceneId")
    strict = not layout_design_mode(store, world_id)
    reachable = reachable_from(graph, active) if active else set()
    return {
        "activeSceneId": active,
        "travelMode": "strict" if strict else "operator",
        "reachableSceneIds": sorted(reachable),
        "adjacentSceneIds": sorted(reachable),
    }


def execute_travel(
    store: SqlitePersistence,
    world_id: str,
    *,
    from_scene_id: str | None,
    to_scene_id: str,
    mode: str = "route",
) -> dict[str, Any]:
    """
    Move persona to to_scene_id.
    mode: route (teleport along validated path) | step (one hop) | jump (teleport, operator only when strict)
    """
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    graph = build_spatial_graph(store, world_id)
    active = from_scene_id or graph.get("activeSceneId")
    strict = not layout_design_mode(store, world_id)

    if mode == "jump":
        if strict:
            raise ValueError("jump not allowed when geography is locked")
        store.update_world(world_id, activeSceneId=to_scene_id)
        return {
            "activeSceneId": to_scene_id,
            "mode": "jump",
            "route": None,
            "stoppedAtSceneId": to_scene_id,
        }

    route = plan_route(graph, active, to_scene_id)
    if not route["reachable"]:
        raise ValueError("destination unreachable via exits")

    if mode == "step":
        scene_ids = route["sceneIds"]
        if len(scene_ids) <= 1:
            next_scene = to_scene_id
        elif len(scene_ids) == 2:
            next_scene = to_scene_id
        else:
            next_scene = scene_ids[1]
        store.update_world(world_id, activeSceneId=next_scene)
        return {
            "activeSceneId": next_scene,
            "mode": "step",
            "route": route,
            "stoppedAtSceneId": next_scene,
        }

    store.update_world(world_id, activeSceneId=to_scene_id)
    return {
        "activeSceneId": to_scene_id,
        "mode": "route",
        "route": route,
        "stoppedAtSceneId": to_scene_id,
    }
