"""Spatial golden path (docs/17-acceptance-criteria.md §2) — integration with mock LLM."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.inference.profiles import quality_addendum


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, Path]:
    db = tmp_path / "golden.db"
    settings = Settings(
        db_path=db,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app), db


def _wait_jobs(client: TestClient, world_id: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
        if not q.get("busy") and q.get("depth", 0) == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_golden_path_spatial(client: tuple[TestClient, Path]) -> None:
    client, db_path = client
    # GP-SETUP
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    assert r.status_code == 200
    world_id = r.json()["worldId"]
    hall = "scene-hall"
    kitchen = "scene-kitchen"

    # Step 1: world has 2 scenes and cast
    scenes = client.get(f"/api/v1/worlds/{world_id}/scenes").json()
    assert len(scenes) >= 2

    # Step 2: public line → NPC reply
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={"text": "Hello Alice?", "scope": "public"},
    )
    _wait_jobs(client, world_id)
    msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}/messages").json()
    assert any(m["role"] == "assistant" for m in msgs)

    # Step 3: move persona to kitchen; elsewhere roster
    client.patch(f"/api/v1/worlds/{world_id}", json={"activeSceneId": kitchen})
    roster = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    elsewhere = {e["characterId"] for e in roster["elsewhere"]}
    assert "char-alice" in elsewhere

    # Step 4: knock — signal pending, no generation enqueued (CC-11a)
    depth_before = client.get(f"/api/v1/worlds/{world_id}/queue").json()["depth"]
    client.post(
        f"/api/v1/worlds/{world_id}/signals",
        json={"kind": "knock", "sourceSceneId": kitchen, "targetSceneId": hall},
    )
    sigs = client.get(f"/api/v1/worlds/{world_id}/signals").json()
    assert any(s["status"] == "pending" for s in sigs)
    depth_after = client.get(f"/api/v1/worlds/{world_id}/queue").json()["depth"]
    assert depth_after == depth_before

    # Step 5: Observer meta-chat
    client.post(
        f"/api/v1/worlds/{world_id}/observer/meta-messages",
        json={"text": "Rename hall fixture chandelier to grand chandelier"},
    )
    meta = client.get(f"/api/v1/worlds/{world_id}/observer/meta-messages").json()
    assert len(meta) >= 2

    # Step 6: restart hydration — new client, same DB
    settings = Settings(
        db_path=db_path,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client2 = TestClient(create_app(settings))
    w2 = client2.get(f"/api/v1/worlds/{world_id}").json()
    assert w2["activeSceneId"] == kitchen
    sigs2 = client2.get(f"/api/v1/worlds/{world_id}/signals").json()
    assert any(s["status"] == "pending" for s in sigs2)


def test_oq1_quality_addendum(tmp_path: Path) -> None:
    settings = Settings(models_dir=Path(__file__).resolve().parents[1] / "config" / "models")
    text = quality_addendum(settings)
    assert "in character" in text.lower()
