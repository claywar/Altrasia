from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

ToolHandler = Callable[[dict[str, Any], "ToolContext"], Awaitable[Any]]


@dataclass
class ToolContext:
    world_id: str
    scene_id: str
    character_id: str
    services: Any
    commission_id: str | None = None
    message_id: str | None = None


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def list_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    async def invoke(self, name: str, params: dict[str, Any], ctx: ToolContext) -> str:
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"unknown tool {name}"})
        result = await tool.handler(params, ctx)
        if isinstance(result, str):
            return result
        return json.dumps(result)
