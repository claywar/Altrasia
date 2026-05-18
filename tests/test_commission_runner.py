"""COM-6 presence gate + minimal commission_started runtime."""

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


def test_commission_com6_and_runtime(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "crun.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall, kitchen = "scene-hall", "scene-kitchen"

    created = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-alice",
            "targetSceneId": kitchen,
            "brief": "Find who left the pantry door open.",
        },
    ).json()
    assert created["status"] == "blocked"
    cid = created["commissionId"]

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-alice"},
    )
    listed = client.get(f"/api/v1/worlds/{world_id}/commissions").json()
    row = next(c for c in listed if c["commissionId"] == cid)
    if row["status"] == "queued":
        start = client.post(f"/api/v1/worlds/{world_id}/commissions/{cid}/start")
        assert start.status_code == 200

    _wait_jobs(client, world_id)
    done = client.get(f"/api/v1/worlds/{world_id}/commissions").json()
    final = next(c for c in done if c["commissionId"] == cid)
    assert final["status"] == "done"
    assert len(final["deliverableLocusKeys"]) >= 1

    mind = client.get(
        f"/api/v1/worlds/{world_id}/characters/char-alice/mind"
    ).json()
    assert any("commission:" in loc.get("locusKey", "") for loc in mind)
