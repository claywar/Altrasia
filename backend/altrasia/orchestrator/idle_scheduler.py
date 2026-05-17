from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from altrasia.domain.presence import PERSONA_ID

log = logging.getLogger(__name__)


class IdleScheduler:
    """AO-4: scene-scoped round-robin idle_timer when operator tab is connected (v1 tab-visible)."""

    def __init__(self, services: Any, interval_seconds: float = 45.0) -> None:
        self.svc = services
        self.interval_seconds = interval_seconds
        self._active_worlds: set[str] = set()
        self._task: asyncio.Task | None = None

    def mark_world_active(self, world_id: str) -> None:
        self._active_worlds.add(world_id)

    def mark_world_inactive(self, world_id: str) -> None:
        self._active_worlds.discard(world_id)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            for world_id in list(self._active_worlds):
                if world_id in self.svc.paused_worlds:
                    continue
                try:
                    await self._tick_world(world_id)
                except Exception as exc:
                    log.warning("idle tick failed world=%s: %s", world_id, exc)

    async def _tick_world(self, world_id: str) -> None:
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
            )
            return  # one idle job per world tick (AO-12 spirit)

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
