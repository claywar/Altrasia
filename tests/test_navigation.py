"""Navigation pathfinding and travel API."""

from __future__ import annotations

from pathlib import Path

import pytest

from altrasia.domain.navigation import (
    are_adjacent,
    execute_travel,
    plan_route,
    reachable_from,
)
from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.world_geography import lock_geography


@pytest.fixture
def demo_world(tmp_path):
    store = SqlitePersistence(str(tmp_path / "nav.db"))
    store.migrate()
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    world = load_fixture_by_id(store, fixtures_dir, "demo-spatial-v1")
    return store, world["worldId"]


def _graph(store, world_id):
    return build_spatial_graph(store, world_id)


def test_reachable_from_hall(demo_world):
    store, wid = demo_world
    g = _graph(store, wid)
    active = g["activeSceneId"]
    reach = reachable_from(g, active)
    assert isinstance(reach, set)
    assert len(reach) >= 1


def test_plan_route_same_scene(demo_world):
    store, wid = demo_world
    g = _graph(store, wid)
    active = g["activeSceneId"]
    route = plan_route(g, active, active)
    assert route["reachable"] is True
    assert route["totalTravelSteps"] == 0


def test_step_travel_advances_one_hop(demo_world):
    store, wid = demo_world
    g = _graph(store, wid)
    start = g["activeSceneId"]
    reach = reachable_from(g, start)
    if len(reach) < 2:
        pytest.skip("need distant reachable scene")
  # pick farthest by route length
    target = next(iter(reach))
    route = plan_route(g, start, target)
    if not route["reachable"] or len(route["sceneIds"]) < 3:
        pytest.skip("need multi-hop route")
    result = execute_travel(
        store, wid, from_scene_id=start, to_scene_id=target, mode="step"
    )
    assert result["mode"] == "step"
    assert result["activeSceneId"] == route["sceneIds"][1]
    assert result["activeSceneId"] != target


def test_step_travel_adjacent(demo_world):
    store, wid = demo_world
    g = _graph(store, wid)
    start = g["activeSceneId"]
    reach = reachable_from(g, start)
    if not reach:
        pytest.skip("no reachable")
    target = next(iter(reach))
    if not are_adjacent(g, start, target):
        pytest.skip("need adjacent pair")
    result = execute_travel(
        store, wid, from_scene_id=start, to_scene_id=target, mode="step"
    )
    assert result["activeSceneId"] == target


def test_plan_route_multi_hop(demo_world):
    store, wid = demo_world
    g = _graph(store, wid)
    nodes = {n["sceneId"] for n in g["nodes"]}
    if len(nodes) < 3:
        pytest.skip("need multi-scene demo")
    start = g["activeSceneId"]
    # pick a node not directly reachable in one hop if possible
    reach = reachable_from(g, start)
    two_hop = None
    for mid in reach:
        for far in reachable_from(g, mid):
            if far not in reach and far != start:
                two_hop = far
                break
        if two_hop:
            break
    if not two_hop:
        pytest.skip("no two-hop destination in fixture")
    route = plan_route(g, start, two_hop)
    assert route["reachable"] is True
    assert len(route["steps"]) >= 2


def test_execute_travel_route(demo_world):
    store, wid = demo_world
    g = _graph(store, wid)
    active = g["activeSceneId"]
    reach = reachable_from(g, active)
    if not reach:
        pytest.skip("no adjacent scenes")
    target = next(iter(reach))
    result = execute_travel(store, wid, from_scene_id=active, to_scene_id=target, mode="route")
    assert result["activeSceneId"] == target
    assert result["mode"] == "route"


def test_jump_blocked_when_locked(demo_world):
    store, wid = demo_world
    lock_geography(store, wid)
    g = _graph(store, wid)
    nodes = [n["sceneId"] for n in g["nodes"]]
    if len(nodes) < 2:
        pytest.skip("need 2 scenes")
    a, b = nodes[0], nodes[1]
    if not are_adjacent(g, a, b):
        with pytest.raises(ValueError, match="jump not allowed"):
            execute_travel(store, wid, from_scene_id=a, to_scene_id=b, mode="jump")
