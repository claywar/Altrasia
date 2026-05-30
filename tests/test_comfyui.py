"""ComfyUI client and pipeline tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from altrasia.config import Settings
from altrasia.inference.comfyui import generate_portrait
from altrasia.inference.comfyui.workflows import build_prompt_for_profile, load_workflow_file
from altrasia.inference.comfyui.profiles import ImageProfileRegistry
from altrasia.services import AppServices


@pytest.mark.asyncio
async def test_portrait_mock_when_no_comfy_url(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "c.db", comfy_url=None)
    svc = AppServices.create(settings)
    r = await generate_portrait(
        svc, world_id="w1", character_id="char-a", prompt="portrait"
    )
    assert r.get("ok") is True
    assert r.get("mock") is True


def test_workflow_inject_sdxl() -> None:
    reg = ImageProfileRegistry(Path.home() / ".altrasia")
    profile = reg.get("sdxl-default")
    assert profile is not None
    meta, prompt = build_prompt_for_profile(
        "character_portrait", profile, positive_prompt="hero portrait", seed=42
    )
    assert meta["family"] == "sdxl"
    assert prompt["6"]["inputs"]["text"] == "hero portrait"
    assert prompt["3"]["inputs"]["seed"] == 42


@pytest.mark.asyncio
async def test_portrait_saves_asset_when_comfy_mocked(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "c2.db", comfy_url="http://127.0.0.1:8188")
    svc = AppServices.create(settings)
    svc.store.insert_world(
        {
            "worldId": "w1",
            "name": "T",
            "activeSceneId": "s1",
            "defaultModelProfile": "default",
            "configJson": "{}",
            "worldMapJson": "{}",
            "eventSeq": 0,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
    )
    svc.store.insert_character(
        {
            "characterId": "char-b",
            "displayName": "Bob",
            "definitionJson": "{}",
            "modelProfile": "default",
            "speechWeight": 1.0,
            "createdAt": "2026-01-01T00:00:00Z",
        }
    )
    fake_png = b"\x89PNG\r\n\x1a\nfake"

    with patch(
        "altrasia.inference.comfyui.pipeline.ComfyUiClient.run_prompt_to_image",
        new_callable=AsyncMock,
        return_value=fake_png,
    ):
        r = await generate_portrait(
            svc, world_id="w1", character_id="char-b", prompt="test portrait"
        )
    assert r.get("ok") is True
    assert r.get("assetId")
    assert r.get("portraitUrl")
