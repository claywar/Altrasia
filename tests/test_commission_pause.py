"""Defer commission start while persona dialogue is active at target scene."""

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


def test_commission_deferred_during_persona_play(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "cpause.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall = "scene-hall"

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={"text": "Alice, hold on — I need you here.", "scope": "public"},
    )
    _wait_jobs(client, world_id)

    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-alice",
            "targetSceneId": hall,
            "brief": "Catalog the bookshelves after we finish talking.",
        },
    ).json()
    assert com["status"] == "queued"
    cid = com["commissionId"]

    blocked_start = client.post(f"/api/v1/worlds/{world_id}/commissions/{cid}/start")
    assert blocked_start.status_code == 400
    assert "deferred" in blocked_start.json()["detail"].lower()
