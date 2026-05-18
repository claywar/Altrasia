from __future__ import annotations

import importlib.util
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from altrasia.tools.registry import ToolDef, ToolRegistry

log = logging.getLogger(__name__)

HookFn = Callable[..., Awaitable[Any] | Any]


@dataclass
class PluginManifest:
    id: str
    version: str = "0.0.0"
    hooks: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


@dataclass
class PluginContext:
    world_id: str
    character_id: str | None = None
    scene_id: str | None = None


class PluginHost:
    """PL-1–PL-3: discover and register local plugins."""

    def __init__(self) -> None:
        self.manifests: list[PluginManifest] = []
        self._hooks: dict[str, list[HookFn]] = {
            "onGenerationStart": [],
            "onToolInvoke": [],
            "onMessageAppend": [],
            "onApprovalRequired": [],
        }

    def register_hook(self, name: str, fn: HookFn) -> None:
        if name in self._hooks:
            self._hooks[name].append(fn)

    async def run_hook(self, name: str, ctx: PluginContext, payload: dict[str, Any]) -> None:
        for fn in self._hooks.get(name, []):
            try:
                result = fn(ctx, payload)
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                log.warning("plugin hook %s failed: %s", name, exc)

    def register_tools(self, registry: ToolRegistry, tools: list[ToolDef]) -> None:
        for t in tools:
            registry.register(t)


def _load_manifest(path: Path) -> PluginManifest | None:
    mf = path / "manifest.json"
    if not mf.exists():
        return None
    raw = json.loads(mf.read_text(encoding="utf-8"))
    return PluginManifest(
        id=str(raw.get("id", path.name)),
        version=str(raw.get("version", "0.0.0")),
        hooks=list(raw.get("hooks", [])),
        tools=list(raw.get("tools", [])),
        permissions=list(raw.get("permissions", [])),
    )


def _import_plugin_module(path: Path) -> Any | None:
    main = path / "plugin.py"
    if not main.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"altrasia_plugin_{path.name}", main)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover_plugin_dirs(settings: Any) -> list[Path]:
    dirs: list[Path] = []
    home = Path.home() / ".altrasia" / "plugins"
    if home.is_dir():
        dirs.extend(p for p in home.iterdir() if p.is_dir())
    project = settings.fixtures_dir.parent.parent / "plugins"
    if project.is_dir():
        dirs.extend(p for p in project.iterdir() if p.is_dir())
    return dirs


def load_plugins(host: PluginHost, registry: ToolRegistry, services: Any) -> list[PluginManifest]:
    if not services.operator_settings.load_plugins_enabled(services.settings):
        return []
    loaded: list[PluginManifest] = []
    for path in discover_plugin_dirs(services.settings):
        manifest = _load_manifest(path)
        if not manifest:
            continue
        mod = _import_plugin_module(path)
        if mod and hasattr(mod, "register"):
            try:
                mod.register(host, registry, services)
                loaded.append(manifest)
                host.manifests.append(manifest)
            except Exception as exc:
                log.warning("plugin %s register failed: %s", path.name, exc)
    return loaded
