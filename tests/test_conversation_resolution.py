"""Continue-until-resolved depth policy."""

from __future__ import annotations

from altrasia.orchestrator.conversation_resolution import (
    effective_continue_depth_limit,
    is_scene_conversation_unresolved,
)


class _FakeStore:
    def __init__(self, messages: list[dict]) -> None:
        self._messages = messages

    def list_messages(self, _world_id: str, scene_id: str | None = None) -> list[dict]:
        return self._messages


def test_unresolved_extends_past_base_depth() -> None:
    cfg = {
        "maxContinueDepth": 8,
        "continueUntilResolved": True,
        "maxContinueDepthExtended": 20,
        "maxContinueDepthCap": 24,
    }
    assert effective_continue_depth_limit(cfg, 8, unresolved=True) == 20
    assert effective_continue_depth_limit(cfg, 8, unresolved=False) == 8
    assert effective_continue_depth_limit(cfg, 3, unresolved=True) == 8


def test_resolution_detected_stops_extension() -> None:
    store = _FakeStore(
        [
            {
                "role": "user",
                "outputText": "Everyone discuss program management — how should we align?",
            },
            {
                "role": "assistant",
                "characterId": "a",
                "streamStatus": "final",
                "outputText": "We have agreed to use a single intake board and next steps are defined.",
            },
        ]
    )
    unresolved, reason = is_scene_conversation_unresolved(
        store, "w", "s", min_cast_replies=1
    )
    assert not unresolved
    assert reason == "resolution_detected"


def test_open_discussion_stays_unresolved() -> None:
    store = _FakeStore(
        [
            {
                "role": "user",
                "outputText": "Discuss program management among yourselves.",
            },
            {
                "role": "assistant",
                "characterId": "a",
                "streamStatus": "final",
                "outputText": "Dependencies are still TBD on my side.",
            },
            {
                "role": "assistant",
                "characterId": "b",
                "streamStatus": "final",
                "outputText": "I see tension between roadmap and capacity.",
            },
        ]
    )
    unresolved, reason = is_scene_conversation_unresolved(store, "w", "s")
    assert unresolved
    assert reason in ("still_open_language", "discussion_invited_no_closure")
