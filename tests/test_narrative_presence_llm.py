"""Narrative presence llm/detect mode (NP-LLM-1–4)."""

import json
from pathlib import Path

import pytest

from altrasia.domain.narrative_presence import apply_narrative_presence
from altrasia.domain.narrative_presence_llm import (
    detect_narrative_presence_llm,
    extract_presence_block,
    parse_presence_actions,
)
from altrasia.domain.shared_stash import get_scene_stash
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.services import AppServices
from altrasia.config import Settings


SAMPLE = '''Sure — I'll grab a snack.

```json
{
  "narrativePresence": {
    "actions": [
      {"kind": "stash_take", "stashKey": "snack-shelf", "itemId": "item-granola-2"}
    ]
  }
}
```
'''


def test_extract_presence_block_strips_fence() -> None:
    cleaned, presence = extract_presence_block(SAMPLE)
    assert presence is not None
    assert presence.get("actions")
    assert "```" not in cleaned
    assert "grab a snack" in cleaned


def test_parse_presence_actions_defaults_character() -> None:
    presence = {"actions": [{"kind": "join", "sceneId": "scene-break-room"}]}
    acts = parse_presence_actions(presence, speaker_id="char-a")
    assert acts[0]["characterId"] == "char-a"


def test_detect_mode_does_not_apply_by_default() -> None:
    cleaned, detection = detect_narrative_presence_llm(
        SAMPLE, mode="detect", speaker_id="char-jordan-reyes"
    )
    assert detection is not None
    assert detection["mode"] == "detect"
    assert cleaned != SAMPLE


@pytest.mark.asyncio
async def test_llm_stash_take_applied(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "np-llm.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    world_id = meta["worldId"]
    scene_id = "scene-break-room"
    cid = "char-jordan-reyes"
    svc.presence.join(scene_id, cid)
    before = len(get_scene_stash(svc.store, scene_id)["snack-shelf"]["items"])
    _, detection = detect_narrative_presence_llm(SAMPLE, mode="llm", speaker_id=cid)
    assert detection
    applied = await apply_narrative_presence(
        svc,
        world_id=world_id,
        detection=detection,
        speaker_id=cid,
        source_scene_id=scene_id,
    )
    assert applied
    after = len(get_scene_stash(svc.store, scene_id)["snack-shelf"]["items"])
    assert after == before - 1


def test_invalid_json_block_is_noop() -> None:
    text = "Hello\n```json\n{not json}\n```"
    cleaned, payload = extract_presence_block(text)
    assert payload is None
    assert cleaned == text
