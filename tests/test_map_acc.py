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
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "map-layouts"
    if fixtures_dir.exists():
        for f in fixtures_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            assert "nodes" in data or "scenes" in data
