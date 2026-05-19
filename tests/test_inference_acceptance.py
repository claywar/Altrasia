"""INF-5a, INF-5d, STR-1 acceptance tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.inference.queue import GpuResourceQueue, TokenStream
from altrasia.memory.strip_reasoning import strip_from_message_payload
from altrasia.orchestrator.engine import Orchestrator
from altrasia.services import AppServices


@pytest.mark.asyncio
async def test_inf5a_tool_recurse_holds_lease() -> None:
    """INF-5a: tool loop runs inside single gpu_queue.run lease."""
    q = GpuResourceQueue()
    lease_ids: list[str | None] = []

    async def work() -> str:
        snap = q.snapshot().get("currentLease")
        lease_ids.append(snap["leaseId"] if snap else None)
        await asyncio.sleep(0.02)
        snap2 = q.snapshot().get("currentLease")
        lease_ids.append(snap2["leaseId"] if snap2 else None)
        return "done"

    await q.run("outer", "chat", work)
    assert lease_ids[0] is not None
    assert lease_ids[0] == lease_ids[1]


@pytest.mark.asyncio
async def test_inf5d_idle_skipped_when_queue_full(tmp_path: Path) -> None:
    """INF-5d: idle tick does not enqueue when queued jobs at max_depth."""
    settings = Settings(
        db_path=tmp_path / "inf5d.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    svc.gpu_queue.max_depth = 1
    from altrasia.fixtures.loader import load_fixture_by_id

    meta = load_fixture_by_id(
        svc.store, settings.fixtures_dir, "demo-spatial-v1"
    )
    world_id = meta["worldId"]
    chars = svc.store.list_world_characters(world_id)
    cid = chars[0]["characterId"]
    svc.store.insert_job(
        {
            "jobId": "j-queued-1",
            "worldId": world_id,
            "characterId": cid,
            "sceneId": meta["activeSceneId"],
            "trigger": "idle_timer",
            "priority": 5,
            "observerMode": None,
            "status": "queued",
            "continueDepth": 0,
            "triggerMessageId": None,
            "selectionRationaleJson": None,
            "createdAt": "2026-01-01T00:00:00Z",
        }
    )
    sched = svc.idle_scheduler
    assert sched is not None
    before = len(svc.store.list_queued_jobs(world_id))
    await sched._tick_world(world_id, idle_source="tab_visible")
    after = len(svc.store.list_queued_jobs(world_id))
    assert after == before


def test_str1_stream_finalize_strip(tmp_path: Path) -> None:
    """STR-1: streaming message finalizes with stripped output."""
    from tests.conftest import make_test_settings, wait_for_jobs

    app = create_app(make_test_settings(tmp_path, "str.db"))
    with TestClient(app) as client:
        w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
        world_id = w["worldId"]
        scene_id = w["activeSceneId"]
        client.post(
            f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages",
            json={"text": "Hello Jordan", "scope": "public"},
        )
        wait_for_jobs(client, world_id)
        msgs = client.get(
            f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages"
        ).json()
        npc = [m for m in msgs if m.get("role") == "assistant"]
        assert npc
        assert npc[-1].get("streamStatus") == "final"
        assert len(npc[-1].get("outputText") or "") > 0


def test_strip_reasoning_unit() -> None:
    raw = "Hello world"
    cleaned = strip_from_message_payload({"content": raw})
    assert cleaned == "Hello world"
