"""MAP-GEN-ACC / MAP-ACC topology tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_spatial_graph_has_layout_fields(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "mapacc.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    graph = client.get(f"/api/v1/worlds/{w['worldId']}/spatial-graph").json()
    assert len(graph["nodes"]) >= 2
    assert graph["layout"]["coordinateSpace"] == "normalized-0-100"
    assert graph["layout"]["architectureStyle"] == "blueprint"
    edge = next(e for e in graph["edges"] if e.get("direction") == "N")
    assert edge.get("travelSteps") == 1
    assert edge.get("exitAnchor") == "N"
    names = {s["displayName"] for s in graph["structures"]}
    assert "Vertex Labs HQ" in names
    assert len(graph["nodes"]) == 20
    hq_levels = {
        n.get("levelIndex")
        for n in graph["nodes"]
        if n.get("structureId") == "hq" and n.get("levelIndex") is not None
    }
    assert hq_levels == {0, 1}
    hq = next(s for s in graph["structures"] if s["structureId"] == "hq")
    assert hq["boundary"]["shape"] == "polygon"
    lobby = next(n for n in graph["nodes"] if n["sceneId"] == "scene-lobby")
    assert lobby.get("planPosition") is not None
    assert lobby.get("locationDescription")
    assert graph.get("layoutStatus") in ("complete", "partial")
    assert graph.get("worldMap") is not None
    assert len(graph["worldMap"].get("structurePlacements", [])) >= 1
    hq_nodes = [n for n in graph["nodes"] if n.get("structureId") == "hq"]
    assert len(hq_nodes) == 20
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "map-layouts"
    if fixtures_dir.exists():
        for f in fixtures_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            assert "nodes" in data or "scenes" in data
