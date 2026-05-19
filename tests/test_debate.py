"""Debate activity DEB-2 speaker lock."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from tests.conftest import make_test_settings, wait_for_jobs


def test_debate_start_and_turn(tmp_path: Path) -> None:
    with TestClient(create_app(make_test_settings(tmp_path, "debate.db"))) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        hall = "scene-lobby"
        order = ["char-jordan-reyes"]

        started = client.post(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/debate",
            json={"speakingOrder": order, "phase": "opening"},
        ).json()
        assert started["activity"]["kind"] == "debate"
        if started.get("generationJob"):
            wait_for_jobs(client, world_id)

        deb = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/debate").json()
        assert deb["activity"] is not None

        client.post(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
            json={"text": "What do you think?", "scope": "public"},
        )
        wait_for_jobs(client, world_id)
        msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/messages").json()
        assistants = [
            m for m in msgs if m.get("role") == "assistant" and m.get("characterId")
        ]
        assert assistants
        assert assistants[-1]["characterId"] in order

        client.delete(f"/api/v1/worlds/{world_id}/scenes/{hall}/debate")
        cleared = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/debate").json()
        assert cleared["activity"] is None
