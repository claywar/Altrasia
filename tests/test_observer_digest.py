"""Observer digest (CC-6) and first-run API walkthrough."""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        db_path=tmp_path / "digest.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    return TestClient(create_app(settings))


def _wait_jobs(client: TestClient, world_id: str, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
        if not q.get("busy") and q.get("depth", 0) == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_observer_digest_cc6(client: TestClient) -> None:
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    hall = "scene-hall"
    kitchen = "scene-kitchen"

    d0 = client.get(f"/api/v1/worlds/{world_id}/observer/digest").json()
    assert d0["worldId"] == world_id
    assert len(d0["scenes"]) >= 2
    assert d0["pendingSignals"] == []
    assert "summary" in d0

    client.post(
        f"/api/v1/worlds/{world_id}/signals",
        json={"kind": "knock", "sourceSceneId": kitchen, "targetSceneId": hall},
    )
    d1 = client.get(f"/api/v1/worlds/{world_id}/observer/digest").json()
    assert len(d1["pendingSignals"]) >= 1
    assert "pending signal" in d1["summary"].lower()


def test_first_run_experience_api(client: TestClient) -> None:
    """Automates docs/guides/first-run-experience.md core API steps."""
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    hall = "scene-hall"
    kitchen = "scene-kitchen"

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={"text": "Hello Alice?", "scope": "public"},
    )
    _wait_jobs(client, world_id)

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={
            "text": "Alice, this is just for you.",
            "scope": "whisper",
            "targetCharacterId": "char-alice",
        },
    )
    _wait_jobs(client, world_id)
    hall_msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/messages").json()
    whisper = next(
        m
        for m in hall_msgs
        if '"scope": "whisper"' in (m.get("metaJson") or "")
        or "whisper" in (m.get("metaJson") or "")
    )
    meta = json.loads(whisper["metaJson"])
    assert meta.get("communication", {}).get("scope") == "whisper"

    client.patch(f"/api/v1/worlds/{world_id}", json={"activeSceneId": kitchen})
    roster = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    assert "char-alice" in {e["characterId"] for e in roster["elsewhere"]}

    depth_before = client.get(f"/api/v1/worlds/{world_id}/queue").json()["depth"]
    client.post(
        f"/api/v1/worlds/{world_id}/signals",
        json={"kind": "knock", "sourceSceneId": kitchen, "targetSceneId": hall},
    )
    assert client.get(f"/api/v1/worlds/{world_id}/queue").json()["depth"] == depth_before

    client.post(
        f"/api/v1/worlds/{world_id}/observer/meta-messages",
        json={"text": "Tweak: hall feels warmer."},
    )
    assert len(client.get(f"/api/v1/worlds/{world_id}/observer/meta-messages").json()) >= 1

    digest = client.get(f"/api/v1/worlds/{world_id}/observer/digest").json()
    assert len(digest["pendingSignals"]) >= 1
