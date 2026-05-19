"""AO-17 / AO-18 classroom and scoring tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.speaker_selection import (
    parse_addressing,
    pick_directed_witness,
    score_speakers,
    speak_readiness_score,
)
from altrasia.services import AppServices

PROGRAM_OFFICE_CAST = [
    "char-liam-park",
    "char-rachel-kim",
    "char-tom-bradley",
    "char-nina-patel",
    "char-chris-doyle",
]


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
    student_a = next(
        (c for c in chars if c["characterId"] == "char-sofia-mendez"), chars[0]
    )
    student_b = next(
        (c for c in chars if c["characterId"] == "char-lena-cho"), chars[1]
    )
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
    from tests.conftest import make_test_settings

    settings = make_test_settings(tmp_path, "class.db")
    with TestClient(create_app(settings)) as client:
        w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
        world_id = w["worldId"]
        scene_id = w["activeSceneId"]
        chars = client.get(f"/api/v1/worlds/{world_id}/characters").json()
        sofia = next(c for c in chars if c["characterId"] == "char-sofia-mendez")
        lena = next(c for c in chars if c["characterId"] == "char-lena-cho")
        for cid in (sofia["characterId"], lena["characterId"]):
            client.post(
                f"/api/v1/worlds/{world_id}/scenes/{scene_id}/presence/join",
                json={"characterId": cid},
            )
        svc2 = client.app.state.services
        svc2.store.update_scene(
            scene_id,
            presentJson=json.dumps([sofia["characterId"], lena["characterId"]]),
        )
        svc2.store.conn.execute(
            "UPDATE WorldMember SET sceneRole = ? WHERE worldId = ? AND characterId = ?",
            ("student", world_id, sofia["characterId"]),
        )
        svc2.store.conn.commit()
        svc2.memory.memory_store(
            pool="mind",
            owner_id=sofia["characterId"],
            locus_key="geo.france",
            value="Paris is the capital of France.",
        )
        cast = [sofia["characterId"], lena["characterId"]]
        trigger = "capital France Paris"
        assert speak_readiness_score(svc2.memory, sofia["characterId"], trigger) > speak_readiness_score(
            svc2.memory, lena["characterId"], trigger
        )
        pick = score_speakers(
            svc2,
            world_id=world_id,
            scene_id=scene_id,
            trigger_text=trigger,
            eligible=cast,
            trigger_message_id="test-ao18-france",
        )
        assert pick is not None
        assert pick.character_id == sofia["characterId"]
    assert pick.rationale.get("scores")


def test_parse_addressing_liam_first_name(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    result = parse_addressing(
        "Liam, what is your last name?",
        PROGRAM_OFFICE_CAST,
        chars,
    )
    assert result.mode == "directed"
    assert result.primary_id == "char-liam-park"


def test_parse_addressing_full_name(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    result = parse_addressing(
        "Hey Liam Park, are you free?",
        PROGRAM_OFFICE_CAST,
        chars,
    )
    assert result.mode == "directed"
    assert result.primary_id == "char-liam-park"


def test_parse_addressing_ensemble_cues(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    result = parse_addressing(
        "Everyone, discuss how program management works here.",
        PROGRAM_OFFICE_CAST,
        chars,
    )
    assert result.mode == "ensemble"
    assert result.primary_id is None


def test_parse_addressing_fuzzy_lean_to_lena(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    cast = ["char-lena-cho", "char-marco-delgado", "char-sofia-mendez"]
    result = parse_addressing(
        "Lean, what is your role?",
        cast,
        chars,
        fuzzy_enabled=True,
        fuzzy_max_distance=2,
    )
    assert result.mode == "directed"
    assert result.primary_id == "char-lena-cho"
    assert result.match_reason == "fuzzy"


def test_parse_addressing_jordie_alias_to_jordan(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    cast = ["char-jordan-reyes", "char-sofia-mendez"]
    result = parse_addressing("Jordie, what is your role?", cast, chars)
    assert result.mode == "directed"
    assert result.primary_id == "char-jordan-reyes"
    assert result.match_reason == "exact"


def test_pick_directed_witness_skips_unmentioned(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    cast = ["char-jordan-reyes", "char-sofia-mendez"]
    witness = pick_directed_witness(
        svc,
        world_id=world_id,
        scene_id="scene-lobby",
        trigger_text="Jordie, what is your role?",
        primary_id="char-jordan-reyes",
        eligible=cast,
        exclude_ids={"char-jordan-reyes"},
        trigger_message_id=None,
        relevance_min=0.55,
        require_mention=True,
    )
    assert witness is None


def test_parse_addressing_alias_andy_to_andre(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    cast = list(chars.keys())
    result = parse_addressing("Andy, quick question", cast, chars)
    assert result.mode == "directed"
    assert result.primary_id == "char-andre-silva"
    assert result.match_reason == "exact"


def test_parse_addressing_andie_lenlen_multi() -> None:
    import json
    from pathlib import Path

    data = json.loads(
        Path(__file__).resolve().parent.joinpath("fixtures/demo-world/demo-spatial-v1.json").read_text()
    )
    cast = [
        "char-sofia-mendez",
        "char-priya-nair",
        "char-marco-delgado",
        "char-lena-cho",
        "char-andre-silva",
    ]
    chars = {c["characterId"]: c for c in data["characters"]}
    result = parse_addressing(
        "Andie, LenLen, what are your roles here?",
        cast,
        chars,
    )
    assert result.mode == "directed"
    assert result.addressee_ids == ["char-andre-silva", "char-lena-cho"]
    assert result.match_reason == "multi_name"


def test_parse_addressing_lenlen_followup() -> None:
    import json
    from pathlib import Path

    data = json.loads(
        Path(__file__).resolve().parent.joinpath("fixtures/demo-world/demo-spatial-v1.json").read_text()
    )
    cast = ["char-lena-cho", "char-andre-silva", "char-sofia-mendez"]
    chars = {c["characterId"]: c for c in data["characters"]}
    result = parse_addressing("LenLen?", cast, chars)
    assert result.mode == "directed"
    assert result.primary_id == "char-lena-cho"


def test_parse_addressing_partial_multi_present_only() -> None:
    import json
    from pathlib import Path

    data = json.loads(
        Path(__file__).resolve().parent.joinpath("fixtures/demo-world/demo-spatial-v1.json").read_text()
    )
    cast = [
        "char-liam-park",
        "char-rachel-kim",
        "char-tom-bradley",
        "char-nina-patel",
        "char-chris-doyle",
    ]
    chars = {c["characterId"]: c for c in data["characters"]}
    result = parse_addressing(
        "Lili, Rach, what do you do here?",
        cast,
        chars,
        fuzzy_enabled=True,
        fuzzy_max_distance=2,
    )
    assert result.mode == "directed"
    assert result.addressee_ids == ["char-rachel-kim"]
    assert result.match_reason == "exact"


def test_parse_addressing_absent_name_not_open() -> None:
    import json
    from pathlib import Path

    data = json.loads(
        Path(__file__).resolve().parent.joinpath("fixtures/demo-world/demo-spatial-v1.json").read_text()
    )
    cast = [
        "char-liam-park",
        "char-rachel-kim",
        "char-tom-bradley",
        "char-nina-patel",
        "char-chris-doyle",
    ]
    chars = {c["characterId"]: c for c in data["characters"]}
    result = parse_addressing(
        "Lili, what is your role?",
        cast,
        chars,
        fuzzy_enabled=True,
        fuzzy_max_distance=2,
    )
    assert result.mode == "clarification"
    assert result.match_reason == "not_in_scene"
    assert result.absent_names == ["Lili"]
    assert result.clarifier_id in cast


def test_parse_addressing_marco_and_lena(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    cast = [
        "char-sofia-mendez",
        "char-priya-nair",
        "char-marco-delgado",
        "char-lena-cho",
        "char-andre-silva",
        "char-hannah-brooks",
        "char-omar-haddad",
    ]
    result = parse_addressing("Marco and Lena, what are your roles?", cast, chars)
    assert result.mode == "directed"
    assert result.addressee_ids == ["char-marco-delgado", "char-lena-cho"]


def test_parse_addressing_andre_product_studio(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    cast = [
        "char-sofia-mendez",
        "char-priya-nair",
        "char-marco-delgado",
        "char-lena-cho",
        "char-andre-silva",
        "char-hannah-brooks",
        "char-omar-haddad",
    ]
    result = parse_addressing(
        "Andre, what is your last name and who do you report to?",
        cast,
        chars,
    )
    assert result.mode == "directed"
    assert result.primary_id == "char-andre-silva"


def test_parse_addressing_open_question(svc: AppServices) -> None:
    world = svc.store.conn.execute("SELECT worldId FROM World").fetchone()
    if not world:
        pytest.skip("no world")
    world_id = world[0]
    chars = {c["characterId"]: c for c in svc.store.list_world_characters(world_id)}
    result = parse_addressing("Hello everyone", PROGRAM_OFFICE_CAST, chars)
    assert result.mode == "open"
