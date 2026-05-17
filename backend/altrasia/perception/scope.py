from __future__ import annotations

import json
from typing import Any


def parse_comm(meta_json: str) -> dict[str, Any]:
    meta = json.loads(meta_json or "{}")
    return meta.get("communication", {})


def can_perceive(
    *,
    viewer_id: str,
    message: dict[str, Any],
    present: list[str],
) -> bool:
    """CC-7 v1: public, whisper, dm, narrator."""
    comm = parse_comm(message.get("metaJson", "{}"))
    scope = comm.get("scope", "public")
    if scope == "public" or scope == "narrator":
        return True
    if scope == "whisper":
        participants = comm.get("participants") or []
        return viewer_id in participants or viewer_id == "__persona__"
    if scope == "dm":
        participants = comm.get("participants") or []
        speaker = message.get("characterId")
        return viewer_id in participants or viewer_id == speaker
    return True
