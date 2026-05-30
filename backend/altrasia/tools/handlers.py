from __future__ import annotations

import json
from typing import Any

from altrasia.tools.registry import ToolContext, ToolDef, ToolRegistry


def register_core_tools(registry: ToolRegistry, services: Any) -> None:
    mem = services.memory

    def _sync_fixtures(scene_id: str) -> None:
        from altrasia.memory.fixture_sync import sync_scene_fixtures_to_loci

        sync_scene_fixtures_to_loci(services.store, scene_id=scene_id)

    def _emit_inventory(world_id: str, character_id: str) -> None:
        if hasattr(services, "event_bus") and services.event_bus:
            services.event_bus.emit(
                services.store,
                world_id,
                "inventory.changed",
                {"characterId": character_id},
            )

    def _character_at_scene(world_id: str, scene_id: str, character_id: str) -> bool:
        scene = services.store.get_scene(scene_id)
        if not scene:
            return False
        from altrasia.domain.presence import PresenceService

        present = PresenceService.parse_present(scene.get("presentJson", "[]"))
        return character_id in present

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
            execute_web_fetch,
            mark_approval_applied,
            world_tool_policy,
        )
        from altrasia.tools.web_access import resolve_web_tools_policy

        char_policy = resolve_web_tools_policy(
            services.store, ctx.world_id, ctx.character_id
        )
        if not char_policy["exposed"]:
            return {
                "ok": False,
                "error": "web tools not enabled for this character",
            }
        if char_policy["require_approval"]:
            approval = create_approval(
                services.store,
                world_id=ctx.world_id,
                tool_name="webtools_invoke",
                params=params,
                state="pending",
                character_id=ctx.character_id,
                job_id=ctx.job_id,
                message_id=ctx.message_id,
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
        result = await execute_web_fetch(services, ctx.world_id, params)
        world_policy = world_tool_policy(services.store, ctx.world_id)
        if world_policy["auditWebTools"]:
            approval = create_approval(
                services.store,
                world_id=ctx.world_id,
                tool_name="webtools_invoke",
                params=params,
                state="approved",
                character_id=ctx.character_id,
                job_id=ctx.job_id,
                message_id=ctx.message_id,
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
        _sync_fixtures(ctx.scene_id)
        return {"ok": True, "fixtureKey": key}

    async def scene_fixture_pickup(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import pickup_fixture

        if not _character_at_scene(ctx.world_id, ctx.scene_id, ctx.character_id):
            return {"ok": False, "error": "not present at scene"}
        try:
            out = pickup_fixture(
                services.store,
                world_id=ctx.world_id,
                scene_id=ctx.scene_id,
                character_id=ctx.character_id,
                fixture_key=params["fixtureKey"],
            )
            _sync_fixtures(ctx.scene_id)
            _emit_inventory(ctx.world_id, ctx.character_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_fixture_place(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import place_fixture

        if not _character_at_scene(ctx.world_id, ctx.scene_id, ctx.character_id):
            return {"ok": False, "error": "not present at scene"}
        try:
            out = place_fixture(
                services.store,
                world_id=ctx.world_id,
                scene_id=ctx.scene_id,
                character_id=ctx.character_id,
                item_id=params["itemId"],
                fixture_key=params.get("fixtureKey"),
            )
            _sync_fixtures(ctx.scene_id)
            _emit_inventory(ctx.world_id, ctx.character_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_fixture_move(params: dict, ctx: ToolContext) -> Any:
        scene = services.store.get_scene(ctx.scene_id)
        fixtures = json.loads(scene.get("fixturesJson") or "{}")
        old_key = params["fixtureKey"]
        new_key = params.get("newFixtureKey") or params.get("targetFixtureKey")
        if not new_key or old_key not in fixtures:
            return {"ok": False, "error": "fixture not found"}
        if new_key in fixtures and new_key != old_key:
            return {"ok": False, "error": "target key taken"}
        fixtures[new_key] = fixtures.pop(old_key)
        services.store.update_scene(ctx.scene_id, fixturesJson=json.dumps(fixtures))
        _sync_fixtures(ctx.scene_id)
        return {"ok": True, "fixtureKey": new_key}

    async def scene_fixture_describe(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import describe_fixture

        try:
            return describe_fixture(
                services.store,
                scene_id=ctx.scene_id,
                fixture_key=params["fixtureKey"],
            )
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_fixture_harvest(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import harvest_fixture

        if not _character_at_scene(ctx.world_id, ctx.scene_id, ctx.character_id):
            return {"ok": False, "error": "not present at scene"}
        try:
            out = harvest_fixture(
                services.store,
                world_id=ctx.world_id,
                scene_id=ctx.scene_id,
                character_id=ctx.character_id,
                fixture_key=params["fixtureKey"],
            )
            _sync_fixtures(ctx.scene_id)
            _emit_inventory(ctx.world_id, ctx.character_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_fixture_replenish(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import replenish_fixture

        picks = params.get("picksRemaining")
        try:
            out = replenish_fixture(
                services.store,
                scene_id=ctx.scene_id,
                fixture_key=params["fixtureKey"],
                picks_remaining=int(picks) if picks is not None else None,
            )
            _sync_fixtures(ctx.scene_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_stash_take(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.shared_stash import take_from_stash

        if not _character_at_scene(ctx.world_id, ctx.scene_id, ctx.character_id):
            return {"ok": False, "error": "not present at scene"}
        try:
            out = take_from_stash(
                services.store,
                world_id=ctx.world_id,
                scene_id=ctx.scene_id,
                character_id=ctx.character_id,
                stash_key=params["stashKey"],
                item_id=params.get("itemId"),
            )
            _emit_inventory(ctx.world_id, ctx.character_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_stash_deposit(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.shared_stash import deposit_to_stash

        if not _character_at_scene(ctx.world_id, ctx.scene_id, ctx.character_id):
            return {"ok": False, "error": "not present at scene"}
        try:
            out = deposit_to_stash(
                services.store,
                world_id=ctx.world_id,
                scene_id=ctx.scene_id,
                character_id=ctx.character_id,
                stash_key=params["stashKey"],
                item_id=params["itemId"],
            )
            _emit_inventory(ctx.world_id, ctx.character_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_inventory_apply_outfit(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import apply_outfit_preset

        target_id = params.get("characterId") or ctx.character_id
        try:
            out = apply_outfit_preset(
                services.store,
                world_id=ctx.world_id,
                character_id=target_id,
                preset_id=params["presetId"],
            )
            _emit_inventory(ctx.world_id, target_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_inventory_give(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import give_item

        to_id = params["toCharacterId"]
        if not _character_at_scene(ctx.world_id, ctx.scene_id, ctx.character_id):
            return {"ok": False, "error": "giver not present at scene"}
        if not _character_at_scene(ctx.world_id, ctx.scene_id, to_id):
            return {"ok": False, "error": "recipient not present at scene"}
        try:
            out = give_item(
                services.store,
                world_id=ctx.world_id,
                from_character_id=ctx.character_id,
                to_character_id=to_id,
                item_id=params["itemId"],
                to_slot=params.get("toSlot", "held"),
                container_item_id=params.get("containerItemId"),
            )
            _emit_inventory(ctx.world_id, ctx.character_id)
            _emit_inventory(ctx.world_id, to_id)
            return out
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_inventory_wear(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import move_item

        try:
            move_item(
                services.store,
                world_id=ctx.world_id,
                character_id=ctx.character_id,
                item_id=params["itemId"],
                to_slot="worn",
            )
            _emit_inventory(ctx.world_id, ctx.character_id)
            return {"ok": True, "itemId": params["itemId"], "slot": "worn"}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    async def scene_inventory_stow(params: dict, ctx: ToolContext) -> Any:
        from altrasia.domain.inventory import move_item

        try:
            move_item(
                services.store,
                world_id=ctx.world_id,
                character_id=ctx.character_id,
                item_id=params["itemId"],
                to_slot="container",
                container_item_id=params.get("containerItemId"),
            )
            _emit_inventory(ctx.world_id, ctx.character_id)
            return {"ok": True, "itemId": params["itemId"], "slot": "container"}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

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
            summoner_id=ctx.character_id,
            source_scene_id=ctx.scene_id,
            source="tool",
            related_message_id=ctx.message_id,
            announce=False,
        )

    async def image_generate(params: dict, ctx: ToolContext) -> Any:
        from altrasia.approvals import create_approval
        from altrasia.inference.comfyui.pipeline import (
            WORKFLOW_IDS,
            run_image_workflow,
            save_media_asset,
            write_image_locus,
        )
        from altrasia.world_config import get_world_config

        wc = get_world_config(services.store, ctx.world_id)

        workflow_id = str(params.get("workflowId") or "scene_establishing")
        if workflow_id not in WORKFLOW_IDS:
            return {"ok": False, "error": f"workflow not allowed: {workflow_id} (IMG-9)"}

        if ctx.character_id and not wc.get("allowCastImageGen", False):
            return {"ok": False, "error": "cast image generation not allowed (IMG-7)"}

        prompt = str(params.get("prompt") or "").strip()
        if not prompt:
            return {"ok": False, "error": "prompt required"}

        if wc.get("requireApprovalForImageGen"):
            approval = create_approval(
                services.store,
                world_id=ctx.world_id,
                tool_name="image_generate",
                params=params,
                state="pending",
                character_id=ctx.character_id,
                job_id=ctx.job_id,
                message_id=ctx.message_id,
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
                "message": "Operator must approve image generation.",
            }

        gen = await run_image_workflow(
            services,
            world_id=ctx.world_id,
            workflow_id=workflow_id,
            prompt=prompt,
            model_profile_id=params.get("modelProfileId"),
            reference_asset_id=params.get("referenceAssetId"),
            job_id=ctx.job_id,
        )
        if gen.get("mock"):
            return gen
        if not gen.get("ok"):
            return gen

        locus_key = params.get("locusKey")
        character_id = params.get("characterId") or ctx.character_id
        scene_id = params.get("sceneId")
        asset = save_media_asset(
            services,
            world_id=ctx.world_id,
            png_bytes=gen["png"],
            workflow_id=workflow_id,
            model_profile_id=gen["modelProfileId"],
            character_id=character_id if workflow_id == "character_portrait" else None,
            scene_id=scene_id if workflow_id in ("scene_establishing", "map_thumbnail") else None,
            source_job_id=gen.get("jobId"),
        )
        if locus_key:
            write_image_locus(
                services,
                locus_key=str(locus_key),
                owner_id=ctx.world_id,
                caption=prompt,
                asset_id=asset["assetId"],
            )
        return {
            "ok": True,
            "assetId": asset["assetId"],
            "url": asset["url"],
            "modelProfileId": gen["modelProfileId"],
        }

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
            description=(
                "Search the web or fetch a URL for external facts. Use when the operator "
                "asks about live sites, news, or information not in memory. Pass query "
                "and/or url."
            ),
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
            name="scene_fixture_pickup",
            description="Pick up a portable discrete fixture into inventory.",
            parameters={
                "type": "object",
                "properties": {"fixtureKey": {"type": "string"}},
                "required": ["fixtureKey"],
            },
            handler=scene_fixture_pickup,
        )
    )
    registry.register(
        ToolDef(
            name="scene_fixture_place",
            description="Place a held item into the scene as a discrete fixture.",
            parameters={
                "type": "object",
                "properties": {
                    "itemId": {"type": "string"},
                    "fixtureKey": {"type": "string"},
                },
                "required": ["itemId"],
            },
            handler=scene_fixture_place,
        )
    )
    registry.register(
        ToolDef(
            name="scene_fixture_move",
            description="Rename or move a fixture key within the scene (Observer).",
            parameters={
                "type": "object",
                "properties": {
                    "fixtureKey": {"type": "string"},
                    "newFixtureKey": {"type": "string"},
                },
                "required": ["fixtureKey", "newFixtureKey"],
            },
            handler=scene_fixture_move,
        )
    )
    registry.register(
        ToolDef(
            name="scene_fixture_describe",
            description="Describe a scene fixture record.",
            parameters={
                "type": "object",
                "properties": {"fixtureKey": {"type": "string"}},
                "required": ["fixtureKey"],
            },
            handler=scene_fixture_describe,
        )
    )
    registry.register(
        ToolDef(
            name="scene_fixture_harvest",
            description="Harvest from an aggregate fixture into held inventory.",
            parameters={
                "type": "object",
                "properties": {"fixtureKey": {"type": "string"}},
                "required": ["fixtureKey"],
            },
            handler=scene_fixture_harvest,
        )
    )
    registry.register(
        ToolDef(
            name="scene_fixture_replenish",
            description="Replenish an aggregate fixture (Observer).",
            parameters={
                "type": "object",
                "properties": {
                    "fixtureKey": {"type": "string"},
                    "picksRemaining": {"type": "integer"},
                },
                "required": ["fixtureKey"],
            },
            handler=scene_fixture_replenish,
        )
    )
    registry.register(
        ToolDef(
            name="scene_stash_take",
            description="Take an item from a scene shared stash into held inventory.",
            parameters={
                "type": "object",
                "properties": {
                    "stashKey": {"type": "string"},
                    "itemId": {"type": "string"},
                },
                "required": ["stashKey"],
            },
            handler=scene_stash_take,
        )
    )
    registry.register(
        ToolDef(
            name="scene_stash_deposit",
            description="Deposit a held or container item into a scene shared stash.",
            parameters={
                "type": "object",
                "properties": {
                    "stashKey": {"type": "string"},
                    "itemId": {"type": "string"},
                },
                "required": ["stashKey", "itemId"],
            },
            handler=scene_stash_deposit,
        )
    )
    registry.register(
        ToolDef(
            name="scene_inventory_apply_outfit",
            description="Apply a world outfit preset to a character inventory.",
            parameters={
                "type": "object",
                "properties": {
                    "presetId": {"type": "string"},
                    "characterId": {"type": "string"},
                },
                "required": ["presetId"],
            },
            handler=scene_inventory_apply_outfit,
        )
    )
    registry.register(
        ToolDef(
            name="scene_inventory_give",
            description="Give an inventory item to another present character.",
            parameters={
                "type": "object",
                "properties": {
                    "itemId": {"type": "string"},
                    "toCharacterId": {"type": "string"},
                    "toSlot": {"type": "string"},
                    "containerItemId": {"type": "string"},
                },
                "required": ["itemId", "toCharacterId"],
            },
            handler=scene_inventory_give,
        )
    )
    registry.register(
        ToolDef(
            name="scene_inventory_wear",
            description="Move a held item to worn slots.",
            parameters={
                "type": "object",
                "properties": {"itemId": {"type": "string"}},
                "required": ["itemId"],
            },
            handler=scene_inventory_wear,
        )
    )
    registry.register(
        ToolDef(
            name="scene_inventory_stow",
            description="Stow a held item into a container.",
            parameters={
                "type": "object",
                "properties": {
                    "itemId": {"type": "string"},
                    "containerItemId": {"type": "string"},
                },
                "required": ["itemId", "containerItemId"],
            },
            handler=scene_inventory_stow,
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
    async def discussion_signal(params: dict, ctx: ToolContext) -> Any:
        from altrasia.orchestrator.discussion_judgement import record_character_signal

        gaps = params.get("gaps")
        if gaps is not None and not isinstance(gaps, list):
            gaps = [str(gaps)]
        signal = record_character_signal(
            services.store,
            ctx.scene_id,
            ctx.character_id,
            sufficient=bool(params.get("sufficient")),
            gaps=gaps or [],
            note=str(params.get("note") or ""),
        )
        return {"ok": True, "signal": signal}

    registry.register(
        ToolDef(
            name="discussion_signal",
            description=(
                "File whether the current group discussion has surfaced enough "
                "information for the operator's request. Call when you believe key "
                "topics are still missing (sufficient=false, gaps listed) or when "
                "your perspective is fully on the table (sufficient=true)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "sufficient": {
                        "type": "boolean",
                        "description": "True if your view is fully represented.",
                    },
                    "gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Topics or concerns not yet adequately covered.",
                    },
                    "note": {
                        "type": "string",
                        "description": "Brief rationale for the operator/orchestrator.",
                    },
                },
                "required": ["sufficient"],
            },
            handler=discussion_signal,
        )
    )

    async def social_signal(params: dict, ctx: ToolContext) -> Any:
        note = str(params.get("note") or "").strip()
        target_id = str(params.get("targetCharacterId") or "").strip()
        pool = str(params.get("pool") or "mind").strip().lower()
        if not note:
            return {"ok": False, "error": "note required"}
        if pool not in ("mind", "world"):
            pool = "mind"
        if pool == "mind":
            if not target_id:
                return {"ok": False, "error": "targetCharacterId required for mind pool"}
            key = f"relationship:{target_id}"
            owner = ctx.character_id
        else:
            key = str(params.get("locusKey") or "culture:recent").strip()
            if not key.startswith("culture:"):
                key = f"culture:{key}"
            owner = ctx.scene_id
        services.memory.memory_store(
            pool=pool,
            owner_id=owner,
            locus_key=key,
            value=note[:2000],
        )
        return {"ok": True, "pool": pool, "locusKey": key}

    registry.register(
        ToolDef(
            name="social_signal",
            description=(
                "After sidebar banter, record a brief relationship or culture note. "
                "Use pool=mind with targetCharacterId for private relationship notes; "
                "pool=world with locusKey culture:* for shared culture (sparingly)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "note": {"type": "string"},
                    "targetCharacterId": {"type": "string"},
                    "pool": {"type": "string", "enum": ["mind", "world"]},
                    "locusKey": {"type": "string"},
                },
                "required": ["note"],
            },
            handler=social_signal,
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
            name="image_generate",
            description=(
                "Generate an image via ComfyUI (scene, portrait, fixture icon, or map thumbnail). "
                "Store caption + assetId in a world locus; never store binary in diary."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "workflowId": {
                        "type": "string",
                        "enum": [
                            "character_portrait",
                            "scene_establishing",
                            "fixture_icon",
                            "map_thumbnail",
                        ],
                    },
                    "prompt": {"type": "string"},
                    "locusKey": {"type": "string"},
                    "modelProfileId": {"type": "string"},
                    "referenceAssetId": {"type": "string"},
                    "characterId": {"type": "string"},
                    "sceneId": {"type": "string"},
                },
                "required": ["prompt"],
            },
            handler=image_generate,
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
