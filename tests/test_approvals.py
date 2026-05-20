"""APR-1 approval queue for webtools_invoke."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.approvals import apply_web_approval, create_approval, mark_approval_applied
from altrasia.config import Settings
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.orchestrator.addressing_policy import may_character_generate
from altrasia.services import AppServices
from altrasia.tools.handlers import register_core_tools
from altrasia.tools.registry import ToolContext, ToolRegistry
from altrasia.world_config import get_world_config
from tests.conftest import make_test_settings, wait_for_jobs


def test_webtools_requires_approval_when_character_asks(tmp_path: Path) -> None:
    settings = make_test_settings(tmp_path, "apr.db")
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    cid = "char-jordan-reyes"
    client.patch(
        f"/api/v1/characters/{cid}",
        json={"definition": {"webToolsAccess": "ask"}},
    )

    tools = ToolRegistry()
    register_core_tools(tools, svc)
    import asyncio

    result = asyncio.run(
        tools.invoke(
            "webtools_invoke",
            {"query": "library hours"},
            ToolContext(
                world_id=world_id,
                scene_id="scene-lobby",
                character_id=cid,
                services=svc,
                job_id="job-test",
                message_id="msg-test",
            ),
        )
    )
    data = json.loads(result)
    assert data.get("approvalRequired") is True
    pending = client.get(f"/api/v1/worlds/{world_id}/approvals").json()
    assert len(pending) >= 1
    row = pending[0]
    assert row["characterId"] == cid
    assert row["jobId"] == "job-test"
    aid = row["approvalId"]
    approved = client.post(f"/api/v1/worlds/{world_id}/approvals/{aid}/approve").json()
    assert approved["state"] == "applied"
    assert approved.get("result") is not None
    stored = svc.store.get_approval(aid)
    assert stored.get("resultJson")


def test_agent_tool_trigger_bypasses_addressing_gate(tmp_path: Path) -> None:
    """Follow-up after web approval must not be blocked by clarification/directed gates."""
    settings = make_test_settings(tmp_path, "apr_gate.db")
    app = create_app(settings)
    svc = app.state.services
    client = TestClient(app)
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    scene_id = client.get(f"/api/v1/worlds/{world_id}/scenes").json()[0]["sceneId"]
    cid = "char-jordan-reyes"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages",
        json={"text": "Jordan, check the news for me.", "scope": "public"},
    )
    wait_for_jobs(client, world_id)
    cfg = get_world_config(svc.store, world_id)
    job = {
        "worldId": world_id,
        "sceneId": scene_id,
        "characterId": cid,
        "trigger": "agent_tool",
        "continueDepth": 0,
        "triggerMessageId": None,
        "selectionRationaleJson": json.dumps({"pick": "web_approval_resume"}),
    }
    allowed, reason = may_character_generate(svc, job, cfg)
    assert allowed is True
    assert reason == "explicit_target"


@pytest.mark.asyncio
async def test_web_approval_follow_up_job_completes(tmp_path: Path) -> None:
    """Approved web fetch enqueues agent_tool follow-up that is not addressing-suppressed."""
    settings = make_test_settings(tmp_path, "apr_follow.db")
    svc = AppServices.create(settings)
    meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    world_id = meta["worldId"]
    scene_id = meta["activeSceneId"]
    cid = "char-jordan-reyes"
    approval = create_approval(
        svc.store,
        world_id=world_id,
        tool_name="webtools_invoke",
        params={"url": "https://soylentnews.org"},
        state="pending",
        character_id=cid,
        job_id="job-orig",
        message_id="msg-orig",
    )
    result = await apply_web_approval(svc.store, svc, approval)
    mark_approval_applied(svc.store, approval["approvalId"])
    follow = await svc.orchestrator.resume_after_web_approval(approval, result)
    assert follow and follow.get("jobId")
    job_id = follow["jobId"]
    job = None
    for _ in range(200):
        job = svc.store.get_job(job_id)
        assert job is not None
        if job["status"] in ("done", "cancelled"):
            break
        await asyncio.sleep(0.05)
    assert job is not None
    assert job["status"] == "done", job.get("selectionRationaleJson")
    msgs = svc.store.list_messages(world_id, scene_id=scene_id)
    follow_msgs = [m for m in msgs if m.get("generationJobId") == job_id]
    assert follow_msgs
    assert (follow_msgs[0].get("outputText") or "").strip()
