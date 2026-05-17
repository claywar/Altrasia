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

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(LOOP_GRANULARITY_SECONDS)
            now = time.monotonic()
            if now - self._last_tab_tick >= TAB_IDLE_SECONDS:
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
        orch = self.svc.orchestrator
        if self.svc.gpu_queue.busy:
            return
        if self.svc.store.list_queued_jobs(world_id):
            return
        for scene in self.svc.store.list_scenes(world_id):
            scene_id = scene["sceneId"]
            if scene_id in orch._scene_chain_active:
                continue
            cast = [
                c
                for c in json.loads(scene["presentJson"])
                if c not in (PERSONA_ID,)
            ]
            if len(cast) < 1:
                continue
            cid = self._pick_idle_character(scene, cast)
            if not cid:
                continue
            await orch.enqueue_generation(
                world_id=world_id,
                scene_id=scene_id,
                character_id=cid,
                trigger="idle_timer",
                continue_depth=0,
                idle_source=idle_source,
            )
            return

    def _pick_idle_character(self, scene: dict, cast: list[str]) -> str | None:
        idx = int(scene.get("roundRobinIndex") or 0)
        ordered = sorted(cast)
        if not ordered:
            return None
        pick = ordered[idx % len(ordered)]
        self.svc.store.update_scene(
            scene["sceneId"],
            roundRobinIndex=(idx + 1) % len(ordered),
        )
        return pick
