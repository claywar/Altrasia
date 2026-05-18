"""MP-21 EvidenceRecord on commission completion."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def _wait_jobs(client: TestClient, world_id: str) -> None:
    deadline = time.time() + 12
    while time.time() < deadline:
        q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
        if not q.get("busy") and q.get("depth", 0) == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("timeout")


def test_commission_evidence_record(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "ev.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    kitchen = "scene-kitchen"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-alice"},
    )
    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-alice",
            "targetSceneId": kitchen,
            "brief": "Summarize the hall fixtures.",
        },
    ).json()
    if com["status"] == "queued":
        client.post(f"/api/v1/worlds/{world_id}/commissions/{com['commissionId']}/start")
    _wait_jobs(client, world_id)
    rows = svc.store.list_evidence_for_locus(
        "mind", "char-alice", f"commission:{com['commissionId']}:summary"
    )
    assert len(rows) >= 1
    assert rows[0]["sourceKind"] == "commission"
