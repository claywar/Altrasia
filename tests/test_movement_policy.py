"""Movement only on explicit summon or per-character self-decision."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.narrative_presence import detect_narrative_presence
from altrasia.tools.cast_tools import (
    AMBIENT_MOVEMENT_TRIGGERS,
    cast_allowed_tool_names,
    narrative_presence_eligible,
)


@pytest.fixture
def svc(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "move.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc.app.state.services


def test_idle_trigger_is_ambient() -> None:
    assert "idle_timer" in AMBIENT_MOVEMENT_TRIGGERS
    assert not narrative_presence_eligible("idle_timer")
    assert narrative_presence_eligible("persona_message")


def test_idle_jobs_exclude_scene_summon(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    allowed = cast_allowed_tool_names(
        svc.store,
        world_id,
        "char-jordan-reyes",
        trigger="idle_timer",
    )
    assert allowed is not None
    assert "scene_join" in allowed
    assert "scene_summon" not in allowed


def test_reactive_leadership_still_has_scene_summon(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    allowed = cast_allowed_tool_names(
        svc.store,
        world_id,
        "char-jordan-reyes",
        trigger="persona_message",
    )
    assert allowed is not None
    assert "scene_summon" in allowed


def test_narrative_no_bulk_team_summon(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    cfg = {
        "narrativePresenceMode": "auto",
        "castSummonEnabled": True,
        "summonRoles": ["cto", "director"],
    }
    detection = detect_narrative_presence(
        svc,
        world_id=world_id,
        speaker_id="char-jordan-reyes",
        scene_id="scene-lobby",
        output_text="I'll gather the team and directors here in the lobby.",
        cfg=cfg,
    )
    assert detection is None


def test_narrative_named_summon_requires_destination(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    cfg = {
        "narrativePresenceMode": "auto",
        "castSummonEnabled": True,
        "summonRoles": ["cto", "director"],
    }
    without_dest = detect_narrative_presence(
        svc,
        world_id=world_id,
        speaker_id="char-jordan-reyes",
        scene_id="scene-lobby",
        output_text="Sofia Mendez and Liam Park should join us soon.",
        cfg=cfg,
    )
    assert without_dest is None

    with_dest = detect_narrative_presence(
        svc,
        world_id=world_id,
        speaker_id="char-jordan-reyes",
        scene_id="scene-lobby",
        output_text=(
            "Sofia Mendez and Liam Park, meet me in the Conference Room in five minutes."
        ),
        cfg=cfg,
    )
    assert with_dest is not None
    assert any(a["kind"] == "summon" for a in with_dest["actions"])
