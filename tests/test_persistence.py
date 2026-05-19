from pathlib import Path

import pytest

from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.persistence.sqlite_store import SqlitePersistence


@pytest.fixture
def store(tmp_path: Path) -> SqlitePersistence:
    db = SqlitePersistence(tmp_path / "test.db")
    db.migrate()
    yield db
    db.close()


def test_migration_creates_world_table(store: SqlitePersistence) -> None:
    cur = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='World'"
    )
    assert cur.fetchone() is not None


def test_load_demo_fixture(store: SqlitePersistence) -> None:
    fixtures = Path(__file__).resolve().parent / "fixtures"
    result = load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    assert result["worldId"] == "demo-spatial-v1"
    scenes = store.list_scenes(result["worldId"])
    assert len(scenes) == 20
    structures = store.list_structures(result["worldId"])
    assert len(structures) == 1
    world = store.get_world(result["worldId"])
    assert world["activeSceneId"] == "scene-lobby"
    assert world.get("worldMapJson")


def test_load_demo_fixture_twice_on_same_db(store: SqlitePersistence) -> None:
    """Reload replaces the prior demo world instead of accumulating copies."""
    fixtures = Path(__file__).resolve().parent / "fixtures"
    first = load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    store.update_world(first["worldId"], name="Mutated demo")
    second = load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    assert first["worldId"] == second["worldId"] == "demo-spatial-v1"
    assert second["activeSceneId"] == "scene-lobby"
    assert len(store.list_worlds()) == 1
    assert store.get_world(second["worldId"])["name"] == "Vertex Labs HQ — Demo"
    assert len(store.list_scenes(second["worldId"])) == 20
