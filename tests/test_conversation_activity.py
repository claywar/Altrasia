"""Conversation overlay and operator banter REST (AO-22-full)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.debate_activity import get_active_banter
from tests.conftest import make_test_settings, wait_for_jobs


def test_conversation_start_and_turn(tmp_path: Path) -> None:
    with TestClient(create_app(make_test_settings(tmp_path, "conv.db"))) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        hall = "scene-lobby"
        order = ["char-jordan-reyes", "char-sofia-chen"]
        for cid in order:
            client.post(
                f"/api/v1/worlds/{world_id}/scenes/{hall}/presence/join",
                json={"characterId": cid},
            )

        started = client.post(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/conversation",
            json={"speakingOrder": order, "topic": "Sprint planning"},
        ).json()
        assert started["activity"]["kind"] == "conversation"
        assert started["activity"]["topic"] == "Sprint planning"
        if started.get("generationJob"):
            wait_for_jobs(client, world_id)

        conv = client.get(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/conversation"
        ).json()
        assert conv["activity"] is not None

        client.delete(f"/api/v1/worlds/{world_id}/scenes/{hall}/conversation")
        cleared = client.get(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/conversation"
        ).json()
        assert cleared["activity"] is None


def test_operator_banter_start(tmp_path: Path) -> None:
    with TestClient(create_app(make_test_settings(tmp_path, "banter-op.db"))) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        hall = "scene-lobby"
        order = ["char-jordan-reyes", "char-sofia-chen"]
        for cid in order:
            client.post(
                f"/api/v1/worlds/{world_id}/scenes/{hall}/presence/join",
                json={"characterId": cid},
            )
        started = client.post(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/banter",
            json={"speakingOrder": order, "turnsRemaining": 2},
        ).json()
        assert started["activity"]["kind"] == "banter"
        store = client.app.state.services.store  # type: ignore[attr-defined]
        scene = store.get_scene(hall)
        assert get_active_banter(scene) is not None
        client.delete(f"/api/v1/worlds/{world_id}/scenes/{hall}/banter")
        scene2 = store.get_scene(hall)
        assert get_active_banter(scene2) is None


def test_activity_framing_line(tmp_path: Path) -> None:
    from altrasia.debate_activity import start_conversation
    from altrasia.fixtures.loader import load_fixture_by_id
    from altrasia.prompt.scene_framing import build_scene_framing
    from altrasia.services import AppServices
    from altrasia.config import Settings

    settings = Settings(
        db_path=tmp_path / "act-frame.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    world_id = meta["worldId"]
    scene_id = "scene-lobby"
    svc.presence.join(scene_id, "char-jordan-reyes")
    start_conversation(
        svc.store,
        scene_id,
        speaking_order=["char-jordan-reyes"],
        topic="Coffee run",
    )
    framing = build_scene_framing(
        svc.store,
        svc.presence,
        world_id=world_id,
        character_id="char-jordan-reyes",
        scene_id=scene_id,
    )
    assert "Activity: conversation" in framing
    assert "Coffee run" in framing
