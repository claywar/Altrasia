"""Shared pytest helpers for API integration tests."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.services import AppServices


def make_test_settings(tmp_path: Path, db_name: str = "test.db", **extra: object) -> Settings:
    """Isolated Settings: tmp data_dir prevents ~/.altrasia operator config from disabling mock LLM."""
    return Settings(
        data_dir=tmp_path,
        db_path=tmp_path / db_name,
        mock_llm=True,
        web_tools_mock=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
        **extra,  # type: ignore[arg-type]
    )


def wait_for_jobs(
    client: TestClient,
    world_id: str,
    *,
    timeout: float = 45.0,
) -> None:
    """Wait until no queued/running generation jobs remain for the world."""
    deadline = time.time() + timeout
    store = client.app.state.services.store
    while time.time() < deadline:
        row = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND status IN ('queued', 'running')""",
            (world_id,),
        ).fetchone()
        if row[0] == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


@pytest.fixture
def app_client(tmp_path: Path) -> Iterator[tuple[TestClient, AppServices]]:
    """TestClient with isolated data_dir so operator ~/.altrasia config cannot disable mock LLM."""
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "test.db",
        mock_llm=True,
        web_tools_mock=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, client.app.state.services
