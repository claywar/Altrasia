from __future__ import annotations

import json
from typing import Any

PERSONA_ID = "__persona__"


def parse_comm(meta_json: str) -> dict[str, Any]:
    meta = json.loads(meta_json or "{}")
    return meta.get("communication", {})


def can_perceive(
    *,
    viewer_id: str,
    message: dict[str, Any],
    present: list[str],
    viewer_scene_id: str | None = None,
    channel: dict[str, Any] | None = None,
) -> bool:
    """CC-7 / CC-8: public, whisper, dm, narrator, phone."""
    if viewer_id == PERSONA_ID and message.get("role") == "user":
        return True
    comm = parse_comm(message.get("metaJson", "{}"))
    scope = comm.get("scope", "public")
    if scope == "public" or scope == "narrator":
        return True
    if scope == "whisper":
        participants = comm.get("participants") or []
        return viewer_id in participants or viewer_id == PERSONA_ID
    if scope == "dm":
        participants = comm.get("participants") or []
        speaker = message.get("characterId")
        return viewer_id in participants or viewer_id == speaker
    if scope == "phone":
        return _can_perceive_phone(
            viewer_id=viewer_id,
            message=message,
            comm=comm,
            present=present,
            viewer_scene_id=viewer_scene_id,
            channel=channel,
        )
    return True


def _can_perceive_phone(
    *,
    viewer_id: str,
    message: dict[str, Any],
    comm: dict[str, Any],
    present: list[str],
    viewer_scene_id: str | None,
    channel: dict[str, Any] | None,
) -> bool:
    participants = comm.get("participants") or []
    if viewer_id in participants:
        return True
    if viewer_id == PERSONA_ID and viewer_id in present:
        return True
    if not viewer_scene_id or not channel:
        return False
    if viewer_id not in present:
        return False
    endpoints = json.loads(channel.get("endpointsJson") or "[]")
    endpoint = next((e for e in endpoints if e.get("sceneId") == viewer_scene_id), None)
    if not endpoint:
        return False
    if endpoint.get("speakerphone"):
        return True
    meta = json.loads(message.get("metaJson") or "{}")
    speaker_scene = (meta.get("phone") or {}).get("speakerSceneId")
    return speaker_scene == viewer_scene_id
