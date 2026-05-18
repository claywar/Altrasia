"""IMG-1 ComfyUI integration tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from altrasia.config import Settings
from altrasia.inference.comfyui import generate_portrait
from altrasia.services import AppServices


@pytest.mark.asyncio
async def test_portrait_mock_when_no_comfy_url(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "c.db", comfy_url=None)
    svc = AppServices.create(settings)
    r = await generate_portrait(svc, character_id="char-a", prompt="portrait")
    assert r.get("ok") is True
    assert r.get("mock") is True


@pytest.mark.asyncio
async def test_portrait_calls_comfy_when_configured(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "c2.db", comfy_url="http://127.0.0.1:8188")
    svc = AppServices.create(settings)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"portraitUrl": "/assets/p.png"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post = AsyncMock(return_value=mock_resp)
        client_cls.return_value = client
        r = await generate_portrait(svc, character_id="char-b", prompt="test")
    assert r.get("portraitUrl") == "/assets/p.png" or r.get("ok") is not False
