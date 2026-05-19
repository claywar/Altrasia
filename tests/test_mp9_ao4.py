"""MP-9 mandatory recall tool gating; AO-4 idle round-robin."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.inference import mock_llm
ISO = lambda: datetime.now(timezone.utc).isoformat()


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "spec.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app), app.state.services


def _wait_jobs(client: TestClient, world_id: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
        if not q.get("busy") and q.get("depth", 0) == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_mp9_first_call_memory_tools_only(client: tuple[TestClient, object]) -> None:
    """docs/17 — MP-9: blocking on limits first model call to memory_* / diary_*."""
    client, _ = client
    mock_llm.clear_tool_snapshots()
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    hall = "scene-lobby"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/messages",
        json={"text": "What is the capital of France?", "scope": "public"},
    )
    _wait_jobs(client, world_id)
    assert mock_llm.tool_snapshots(), "expected at least one LLM call with tools"
    first = mock_llm.tool_snapshots()[0]
    assert first, "first call should expose tools when blocking is on"
    assert all(n.startswith("memory_") or n.startswith("diary_") for n in first)
    assert "scene_update_fixture" not in first


def test_ao4_idle_round_robin_three_npcs(client: tuple[TestClient, object]) -> None:
    """docs/17 — AO-4: idle cursor visits jordan → sofia → priya in sorted order."""
    client, services = client
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    hall = "scene-lobby"
    store = services.store
    store.update_scene(
        hall,
        presentJson=json.dumps(["char-jordan-reyes", "char-sofia-mendez", "char-priya-nair"]),
        roundRobinIndex=0,
    )
    sched = services.idle_scheduler
    assert sched is not None
    cast = sorted(["char-jordan-reyes", "char-sofia-mendez", "char-priya-nair"])
    picked: list[str] = []
    for _ in range(3):
        scene = store.get_scene(hall)
        picked.append(sched._pick_idle_character(scene, cast))
    assert picked == cast
    assert int(store.get_scene(hall)["roundRobinIndex"]) == 0
