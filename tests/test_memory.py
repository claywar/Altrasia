import json
from pathlib import Path

import pytest

from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.memory.service import MemoryService
from altrasia.memory.strip_reasoning import strip_reasoning
from altrasia.persistence.sqlite_store import SqlitePersistence


@pytest.fixture
def mem(tmp_path: Path) -> MemoryService:
    store = SqlitePersistence(tmp_path / "t.db")
    store.migrate()
    return MemoryService(store)


def test_strip_reasoning_think_tags() -> None:
    raw = "Before \u003cthink\u003ehidden\u003c/think\u003e after"
    out = strip_reasoning(raw)
    assert "hidden" not in out
    assert "Before" in out and "after" in out
    assert "hidden" not in out


def test_memory_store_rejects_empty(mem: MemoryService) -> None:
    with pytest.raises(ValueError):
        mem.memory_store(pool="mind", owner_id="c1", locus_key="k", value="   ")


def test_diary_fanout(mem: MemoryService, tmp_path: Path) -> None:
    store = mem.store
    fixtures = Path(__file__).resolve().parent / "fixtures"
    load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    mem.capture_diary_fanout(
        scene_id="scene-lobby",
        present_ids=["char-jordan-reyes", "char-sofia-mendez"],
        snippet="Alice: Hello\nBob: Hi",
        message_ids=["m1", "m2"],
    )
    a = store.list_diary("char-jordan-reyes")
    b = store.list_diary("char-sofia-mendez")
    assert len(a) == 1
    assert len(b) == 1
    assert a[0]["dedupeKey"] == b[0]["dedupeKey"]
