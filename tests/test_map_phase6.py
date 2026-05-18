"""MAP-ACC / map artifact API (Phase 6 depth)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.map_artifacts import get_scene_artifact, get_world_site_artifact, put_artifact


def test_map_artifact_round_trip(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "map6.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    world_id = w["worldId"]
    scene_id = w["activeSceneId"]
    svc = app.state.services
    put_artifact(
        svc.store,
        world_id=world_id,
        kind="floor",
        scene_id=scene_id,
        payload={"fixtures": [], "bounds": {"w": 100, "h": 100}},
    )
    put_artifact(
        svc.store,
        world_id=world_id,
        kind="site",
        scene_id=None,
        payload={"structures": [{"id": "manor", "label": "Manor"}]},
    )
    floor = get_scene_artifact(svc.store, world_id, scene_id)
    site = get_world_site_artifact(svc.store, world_id)
    assert floor is not None
    assert site is not None
    assert site["structures"][0]["id"] == "manor"
    r = client.get(f"/api/v1/worlds/{world_id}/map-artifacts/site")
    assert r.status_code == 200
    assert r.json()["artifact"] is not None


def test_manor_fixture_topology() -> None:
    path = Path(__file__).resolve().parent / "fixtures" / "map-layouts" / "manor-envelope.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["nodes"]) >= 2
    assert data["edges"]
