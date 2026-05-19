"""CC-11c broken door + scene_exit_set_state."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_scene_exit_set_state_broken(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "cc11c.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    world_id = w["worldId"]
    scene_id = "scene-lobby"
    import json

    scene = client.get(f"/api/v1/worlds/{world_id}/scenes/{scene_id}").json()
    exits = json.loads(scene.get("exitsJson") or "[]")
    assert exits, "demo world should have exits"
    exit_id = exits[0]["exitId"]
    r = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}/exits/{exit_id}/state",
        json={"doorState": "broken"},
    )
    assert r.status_code == 200
    assert r.json()["doorState"] == "broken"
