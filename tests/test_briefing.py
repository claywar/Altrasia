"""Briefing fixture + world pool mirror."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_briefing_fixture_and_world_pool(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "brief.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall = "scene-hall"
    out = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/briefing",
        json={"text": "Meeting at dusk. Doors locked.", "fixtureKey": "board"},
    ).json()
    assert out["locusKey"] == f"briefing:{hall}:board"
    scene = client.get(f"/api/v1/worlds/{world_id}/scenes/{hall}").json()
    import json

    fixtures = json.loads(scene["fixturesJson"])
    assert fixtures["board"]["kind"] == "briefing"
