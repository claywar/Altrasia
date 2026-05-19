"""Post-discussion deliverables: parse, schedule, fulfill."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.discussion_deliverables import (
    bootstrap_ensemble_discussion,
    enqueue_pending_deliverables,
    parse_operator_deliverables,
    pending_deliverables,
)

PROGRAM_OFFICE = "scene-program-office"
LIAM_LINE = (
    "Good afternoon everyone. Discuss amongst yourselves. "
    "Liam, when your team is finished, I expect a report from you."
)


@pytest.fixture
def deliverable_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "deliverables.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def test_parse_operator_deliverables_liam() -> None:
    roster = [
        {"characterId": "char-liam-park", "displayName": "Liam Park"},
        {"characterId": "char-nina-patel", "displayName": "Nina Patel"},
    ]
    found = parse_operator_deliverables(LIAM_LINE, roster)
    assert len(found) == 1
    assert found[0]["characterId"] == "char-liam-park"
    assert found[0]["kind"] == "report"
    assert found[0]["status"] == "pending"


def test_bootstrap_stores_deliverable_on_ensemble(deliverable_client: TestClient) -> None:
    svc = deliverable_client.app.state.services
    world_id = deliverable_client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    cfg = json.loads(svc.store.get_world(world_id)["configJson"])
    activity = bootstrap_ensemble_discussion(
        svc.store,
        PROGRAM_OFFICE,
        operator_text=LIAM_LINE,
        operator_message_id="op-msg-1",
        world_id=world_id,
        cfg=cfg,
    )
    pending = pending_deliverables(activity)
    assert len(pending) == 1
    assert pending[0]["characterId"] == "char-liam-park"


def _wait_job(client: TestClient, job_id: str, timeout: float = 45.0) -> dict:
    store = client.app.state.services.store
    deadline = time.time() + timeout
    while time.time() < deadline:
        row = store.get_job(job_id)
        if row and row["status"] in ("done", "cancelled"):
            return row
        time.sleep(0.05)
    raise TimeoutError(f"job {job_id} did not finish")


def test_discussion_deliverable_job_after_chain_stop(deliverable_client: TestClient) -> None:
    svc = deliverable_client.app.state.services
    world_id = deliverable_client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    deliverable_client.patch(
        f"/api/v1/worlds/{world_id}", json={"activeSceneId": PROGRAM_OFFICE}
    )
    cfg = json.loads(svc.store.get_world(world_id)["configJson"])
    bootstrap_ensemble_discussion(
        svc.store,
        PROGRAM_OFFICE,
        operator_text=LIAM_LINE,
        operator_message_id="op-msg-1",
        world_id=world_id,
        cfg=cfg,
    )

    base_job = {
        "worldId": world_id,
        "sceneId": PROGRAM_OFFICE,
        "characterId": "char-tom-bradley",
        "trigger": "agent_continue",
        "continueDepth": 8,
        "triggerMessageId": "op-msg-1",
    }
    scheduled = asyncio.run(
        enqueue_pending_deliverables(svc.orchestrator, base_job, "conversation_resolved")
    )
    assert len(scheduled) == 1
    assert scheduled[0]["characterId"] == "char-liam-park"
    job_id = scheduled[0]["jobId"]
    assert job_id

    row = _wait_job(deliverable_client, job_id)
    assert row["status"] == "done"

    msg = svc.store.fetchone(
        "SELECT outputText, metaJson FROM Message WHERE generationJobId = ?",
        (job_id,),
    )
    assert "report" in (msg["outputText"] or "").lower()
    meta = json.loads(msg["metaJson"] or "{}")
    assert meta.get("orchestration", {}).get("trigger") == "discussion_deliverable"

    locus = f"discussion:{PROGRAM_OFFICE}:char-liam-park:report"
    mind = svc.store.conn.execute(
        "SELECT value FROM Locus WHERE pool='mind' AND ownerId=? AND locusKey=?",
        ("char-liam-park", locus),
    ).fetchone()
    assert mind and "Jordan" in mind[0]

    commissions = deliverable_client.get(f"/api/v1/worlds/{world_id}/commissions").json()
    assert any(c.get("status") == "done" for c in commissions)
