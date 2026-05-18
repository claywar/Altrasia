"""Reference plugin (PL-5) wrapping SSRF-safe fetch."""

from __future__ import annotations

from typing import Any

from altrasia.tools.registry import ToolContext, ToolDef


def register(host: Any, registry: Any, services: Any) -> None:
    from altrasia.tools.web_fetch import safe_fetch

    async def web_fetch_plugin(params: dict, ctx: ToolContext) -> Any:
        url = params.get("url", "")
        return await safe_fetch(url, allowlist=services.settings.web_allowlist_set())

    registry.register(
        ToolDef(
            name="web_fetch_plugin",
            description="Plugin: fetch URL via allowlist (reference web-tools).",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            handler=web_fetch_plugin,
        )
    )
