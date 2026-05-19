"""MAP tool and validator tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.map_layout_validator import check_readiness
from altrasia.persistence.sqlite_store import SqlitePersistence


def test_spatial_graph_edge_fields(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "maptools.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    graph = client.get(f"/api/v1/worlds/{w['worldId']}/spatial-graph").json()
    assert graph["edges"]
    edge = graph["edges"][0]
    assert edge.get("travelSteps") == 1
    assert edge.get("direction") in ("N", "S", "E", "W", "NE", "NW", "SE", "SW", "U", "D")
    assert edge.get("doorState") == "closed"
    assert graph["structures"][0].get("boundary")


def test_layout_draft_insufficient_framing(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "maptools2.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    w = client.post("/api/v1/worlds", json={"name": "Empty"}).json()
    world_id = w["worldId"]
    r = client.post(
        f"/api/v1/worlds/{world_id}/layout-drafts",
        json={"brief": "x", "scope": "mini"},
    )
    assert r.status_code == 400


def test_readiness_single_scene(tmp_path: Path) -> None:
    store = SqlitePersistence(tmp_path / "r.db")
    store.migrate()
    store.insert_world(
        {
            "worldId": "w1",
            "name": "T",
            "activeSceneId": "s1",
            "defaultModelProfile": "mock",
            "configJson": "{}",
            "worldMapJson": None,
            "eventSeq": 0,
            "createdAt": "t",
            "updatedAt": "t",
        }
    )
    store.insert_scene(
        {
            "sceneId": "s1",
            "worldId": "w1",
            "structureId": None,
            "mapLevel": 0,
            "levelLabel": None,
            "planPositionJson": None,
            "mapArtifactJson": None,
            "locationName": "Only",
            "locationDescription": "",
            "layoutHintsJson": "{}",
            "exitsJson": "[]",
            "presentJson": "[]",
            "fixturesJson": "{}",
            "activityJson": None,
            "roundRobinIndex": 0,
            "updatedAt": "t",
        }
    )
    r = check_readiness(store, "w1", "mini", "")
    assert r["ready"] is False
    assert r["code"] == "insufficient_framing"
