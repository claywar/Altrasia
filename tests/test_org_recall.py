"""Org recall and scene framing for leadership roles."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.presence import PresenceService
from altrasia.memory.org_recall import build_org_recall
from altrasia.prompt.scene_framing import build_scene_framing


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    db = tmp_path / "org.db"
    settings = Settings(
        data_dir=db.parent,
        db_path=db,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc, tc.app.state.services


def test_org_recall_lists_cast_for_cto(client: tuple[TestClient, object]) -> None:
    tc, svc = client
    world_id = tc.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()["worldId"]
    recall = build_org_recall(
        svc.store,
        PresenceService(svc.store),
        world_id=world_id,
        character_id="char-jordan-reyes",
        max_chars=8000,
    )
    assert "## Organization roster" in recall
    assert "Sofia Mendez" in recall
    assert "Liam Park" in recall
    assert "Sarah" not in recall


def test_scene_framing_includes_elsewhere_for_cto(client: tuple[TestClient, object]) -> None:
    tc, svc = client
    world_id = tc.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()["worldId"]
    framing = build_scene_framing(
        svc.store,
        svc.presence,
        world_id=world_id,
        character_id="char-jordan-reyes",
        scene_id="scene-lobby",
    )
    assert "Elsewhere" in framing or "Locations in this world" in framing
    assert "Conference Room" in framing or "scene-conference-room" in framing
