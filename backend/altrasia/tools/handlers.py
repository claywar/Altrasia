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
        out = mem.memory_store(
            pool="mind",
            owner_id=ctx.character_id,
            locus_key=params["locusKey"],
            value=params["value"],
        )
        services.embeddings.schedule_embed(
            owner_scope="mind",
            owner_id=ctx.character_id,
            source_type="locus",
            source_ref=params["locusKey"],
            text=params["value"],
        )
        from altrasia.evidence import record_evidence

        kind = "commission" if ctx.commission_id else "dialogue"
        record_evidence(
            services.store,
            locus_key=params["locusKey"],
            pool="mind",
            owner_id=ctx.character_id,
            source_kind=kind,
            source_ref=params["locusKey"],
            commission_id=ctx.commission_id,
        )
        return out

    async def diary_search(params: dict, ctx: ToolContext) -> Any:
        return mem.diary_search(
            character_id=ctx.character_id,
            query=params.get("query", ""),
            limit=int(params.get("limit", 10)),
        )

    async def diary_read(params: dict, ctx: ToolContext) -> Any:
        limit = int(params.get("limit", 20))
        offset = int(params.get("offset", 0))
        rows = mem.store.list_diary(ctx.character_id, limit=limit + offset)
        page = rows[offset : offset + limit] if offset else rows[-limit:]
        return {
            "segments": [
                {"text": s["text"], "createdAt": s["createdAt"], "sourceSceneId": s["sourceSceneId"]}
                for s in page
            ]
        }

    async def memory_read(params: dict, ctx: ToolContext) -> Any:
        rows = services.store.conn.execute(
            """SELECT locusKey, value FROM Locus
               WHERE pool = 'mind' AND ownerId = ? AND locusKey = ?""",
            (ctx.character_id, params["locusKey"]),
        ).fetchall()
        if not rows:
            return {"found": False}
        return {"locusKey": rows[0][0], "value": rows[0][1]}

    async def webtools_invoke(params: dict, ctx: ToolContext) -> Any:
        from altrasia.approvals import (
            create_approval,
            mark_approval_applied,
            world_tool_policy,
        )
        from altrasia.tools.web_fetch import safe_fetch
        from altrasia.world_config import get_world_config

        query = (params.get("query") or params.get("url") or "").strip()
        policy = world_tool_policy(services.store, ctx.world_id)
        wcfg = get_world_config(services.store, ctx.world_id)
        use_mock = services.settings.web_tools_mock or wcfg.get("webToolsMock", True)
        if policy["requireWebToolApproval"]:
            approval = create_approval(
                services.store,
                world_id=ctx.world_id,
                tool_name="webtools_invoke",
                params=params,
                state="pending",
            )
            services.event_bus.emit(
                services.store,
                ctx.world_id,
                "approval.updated",
                {"approvalId": approval["approvalId"], "state": "pending"},
            )
            return {
                "ok": False,
                "approvalRequired": True,
                "approvalId": approval["approvalId"],
                "message": "Operator must approve this web fetch before results are available.",
            }
        if use_mock:
            summary = (
                f"[mock web] No live fetch in dev. Treat as placeholder fact for: {query[:200]}"
                if query
                else "[mock web] supply query or url"
            )
            result = {"ok": True, "query": query, "summary": summary, "mock": True}
        else:
            url = params.get("url") or (
                f"https://www.example.org/?q={query}" if query else ""
            )
            result = await safe_fetch(
                url, allowlist=services.settings.web_allowlist_set()
            )
        if policy["auditWebTools"]:
            approval = create_approval(
                services.store,
                world_id=ctx.world_id,
                tool_name="webtools_invoke",
                params=params,
                state="approved",
            )
            mark_approval_applied(services.store, approval["approvalId"])
        return result

    async def fs_read(params: dict, ctx: ToolContext) -> Any:
        agent = services.fs_for_world(ctx.world_id)
        return agent.read(params.get("path", ""))

    async def fs_write(params: dict, ctx: ToolContext) -> Any:
        from altrasia.approvals import create_approval, world_tool_policy

        policy = world_tool_policy(services.store, ctx.world_id)
        if policy.get("requireWebToolApproval"):
            approval = create_approval(
                services.store,
                world_id=ctx.world_id,
                tool_name="fs_write",
                params=params,
                state="pending",
            )
            return {"ok": False, "approvalRequired": True, "approvalId": approval["approvalId"]}
        agent = services.fs_for_world(ctx.world_id)
        return agent.write(params.get("path", ""), params.get("content", ""))

    async def schedule_create(params: dict, ctx: ToolContext) -> Any:
        if not services.settings.scheduler_enabled:
            return {"ok": False, "error": "scheduler disabled (RW-4)"}
        return {"ok": True, "scheduled": params.get("cron"), "note": "stub scheduler recorded"}

    async def scene_exit_set_state(params: dict, ctx: ToolContext) -> Any:
        """CC-11c: set doorState on exit; broken requires explicit join elsewhere."""
        scene = services.store.get_scene(ctx.scene_id)
        exits = json.loads(scene.get("exitsJson") or "[]")
        exit_id = params.get("exitId")
        state = params.get("doorState")
        found = False
        for ex in exits:
            if ex.get("exitId") == exit_id:
                ex["doorState"] = state
                found = True
                break
        if not found:
            return {"ok": False, "error": "exit not found"}
        services.store.update_scene(ctx.scene_id, exitsJson=json.dumps(exits))
        return {"ok": True, "exitId": exit_id, "doorState": state}

    async def scene_update_fixture(params: dict, ctx: ToolContext) -> Any:
        scene = services.store.get_scene(ctx.scene_id)
        fixtures = json.loads(scene["fixturesJson"])
        key = params["fixtureKey"]
        fixtures[key] = params.get("fixture", fixtures.get(key, {}))
        services.store.update_scene(ctx.scene_id, fixturesJson=json.dumps(fixtures))
        return {"ok": True, "fixtureKey": key}

    async def character_list(params: dict, ctx: ToolContext) -> Any:
        world_id = params.get("worldId") or ctx.world_id
        roster = services.presence.roster(world_id)
        loc: dict[str, dict] = {}
        for bucket in ("atLocation", "elsewhere", "unplaced"):
            for e in roster.get(bucket, []):
                loc[e["characterId"]] = e
        chars = []
        for m in services.store.list_world_characters(world_id):
            cid = m["characterId"]
            entry = loc.get(cid, {})
            chars.append(
                {
                    "characterId": cid,
                    "displayName": m.get("displayName", cid),
                    "sceneRole": m.get("sceneRole"),
                    "presentSceneId": entry.get("sceneId"),
                    "locationName": entry.get("locationName"),
                }
            )
        return {"characters": chars}

    async def scene_location_list(params: dict, ctx: ToolContext) -> Any:
        world_id = params.get("worldId") or ctx.world_id
        scenes = []
        for sc in services.store.list_scenes(world_id):
            present = services.presence.parse_present(sc.get("presentJson", "[]"))
            scenes.append(
                {
                    "sceneId": sc["sceneId"],
                    "locationName": sc["locationName"],
                    "presentCount": len([c for c in present if c != "__persona__"]),
                }
            )
        return {"scenes": scenes}

    async def scene_join(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.presence_ops import presence_join

        target = params.get("sceneId") or params.get("targetSceneId") or ctx.scene_id
        cid = params.get("characterId") or ctx.character_id
        if cid != ctx.character_id:
            return {"ok": False, "error": "cast may only scene_join for self"}
        members = {m["characterId"] for m in services.store.list_world_characters(ctx.world_id)}
        if cid not in members:
            return {"ok": False, "error": "unknown character"}
        if not services.store.get_scene(target):
            return {"ok": False, "error": "scene not found"}
        await presence_join(
            services,
            world_id=ctx.world_id,
            scene_id=target,
            character_id=cid,
            action="join",
        )
        return {"ok": True, "sceneId": target, "characterId": cid}

    async def scene_summon(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.presence_ops import presence_summon_batch
        from altrasia.memory.org_recall import can_summon_others
        from altrasia.world_config import get_world_config

        cfg = get_world_config(services.store, ctx.world_id)
        members = services.store.list_world_characters(ctx.world_id)
        speaker = next((m for m in members if m["characterId"] == ctx.character_id), None)
        if not can_summon_others(cfg, speaker.get("sceneRole") if speaker else None):
            return {"ok": False, "error": "not authorized to summon others"}
        target = params.get("targetSceneId") or params.get("sceneId")
        if not target or not services.store.get_scene(target):
            return {"ok": False, "error": "target scene not found"}
        ids = params.get("characterIds") or []
        if not ids:
            return {"ok": False, "error": "characterIds required"}
        member_ids = {m["characterId"] for m in members}
        for cid in ids:
            if cid not in member_ids:
                return {"ok": False, "error": f"unknown character {cid}"}
        return await presence_summon_batch(
            services,
            world_id=ctx.world_id,
            target_scene_id=target,
            character_ids=ids,
        )

    async def map_layout_generate(params: dict, ctx: ToolContext) -> Any:
        from altrasia.map_authoring import create_layout_draft

        world_id = params.get("worldId") or ctx.world_id
        scope = params.get("scope", "mini")
        brief = params.get("brief") or params.get("description") or ""
        if not brief.strip():
            return {"ok": False, "error": "brief or description required"}
        try:
            draft = await create_layout_draft(services, world_id, brief.strip(), scope=scope)
            return {
                "ok": True,
                "layoutDraftId": draft["layoutDraftId"],
                "status": draft["status"],
                "scope": draft["scope"],
                "message": "Review and commit via MapDraft panel",
            }
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def map_world_bootstrap(params: dict, ctx: ToolContext) -> Any:
        from altrasia.map_world_bootstrap import create_world_bootstrap_draft

        world_id = params.get("worldId") or ctx.world_id
        description = params.get("description") or params.get("brief") or ""
        if not description.strip():
            return {"ok": False, "error": "description required"}
        try:
            draft = await create_world_bootstrap_draft(
                services,
                world_id,
                description.strip(),
                connect_from_scene_id=params.get("connectFromSceneId"),
            )
            return {
                "ok": True,
                "layoutDraftId": draft["layoutDraftId"],
                "status": draft["status"],
                "message": "Review and commit via MapDraft panel",
            }
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def map_layout_patch(params: dict, ctx: ToolContext) -> Any:
        from altrasia.map_authoring import create_layout_draft, patch_layout_safe

        world_id = params.get("worldId") or ctx.world_id
        patch = params.get("patch") or {
            k: v for k, v in params.items() if k not in ("worldId", "brief")
        }
        nodes = patch.get("nodes") or []
        if len(nodes) == 1 and not patch.get("structures") and not patch.get("edges"):
            result = patch_layout_safe(services, world_id, patch)
            if result.get("autoApplied"):
                return {"ok": True, **result}
        try:
            brief = params.get("brief") or f"Apply patch: {json.dumps(patch)}"
            draft = await create_layout_draft(services, world_id, brief, scope="mini")
            return {
                "ok": True,
                "layoutDraftId": draft["layoutDraftId"],
                "status": "draft_opened",
            }
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

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
            name="memory_read",
            description="Read one mind locus by key.",
            parameters={
                "type": "object",
                "properties": {"locusKey": {"type": "string"}},
                "required": ["locusKey"],
            },
            handler=memory_read,
        )
    )
    registry.register(
        ToolDef(
            name="diary_read",
            description="Read recent witnessed diary segments (paginated).",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                },
            },
            handler=diary_read,
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
            name="webtools_invoke",
            description="Search or fetch external facts (approval-gated in production).",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "url": {"type": "string"},
                },
            },
            handler=webtools_invoke,
        )
    )
    registry.register(
        ToolDef(
            name="fs_read",
            description="Read a file under this world's data directory.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=fs_read,
        )
    )
    registry.register(
        ToolDef(
            name="fs_write",
            description="Write a file under this world's data directory (approval may apply).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=fs_write,
        )
    )
    registry.register(
        ToolDef(
            name="schedule_create",
            description="Create a scheduled task (when scheduler enabled).",
            parameters={
                "type": "object",
                "properties": {
                    "cron": {"type": "string"},
                    "action": {"type": "string"},
                },
                "required": ["cron"],
            },
            handler=schedule_create,
        )
    )
    registry.register(
        ToolDef(
            name="scene_exit_set_state",
            description="Set doorState on a scene exit (closed, unlocked, open, broken).",
            parameters={
                "type": "object",
                "properties": {
                    "exitId": {"type": "string"},
                    "doorState": {"type": "string"},
                },
                "required": ["exitId", "doorState"],
            },
            handler=scene_exit_set_state,
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
    registry.register(
        ToolDef(
            name="character_list",
            description="List all characters in this world with current location.",
            parameters={
                "type": "object",
                "properties": {"worldId": {"type": "string"}},
            },
            handler=character_list,
        )
    )
    registry.register(
        ToolDef(
            name="scene_location_list",
            description="List scenes in this world with location names.",
            parameters={
                "type": "object",
                "properties": {"worldId": {"type": "string"}},
            },
            handler=scene_location_list,
        )
    )
    registry.register(
        ToolDef(
            name="scene_join",
            description="Move yourself to another scene (existing locations only).",
            parameters={
                "type": "object",
                "properties": {
                    "sceneId": {"type": "string"},
                    "targetSceneId": {"type": "string"},
                },
            },
            handler=scene_join,
        )
    )
    registry.register(
        ToolDef(
            name="scene_summon",
            description="Summon other cast members to a scene (leadership roles).",
            parameters={
                "type": "object",
                "properties": {
                    "targetSceneId": {"type": "string"},
                    "characterIds": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["targetSceneId", "characterIds"],
            },
            handler=scene_summon,
        )
    )
    registry.register(
        ToolDef(
            name="map_layout_generate",
            description="Generate map layout draft (mini/site/stack). Requires operator commit.",
            parameters={
                "type": "object",
                "properties": {
                    "worldId": {"type": "string"},
                    "scope": {"type": "string", "enum": ["mini", "site", "stack", "floor"]},
                    "brief": {"type": "string"},
                    "description": {"type": "string"},
                    "referenceDiagramId": {"type": "string"},
                },
                "required": ["brief"],
            },
            handler=map_layout_generate,
        )
    )
    registry.register(
        ToolDef(
            name="map_world_bootstrap",
            description="Create new scenes and 3D layout from a world description (operator commit).",
            parameters={
                "type": "object",
                "properties": {
                    "worldId": {"type": "string"},
                    "description": {"type": "string"},
                    "connectFromSceneId": {"type": "string"},
                },
                "required": ["description"],
            },
            handler=map_world_bootstrap,
        )
    )
    registry.register(
        ToolDef(
            name="map_layout_patch",
            description="Patch map layout (safe single-node moves auto-apply; else opens draft).",
            parameters={
                "type": "object",
                "properties": {
                    "worldId": {"type": "string"},
                    "brief": {"type": "string"},
                    "patch": {"type": "object"},
                    "nodes": {"type": "array"},
                },
            },
            handler=map_layout_patch,
        )
    )
