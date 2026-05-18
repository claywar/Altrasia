from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Awaitable

LeaseKind = str


@dataclass
class GpuLease:
    lease_id: str
    job_id: str
    kind: LeaseKind
    started_at: str
    released_at: str | None = None


class GpuResourceQueue:
    """INF-5: single concurrent GPU work by default."""

    def __init__(self, max_depth: int = 4) -> None:
        self._lock = asyncio.Lock()
        self._current: GpuLease | None = None
        self._busy = False
        self.max_depth = max(1, max_depth)

    @property
    def busy(self) -> bool:
        return self._busy

    async def run(
        self,
        job_id: str,
        kind: LeaseKind,
        fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        async with self._lock:
            self._busy = True
            lease = GpuLease(
                lease_id=str(uuid.uuid4()),
                job_id=job_id,
                kind=kind,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            self._current = lease
            try:
                return await fn()
            finally:
                lease.released_at = datetime.now(timezone.utc).isoformat()
                self._current = None
                self._busy = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "busy": self._busy,
            "currentLease": (
                {
                    "leaseId": self._current.lease_id,
                    "jobId": self._current.job_id,
                    "kind": self._current.kind,
                }
                if self._current
                else None
            ),
        }


@dataclass
class StreamEvent:
    event: str
    data: dict[str, Any]


class TokenStream:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()

    async def push(self, event: str, data: dict[str, Any]) -> None:
        await self._queue.put(StreamEvent(event=event, data=data))

    async def close(self) -> None:
        await self._queue.put(None)

    async def iter_events(self) -> AsyncIterator[StreamEvent]:
        while True:
            item = await self._queue.get()
            if item is None:
                break
            yield item
