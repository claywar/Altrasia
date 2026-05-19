"""APR-1 approval queue for webtools_invoke."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.tools.handlers import register_core_tools
from altrasia.tools.registry import ToolContext, ToolRegistry


def test_webtools_requires_approval_when_configured(tmp_path: Path) -> None:
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
    world = svc.store.get_world(world_id)
    cfg = json.loads(world["configJson"])
    cfg["requireWebToolApproval"] = True
    svc.store.update_world(world_id, configJson=json.dumps(cfg))

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
                character_id="char-jordan-reyes",
                services=svc,
            ),
        )
    )
    data = json.loads(result)
    assert data.get("approvalRequired") is True
    pending = client.get(f"/api/v1/worlds/{world_id}/approvals").json()
    assert len(pending) >= 1
    aid = pending[0]["approvalId"]
    approved = client.post(f"/api/v1/worlds/{world_id}/approvals/{aid}/approve").json()
    assert approved["state"] == "approved"
