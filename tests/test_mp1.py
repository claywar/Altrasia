from pathlib import Path

import pytest

from altrasia.memory.service import MemoryService
from altrasia.persistence.sqlite_store import SqlitePersistence


@pytest.fixture
def mem(tmp_path: Path) -> MemoryService:
    store = SqlitePersistence(tmp_path / "mp1.db")
    store.migrate()
    return MemoryService(store)


def test_mp1_mind_search_isolated(mem: MemoryService) -> None:
    mem.memory_store(pool="mind", owner_id="char-alice", locus_key="secret", value="Alice only fact")
    mem.memory_store(pool="mind", owner_id="char-bob", locus_key="secret", value="Bob only fact")
    alice_hits = mem.memory_search(pool="mind", owner_id="char-alice", query="only")
    bob_hits = mem.memory_search(pool="mind", owner_id="char-bob", query="only")
    assert all(h["ownerId"] == "char-alice" for h in alice_hits)
    assert all(h["ownerId"] == "char-bob" for h in bob_hits)
    assert not any("Bob" in h.get("value", "") for h in alice_hits)
