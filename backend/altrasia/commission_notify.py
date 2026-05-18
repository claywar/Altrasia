from __future__ import annotations

from typing import Any

from altrasia.commissions import sync_presence_statuses
from altrasia.commission_runner import tick_commissions


async def refresh_commissions(svc: Any, world_id: str) -> None:
    """Sync COM-6 presence gates and try to start queued work."""
    changed = sync_presence_statuses(svc.store, world_id)
    for cid in changed:
        svc.event_bus.emit(
            svc.store, world_id, "commission.updated", {"commissionId": cid}
        )
    result = await tick_commissions(svc, world_id)
    if result:
        svc.event_bus.emit(
            svc.store,
            world_id,
            "commission.updated",
            {"commissionId": result["commissionId"], "status": "running"},
        )
