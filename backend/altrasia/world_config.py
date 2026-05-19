from __future__ import annotations

import json
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

POLICY_KEYS = (
    "requireWebToolApproval",
    "auditWebTools",
    "webToolsMock",
    "pauseCommissionsDuringPersonaDialogue",
    "mandatoryRecallBlocking",
    "maxContinueDepth",
    "citeProvenanceInPrompt",
    "commonsAccessIds",
    "speakIntentOnTie",
    "orgRecallEnabled",
    "orgRecallMaxChars",
    "sceneFramingEnabled",
    "castSummonEnabled",
    "summonRoles",
    "narrativePresenceMode",
    "briefingMaxReplies",
)


def get_world_config(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        return {}
    return SqlitePersistence.json_loads(world.get("configJson"), {})


def merge_world_policy(store: SqlitePersistence, world_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    cfg = get_world_config(store, world_id)
    for key in POLICY_KEYS:
        if key in policy and policy[key] is not None:
            cfg[key] = policy[key]
    store.update_world(world_id, configJson=json.dumps(cfg))
    return cfg
