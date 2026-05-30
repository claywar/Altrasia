"""image_generate tool policy gates."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from altrasia.config import Settings
from altrasia.services import AppServices
from altrasia.tools.registry import ToolContext


@pytest.mark.asyncio
async def test_image_generate_denylist(tmp_path: Path) -> None:
    svc = AppServices.create(Settings(db_path=tmp_path / "t.db"))
    ctx = ToolContext(
        world_id="w1",
        scene_id="s1",
        character_id="c1",
        services=svc,
        job_id="j1",
        message_id="m1",
        commission_id=None,
    )
    tool = svc.tools._tools["image_generate"]
    out = await tool.handler({"workflowId": "invalid", "prompt": "test"}, ctx)
    assert out.get("ok") is False
    assert "IMG-9" in str(out.get("error", ""))


@pytest.mark.asyncio
async def test_image_generate_cast_blocked(tmp_path: Path) -> None:
    svc = AppServices.create(Settings(db_path=tmp_path / "t2.db"))
    svc.store.insert_world(
        {
            "worldId": "w1",
            "name": "T",
            "activeSceneId": "s1",
            "defaultModelProfile": "default",
            "configJson": '{"allowCastImageGen": false}',
            "worldMapJson": "{}",
            "eventSeq": 0,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
    )
    ctx = ToolContext(
        world_id="w1",
        scene_id="s1",
        character_id="c1",
        services=svc,
        job_id="j1",
        message_id="m1",
        commission_id=None,
    )
    tool = svc.tools._tools["image_generate"]
    out = await tool.handler({"prompt": "a scene"}, ctx)
    assert out.get("ok") is False
    assert "IMG-7" in str(out.get("error", ""))


@pytest.mark.asyncio
async def test_image_generate_mock_when_no_comfy(tmp_path: Path) -> None:
    svc = AppServices.create(Settings(db_path=tmp_path / "t3.db", comfy_url=None))
    svc.store.insert_world(
        {
            "worldId": "w1",
            "name": "T",
            "activeSceneId": "s1",
            "defaultModelProfile": "default",
            "configJson": '{"allowCastImageGen": true}',
            "worldMapJson": "{}",
            "eventSeq": 0,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
    )
    ctx = ToolContext(
        world_id="w1",
        scene_id="s1",
        character_id="c1",
        services=svc,
        job_id="j1",
        message_id="m1",
        commission_id=None,
    )
    tool = svc.tools._tools["image_generate"]
    out = await tool.handler({"prompt": "sunset over mountains"}, ctx)
    assert out.get("mock") is True
