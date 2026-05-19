from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from altrasia.domain.presence import PERSONA_ID

log = logging.getLogger(__name__)

TAB_IDLE_SECONDS = 45.0
LOOP_GRANULARITY_SECONDS = 15.0


class IdleScheduler:
    """AO-4 idle_timer: tab-visible (WS) and optional global heartbeat (HB-1)."""

    def __init__(self, services: Any) -> None:
        self.svc = services
        self._active_worlds: set[str] = set()
        self._task: asyncio.Task | None = None
        self._hb_world_index = 0
        self._last_tab_tick = 0.0
        self._last_hb_tick = 0.0

    def mark_world_active(self, world_id: str) -> None:
        self._active_worlds.add(world_id)

    def mark_world_inactive(self, world_id: str) -> None:
        self._active_worlds.discard(world_id)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._last_tab_tick = time.monotonic()
            self._last_hb_tick = time.monotonic()
            self._task = asyncio.create_task(self._loop())

    def _tab_idle_seconds(self, world_id: str) -> float:
        from altrasia.world_config import get_idle_social_config

        cfg = get_idle_social_config(self.svc.store, world_id)
        return float(cfg.get("idleSocialTabIntervalSeconds", TAB_IDLE_SECONDS))

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(LOOP_GRANULARITY_SECONDS)
            now = time.monotonic()
            tab_due = False
            for world_id in list(self._active_worlds):
                if world_id in self.svc.paused_worlds:
                    continue
                if now - self._last_tab_tick >= self._tab_idle_seconds(world_id):
                    tab_due = True
                    break
            if tab_due:
                self._last_tab_tick = now
                for world_id in list(self._active_worlds):
                    if world_id in self.svc.paused_worlds:
                        continue
                    try:
                        await self._tick_world(world_id, idle_source="tab_visible")
                    except Exception as exc:
                        log.warning("tab idle tick failed world=%s: %s", world_id, exc)

            hb = self.svc.operator_settings.load().heartbeat.normalized()
            if hb.enabled and now - self._last_hb_tick >= hb.intervalSeconds:
                self._last_hb_tick = now
                self.svc.operator_settings.record_heartbeat()
                try:
                    await self._heartbeat_tick()
                except Exception as exc:
                    log.warning("heartbeat tick failed: %s", exc)

    async def _heartbeat_tick(self) -> None:
        """HB-1: one eligible world per heartbeat interval when no tab connected."""
        worlds = self.svc.store.list_worlds()
        eligible = [
            w
            for w in worlds
            if w["worldId"] not in self.svc.paused_worlds
            and w["worldId"] not in self._active_worlds
            and self._world_has_idle_npc(w["worldId"])
        ]
        if not eligible:
            return
        self._hb_world_index %= len(eligible)
        world_id = eligible[self._hb_world_index]["worldId"]
        self._hb_world_index += 1
        await self._tick_world(world_id, idle_source="server_heartbeat")

    def _world_has_idle_npc(self, world_id: str) -> bool:
        for scene in self.svc.store.list_scenes(world_id):
            cast = [
                c
                for c in json.loads(scene["presentJson"])
                if c not in (PERSONA_ID,)
            ]
            if cast:
                return True
        return False

    async def _tick_world(self, world_id: str, *, idle_source: str) -> None:
        from altrasia.banter_runner import tick_banter_scenes
        from altrasia.commission_runner import tick_commissions
        from altrasia.debate_runner import tick_debate_scenes

        await tick_commissions(self.svc, world_id)
        if await tick_debate_scenes(self.svc, world_id):
            return
        if await tick_banter_scenes(self.svc, world_id):
            return
        orch = self.svc.orchestrator
        if self.svc.gpu_queue.busy:
            return
        queued = self.svc.store.list_queued_jobs(world_id)
        if queued and len(queued) >= self.svc.gpu_queue.max_depth:
            return
        if queued:
            return
        world = self.svc.store.get_world(world_id)
        active_scene_id = (world or {}).get("activeSceneId")
        if idle_source == "tab_visible" and active_scene_id:
            scene = self.svc.store.get_scene(active_scene_id)
            scenes = [scene] if scene else []
        else:
            scenes = self.svc.store.list_scenes(world_id)
        for scene in scenes:
            if not scene:
                continue
            scene_id = scene["sceneId"]
            if scene_id in orch._scene_chain_active:
                continue
            from altrasia.orchestrator.banter_gates import should_start_idle_banter

            cast = [
                c
                for c in json.loads(scene["presentJson"])
                if c not in (PERSONA_ID,)
            ]
            if len(cast) < 1:
                continue
            cid, rationale = self._pick_idle_character(scene, cast, world_id)
            if not cid:
                continue
            await orch.enqueue_generation(
                world_id=world_id,
                scene_id=scene_id,
                character_id=cid,
                trigger="idle_timer",
                continue_depth=0,
                idle_source=idle_source,
                selection_rationale_json=json.dumps(rationale),
            )
            return

    def _pick_idle_character(
        self, scene: dict, cast: list[str], world_id: str
    ) -> tuple[str | None, dict[str, Any]]:
        from altrasia.debate_activity import debate_current_speaker, parse_activity
        from altrasia.orchestrator.social_selection import pick_idle_participant
        from altrasia.world_config import get_idle_social_config

        activity = parse_activity(scene)
        if activity and activity.get("kind") == "debate":
            speaker = debate_current_speaker(activity)
            if speaker and speaker in cast:
                return speaker, {"pick": "debate", "characterId": speaker}
        cfg = get_idle_social_config(self.svc.store, world_id)
        if cfg.get("idleSocialEnabled", True) and len(cast) >= int(
            cfg.get("idleSocialMinCast", 2)
        ):
            from altrasia.orchestrator.banter_gates import should_start_idle_banter

            ok, gate_reason = should_start_idle_banter(
                self.svc,
                world_id,
                scene["sceneId"],
                orchestrator=self.svc.orchestrator,
            )
            if ok:
                return None, {"pick": "banter_preferred"}
            cid, rationale = pick_idle_participant(
                self.svc,
                world_id=world_id,
                scene=scene,
                cast=cast,
            )
            if cid:
                rationale = {**rationale, "banterGated": gate_reason}
            return cid, rationale
        return pick_idle_participant(
            self.svc, world_id=world_id, scene=scene, cast=cast
        )
