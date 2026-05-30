import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.memory.service import MemoryService
from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.reflection.graph import neighbors_for_recall, write_links
from altrasia.reflection.persona_proposals import approve_persona_proposal, reject_persona_proposal
from altrasia.reflection.runner import (
    character_has_reflection_input,
    run_reflection,
    _parse_reflection_json,
)


@pytest.fixture
def store(tmp_path: Path) -> SqlitePersistence:
    s = SqlitePersistence(tmp_path / "t.db")
    s.migrate()
    return s


@pytest.fixture
def mem(store: SqlitePersistence) -> MemoryService:
    return MemoryService(store)


def test_memory_store_appends_on_repeat_key(mem: MemoryService, store: SqlitePersistence) -> None:
    mem.memory_store(pool="mind", owner_id="c1", locus_key="reflection:goals", value="First note.")
    mem.memory_store(pool="mind", owner_id="c1", locus_key="reflection:goals", value="Second note.")
    row = store.get_locus("mind", "c1", "reflection:goals")
    assert row is not None
    assert "First note." in row["value"]
    assert "Second note." in row["value"]


def test_memory_store_overwrite(mem: MemoryService, store: SqlitePersistence) -> None:
    mem.memory_store(pool="mind", owner_id="c1", locus_key="commission:x", value="v1", overwrite=True)
    mem.memory_store(pool="mind", owner_id="c1", locus_key="commission:x", value="v2", overwrite=True)
    row = store.get_locus("mind", "c1", "commission:x")
    assert row["value"] == "v2"


def test_memory_store_dedupes_identical_append(mem: MemoryService, store: SqlitePersistence) -> None:
    mem.memory_store(pool="mind", owner_id="c1", locus_key="k", value="Same.")
    mem.memory_store(pool="mind", owner_id="c1", locus_key="k", value="Same.")
    row = store.get_locus("mind", "c1", "k")
    assert row["value"].count("Same.") == 1


def test_parse_reflection_json_extracts_object() -> None:
    raw = 'Here is output:\n{"summary": "ok", "loci": [], "links": []}'
    parsed = _parse_reflection_json(raw)
    assert parsed is not None
    assert parsed["summary"] == "ok"


def test_write_links_and_neighbors(store: SqlitePersistence) -> None:
    count = write_links(
        store,
        character_id="char-a",
        reflection_run_id="run-1",
        links=[
            {
                "fromKind": "diary",
                "fromRef": "seg-1",
                "relation": "learned_from",
                "toKind": "character",
                "toRef": "char-b",
                "summary": "Learned to trust Bob after the meeting.",
            }
        ],
    )
    assert count == 1
    lines = neighbors_for_recall(
        store,
        character_id="char-a",
        seed_refs=[("diary", "seg-1")],
        limit=5,
    )
    assert len(lines) == 1
    assert "trust Bob" in lines[0]


def test_mp1_links_isolated(store: SqlitePersistence) -> None:
    write_links(
        store,
        character_id="char-a",
        reflection_run_id="run-1",
        links=[
            {
                "fromKind": "diary",
                "fromRef": "seg-1",
                "relation": "relates_to",
                "toKind": "character",
                "toRef": "char-b",
                "summary": "Alice private link.",
            }
        ],
    )
    lines = neighbors_for_recall(
        store,
        character_id="char-b",
        seed_refs=[("diary", "seg-1")],
        limit=5,
    )
    assert lines == []


def test_reflection_checkpoint_skips_rerun(store: SqlitePersistence, mem: MemoryService) -> None:
    fixtures = Path(__file__).resolve().parent / "fixtures"
    load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    mem.capture_diary_fanout(
        scene_id="scene-lobby",
        present_ids=["char-jordan-reyes"],
        snippet="Jordan: Hello",
        message_ids=["m1"],
    )
    assert character_has_reflection_input(store, "char-jordan-reyes")
    store.insert_reflection_run(
        {
            "runId": "run-done",
            "characterId": "char-jordan-reyes",
            "worldId": "world-demo-spatial",
            "trigger": "manual",
            "inputSegmentIdsJson": "[]",
            "inputMessageCount": 1,
            "outputLociJson": "[]",
            "outputLinkCount": 0,
            "status": "completed",
            "errorText": None,
            "startedAt": "2026-01-01T00:00:00+00:00",
            "completedAt": "2099-01-02T00:00:00+00:00",
        }
    )
    assert not character_has_reflection_input(store, "char-jordan-reyes")


@pytest.mark.asyncio
async def test_run_reflection_mock_llm(store: SqlitePersistence, mem: MemoryService) -> None:
    fixtures = Path(__file__).resolve().parent / "fixtures"
    load_fixture_by_id(store, fixtures, "demo-spatial-v1")
    mem.capture_diary_fanout(
        scene_id="scene-lobby",
        present_ids=["char-jordan-reyes"],
        snippet="Jordan: We closed the deal today.",
        message_ids=["m-reflect-1"],
    )

    llm_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Jordan reflects on closing the deal.",
                            "loci": [
                                {
                                    "key": "reflection:lessons",
                                    "value": "[2026-05-30] Closing deals requires patience.",
                                }
                            ],
                            "links": [
                                {
                                    "fromKind": "diary",
                                    "fromRef": "seg-placeholder",
                                    "relation": "learned_from",
                                    "toKind": "scene",
                                    "toRef": "scene-lobby",
                                    "summary": "Deal closed at the lobby.",
                                }
                            ],
                            "persona_proposals": [],
                        }
                    )
                }
            }
        ]
    }

    svc = MagicMock()
    svc.store = store
    svc.memory = mem
    svc.embeddings = MagicMock()
    svc.embeddings.schedule_embed = MagicMock()
    svc.llm = MagicMock()
    svc.llm.chat = AsyncMock(return_value=llm_response)
    svc.gpu_queue = MagicMock()

    async def run_work(_job_id, _kind, work):
        return await work()

    svc.gpu_queue.run = run_work

    result = await run_reflection(
        svc,
        character_id="char-jordan-reyes",
        world_id="demo-spatial-v1",
        trigger="manual",
    )
    assert result["status"] == "completed"
    locus = store.get_locus("mind", "char-jordan-reyes", "reflection:lessons")
    assert locus is not None
    assert "patience" in locus["value"]
    assert store.list_memory_links("char-jordan-reyes", limit=10)


def test_persona_proposal_approve(store: SqlitePersistence) -> None:
    store.insert_character(
        {
            "characterId": "c1",
            "displayName": "Test",
            "definitionJson": json.dumps({"persona": "Original.", "instructions": "Be kind."}),
            "modelProfile": "default",
            "speechWeight": 0.5,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    store.insert_persona_proposal(
        {
            "proposalId": "p1",
            "characterId": "c1",
            "reflectionRunId": "run-1",
            "field": "persona",
            "proposedValue": "Updated persona after growth.",
            "rationale": "Character has matured.",
            "status": "pending",
            "createdAt": "2026-01-01T00:00:00+00:00",
            "resolvedAt": None,
        }
    )
    svc = MagicMock()
    svc.store = store
    out = approve_persona_proposal(svc, "p1")
    assert out["status"] == "approved"
    ch = store.get_character("c1")
    definition = json.loads(ch["definitionJson"])
    assert definition["persona"] == "Updated persona after growth."

    store.insert_persona_proposal(
        {
            "proposalId": "p2",
            "characterId": "c1",
            "reflectionRunId": "run-2",
            "field": "instructions",
            "proposedValue": "New instructions.",
            "rationale": "Test reject.",
            "status": "pending",
            "createdAt": "2026-01-02T00:00:00+00:00",
            "resolvedAt": None,
        }
    )
    reject_out = reject_persona_proposal(svc, "p2")
    assert reject_out["status"] == "rejected"
    prop = store.get_persona_proposal("p2")
    assert prop["status"] == "rejected"
