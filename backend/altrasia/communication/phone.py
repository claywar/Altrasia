"""v1.1 phone channels (CC-8–CC-13, docs/04-communication.md §3)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from altrasia.domain.presence import PERSONA_ID


def parse_endpoints(channel: dict[str, Any]) -> list[dict[str, Any]]:
    return json.loads(channel.get("endpointsJson") or "[]")


def parse_participants(channel: dict[str, Any]) -> list[str]:
    return json.loads(channel.get("participantsJson") or "[]")


class PhoneService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def list_active(self, world_id: str) -> list[dict[str, Any]]:
        return self.store.list_channels(world_id, active_only=True)

    def get(self, channel_id: str) -> dict[str, Any] | None:
        return self.store.get_channel(channel_id)

    def create_channel(
        self,
        *,
        world_id: str,
        scene_a: str,
        character_a: str,
        scene_b: str,
        character_b: str,
    ) -> dict[str, Any]:
        channel_id = str(uuid.uuid4())
        endpoints = [
            {
                "sceneId": scene_a,
                "participantIds": [character_a],
                "speakerphone": False,
            },
            {
                "sceneId": scene_b,
                "participantIds": [character_b],
                "speakerphone": False,
            },
        ]
        participants = [character_a, character_b]
        row = {
            "channelId": channel_id,
            "worldId": world_id,
            "endpointsJson": json.dumps(endpoints),
            "participantsJson": json.dumps(participants),
            "active": 1,
        }
        self.store.insert_channel(row)
        return row

    def set_speakerphone(self, channel_id: str, scene_id: str, enabled: bool) -> dict[str, Any]:
        ch = self.get(channel_id)
        if not ch:
            raise ValueError("channel not found")
        endpoints = parse_endpoints(ch)
        for ep in endpoints:
            if ep["sceneId"] == scene_id:
                ep["speakerphone"] = enabled
        self.store.update_channel(channel_id, endpointsJson=json.dumps(endpoints))
        return self.get(channel_id)  # type: ignore[return-value]

    def end_channel(self, channel_id: str) -> None:
        self.store.update_channel(channel_id, active=0)

    def endpoint_for_scene(self, channel: dict[str, Any], scene_id: str) -> dict[str, Any] | None:
        for ep in parse_endpoints(channel):
            if ep["sceneId"] == scene_id:
                return ep
        return None

    def remote_scenes(self, channel: dict[str, Any], speaker_scene_id: str) -> list[str]:
        return [
            ep["sceneId"]
            for ep in parse_endpoints(channel)
            if ep["sceneId"] != speaker_scene_id
        ]

    def insert_phone_line(
        self,
        *,
        world_id: str,
        speaker_scene_id: str,
        channel_id: str,
        text: str,
        role: str = "user",
        character_id: str | None = None,
        created_at: str,
    ) -> tuple[str, list[str]]:
        """Canonical message + mirror stubs on other endpoint scenes (CC-10)."""
        ch = self.get(channel_id)
        if not ch or ch["worldId"] != world_id:
            raise ValueError("invalid channel")
        msg_id = str(uuid.uuid4())
        meta = {
            "communication": {
                "scope": "phone",
                "channelId": channel_id,
                "participants": parse_participants(ch),
            },
            "phone": {"speakerSceneId": speaker_scene_id},
        }
        self.store.insert_message(
            {
                "messageId": msg_id,
                "worldId": world_id,
                "channelKind": "scene",
                "sceneId": speaker_scene_id,
                "role": role,
                "characterId": character_id,
                "outputText": text,
                "reasoning": None,
                "streamStatus": "final",
                "generationJobId": None,
                "metaJson": json.dumps(meta),
                "createdAt": created_at,
            }
        )
        mirror_ids: list[str] = []
        for remote_scene in self.remote_scenes(ch, speaker_scene_id):
            mid = str(uuid.uuid4())
            mirror_meta = {
                "communication": {
                    "scope": "phone",
                    "channelId": channel_id,
                    "participants": parse_participants(ch),
                    "mirrorOf": msg_id,
                },
                "phone": {"speakerSceneId": speaker_scene_id},
            }
            self.store.insert_message(
                {
                    "messageId": mid,
                    "worldId": world_id,
                    "channelKind": "scene",
                    "sceneId": remote_scene,
                    "role": role,
                    "characterId": character_id,
                    "outputText": text,
                    "reasoning": None,
                    "streamStatus": "final",
                    "generationJobId": None,
                    "metaJson": json.dumps(mirror_meta),
                    "createdAt": created_at,
                }
            )
            mirror_ids.append(mid)
        return msg_id, mirror_ids

    def phone_target_at_other_end(self, channel_id: str, speaker_scene_id: str) -> tuple[str, str] | None:
        """Return (character_id, scene_id) for participant at the other endpoint."""
        ch = self.get(channel_id)
        if not ch:
            return None
        for ep in parse_endpoints(ch):
            if ep["sceneId"] == speaker_scene_id:
                continue
            pids = ep.get("participantIds") or []
            for pid in pids:
                if pid != PERSONA_ID:
                    return pid, ep["sceneId"]
        return None
