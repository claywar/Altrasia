"""commission_tick scheduler while commission status is running."""

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.commission_runner import tick_running_commissions
from altrasia.commissions import ISO
from altrasia.config import Settings


def test_commission_tick_enqueues_while_running(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "ctick.db",
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

    created = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-alice",
            "targetSceneId": kitchen,
            "brief": "Inventory the spice rack.",
        },
    ).json()
    assert created["status"] == "blocked"
    cid = created["commissionId"]

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-alice"},
    )
    svc.store.update_commission(cid, status="running", updatedAt=ISO())

    result = asyncio.run(tick_running_commissions(svc, world_id))
    assert result is not None
    assert result["commissionId"] == cid

    row = svc.store.conn.execute(
        "SELECT trigger FROM GenerationJob WHERE worldId = ? ORDER BY createdAt DESC LIMIT 1",
        (world_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "commission_tick"
