"""MAP-GEN-ACC: layout validator + structural invariants."""

from __future__ import annotations

import json
from pathlib import Path

from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.map_layout_invariants import check_invariants
from altrasia.map_layout_validator import validate_layout
from altrasia.persistence.sqlite_store import SqlitePersistence

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "map-layouts"
WORLD_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_layout(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_demo_site_layout_passes_invariants(tmp_path: Path) -> None:
    store = SqlitePersistence(tmp_path / "inv.db")
    store.migrate()
    load_fixture_by_id(store, WORLD_FIXTURES, "demo-spatial-v1")
    layout = _load_layout("site-valid.json")
    result = validate_layout(layout, store, "demo-spatial-v1")
    assert result["valid"], result["errors"]
    inv = check_invariants(layout, store, "demo-spatial-v1")
    assert inv["valid"], inv["errors"]


def test_site_without_world_map_fails(tmp_path: Path) -> None:
    store = SqlitePersistence(tmp_path / "inv2.db")
    store.migrate()
    load_fixture_by_id(store, WORLD_FIXTURES, "demo-spatial-v1")
    layout = _load_layout("site-broken.json")
    result = validate_layout(layout, store, "demo-spatial-v1")
    assert not result["valid"]
    assert any("structurePlacements" in e for e in result["errors"])


def test_mini_valid_fixture(tmp_path: Path) -> None:
    store = SqlitePersistence(tmp_path / "inv3.db")
    store.migrate()
    load_fixture_by_id(store, WORLD_FIXTURES, "demo-spatial-v1")
    layout = _load_layout("mini-valid.json")
    result = validate_layout(layout, store, "demo-spatial-v1")
    assert result["valid"], result["errors"]


def test_overlap_same_floor_fails(tmp_path: Path) -> None:
    store = SqlitePersistence(tmp_path / "overlap.db")
    store.migrate()
    load_fixture_by_id(store, WORLD_FIXTURES, "demo-spatial-v1")
    layout = _load_layout("mini-valid.json")
    scenes = layout.get("scenes") or layout.get("nodes") or []
    if len(scenes) < 2:
        pytest.skip("need scenes")
    a, b = scenes[0], scenes[1]
    pos = a.get("layout") or a.get("mapPosition") or {"x": 50, "y": 50}
    b["layout"] = {"x": pos.get("x", 50), "y": pos.get("y", 50)}
    b["structureId"] = a.get("structureId")
    b["mapLevel"] = a.get("mapLevel", a.get("levelIndex", 0))
    b["levelIndex"] = a.get("levelIndex", a.get("mapLevel", 0))
    inv = check_invariants(layout, store, "demo-spatial-v1")
    assert not inv["valid"]
    assert any("overlap" in e for e in inv["errors"])


def test_stack_same_level_vertical_edge_fails(tmp_path: Path) -> None:
    store = SqlitePersistence(tmp_path / "inv4.db")
    store.migrate()
    load_fixture_by_id(store, WORLD_FIXTURES, "demo-spatial-v1")
    layout = _load_layout("stack-valid.json")
    layout["nodes"][1]["levelIndex"] = 0
    inv = check_invariants(layout, store, "demo-spatial-v1")
    assert not inv["valid"]
    assert any("same level" in e for e in inv["errors"])
