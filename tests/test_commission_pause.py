"""Defer commission start while persona dialogue is active at target scene."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from tests.conftest import make_test_settings, wait_for_jobs


def test_commission_deferred_during_persona_play(tmp_path: Path) -> None:
    with TestClient(create_app(make_test_settings(tmp_path, "cpause.db"))) as client:
        _run_commission_pause(client)


def _run_commission_pause(client: TestClient) -> None:
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall = "scene-lobby"

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={"text": "Alice, hold on — I need you here.", "scope": "public"},
    )
    wait_for_jobs(client, world_id)

    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-jordan-reyes",
            "targetSceneId": hall,
            "brief": "Catalog the bookshelves after we finish talking.",
        },
    ).json()
    assert com["status"] == "queued"
    cid = com["commissionId"]

    blocked_start = client.post(f"/api/v1/worlds/{world_id}/commissions/{cid}/start")
    assert blocked_start.status_code == 400
    assert "deferred" in blocked_start.json()["detail"].lower()
