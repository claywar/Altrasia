"""Fixture and inventory tool handlers."""

import json
from pathlib import Path

import pytest

from altrasia.config import Settings
from altrasia.tools.registry import ToolContext


@pytest.fixture
def tool_ctx(tmp_path: Path) -> tuple:
    settings = Settings(
        db_path=tmp_path / "tools.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    from altrasia.services import AppServices

    svc = AppServices.create(settings)
    world_id = "w-tools"
    svc.store.insert_world(
        {
            "worldId": world_id,
            "name": "Tools",
            "activeSceneId": "scene-a",
            "defaultModelProfile": "mock",
            "configJson": "{}",
            "worldMapJson": None,
            "eventSeq": 0,
            "createdAt": "2026-01-01T00:00:00+00:00",
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.insert_scene(
        {
            "sceneId": "scene-a",
            "worldId": world_id,
            "structureId": None,
            "mapLevel": 0,
            "levelLabel": None,
            "planPositionJson": None,
            "mapArtifactJson": None,
            "locationName": "Room A",
            "locationDescription": "",
            "presentJson": '["char-a"]',
            "fixturesJson": json.dumps(
                {
                    "herbs": {
                        "label": "Herb rack",
                        "kind": "aggregate",
                        "picksRemaining": 2,
                        "defaultPicks": 2,
                        "yield": {"label": "dried herbs"},
                    },
                    "mug": {
                        "label": "Mug",
                        "kind": "discrete",
                        "portable": True,
                    },
                }
            ),
            "exitsJson": "[]",
            "activityJson": None,
            "roundRobinIndex": 0,
            "layoutHintsJson": None,
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.insert_character(
        {
            "characterId": "char-a",
            "displayName": "Alice",
            "definitionJson": "{}",
            "modelProfile": "mock",
            "speechWeight": 0.5,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.add_world_member(world_id, "char-a")
    ctx = ToolContext(
        world_id=world_id,
        scene_id="scene-a",
        character_id="char-a",
        services=svc,
        commission_id=None,
    )
    return svc, ctx


@pytest.mark.asyncio
async def test_fixture_harvest_and_pickup(tool_ctx) -> None:
    svc, ctx = tool_ctx
    harvest = svc.tools._tools["scene_fixture_harvest"]
    out = await harvest.handler({"fixtureKey": "herbs"}, ctx)
    assert out["ok"] is True
    assert out["picksRemaining"] == 1

    pickup = svc.tools._tools["scene_fixture_pickup"]
    out2 = await pickup.handler({"fixtureKey": "mug"}, ctx)
    assert out2["ok"] is True
    scene = svc.store.get_scene("scene-a")
    fixtures = json.loads(scene["fixturesJson"])
    assert "mug" not in fixtures


@pytest.mark.asyncio
async def test_fixture_describe(tool_ctx) -> None:
    svc, ctx = tool_ctx
    describe = svc.tools._tools["scene_fixture_describe"]
    out = await describe.handler({"fixtureKey": "herbs"}, ctx)
    assert out["fixture"]["kind"] == "aggregate"
