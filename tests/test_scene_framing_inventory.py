"""LP-3: scene framing includes inventory summaries."""

from pathlib import Path

from altrasia.config import Settings
from altrasia.domain.presence import PresenceService
from altrasia.prompt.scene_framing import build_scene_framing
from altrasia.services import AppServices


def test_scene_framing_includes_inventory(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "frame.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    from altrasia.fixtures.loader import load_fixture_by_id

    load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    world_id = "demo-spatial-v1"
    world = svc.store.get_world(world_id)
    scene_id = world["activeSceneId"]
    presence = PresenceService(svc.store)
    presence.join(scene_id, "char-jordan-reyes")
    framing = build_scene_framing(
        svc.store,
        presence,
        world_id=world_id,
        character_id="char-jordan-reyes",
        scene_id=scene_id,
    )
    assert "Present:" in framing
    assert "blazer" in framing.lower() or "tablet" in framing.lower()
    assert "aggregate" in framing.lower() or "discrete" in framing.lower()
