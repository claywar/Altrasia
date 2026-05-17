from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        data_dir=tmp_path,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_load_fixture_world(client: TestClient) -> None:
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    assert r.status_code == 200
    world_id = r.json()["worldId"]
    r2 = client.get(f"/api/v1/worlds/{world_id}/spatial-graph")
    assert r2.status_code == 200
    assert len(r2.json()["nodes"]) == 2


def test_knock_no_generation(client: TestClient) -> None:
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    client.post(
        f"/api/v1/worlds/{world_id}/signals",
        json={
            "kind": "knock",
            "sourceSceneId": "scene-hall",
            "targetSceneId": "scene-kitchen",
        },
    )
    q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
    assert q["depth"] == 0 or not q.get("currentJob")
