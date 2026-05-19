"""Reference plugin (PL-5) wrapping SSRF-safe fetch."""

from __future__ import annotations

from typing import Any

from altrasia.tools.registry import ToolContext, ToolDef


def register(host: Any, registry: Any, services: Any) -> None:
    from altrasia.tools.web_fetch import safe_fetch

    async def web_fetch_plugin(params: dict, ctx: ToolContext) -> Any:
        from altrasia.tools.web_access import resolve_web_tools_policy

        policy = resolve_web_tools_policy(
            services.store, ctx.world_id, ctx.character_id
        )
        if not policy["exposed"]:
            return {"ok": False, "error": "web tools not enabled for this character"}
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
