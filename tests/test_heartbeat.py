"""HB-1 global heartbeat idle when UI disconnected."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings(
        data_dir=tmp_path,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app), app.state.services


@pytest.mark.asyncio
async def test_hb1_heartbeat_idle_without_websocket(client: tuple[TestClient, object]) -> None:
    client, services = client
    services.operator_settings.patch(
        {"heartbeat": {"enabled": True, "intervalSeconds": 5}}
    )
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    assert world_id not in services.idle_scheduler._active_worlds
    await services.idle_scheduler._heartbeat_tick()
    row = services.store.conn.execute(
        """SELECT trigger, selectionRationaleJson FROM GenerationJob
           WHERE worldId = ? AND trigger = 'idle_timer' ORDER BY createdAt DESC LIMIT 1""",
        (world_id,),
    ).fetchone()
    assert row is not None
    rationale = json.loads(row[1])
    assert rationale.get("idle_source") == "server_heartbeat"


def test_operator_settings_patch(client: tuple[TestClient, object]) -> None:
    client, _ = client
    r = client.patch(
        "/api/v1/operator/settings",
        json={"heartbeat": {"enabled": True, "intervalSeconds": 90}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["heartbeat"]["enabled"] is True
    assert body["heartbeat"]["intervalSeconds"] == 90
    r2 = client.get("/api/v1/operator/settings")
    assert r2.json()["heartbeat"]["enabled"] is True
