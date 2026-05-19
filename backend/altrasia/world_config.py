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
    "generationMaxRetries",
    "generationRetryBackoffSeconds",
    "inferenceTimeoutSeconds",
    "generationRecoveryEnabled",
    "continueUntilResolved",
    "maxContinueDepthExtended",
    "maxContinueDepthCap",
    "conversationJudgementEnabled",
    "discussionSignalsEnabled",
    "discussionDeliverablesEnabled",
    "maxDeliverablesPerDiscussion",
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
    "presenceAnnounce",
    "idleSocialEnabled",
    "idleSocialMaxDepth",
    "idleSocialMinCast",
    "idleSocialRecencyHalfLifeSeconds",
    "idleSocialExplorationRate",
    "idleSocialJitter",
    "idleSocialTopK",
    "idleSocialVarietyWindow",
    "idleParticipationWeights",
    "socialSignalEnabled",
    "floorHoldEnabled",
    "floorHoldClearAfterSeconds",
    "floorClaimBoost",
    "castFloorClaimReactive",
    "addressingFuzzyEnabled",
    "addressingFuzzyMaxDistance",
)

IDLE_SOCIAL_DEFAULTS: dict[str, Any] = {
    "idleSocialEnabled": True,
    "idleSocialMaxDepth": 3,
    "idleSocialMinCast": 2,
    "idleSocialRecencyHalfLifeSeconds": 300,
    "idleSocialExplorationRate": 0.12,
    "idleSocialJitter": 0.15,
    "idleSocialTopK": 3,
    "idleSocialVarietyWindow": 8,
    "idleParticipationWeights": {},
    "socialSignalEnabled": True,
    "floorHoldEnabled": True,
    "floorHoldClearAfterSeconds": 90,
    "floorClaimBoost": 0.85,
    "castFloorClaimReactive": False,
}


def get_world_config(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        return {}
    return SqlitePersistence.json_loads(world.get("configJson"), {})


def get_idle_social_config(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    cfg = {**IDLE_SOCIAL_DEFAULTS, **get_world_config(store, world_id)}
    return cfg


def merge_world_policy(store: SqlitePersistence, world_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    cfg = get_world_config(store, world_id)
    for key in POLICY_KEYS:
        if key in policy and policy[key] is not None:
            cfg[key] = policy[key]
    store.update_world(world_id, configJson=json.dumps(cfg))
    return cfg
