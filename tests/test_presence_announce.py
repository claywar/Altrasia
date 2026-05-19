"""Summon assistance chronicle announcements."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.presence_announce import format_summon_announcement
from altrasia.domain.presence_ops import presence_summon_batch
from altrasia.orchestrator.chat_messages import scene_messages_for_llm


@pytest.fixture
def svc(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "announce.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc.app.state.services


def test_format_summon_announcement_variants() -> None:
    assert "requested assistance" in format_summon_announcement(
        "Jordan Reyes",
        ["Sofia Mendez", "Liam Park"],
        "Conference Room",
        perspective="source",
    )
    assert "join Conference Room" in format_summon_announcement(
        "Jordan Reyes",
        ["Sofia Mendez"],
        "Conference Room",
        perspective="target",
    )
    assert "was called to" in format_summon_announcement(
        None,
        ["Sofia Mendez"],
        "Conference Room",
        perspective="operator",
    )


def test_presence_summon_batch_announces_dual_scene(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    lobby = "scene-lobby"
    conference = "scene-conference-room"

    asyncio.run(
        presence_summon_batch(
            svc,
            world_id=world_id,
            target_scene_id=conference,
            character_ids=["char-sofia-mendez", "char-liam-park"],
            summoner_id="char-jordan-reyes",
            source_scene_id=lobby,
            source="tool",
            announce=True,
        )
    )

    lobby_msgs = svc.store.list_messages(world_id, scene_id=lobby)
    conf_msgs = svc.store.list_messages(world_id, scene_id=conference)
    announce_lobby = [
        m
        for m in lobby_msgs
        if json.loads(m["metaJson"]).get("orchestration", {}).get("kind") == "presence_announce"
    ]
    announce_conf = [
        m
        for m in conf_msgs
        if json.loads(m["metaJson"]).get("orchestration", {}).get("kind") == "presence_announce"
    ]
    assert len(announce_lobby) == 1
    assert len(announce_conf) == 1
    assert "requested assistance" in announce_lobby[0]["outputText"]
    assert "join" in announce_conf[0]["outputText"].lower()
    assert json.loads(announce_lobby[0]["metaJson"])["communication"]["scope"] == "presence"


def test_presence_announce_excluded_from_llm_history(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    lobby = "scene-lobby"

    asyncio.run(
        presence_summon_batch(
            svc,
            world_id=world_id,
            target_scene_id="scene-conference-room",
            character_ids=["char-sofia-mendez"],
            summoner_id="char-jordan-reyes",
            source_scene_id=lobby,
            source="operator",
            announce=True,
        )
    )

    rows = svc.store.list_messages(world_id, scene_id=lobby)
    turns = scene_messages_for_llm(
        rows,
        viewer_id="char-jordan-reyes",
        present=["char-jordan-reyes"],
        viewer_scene_id=lobby,
    )
    assert not any("requested assistance" in t["content"] for t in turns)
    assert not any("was called to" in t["content"] for t in turns)


def test_operator_rest_summon_announces_at_target(tmp_path: Path) -> None:
    from tests.conftest import make_test_settings

    with TestClient(create_app(make_test_settings(tmp_path, "op_summon.db"))) as client:
        world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
            "worldId"
        ]
        hall = "scene-lobby"
        draft = client.post(
            "/api/v1/characters/draft",
            json={"brief": "A quiet herbalist."},
        ).json()
        created = client.post(
            "/api/v1/characters",
            json={"draftId": draft["draftId"], "worldId": world_id, "displayName": "Herbalist"},
        ).json()
        char_id = created["characterId"]

        client.post(
            f"/api/v1/worlds/{world_id}/presence/summon",
            json={"characterIds": [char_id], "targetSceneId": hall},
        )

        msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/messages").json()
        announce = [
            m
            for m in msgs
            if json.loads(m["metaJson"]).get("orchestration", {}).get("kind")
            == "presence_announce"
        ]
        assert len(announce) == 1
        assert "Herbalist" in announce[0]["outputText"]
        assert announce[0]["role"] == "system"
