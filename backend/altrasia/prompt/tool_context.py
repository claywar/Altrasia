from __future__ import annotations

from typing import Any

DEFAULT_TOOL_DESCRIPTION = "Callable function tool (no description provided)."


def tool_description(tool: dict[str, Any]) -> str:
    fn = tool.get("function") or {}
    raw = fn.get("description")
    if raw is None:
        return DEFAULT_TOOL_DESCRIPTION
    text = str(raw).strip()
    return text or DEFAULT_TOOL_DESCRIPTION


def tool_name(tool: dict[str, Any]) -> str:
    fn = tool.get("function") or {}
    return str(fn.get("name") or "").strip()


def format_available_tools_addendum(
    tools_payload: list[dict[str, Any]],
    *,
    deferred_tools: list[dict[str, Any]] | None = None,
) -> str:
    """Model-facing summary of tools exposed for this generation round."""
    deferred_tools = deferred_tools or []
    if not tools_payload and not deferred_tools:
        return ""

    lines = [
        "## Available tools",
        (
            "You may call these tools via tool_calls when needed. Do not claim you "
            "lack a capability listed here (for example, do not invent firewall or "
            "permission blocks if webtools_invoke is available)."
        ),
    ]

    for t in sorted(tools_payload, key=tool_name):
        name = tool_name(t)
        if not name:
            continue
        lines.append(f"- **{name}**: {tool_description(t)}")

    if deferred_tools:
        lines.append("")
        lines.append(
            "After you call memory_search or diary_search once this turn, these "
            "tools also become callable:"
        )
        for t in sorted(deferred_tools, key=tool_name):
            name = tool_name(t)
            if not name:
                continue
            lines.append(f"- **{name}**: {tool_description(t)}")

    return "\n".join(lines)
