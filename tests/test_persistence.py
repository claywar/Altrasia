from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.fixtures.loader import load_fixture_by_id, reset_fixture_world
from altrasia.memory.service import MemoryService
from altrasia.persistence.sqlite_store import SqlitePersistence


@pytest.fixture
def store(tmp_path: Path) -> SqlitePersistence:
    db = SqlitePersistence(tmp_path / "test.db")
    db.migrate()
    yield db
    db.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    db = SqlitePersistence(tmp_path / "idempotent.db")
    db.migrate()
    db.migrate()
    row = db.fetchone(
        "SELECT name FROM SchemaMigration ORDER BY name DESC LIMIT 1"
    )
    assert row is not None
    assert db._has_column("Scene", "socialStateJson")
    db.close()


def test_migration_creates_world_table(store: SqlitePersistence) -> None:
    row = store.fetchone(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='World'"
    )
    assert row is not None


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


def test_load_demo_fixture_after_orphan_structure(store: SqlitePersistence) -> None:
    """Recover when a prior failed load left fixture structure ids without a world."""
    import json

    fixtures = Path(__file__).resolve().parent / "fixtures"
    raw = json.loads(
        (fixtures / "demo-world" / "demo-spatial-v1.json").read_text(encoding="utf-8")
    )
    now = "2026-01-01T00:00:00+00:00"
    wid = raw["worldId"]
    store.insert_world(
        {
            "worldId": wid,
            "name": "stale",
            "activeSceneId": raw["activeSceneId"],
            "defaultModelProfile": "qwen3.6-35b-a3b",
            "configJson": "{}",
            "worldMapJson": None,
            "eventSeq": 0,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    st = raw["structures"][0]
    store.insert_structure(
        {
            "structureId": st["structureId"],
            "worldId": wid,
            "displayName": st["displayName"],
            "kind": st.get("kind", "building"),
            "boundaryJson": None,
            "updatedAt": now,
        }
    )
    # Simulate partial failed load when FK enforcement was off: world row gone, structure remains.
    store.conn.execute("PRAGMA foreign_keys = OFF")
    store.run("DELETE FROM World WHERE worldId = ?", (wid,))
    store.commit()
    store.conn.execute("PRAGMA foreign_keys = ON")
    assert store.get_world(wid) is None
    assert store.fetchone(
        "SELECT 1 FROM Structure WHERE structureId = ?", (st["structureId"],)
    )

    result = load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    assert result["worldId"] == wid
    assert len(store.list_structures(wid)) == 1


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


def test_reset_demo_clears_chat_and_runtime_memory(store: SqlitePersistence) -> None:
    """In-world reset drops transcript, diary, and loci added after fixture load."""
    fixtures = Path(__file__).resolve().parent / "fixtures"
    meta = load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    wid = meta["worldId"]
    mem = MemoryService(store)
    mem.capture_diary_fanout(
        scene_id="scene-lobby",
        present_ids=["char-jordan-reyes"],
        snippet="Operator: test line",
        message_ids=["m-test"],
    )
    mem.memory_store(
        pool="mind",
        owner_id="char-jordan-reyes",
        locus_key="test_extra",
        value="should vanish on reset",
    )
    now = "2026-01-01T00:00:00+00:00"
    store.insert_message(
        {
            "messageId": "msg-reset-test",
            "worldId": wid,
            "channelKind": "scene",
            "sceneId": "scene-lobby",
            "role": "user",
            "characterId": None,
            "outputText": "hello from test",
            "reasoning": None,
            "streamStatus": "final",
            "generationJobId": None,
            "metaJson": "{}",
            "createdAt": now,
        }
    )
    assert store.list_messages(wid, scene_id="scene-lobby")
    assert store.list_diary("char-jordan-reyes")

    reset_fixture_world(store, fixtures, wid)

    assert store.list_messages(wid, scene_id="scene-lobby") == []
    assert store.list_diary("char-jordan-reyes") == []
    rows = store.fetchall(
        "SELECT locusKey, value FROM Locus WHERE pool = 'mind' AND ownerId = ?",
        ("char-jordan-reyes",),
    )
    loci = {r["locusKey"]: r["value"] for r in rows}
    assert "test_extra" not in loci
    assert loci.get("role", "").startswith("Chief Technology Officer")


def test_concurrent_spatial_graph_reads(store: SqlitePersistence) -> None:
    """Regression: shared sqlite conn must not raise InterfaceError under thread pool load."""
    fixtures = Path(__file__).resolve().parent / "fixtures"
    load_fixture_by_id(store, fixtures, "demo-spatial-v1")

    def _read() -> int:
        graph = build_spatial_graph(store, "demo-spatial-v1")
        return len(graph["nodes"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(lambda _: _read(), range(24)))
    assert all(c == 20 for c in counts)
