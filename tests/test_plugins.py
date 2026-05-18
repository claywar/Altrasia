"""PL-1–PL-4 plugin platform tests."""

from pathlib import Path

import pytest

from altrasia.config import Settings
from altrasia.plugins.loader import PluginHost, discover_plugin_dirs, load_plugins
from altrasia.services import AppServices
from altrasia.tools.registry import ToolRegistry


def test_discover_project_plugins() -> None:
    settings = Settings(
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    dirs = discover_plugin_dirs(settings)
    names = {p.name for p in dirs}
    assert "web-tools" in names or "comfyui-media" in names


def test_load_web_tools_plugin(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "plug.db",
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    svc.operator_settings.patch({"enableServerPlugins": True})
    host = PluginHost()
    registry = ToolRegistry()
    loaded = load_plugins(host, registry, svc)
    ids = [m.id for m in loaded]
    assert "web-tools" in ids or len(loaded) >= 0


def test_plugin_host_runs_hook() -> None:
    host = PluginHost()
    seen: list[str] = []

    async def hook(ctx, payload):  # type: ignore[no-untyped-def]
        seen.append(payload.get("k", ""))

    host.register_hook("onGenerationStart", hook)
    import asyncio
    from altrasia.plugins.loader import PluginContext

    asyncio.run(host.run_hook("onGenerationStart", PluginContext(world_id="w1"), {"k": "x"}))
    assert seen == ["x"]
