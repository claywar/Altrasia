"""Idle social: weighted selection, banter gates, floor cues."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.debate_activity import get_active_banter, start_banter
from altrasia.domain.presence import PERSONA_ID
from altrasia.orchestrator.banter_gates import should_start_idle_banter
from altrasia.orchestrator.floor_cues import detect_floor_claim, detect_floor_release
from altrasia.orchestrator.idle_social_state import (
    scene_has_floor_hold,
    set_floor_hold,
)
from altrasia.orchestrator.social_selection import pick_idle_dyad, pick_idle_participant
from altrasia.orchestrator.speaker_selection import parse_addressing
from altrasia.world_config import merge_world_policy


@pytest.fixture
def svc_client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "idle_social.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    merge_world_policy(
        client.app.state.services.store,
        world_id,
        {
            "idleSocialEnabled": True,
            "idleSocialMinCast": 2,
            "idleSocialMaxDepth": 2,
        },
    )
    return client, client.app.state.services, world_id


def test_pick_idle_dyad_returns_two_speakers(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    if len(cast) < 2:
        pytest.skip("demo cast too small")
    pick = pick_idle_dyad(services, world_id=world_id, scene=scene, cast=cast)
    assert pick is not None
    assert len(pick.speaking_order) == 2
    assert pick.speaking_order[0] != pick.speaking_order[1]


def test_pick_idle_participant_weighted(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    cid, rationale = pick_idle_participant(
        services, world_id=world_id, scene=scene, cast=cast[:1]
    )
    assert cid in cast
    assert rationale.get("pick") == "idle_participant"


def test_start_banter_activity(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID][:2]
    if len(cast) < 2:
        pytest.skip("need two cast")
    activity = start_banter(
        services.store,
        scene_id,
        speaking_order=cast,
        session_id="test-session",
        turns_remaining=3,
    )
    assert activity["kind"] == "banter"
    scene2 = services.store.get_scene(scene_id)
    assert get_active_banter(scene2) is not None


def test_floor_hold_blocks_banter_start(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    if len(cast) < 2:
        store = services.store
        store.update_scene(
            scene_id,
            presentJson=json.dumps(cast[:2] if len(cast) >= 2 else cast + ["char-sofia-mendez", "char-jordan-reyes"]),
        )
    set_floor_hold(
        services.store,
        scene_id,
        claimed_by=PERSONA_ID,
        reason="operator_question",
    )
    ok, reason = should_start_idle_banter(
        services, world_id, scene_id, orchestrator=services.orchestrator
    )
    assert not ok
    assert reason in ("floor_hold_active", "cast_too_small")
    if len([c for c in json.loads(services.store.get_scene(scene_id)["presentJson"]) if c != PERSONA_ID]) >= 2:
        assert reason == "floor_hold_active"


def test_detect_floor_claim_operator_question():
    claim = detect_floor_claim("Does anyone have updates?", role="operator", speaker_id=PERSONA_ID)
    assert claim is not None
    assert claim.reason == "operator_question"


def test_detect_floor_release():
    assert detect_floor_release("Okay, carry on everyone")
    assert not detect_floor_release("Hello there")


def test_cast_directed_floor_claim(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}
    if len(cast) < 2:
        pytest.skip("need two cast")
    speaker, target = cast[0], cast[1]
    target_name = chars[target]["displayName"]
    addressing = parse_addressing(
        f"{target_name}, what do you think about the launch?",
        cast,
        chars,
    )
    claim = detect_floor_claim(
        f"{target_name}, what do you think?",
        role="cast",
        speaker_id=speaker,
        cast=cast,
        chars=chars,
        addressing=addressing,
    )
    assert claim is not None
    assert claim.reason == "cast_directed"
    assert target in (claim.awaiting_addressees or [])


def test_scene_has_floor_hold_ttl(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    set_floor_hold(
        services.store,
        scene_id,
        claimed_by="char-x",
        reason="cast_attention",
        clear_after_seconds=0,
    )
    assert not scene_has_floor_hold(services.store, scene_id)
