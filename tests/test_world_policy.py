"""PATCH world policy merges into configJson."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_patch_world_policy(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "pol.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    patched = client.patch(
        f"/api/v1/worlds/{world_id}/policy",
        json={"requireWebToolApproval": True},
    ).json()
    assert patched["requireWebToolApproval"] is True
    got = client.get(f"/api/v1/worlds/{world_id}/policy").json()
    assert got["requireWebToolApproval"] is True
