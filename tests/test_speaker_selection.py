"""AO-17 / AO-18 classroom and scoring tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.speaker_selection import score_speakers, speak_readiness_score
from altrasia.services import AppServices


@pytest.fixture
def svc(tmp_path: Path) -> AppServices:
    settings = Settings(
        db_path=tmp_path / "spk.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    return AppServices.create(settings)


def test_ao17_relevance_prefers_matching_mind(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = svc.store.list_world_characters(world_id)
    student_a = next((c for c in chars if "alice" in c["characterId"].lower()), chars[0])
    student_b = next((c for c in chars if "bob" in c["characterId"].lower()), chars[1])
    svc.memory.memory_store(
        pool="mind",
        owner_id=student_a["characterId"],
        locus_key="geo.france",
        value="The capital of France is Paris.",
    )
    score_a = speak_readiness_score(
        svc.memory, student_a["characterId"], "What is the capital of France?"
    )
    score_b = speak_readiness_score(
        svc.memory, student_b["characterId"], "What is the capital of France?"
    )
    assert score_a > score_b


def test_ao18_classroom_teacher_question(svc: AppServices, tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "class.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    world_id = w["worldId"]
    scene_id = w["activeSceneId"]
    chars = client.get(f"/api/v1/worlds/{world_id}/characters").json()
    alice = next(c for c in chars if "alice" in c["characterId"])
    bob = next(c for c in chars if "bob" in c["characterId"])
    svc2 = AppServices.create(settings)
    svc2.store.conn.execute(
        "UPDATE WorldMember SET sceneRole = ? WHERE worldId = ? AND characterId = ?",
        ("student", world_id, alice["characterId"]),
    )
    svc2.store.conn.execute(
        "UPDATE WorldMember SET sceneRole = ? WHERE worldId = ? AND characterId = ?",
        ("student", world_id, bob["characterId"]),
    )
    svc2.store.conn.commit()
    svc2.memory.memory_store(
        pool="mind",
        owner_id=alice["characterId"],
        locus_key="france.capital",
        value="Paris is the capital of France.",
    )
    present = json.loads(svc2.store.get_scene(scene_id)["presentJson"])
    cast = [c for c in present if c != "__persona__"]
    pick = score_speakers(
        svc2,
        world_id=world_id,
        scene_id=scene_id,
        trigger_text="Teacher asks: what is the capital of France?",
        eligible=cast,
    )
    assert pick is not None
    assert pick.character_id == alice["characterId"]
    assert pick.rationale.get("scores")
