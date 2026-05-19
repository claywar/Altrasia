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
    append_banter_session,
    extend_digest_window,
    scene_has_floor_hold,
    scene_operator_quiet_active,
    set_floor_hold,
)
from altrasia.orchestrator.idle_scheduler import IdleScheduler
from altrasia.commissions import create_commission
from altrasia.orchestrator.idle_task_affinity import (
    collect_active_tasks_by_character,
    dyad_task_affinity_score,
)
from altrasia.orchestrator.social_selection import pick_idle_dyad, pick_idle_participant, score_idle_dyads
from altrasia.orchestrator.speaker_selection import parse_addressing
from altrasia.memory.service import MemoryService, _diary_recall_lines
from altrasia.orchestrator.engine import Orchestrator
from altrasia.orchestrator.idle_social_prompt import banter_system_addendum
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
            "idleSocialStartProbability": 1.0,
            "idleSocialSessionCooldownSeconds": 0,
            "idleSocialDigestWindowSeconds": 0,
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


def test_diary_recall_caps_banter_segments():
    diary = [
        {"kind": "witnessed", "text": "persona: hello room"},
        {"kind": "banter", "text": "a" * 200},
        {"kind": "banter", "text": "short banter line"},
        {"kind": "banter", "text": "newest banter"},
    ]
    lines = _diary_recall_lines(diary, banter_limit=2, banter_max_chars=40)
    text = "\n".join(lines)
    assert "witnessed" in text
    assert "condensed" in text
    assert "newest banter" in text
    assert "a" * 200 not in text
    assert "…" in text or len("a" * 200) > 40


def test_capture_diary_fanout_banter_kind(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    present = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID][:1]
    if not present:
        pytest.skip("no cast in scene")
    mem = MemoryService(services.store)
    mem.capture_diary_fanout(
        scene_id=scene_id,
        present_ids=present,
        snippet="cast: quick sidebar",
        message_ids=["m1"],
        kind="banter",
    )
    rows = services.store.list_diary(present[0], limit=5)
    assert rows[-1]["kind"] == "banter"


def test_banter_professional_prompt_mentions_research(svc_client):
    _, services, world_id = svc_client
    addendum = banter_system_addendum(
        services,
        world_id=world_id,
        scene_id="scene-x",
        speaker_id="char-a",
        activity={"speakingOrder": ["char-a", "char-b"]},
        members={
            "char-a": {"displayName": "Alex", "sceneRole": "analyst"},
            "char-b": {"displayName": "Blake"},
        },
        recent_session_lines=[],
        tone="professional",
    )
    assert "memory_search" in addendum
    assert "analyst" in addendum


def test_dyad_task_affinity_prefers_shared_work():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    tasks = {
        "a": [
            {
                "targetSceneId": "scene-1",
                "updatedAt": now,
                "status": "running",
                "kind": "commission",
            }
        ],
        "b": [
            {
                "targetSceneId": "scene-1",
                "updatedAt": now,
                "status": "queued",
                "kind": "commission",
            }
        ],
        "c": [],
    }
    shared = dyad_task_affinity_score(
        "a", "b", tasks, scene_id="scene-1", half_life=300
    )
    lone = dyad_task_affinity_score(
        "a", "c", tasks, scene_id="scene-1", half_life=300
    )
    none = dyad_task_affinity_score(
        "c", "x", tasks, scene_id="scene-1", half_life=300
    )
    assert shared > lone > none


def test_score_idle_dyads_includes_task_affinity(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    if len(cast) < 2:
        pytest.skip("demo cast too small")
    create_commission(
        services.store,
        world_id,
        assignee_character_id=cast[0],
        target_scene_id=scene_id,
        brief="Finish the quarterly review draft",
    )
    create_commission(
        services.store,
        world_id,
        assignee_character_id=cast[1],
        target_scene_id=scene_id,
        brief="Sync with ops on the rollout checklist",
    )
    scores = score_idle_dyads(
        services, world_id=world_id, scene=scene, cast=cast[:3]
    )
    dyad_ab = next(
        (s for s in scores if {s.a, s.b} == {cast[0], cast[1]}),
        None,
    )
    assert dyad_ab is not None
    assert dyad_ab.factors.get("taskAffinity", 0) > 0.3


def test_pick_idle_dyad_rationale_includes_task_hints(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    if len(cast) < 2:
        pytest.skip("demo cast too small")
    create_commission(
        services.store,
        world_id,
        assignee_character_id=cast[0],
        target_scene_id=scene_id,
        brief="Prepare briefing slides",
    )
    by_char = collect_active_tasks_by_character(
        services, world_id=world_id, scene_id=scene_id
    )
    assert cast[0] in by_char
    pick = pick_idle_dyad(services, world_id=world_id, scene=scene, cast=cast)
    assert pick is not None
    assert pick.rationale.get("taskHints")


def test_diary_fanout_payload_banter_window(svc_client):
    _, services, world_id = svc_client
    engine = Orchestrator(services)
    cfg = {"idleSocialBanterDiaryWindow": 2, "idleSocialBanterDiaryMaxChars": 100}
    recent = [
        {
            "messageId": "m1",
            "characterId": "c1",
            "outputText": "first",
            "metaJson": '{"orchestration":{"socialIdle":true}}',
        },
        {
            "messageId": "m2",
            "characterId": "c2",
            "outputText": "second",
            "metaJson": '{"orchestration":{"socialIdle":true}}',
        },
        {
            "messageId": "m3",
            "characterId": "c1",
            "outputText": "third",
            "metaJson": "{}",
        },
    ]
    snippet, kind, ids = engine._diary_fanout_payload(
        {"trigger": "banter_turn", "worldId": world_id, "sceneId": "s1"},
        recent,
        cfg=cfg,
    )
    assert kind == "banter"
    assert "second" in snippet
    assert "third" not in snippet
    assert len(ids) == 2


def _ensure_two_cast(store, scene_id: str) -> None:
    scene = store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    if len(cast) < 2:
        store.update_scene(
            scene_id,
            presentJson=json.dumps(
                cast + ["char-sofia-mendez", "char-jordan-reyes"][: 2 - len(cast)]
            ),
        )


def test_session_cooldown_blocks_banter_start(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    _ensure_two_cast(services.store, scene_id)
    merge_world_policy(
        services.store,
        world_id,
        {"idleSocialSessionCooldownSeconds": 600, "idleSocialStartProbability": 1.0},
    )
    append_banter_session(
        services.store,
        scene_id,
        session_id="cooldown-test",
        participants=["char-a", "char-b"],
        line_count=2,
        window=8,
    )
    ok, reason = should_start_idle_banter(
        services, world_id, scene_id, orchestrator=services.orchestrator
    )
    assert not ok
    assert reason == "session_cooldown"


def test_start_probability_skip(svc_client, monkeypatch):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    _ensure_two_cast(services.store, scene_id)
    merge_world_policy(
        services.store,
        world_id,
        {
            "idleSocialStartProbability": 0.0,
            "idleSocialSessionCooldownSeconds": 0,
            "idleSocialDigestWindowSeconds": 0,
        },
    )
    monkeypatch.setattr(
        "altrasia.orchestrator.banter_gates.random.random", lambda: 0.5
    )
    ok, reason = should_start_idle_banter(
        services, world_id, scene_id, orchestrator=services.orchestrator
    )
    assert not ok
    assert reason == "start_probability_skip"


def test_digest_window_blocks_banter_start(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    _ensure_two_cast(services.store, scene_id)
    merge_world_policy(
        services.store,
        world_id,
        {
            "idleSocialDigestWindowSeconds": 300,
            "idleSocialStartProbability": 1.0,
            "idleSocialSessionCooldownSeconds": 0,
        },
    )
    extend_digest_window(services.store, scene_id, seconds=600)
    ok, reason = should_start_idle_banter(
        services, world_id, scene_id, orchestrator=services.orchestrator
    )
    assert not ok
    assert reason == "digest_window_active"


def test_banter_gated_falls_back_to_solo_idle(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    scene = services.store.get_scene(scene_id)
    cast = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
    if len(cast) < 2:
        pytest.skip("demo cast too small")
    merge_world_policy(
        services.store,
        world_id,
        {"idleSocialStartProbability": 0.0, "idleSocialDigestWindowSeconds": 0},
    )
    sched = IdleScheduler(services)
    cid, rationale = sched._pick_idle_character(scene, cast, world_id)
    assert cid in cast
    assert rationale.get("pick") == "idle_participant"
    assert rationale.get("banterGated") == "start_probability_skip"


def test_banter_addendum_digest_guidance(svc_client):
    _, services, world_id = svc_client
    addendum = banter_system_addendum(
        services,
        world_id=world_id,
        scene_id="scene-x",
        speaker_id="char-a",
        activity={"speakingOrder": ["char-a", "char-b"]},
        members={
            "char-a": {"displayName": "Alex"},
            "char-b": {"displayName": "Blake"},
        },
        recent_session_lines=[],
        digest_active=True,
    )
    assert "diary_search" in addendum
    assert "memory_search" in addendum


def test_idle_banter_disabled_blocks_start(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    merge_world_policy(services.store, world_id, {"idleBanterEnabled": False})
    ok, reason = should_start_idle_banter(
        services, world_id, scene_id, orchestrator=services.orchestrator
    )
    assert not ok
    assert reason == "idle_banter_disabled"


def test_operator_quiet_blocks_banter_start(svc_client):
    _, services, world_id = svc_client
    scene_id = services.store.get_world(world_id)["activeSceneId"]
    merge_world_policy(
        services.store,
        world_id,
        {"operatorInteractionCooldownSeconds": 300, "idleSocialDigestWindowSeconds": 0},
    )
    extend_digest_window(services.store, scene_id, seconds=300)
    ok, reason = should_start_idle_banter(
        services, world_id, scene_id, orchestrator=services.orchestrator
    )
    assert not ok
    assert reason == "operator_quiet_period"
    assert scene_operator_quiet_active(services, world_id, scene_id)
