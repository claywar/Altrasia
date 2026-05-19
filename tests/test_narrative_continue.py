"""Narrative auto-summon must not block agent_continue; tab idle stays on active scene."""

from __future__ import annotations

from pathlib import Path

import pytest

from altrasia.orchestrator.briefing_chain import movement_tools_ran
from altrasia.orchestrator.engine import Orchestrator


def test_narrative_presence_summon_does_not_block_continue() -> None:
    tool_log = [
        {
            "name": "scene_summon",
            "arguments": {"targetSceneId": "scene-lobby", "characterIds": ["char-liam-park"]},
            "result": "narrative_presence",
        }
    ]
    assert not movement_tools_ran(tool_log)


def test_real_scene_summon_still_blocks_continue() -> None:
    tool_log = [
        {
            "name": "scene_summon",
            "arguments": {"targetSceneId": "scene-lobby"},
            "result": '{"ok": true}',
        }
    ]
    assert movement_tools_ran(tool_log)


def test_should_enqueue_continue_after_narrative_summon(tmp_path: Path) -> None:
    from altrasia.api.app import create_app
    from altrasia.config import Settings
    from fastapi.testclient import TestClient

    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "narr.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        orch: Orchestrator = client.app.state.services.orchestrator
        job = {
            "worldId": world_id,
            "trigger": "persona_message",
            "continueDepth": 0,
        }
        tool_log = [
            {
                "name": "scene_summon",
                "result": "narrative_presence",
                "arguments": {},
            }
        ]
        assert orch._should_enqueue_agent_continue(
            job,
            debate_active=False,
            tool_log=tool_log,
            max_depth=2,
        )
