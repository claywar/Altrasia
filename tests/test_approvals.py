"""APR-1 approval queue for webtools_invoke."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.tools.handlers import register_core_tools
from altrasia.tools.registry import ToolContext, ToolRegistry


def test_webtools_requires_approval_when_character_asks(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "apr.db",
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
