"""Architect World geography: scenes, lock, W-1."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_architect_world_scenes_and_lock(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "geo.db", mock_llm=True)
    client = TestClient(create_app(settings))
    world = client.post("/api/v1/worlds", json={"name": "Architect Test"}).json()
    world_id = world["worldId"]
    start = world["activeSceneId"]

    geo = client.get(f"/api/v1/worlds/{world_id}/geography").json()
    assert geo["layoutDesignMode"] is True
    assert geo["sceneCount"] == 1

    sc2 = client.post(
        f"/api/v1/worlds/{world_id}/scenes",
        json={
            "locationName": "Garden",
            "connectFromSceneId": start,
            "exitLabel": "Garden door",
        },
    )
    assert sc2.status_code == 200
    garden_id = sc2.json()["sceneId"]

    start_scene = client.get(f"/api/v1/worlds/{world_id}/scenes/{start}").json()
    exits = __import__("json").loads(start_scene["exitsJson"])
    assert any(e["targetSceneId"] == garden_id for e in exits)

    locked = client.post(f"/api/v1/worlds/{world_id}/geography/lock").json()
    assert locked["layoutDesignMode"] is False

    blocked = client.post(
        f"/api/v1/worlds/{world_id}/scenes",
        json={"locationName": "Attic"},
    )
    assert blocked.status_code == 403

    del_ok = client.delete(f"/api/v1/worlds/{world_id}/scenes/{garden_id}")
    assert del_ok.status_code == 403

    del_last = client.delete(f"/api/v1/worlds/{world_id}/scenes/{start}")
    assert del_last.status_code == 403


def test_w1_cannot_delete_last_scene_in_design_mode(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "w1.db", mock_llm=True)
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"name": "Solo"}).json()["worldId"]
    scene_id = client.get(f"/api/v1/worlds/{world_id}/scenes").json()[0]["sceneId"]
    r = client.delete(f"/api/v1/worlds/{world_id}/scenes/{scene_id}")
    assert r.status_code == 400
    assert "last scene" in r.json()["detail"].lower()


def test_first_play_locks_geography(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "play.db", mock_llm=True)
    client = TestClient(create_app(settings))
    world = client.post("/api/v1/worlds", json={"name": "Play Lock"}).json()
    world_id = world["worldId"]
    scene_id = world["activeSceneId"]
    assert client.get(f"/api/v1/worlds/{world_id}/geography").json()["layoutDesignMode"] is True

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages",
        json={"text": "Hello?", "scope": "public"},
    )
    geo = client.get(f"/api/v1/worlds/{world_id}/geography").json()
    assert geo["layoutDesignMode"] is False
    assert geo["geographyLockedAt"]
