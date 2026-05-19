"""Narrative presence fallback when model prose implies movement without tools."""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.narrative_presence import apply_narrative_presence, detect_narrative_presence
from altrasia.domain.presence import PresenceService


@pytest.fixture
def svc(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "np.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc.app.state.services


def test_narrative_presence_auto_summons_from_prose(svc) -> None:
    from altrasia.fixtures.loader import load_fixture_by_id

    loaded = load_fixture_by_id(svc.store, svc.settings.fixtures_dir, "demo-spatial-v1")
    world_id = loaded["worldId"]
    cfg = {
        "narrativePresenceMode": "auto",
        "castSummonEnabled": True,
        "summonRoles": ["cto", "director"],
    }
    svc.store.update_world(world_id, configJson=__import__("json").dumps(cfg))

    detection = detect_narrative_presence(
        svc,
        world_id=world_id,
        speaker_id="char-jordan-reyes",
        scene_id="scene-lobby",
        output_text=(
            "I'll pull Sofia Mendez and Liam Park to the conference room. "
            "Meet me in the Conference Room in five minutes."
        ),
        cfg=cfg,
    )
    assert detection is not None
    assert any(a["kind"] == "summon" for a in detection["actions"])

    asyncio.run(
        apply_narrative_presence(
            svc,
            world_id=world_id,
            detection=detection,
            speaker_id="char-jordan-reyes",
            source_scene_id="scene-lobby",
        )
    )
    present = PresenceService.parse_present(
        svc.store.get_scene("scene-conference-room")["presentJson"]
    )
    assert "char-sofia-mendez" in present

    import json

    from altrasia.domain.presence_announce import maybe_announce_summons_from_tool_log

    tool_log = [
        {
            "name": "scene_summon",
            "arguments": {
                "targetSceneId": "scene-conference-room",
                "characterIds": ["char-sofia-mendez", "char-liam-park"],
            },
            "result": "narrative_presence",
        }
    ]
    job = {
        "worldId": world_id,
        "characterId": "char-jordan-reyes",
        "sceneId": "scene-lobby",
    }
    asyncio.run(maybe_announce_summons_from_tool_log(svc, job, tool_log))
    lobby_msgs = svc.store.list_messages(world_id, scene_id="scene-lobby")
    announce = [
        m
        for m in lobby_msgs
        if json.loads(m["metaJson"]).get("orchestration", {}).get("kind") == "presence_announce"
    ]
    assert announce
    assert json.loads(announce[0]["metaJson"])["presence"]["source"] == "narrative"
