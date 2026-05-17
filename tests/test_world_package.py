"""DM-4 world package export/import round-trip."""

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.world_package import export_world_package, import_world_package


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings(
        data_dir=tmp_path,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app), app.state.services


def test_dm4_package_round_trip(client: tuple[TestClient, object]) -> None:
    client, services = client
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    blob = export_world_package(services.store, world_id)
    imported = import_world_package(services.store, blob, assets_dir=services.settings.data_dir / "assets")
    assert imported["worldId"] != world_id
    scenes = services.store.list_scenes(imported["worldId"])
    assert len(scenes) >= 2
    members = services.store.list_world_characters(imported["worldId"])
    assert len(members) >= 2


def test_dm4_api_export_import(client: tuple[TestClient, object]) -> None:
    client, services = client
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    world_id = r.json()["worldId"]
    exp = client.get(f"/api/v1/worlds/{world_id}/package/export")
    assert exp.status_code == 200
    assert exp.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(exp.content))
    assert "manifest.json" in zf.namelist()
    imp = client.post(
        "/api/v1/worlds/import",
        files={"file": ("world.zip", exp.content, "application/zip")},
    )
    assert imp.status_code == 200
    new_id = imp.json()["worldId"]
    assert new_id != world_id
    assert len(services.store.list_scenes(new_id)) >= 2
