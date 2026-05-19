"""MP-22 world commons recall gating."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_commons_gated_recall(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "commons.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall = "scene-lobby"
    client.put(
        f"/api/v1/worlds/{world_id}/commons",
        json={"key": "charter", "text": "No fires in the hall."},
    )
    client.patch(
        f"/api/v1/worlds/{world_id}/policy",
        json={"commonsAccessIds": ["char-jordan-reyes"]},
    )
    recall_alice = svc.memory.build_mandatory_recall(
        character_id="char-jordan-reyes",
        scene_id=hall,
        world_id=world_id,
    )
    recall_bob = svc.memory.build_mandatory_recall(
        character_id="char-sofia-mendez",
        scene_id=hall,
        world_id=world_id,
    )
    assert "commons" in recall_alice
    assert "No fires in the hall" in recall_alice
    assert "commons" not in recall_bob.lower() or "No fires" not in recall_bob
