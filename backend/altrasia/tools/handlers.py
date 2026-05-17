from __future__ import annotations

import json
from typing import Any

from altrasia.tools.registry import ToolContext, ToolDef, ToolRegistry


def register_core_tools(registry: ToolRegistry, services: Any) -> None:
    mem = services.memory

    async def memory_search(params: dict, ctx: ToolContext) -> Any:
        return mem.memory_search(
            pool="mind",
            owner_id=ctx.character_id,
            query=params.get("query", ""),
            limit=int(params.get("limit", 10)),
        )

    async def memory_store(params: dict, ctx: ToolContext) -> Any:
        return mem.memory_store(
            pool="mind",
            owner_id=ctx.character_id,
            locus_key=params["locusKey"],
            value=params["value"],
        )

    async def diary_search(params: dict, ctx: ToolContext) -> Any:
        return mem.diary_search(
            character_id=ctx.character_id,
            query=params.get("query", ""),
            limit=int(params.get("limit", 10)),
        )

    async def scene_update_fixture(params: dict, ctx: ToolContext) -> Any:
        scene = services.store.get_scene(ctx.scene_id)
        fixtures = json.loads(scene["fixturesJson"])
        key = params["fixtureKey"]
        fixtures[key] = params.get("fixture", fixtures.get(key, {}))
        services.store.update_scene(ctx.scene_id, fixturesJson=json.dumps(fixtures))
        return {"ok": True, "fixtureKey": key}

    registry.register(
        ToolDef(
            name="memory_search",
            description="Search this character's mind loci (FTS).",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["query"],
            },
            handler=memory_search,
        )
    )
    registry.register(
        ToolDef(
            name="memory_store",
            description="Store a fact in mind pool (output text only).",
            parameters={
                "type": "object",
                "properties": {
                    "locusKey": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["locusKey", "value"],
            },
            handler=memory_store,
        )
    )
    registry.register(
        ToolDef(
            name="diary_search",
            description="Search witnessed diary segments.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["query"],
            },
            handler=diary_search,
        )
    )
    registry.register(
        ToolDef(
            name="scene_update_fixture",
            description="Update a scene fixture (Observer/architect).",
            parameters={
                "type": "object",
                "properties": {
                    "fixtureKey": {"type": "string"},
                    "fixture": {"type": "object"},
                },
                "required": ["fixtureKey", "fixture"],
            },
            handler=scene_update_fixture,
        )
    )
