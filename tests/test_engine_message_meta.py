"""Scene message metaJson includes orchestration for idle jobs."""

from __future__ import annotations

import json

from altrasia.orchestrator.engine import _merge_tool_calls_rationale, _scene_message_meta


def test_idle_timer_meta_includes_orchestration() -> None:
    job = {
        "trigger": "idle_timer",
        "selectionRationaleJson": json.dumps(
            {"pick": "idle_timer", "characterId": "char-alice", "idle_source": "tab_visible"}
        ),
    }
    meta = _scene_message_meta(job)
    assert meta["orchestration"]["trigger"] == "idle_timer"
    assert meta["orchestration"]["idleSource"] == "tab_visible"


def test_reactive_meta_has_trigger_only() -> None:
    meta = _scene_message_meta({"trigger": "reactive"})
    assert meta["orchestration"]["trigger"] == "reactive"
    assert "idleSource" not in meta["orchestration"]


def test_merge_tool_calls_into_rationale() -> None:
    merged = json.loads(
        _merge_tool_calls_rationale(
            json.dumps({"pick": "reactive", "characterId": "char-alice"}),
            [{"name": "memory_search", "arguments": {"query": "keys"}, "result": "ok"}],
        )
    )
    assert merged["pick"] == "reactive"
    assert merged["toolCalls"][0]["name"] == "memory_search"
