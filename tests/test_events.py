from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_event_seq_increments(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "ev.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    client.post(
        f"/api/v1/worlds/{w['worldId']}/signals",
        json={
            "kind": "knock",
            "sourceSceneId": "scene-lobby",
            "targetSceneId": "scene-conference-room",
        },
    )
    world = client.get(f"/api/v1/worlds/{w['worldId']}").json()
    assert world["eventSeq"] >= 1
