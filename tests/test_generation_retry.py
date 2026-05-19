"""Generation retry policy and orchestrator resilience."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.generation_policy import (
    is_retryable_generation_error,
    world_generation_policy,
)

PROGRAM_OFFICE = "scene-program-office"


def test_is_retryable_generation_error() -> None:
    assert is_retryable_generation_error(TimeoutError())
    assert is_retryable_generation_error(httpx.ReadTimeout("read timed out"))
    assert is_retryable_generation_error(httpx.ConnectError("connection refused"))
    err = httpx.HTTPStatusError(
        "server error",
        request=httpx.Request("POST", "http://test/v1/chat/completions"),
        response=httpx.Response(503),
    )
    assert is_retryable_generation_error(err)
    assert not is_retryable_generation_error(ValueError("bad prompt"))


def test_world_generation_policy_defaults() -> None:
    policy = world_generation_policy({})
    assert policy["max_retries"] == 2
    assert policy["max_continue_depth"] == 2
    assert policy["inference_timeout_seconds"] == 180.0


def test_demo_fixture_policy() -> None:
    import json

    raw = (
        Path(__file__).resolve().parent / "fixtures" / "demo-world" / "demo-spatial-v1.json"
    ).read_text(encoding="utf-8")
    cfg = json.loads(raw)["config"]
    policy = world_generation_policy(cfg)
    assert policy["max_continue_depth"] == 8
    assert policy["max_retries"] == 2
    assert policy["inference_timeout_seconds"] == 180.0


@pytest.fixture
def retry_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "retry.db",
        mock_llm=False,
        llm_base_url="http://127.0.0.1:9",
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def _wait_job_done(client: TestClient, job_id: str, timeout: float = 30.0) -> dict:
    store = client.app.state.services.store
    deadline = time.time() + timeout
    while time.time() < deadline:
        row = store.get_job(job_id)
        if row and row["status"] in ("done", "cancelled"):
            return row
        time.sleep(0.05)
    raise TimeoutError(f"job {job_id} did not finish")


def test_orchestrator_retries_transient_llm_failure(retry_client: TestClient) -> None:
    svc = retry_client.app.state.services
    calls = {"n": 0}

    async def flaky_chat(_messages, _tools=None, *, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ReadTimeout("simulated timeout")
        return {
            "choices": [
                {"message": {"role": "assistant", "content": "Recovered after retries."}}
            ]
        }

    svc.llm.chat = flaky_chat  # type: ignore[method-assign]

    world_id = retry_client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    retry_client.patch(
        f"/api/v1/worlds/{world_id}", json={"activeSceneId": PROGRAM_OFFICE}
    )
    resp = retry_client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={"text": "Quick check-in on program management.", "scope": "public"},
    )
    job_id = resp.json()["generationJob"]["jobId"]
    row = _wait_job_done(retry_client, job_id)
    assert row["status"] == "done"
    assert calls["n"] == 3

    msg = svc.store.fetchone(
        "SELECT outputText FROM Message WHERE generationJobId = ?",
        (job_id,),
    )
    assert "Recovered after retries" in (msg["outputText"] or "")
