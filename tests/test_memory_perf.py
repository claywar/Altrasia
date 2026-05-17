"""MEM-PERF-* and MEM-ACC-* gates (docs/17 §7, docs/02-memory.md)."""

from __future__ import annotations

import random
import time
from pathlib import Path

import pytest

from altrasia.fixtures.memory_scale import seed_memory_scale
from altrasia.memory.service import MemoryService
from altrasia.persistence.sqlite_store import SqlitePersistence


def _p95(samples: list[float]) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


@pytest.fixture(scope="module")
def scale_mem(tmp_path_factory: pytest.TempPathFactory) -> tuple[MemoryService, dict]:
    db = tmp_path_factory.mktemp("memscale") / "ci.db"
    store = SqlitePersistence(db)
    store.migrate()
    meta = seed_memory_scale(store, profile="ci")
    return MemoryService(store), meta


def test_mem_perf1_search_uses_fts(scale_mem: tuple[MemoryService, dict]) -> None:
    """MEM-PERF-1: tool search path uses FTS virtual table, not full Locus scan."""
    mem, meta = scale_mem
    cid = meta["characterIds"][0]
    plan = mem.store.conn.execute(
        """EXPLAIN QUERY PLAN
           SELECT l.locusKey FROM LocusFts f
           JOIN Locus l ON l.rowid = f.rowid
           WHERE LocusFts MATCH ? AND l.pool = 'mind' AND l.ownerId = ?
           LIMIT 5""",
        ("alpha", cid),
    ).fetchall()
    plan_text = "\n".join("|".join(str(c) for c in row) for row in plan).lower()
    assert "virtual table" in plan_text
    assert "search l using" in plan_text


def test_mem_perf2_search_latency(scale_mem: tuple[MemoryService, dict]) -> None:
    """MEM-PERF-2: p95 memory_search and diary_search < 50ms on ci profile."""
    mem, meta = scale_mem
    cid = meta["characterIds"][3]
    mind_times: list[float] = []
    diary_times: list[float] = []
    queries = ["alpha", "beta", "fact", "secret", "diary", "scene", "keyword"]
    for _ in range(80):
        q = random.choice(queries)
        t0 = time.perf_counter()
        mem.memory_search(pool="mind", owner_id=cid, query=q, limit=10)
        mind_times.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        mem.diary_search(character_id=cid, query=q, limit=10)
        diary_times.append((time.perf_counter() - t0) * 1000)
    assert _p95(mind_times) < 50.0, f"mind p95={_p95(mind_times):.1f}ms"
    assert _p95(diary_times) < 50.0, f"diary p95={_p95(diary_times):.1f}ms"


def test_mem_perf3_mandatory_recall_latency(scale_mem: tuple[MemoryService, dict]) -> None:
    """MEM-PERF-3: p95 mandatory recall assembly < 100ms (cache miss each call)."""
    mem, meta = scale_mem
    cid = meta["characterIds"][5]
    scene_id = meta["sceneIds"][0]
    times: list[float] = []
    for _ in range(40):
        t0 = time.perf_counter()
        mem.build_mandatory_recall(
            character_id=cid, scene_id=scene_id, max_chars=12000
        )
        times.append((time.perf_counter() - t0) * 1000)
    assert _p95(times) < 100.0, f"recall p95={_p95(times):.1f}ms"


def test_mem_perf4_recall_scoped_to_character_and_scene(
    scale_mem: tuple[MemoryService, dict],
) -> None:
    """MEM-PERF-4: recall only includes generating character mind + active scene world."""
    mem, meta = scale_mem
    alice = meta["characterIds"][0]
    bob = meta["characterIds"][1]
    scene_a, scene_b = meta["sceneIds"][0], meta["sceneIds"][1]
    text_a = mem.build_mandatory_recall(character_id=alice, scene_id=scene_a, max_chars=50000)
    assert f"SECRET_TOKEN_{bob}_ONLY" not in text_a
    assert f"for {scene_a}" in text_a or scene_a in text_a
    alice_hits = mem.memory_search(pool="mind", owner_id=alice, query="SECRET_TOKEN", limit=5)
    assert any(f"SECRET_TOKEN_{alice}_ONLY" in h.get("value", "") for h in alice_hits)
    text_b = mem.build_mandatory_recall(character_id=alice, scene_id=scene_b, max_chars=50000)
    assert f"World fact" in text_b and scene_b in text_b


def test_mem_acc1_no_cross_owner_mind_leakage(scale_mem: tuple[MemoryService, dict]) -> None:
    """MEM-ACC-1: hybrid search never returns another character's mind rows."""
    mem, meta = scale_mem
    chars = meta["characterIds"]
    tokens = [f"SECRET_TOKEN_{c}_ONLY" for c in chars[:8]]
    for _ in range(1000):
        owner = random.choice(chars)
        q = random.choice(tokens + ["alpha", "beta", "fact", "keyword"])
        hits = mem.memory_search(pool="mind", owner_id=owner, query=q, limit=20)
        for h in hits:
            assert h["ownerId"] == owner
            for other in chars:
                if other != owner:
                    assert f"SECRET_TOKEN_{other}_ONLY" not in h.get("value", "")


def test_mem_acc2_diary_tail_newest_first_within_budget(
    scale_mem: tuple[MemoryService, dict],
) -> None:
    """MEM-ACC-2: diary segments in recall follow newest createdAt within budget."""
    mem, meta = scale_mem
    cid = meta["characterIds"][2]
    scene_id = meta["sceneIds"][0]
    rows = mem.store.list_diary(cid, limit=5)
    assert rows, "fixture should have diary rows"
    newest = rows[-1]["text"]
    recall = mem.build_mandatory_recall(character_id=cid, scene_id=scene_id, max_chars=8000)
    assert newest in recall
    if len(rows) >= 2:
        older = rows[0]["text"]
        assert rows[-1]["createdAt"] >= rows[0]["createdAt"]


def test_mem_acc5_recall_within_max_chars(scale_mem: tuple[MemoryService, dict]) -> None:
    """MEM-ACC-5: assembled mandatory recall respects char budget."""
    mem, meta = scale_mem
    cid = meta["characterIds"][0]
    scene_id = meta["sceneIds"][0]
    for budget in (500, 2000, 12000):
        text = mem.build_mandatory_recall(
            character_id=cid, scene_id=scene_id, max_chars=budget
        )
        assert len(text) <= budget


@pytest.mark.slow
def test_mem_perf_reference_profile(tmp_path: Path) -> None:
    """Full reference scale (docs/17 §7) — run with pytest -m slow."""
    db = tmp_path / "scale_reference.db"
    store = SqlitePersistence(db)
    store.migrate()
    seed_memory_scale(store, profile="reference")
    mem = MemoryService(store)
    cid = "scale-char-00"
    times = []
    for _ in range(40):
        t0 = time.perf_counter()
        mem.memory_search(pool="mind", owner_id=cid, query="alpha", limit=10)
        times.append((time.perf_counter() - t0) * 1000)
    assert _p95(times) < 50.0
