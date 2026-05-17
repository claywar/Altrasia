"""Phone channels and perception (CC-8–CC-13)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.communication.phone import PhoneService
from altrasia.perception.scope import can_perceive


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings(
        data_dir=tmp_path,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app), app.state.services


def test_phone_handset_bystander_hears_one_side_only(client: tuple[TestClient, object]) -> None:
    client, services = client
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    phone = PhoneService(services.store)
    ch = phone.create_channel(
        world_id=world_id,
        scene_a="scene-hall",
        character_a="char-bob",
        scene_b="scene-kitchen",
        character_b="char-alice",
    )
    msg_id, _ = phone.insert_phone_line(
        world_id=world_id,
        speaker_scene_id="scene-kitchen",
        channel_id=ch["channelId"],
        text="Hello from kitchen",
        created_at="2026-01-01T00:00:00+00:00",
    )
    ch_row = phone.get(ch["channelId"])
    msg = services.store.conn.execute(
        "SELECT * FROM Message WHERE messageId = ?", (msg_id,)
    ).fetchone()
    message = dict(msg)
    # Carol in kitchen, not on call — hears Alice side only
    assert can_perceive(
        viewer_id="char-carol",
        message=message,
        present=["char-carol", "char-alice"],
        viewer_scene_id="scene-kitchen",
        channel=ch_row,
    )
    # Bystander in hall should not hear kitchen-spoken line (Bob's leg only when Bob speaks)
    assert not can_perceive(
        viewer_id="char-carol",
        message=message,
        present=["char-carol"],
        viewer_scene_id="scene-hall",
        channel=ch_row,
    )


def test_phone_api_create_and_line(client: tuple[TestClient, object]) -> None:
    client, _ = client
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    ch = client.post(
        f"/api/v1/worlds/{world_id}/channels",
        json={
            "sceneIdA": "scene-hall",
            "characterIdA": "char-bob",
            "sceneIdB": "scene-kitchen",
            "characterIdB": "char-alice",
        },
    ).json()
    client.patch(
        f"/api/v1/worlds/{world_id}/channels/{ch['channelId']}/endpoints/scene-kitchen",
        json={"speakerphone": True},
    )
    send = client.post(
        f"/api/v1/worlds/{world_id}/scenes/scene-kitchen/messages",
        json={"text": "Phone check", "scope": "phone", "channelId": ch["channelId"]},
    )
    assert send.status_code == 200
    hall_msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/scene-hall/messages").json()
    assert any(m.get("outputText") == "Phone check" for m in hall_msgs)


def test_knock_answer_enqueues(client: tuple[TestClient, object]) -> None:
    client, _ = client
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    sig = client.post(
        f"/api/v1/worlds/{world_id}/signals",
        json={
            "kind": "knock",
            "sourceSceneId": "scene-kitchen",
            "targetSceneId": "scene-hall",
        },
    ).json()
    ans = client.post(
        f"/api/v1/worlds/{world_id}/signals/{sig['signalId']}/answer",
        json={"characterId": "char-alice", "targetSceneId": "scene-hall"},
    )
    assert ans.status_code == 200
    assert ans.json().get("generationJob")
