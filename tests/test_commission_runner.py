"""COM-6 presence gate + minimal commission_started runtime."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from tests.conftest import wait_for_jobs as _wait_jobs


def test_commission_com6_and_runtime(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "crun.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    with TestClient(create_app(settings)) as client:
        _run_commission_com6(client)


def _run_commission_com6(client: TestClient) -> None:
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall, kitchen = "scene-lobby", "scene-conference-room"

    created = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-jordan-reyes",
            "targetSceneId": kitchen,
            "brief": "Summarize badge access anomalies for the conference room this week.",
        },
    ).json()
    assert created["status"] == "blocked"
    cid = created["commissionId"]

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-jordan-reyes"},
    )

    _wait_jobs(client, world_id, timeout=45.0)
    done = client.get(f"/api/v1/worlds/{world_id}/commissions").json()
    final = next(c for c in done if c["commissionId"] == cid)
    assert final["status"] == "done"
    assert len(final["deliverableLocusKeys"]) >= 1

    mind = client.get(
        f"/api/v1/worlds/{world_id}/characters/char-jordan-reyes/mind"
    ).json()
    assert any("commission:" in loc.get("locusKey", "") for loc in mind)

