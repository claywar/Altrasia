"""Per-character web tools access policy."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.tools.web_access import (
    parse_web_tools_access,
    resolve_web_tools_policy,
)


@pytest.mark.parametrize(
    "definition,expected",
    [
        ({}, "off"),
        ({"webToolsAccess": "ask"}, "ask"),
        ({"webToolsAccess": "ALLOW"}, "allow"),
        ({"webToolsAccess": "bogus"}, "off"),
    ],
)
def test_parse_web_tools_access(definition: dict, expected: str) -> None:
    assert parse_web_tools_access(definition) == expected


def test_resolve_policy_ask_requires_approval(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "web.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
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
    policy = resolve_web_tools_policy(svc.store, world_id, cid)
    assert policy["exposed"] is True
    assert policy["require_approval"] is True


def test_resolve_policy_allow_overrides_world(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "web.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    world = svc.store.get_world(world_id)
    cfg = json.loads(world["configJson"])
    cfg["requireWebToolApproval"] = True
    svc.store.update_world(world_id, configJson=json.dumps(cfg))
    cid = "char-jordan-reyes"
    client.patch(
        f"/api/v1/characters/{cid}",
        json={"definition": {"webToolsAccess": "allow"}},
    )
    policy = resolve_web_tools_policy(svc.store, world_id, cid)
    assert policy["exposed"] is True
    assert policy["require_approval"] is False


def test_off_character_strips_web_tool_names(tmp_path: Path) -> None:
    from altrasia.orchestrator.engine import Orchestrator

    settings = Settings(
        db_path=tmp_path / "web2.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    cid = "char-jordan-reyes"
    orch = Orchestrator(svc)
    job = {"worldId": world_id, "characterId": cid}
    filtered = orch._apply_web_tool_filter(
        job, {"webtools_invoke", "memory_search", "memory_store"}
    )
    assert "webtools_invoke" not in filtered
    assert "memory_search" in filtered
