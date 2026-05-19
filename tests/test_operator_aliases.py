"""Operator-declared nicknames persisted per world."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.operator_aliases import (
    apply_operator_alias_declaration,
    operator_alias_map,
    operator_aliases_for_character,
    parse_operator_alias_declaration,
)
from altrasia.orchestrator.speaker_selection import parse_addressing

PROGRAM_OFFICE = "scene-program-office"


def _fixture_chars() -> tuple[list[str], dict]:
    data = json.loads(
        Path(__file__).resolve().parent.joinpath("fixtures/demo-world/demo-spatial-v1.json").read_text()
    )
    cast = [
        "char-liam-park",
        "char-rachel-kim",
        "char-tom-bradley",
        "char-nina-patel",
        "char-chris-doyle",
    ]
    chars = {c["characterId"]: c for c in data["characters"]}
    return cast, chars


def test_parse_and_register_lili_for_liam(alias_client: tuple) -> None:
    client, world_id = alias_client
    svc = client.app.state.services
    cast, chars = _fixture_chars()
    text = "Liam, I will now refer to you as LiLi when I desire"
    parsed = parse_operator_alias_declaration(text, cast, chars)
    assert parsed == ("char-liam-park", "LiLi")
    assert apply_operator_alias_declaration(svc.store, world_id, text, cast, chars)
    assert operator_aliases_for_character(svc.store, world_id, "char-liam-park") == ["LiLi"]
    result = parse_addressing(
        "LiLi, what's your role?",
        cast,
        chars,
        operator_alias_map=operator_alias_map(svc.store, world_id),
    )
    assert result.mode == "directed"
    assert result.primary_id == "char-liam-park"


@pytest.fixture
def alias_client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "alias_int.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    with TestClient(create_app(settings)) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        client.patch(
            f"/api/v1/worlds/{world_id}",
            json={"activeSceneId": PROGRAM_OFFICE},
        )
        yield client, world_id


def test_lili_routes_to_liam_after_declaration(alias_client: tuple) -> None:
    client, world_id = alias_client
    declare = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={
            "text": "Liam, I will now refer to you as LiLi when I desire",
            "scope": "public",
        },
    )
    assert declare.status_code == 200
    follow = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={"text": "LiLi, say the word Purple", "scope": "public"},
    )
    assert follow.status_code == 200
    meta = json.loads(
        client.app.state.services.store.fetchone(
            "SELECT metaJson FROM Message WHERE messageId = ?",
            (follow.json()["messageId"],),
        )["metaJson"]
    )
    assert meta["orchestration"]["addressing"]["primaryId"] == "char-liam-park"
    assert meta["orchestration"]["addressing"]["mode"] == "directed"
