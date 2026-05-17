import asyncio

import pytest

from altrasia.inference.queue import GpuResourceQueue


@pytest.mark.asyncio
async def test_inf5_single_concurrent_lease() -> None:
    """INF-5: only one GPU work unit runs at a time."""
    q = GpuResourceQueue()
    order: list[str] = []

    async def job(name: str, delay: float) -> str:
        async def work() -> str:
            order.append(f"{name}-start")
            await asyncio.sleep(delay)
            order.append(f"{name}-end")
            return name

        return await q.run(f"job-{name}", "chat", work)

    t1 = asyncio.create_task(job("a", 0.15))
    await asyncio.sleep(0.02)
    t2 = asyncio.create_task(job("b", 0.05))
    await asyncio.gather(t1, t2)
    assert order.index("a-start") < order.index("a-end")
    assert order.index("b-start") > order.index("a-start")
    assert order.index("b-end") == len(order) - 1
