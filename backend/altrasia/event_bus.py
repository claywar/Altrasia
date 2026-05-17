from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    """Per-world event fan-out with monotonic eventSeq (API-4)."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    def subscribe(self, world_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._subs[world_id].append(q)
        return q

    def unsubscribe(self, world_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        subs = self._subs.get(world_id, [])
        if q in subs:
            subs.remove(q)

    def emit(self, store: Any, world_id: str, event: str, data: dict[str, Any]) -> int:
        seq = store.bump_event_seq(world_id)
        payload = {"event": event, "eventSeq": seq, "worldId": world_id, "data": data}
        for q in list(self._subs.get(world_id, [])):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass
        return seq
