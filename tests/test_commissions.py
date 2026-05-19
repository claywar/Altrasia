"""Commission API (v1.5 schema, manual operator — no runtime)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_commission_crud(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "com.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]

    created = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-jordan-reyes",
            "targetSceneId": "scene-conference-room",
            "brief": "Compile Q1 platform reliability metrics for the leadership review.",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "blocked"  # COM-6: assignee not at target scene yet
    assert body["deliverablePolicy"] == "mind"
    cid = body["commissionId"]

    listed = client.get(f"/api/v1/worlds/{world_id}/commissions").json()
    assert len(listed) >= 1

    blocked = client.patch(
        f"/api/v1/worlds/{world_id}/commissions/{cid}",
        json={"status": "done"},
    )
    assert blocked.status_code == 400

    ok = client.patch(
        f"/api/v1/worlds/{world_id}/commissions/{cid}",
        json={
            "status": "done",
            "deliverableLocusKeys": ["commission:" + cid + ":summary"],
        },
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "done"

    force = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-sofia-mendez",
            "targetSceneId": "scene-lobby",
            "brief": "Quick errand",
        },
    ).json()
    fid = force["commissionId"]
    skipped = client.patch(
        f"/api/v1/worlds/{world_id}/commissions/{fid}",
        json={"status": "done", "forceCompleteReason": "Operator abandoned errand"},
    )
    assert skipped.status_code == 200
