"""Debate activity DEB-2 speaker lock."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def _wait_jobs(client: TestClient, world_id: str, timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
        if not q.get("busy") and q.get("depth", 0) == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_debate_start_and_turn(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "debate.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall = "scene-hall"
    order = ["char-alice"]

    started = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/debate",
        json={"speakingOrder": order, "phase": "opening"},
    ).json()
    assert started["activity"]["kind"] == "debate"
    if started.get("generationJob"):
        _wait_jobs(client, world_id)

    deb = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/debate").json()
    assert deb["activity"] is not None

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={"text": "What do you think?", "scope": "public"},
    )
    _wait_jobs(client, world_id)
    msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/messages").json()
    assistants = [m for m in msgs if m.get("role") == "assistant" and m.get("characterId")]
    assert assistants
    assert assistants[-1]["characterId"] in order

    client.delete(f"/api/v1/worlds/{world_id}/scenes/{hall}/debate")
    cleared = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/debate").json()
    assert cleared["activity"] is None
