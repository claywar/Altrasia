"""MediaAsset persistence and asset route tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.services import AppServices


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_media_asset_roundtrip(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "media2.db",
        data_dir=tmp_path / "altrasia-data",
        api_token="test-token",
    )
    svc = AppServices.create(settings)
    svc.store.insert_world(
        {
            "worldId": "w1",
            "name": "Test",
            "activeSceneId": "s1",
            "defaultModelProfile": "default",
            "configJson": "{}",
            "worldMapJson": "{}",
            "eventSeq": 0,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
    )
    assets_dir = settings.data_dir / "assets" / "w1" / "media"
    assets_dir.mkdir(parents=True)
    png = b"\x89PNG\r\n\x1a\n"
    rel = "w1/media/a1.png"
    (settings.data_dir / "assets" / rel).write_bytes(png)
    svc.store.insert_media_asset(
        asset_id="a1",
        world_id="w1",
        path=rel,
        sha256="abc",
        workflow_id="fixture_icon",
        model_profile_id="sdxl-default",
        created_at="2026-01-01T00:00:00Z",
    )
    app = create_app(settings)
    c = TestClient(app)
    r = c.get("/api/v1/worlds/w1/assets/a1", headers=_auth_headers())
    assert r.status_code == 200
    assert r.content.startswith(b"\x89PNG")
