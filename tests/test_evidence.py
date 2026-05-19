"""MP-21 EvidenceRecord on commission completion."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from tests.conftest import make_test_settings, wait_for_jobs


def test_commission_evidence_record(tmp_path: Path) -> None:
    app = create_app(make_test_settings(tmp_path, "ev.db"))
    with TestClient(app) as client:
        svc = app.state.services
        _run_evidence(client, svc)


def _run_evidence(client: TestClient, svc: object) -> None:
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    kitchen = "scene-conference-room"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-jordan-reyes"},
    )
    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-jordan-reyes",
            "targetSceneId": kitchen,
            "brief": "Summarize the hall fixtures.",
        },
    ).json()
    if com["status"] == "queued":
        client.post(f"/api/v1/worlds/{world_id}/commissions/{com['commissionId']}/start")
    wait_for_jobs(client, world_id)
    rows = svc.store.list_evidence_for_locus(
        "mind", "char-jordan-reyes", f"commission:{com['commissionId']}:summary"
    )
    assert len(rows) >= 1
    assert rows[0]["sourceKind"] == "commission"
