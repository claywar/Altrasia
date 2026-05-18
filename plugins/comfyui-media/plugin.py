"""Optional ComfyUI plugin hook (PL-6)."""

from __future__ import annotations

from typing import Any


def register(host: Any, registry: Any, services: Any) -> None:
    if not services.settings.comfy_url:
        return

    async def on_gen(ctx: Any, payload: dict) -> None:
        pass

    host.register_hook("onGenerationStart", on_gen)
