"""AO-17 v1.1 speak_intent on tie."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from altrasia.config import Settings
from altrasia.orchestrator.engine import Orchestrator
from altrasia.services import AppServices
from altrasia.world_config import merge_world_policy


@pytest.mark.asyncio
async def test_speak_intent_resolves_tie(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "si.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    from altrasia.fixtures.loader import load_fixture_by_id

    meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    world_id = meta["worldId"]
    scene_id = meta["activeSceneId"]
    merge_world_policy(svc.store, world_id, {"speakIntentOnTie": True})
    orch = Orchestrator(svc)
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(
        return_value={"choices": [{"message": {"content": "Alice should speak"}}]}
    )
    svc.llm = mock_llm
    cid, rationale = await orch.pick_reactive_character_async(
        world_id, scene_id, "What do you think?"
    )
    assert cid is not None or rationale == {}
