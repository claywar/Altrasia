"""AO-19 agent_continue chain and thinking-safe history integration."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.engine import Orchestrator

PROGRAM_OFFICE = "scene-program-office"


def _wait_jobs(
    client: TestClient,
    world_id: str,
    scene_id: str,
    *,
    min_done: int = 1,
    timeout: float = 60.0,
) -> None:
    store = client.app.state.services.store
    deadline = time.time() + timeout
    while time.time() < deadline:
        pending = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND status IN ('queued', 'running')""",
            (world_id, scene_id),
        ).fetchone()[0]
        done = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND status = 'done'""",
            (world_id, scene_id),
        ).fetchone()[0]
        if pending == 0 and done >= min_done:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


@pytest.fixture
def orch_client(tmp_path: Path) -> tuple[TestClient, Orchestrator, str]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "agent_continue.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        client.patch(
            f"/api/v1/worlds/{world_id}",
            json={"activeSceneId": PROGRAM_OFFICE},
        )
        svc = client.app.state.services
        yield client, svc.orchestrator, world_id


def test_should_enqueue_agent_continue_gates(orch_client: tuple) -> None:
    _client, orch, world_id = orch_client
    base_job = {
        "worldId": world_id,
        "sceneId": PROGRAM_OFFICE,
        "trigger": "persona_message",
        "continueDepth": 0,
    }
    limit, _, _ = asyncio.run(orch._continue_depth_limit(base_job))
    assert orch._should_enqueue_agent_continue(
        base_job, debate_active=False, tool_log=[], depth_limit=limit
    )
    # At demo maxContinueDepth (8), next step is blocked unless discussion still open.
    limit8, _, _ = asyncio.run(
        orch._continue_depth_limit({**base_job, "continueDepth": 8})
    )
    assert not orch._should_enqueue_agent_continue(
        {**base_job, "continueDepth": 8},
        debate_active=False,
        tool_log=[],
        depth_limit=limit8,
    )
    assert not orch._should_enqueue_agent_continue(
        {**base_job, "trigger": "idle_timer"},
        debate_active=False,
        tool_log=[],
        depth_limit=99,
    )
    assert not orch._should_enqueue_agent_continue(
        base_job,
        debate_active=True,
        tool_log=[],
        depth_limit=99,
    )
    assert not orch._should_enqueue_agent_continue(
        base_job,
        debate_active=False,
        tool_log=[{"name": "scene_summon", "arguments": {}, "result": "ok"}],
        depth_limit=99,
    )

    store = orch.svc.store
    world = store.get_world(world_id)
    cfg = json.loads(world["configJson"])
    cfg["agentContinueEnabled"] = False
    store.update_world(world_id, configJson=json.dumps(cfg))
    assert not orch._should_enqueue_agent_continue(
        base_job, debate_active=False, tool_log=[], depth_limit=99
    )


def test_agent_continue_chain_after_persona_message(orch_client: tuple) -> None:
    client, _orch, world_id = orch_client
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={
            "text": "Hello everyone — how does program management work here?",
            "scope": "public",
        },
    )
    _wait_jobs(client, world_id, PROGRAM_OFFICE, min_done=2, timeout=60.0)

    rows = client.app.state.services.store.conn.execute(
        """SELECT characterId, continueDepth, trigger, status
           FROM GenerationJob
           WHERE worldId = ? AND sceneId = ?
           ORDER BY createdAt""",
        (world_id, PROGRAM_OFFICE),
    ).fetchall()
    done = [r for r in rows if r[3] == "done"]
    depths = {r[1] for r in done}
    assert 0 in depths
    assert 1 in depths, "expected agent_continue at depth 1 after reactive reply"
    assert len(done) >= 2

    msgs = client.get(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages"
    ).json()
    finals = [
        m
        for m in msgs
        if m["role"] == "assistant" and m.get("streamStatus") == "final"
    ]
    assert len(finals) >= 2
    assert all((m.get("outputText") or "").strip() for m in finals)
    speakers = {m["characterId"] for m in finals}
    assert len(speakers) >= 2, "each reply should be a distinct cast member"
    for m in finals:
        body = m["outputText"] or ""
        for other in finals:
            if other["characterId"] == m["characterId"]:
                continue
            other_ch = client.app.state.services.store.get_character(other["characterId"])
            name = other_ch.get("displayName", "")
            if name and f"**{name}:**" in body:
                pytest.fail(f"message for {m['characterId']} scripts dialogue for {name}")
