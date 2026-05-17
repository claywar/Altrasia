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
    assert result["worldId"]
    scenes = store.list_scenes(result["worldId"])
    assert len(scenes) == 2
    world = store.get_world(result["worldId"])
    assert world["activeSceneId"] == "scene-hall"
