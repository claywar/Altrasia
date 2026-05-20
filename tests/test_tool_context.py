"""Prompt injection for per-generation tool exposure."""

from altrasia.prompt.tool_context import (
    DEFAULT_TOOL_DESCRIPTION,
    format_available_tools_addendum,
    tool_description,
)


def _tool(name: str, description: str | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_tool_description_defaults_when_missing() -> None:
    assert tool_description(_tool("memory_search", "")) == DEFAULT_TOOL_DESCRIPTION
    assert tool_description(_tool("memory_search", None)) == DEFAULT_TOOL_DESCRIPTION
    assert tool_description(_tool("memory_search", "  find facts  ")) == "find facts"


def test_format_available_tools_addendum_lists_current_and_deferred() -> None:
    text = format_available_tools_addendum(
        [_tool("memory_search", "Search mind pool")],
        deferred_tools=[_tool("webtools_invoke", "Fetch URL or search web")],
    )
    assert "## Available tools" in text
    assert "**memory_search**: Search mind pool" in text
    assert "memory_search or diary_search" in text
    assert "**webtools_invoke**: Fetch URL or search web" in text
    assert "firewall" in text


def test_format_empty_when_no_tools() -> None:
    assert format_available_tools_addendum([]) == ""
