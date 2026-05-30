from __future__ import annotations

import json
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

POLICY_KEYS = (
    "requireWebToolApproval",
    "auditWebTools",
    "webToolsMock",
    "webAllowlistHosts",
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
    "idleBanterEnabled",
    "idleSocialEnabled",
    "operatorInteractionCooldownSeconds",
    "idleSocialMaxDepth",
    "idleSocialMinCast",
    "idleSocialRecencyHalfLifeSeconds",
    "idleSocialExplorationRate",
    "idleSocialJitter",
    "idleSocialTopK",
    "idleSocialVarietyWindow",
    "idleParticipationWeights",
    "idleSocialTone",
    "idleSocialTaskAffinityEnabled",
    "idleSocialTaskAffinityWeight",
    "idleSocialBanterDiaryWindow",
    "idleSocialBanterDiaryMaxChars",
    "idleSocialBanterDiaryMaxEntries",
    "idleSocialBanterRecallMaxChars",
    "idleSocialSessionCooldownSeconds",
    "idleSocialStartProbability",
    "idleSocialDigestWindowSeconds",
    "idleSocialTabIntervalSeconds",
    "socialSignalEnabled",
    "floorHoldEnabled",
    "floorHoldClearAfterSeconds",
    "floorClaimBoost",
    "castFloorClaimReactive",
    "addressingFuzzyEnabled",
    "addressingFuzzyMaxDistance",
    "defaultWebToolsAccessBySceneRole",
    "reflectionEnabled",
    "reflectionNightlyHourUtc",
    "reflectionMaxCharsPerRun",
    "reflectionAutoApproveLoci",
    "reflectionLocusMaxChars",
    "reflectionPersonaProposalsEnabled",
    "imageDefaultProfileId",
    "imageWorkflowProfiles",
    "imageUseOperatorDefaults",
    "requireApprovalForImageGen",
    "allowCastImageGen",
)

IDLE_SOCIAL_DEFAULTS: dict[str, Any] = {
    "idleBanterEnabled": True,
    "idleSocialEnabled": True,
    "operatorInteractionCooldownSeconds": 120,
    "idleSocialMaxDepth": 3,
    "idleSocialMinCast": 2,
    "idleSocialRecencyHalfLifeSeconds": 300,
    "idleSocialExplorationRate": 0.12,
    "idleSocialJitter": 0.15,
    "idleSocialTopK": 3,
    "idleSocialVarietyWindow": 8,
    "idleParticipationWeights": {},
    "idleSocialTone": "roleplay",
    "idleSocialTaskAffinityEnabled": True,
    "idleSocialTaskAffinityWeight": 0.22,
    "idleSocialBanterDiaryWindow": 2,
    "idleSocialBanterDiaryMaxChars": 480,
    "idleSocialBanterDiaryMaxEntries": 2,
    "idleSocialBanterRecallMaxChars": 120,
    "idleSocialSessionCooldownSeconds": 180,
    "idleSocialStartProbability": 0.4,
    "idleSocialDigestWindowSeconds": 300,
    "idleSocialTabIntervalSeconds": 45,
    "socialSignalEnabled": True,
    "floorHoldEnabled": True,
    "floorHoldClearAfterSeconds": 90,
    "floorClaimBoost": 0.85,
    "castFloorClaimReactive": False,
}

# Apply via merge_world_policy for quieter, digestion-focused idle social.
BALANCED_SOCIAL_PRESET: dict[str, Any] = {
    **IDLE_SOCIAL_DEFAULTS,
    "idleSocialMaxDepth": 2,
    "idleSocialRecencyHalfLifeSeconds": 600,
    "idleSocialExplorationRate": 0,
    "idleSocialJitter": 0.08,
    "idleSocialTaskAffinityWeight": 0.35,
    "idleSocialTone": "professional",
    "floorHoldClearAfterSeconds": 120,
}


def get_world_config(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        return {}
    return SqlitePersistence.json_loads(world.get("configJson"), {})


def get_idle_social_config(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    cfg = {**IDLE_SOCIAL_DEFAULTS, **get_world_config(store, world_id)}
    return cfg


REFLECTION_DEFAULTS: dict[str, Any] = {
    "reflectionEnabled": False,
    "reflectionNightlyHourUtc": 3,
    "reflectionMaxCharsPerRun": 6000,
    "reflectionAutoApproveLoci": True,
    "reflectionLocusMaxChars": 2000,
    "reflectionPersonaProposalsEnabled": True,
}


def get_reflection_config(store: SqlitePersistence, world_id: str) -> dict[str, Any]:
    return {**REFLECTION_DEFAULTS, **get_world_config(store, world_id)}


def merge_world_policy(store: SqlitePersistence, world_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    cfg = get_world_config(store, world_id)
    for key in POLICY_KEYS:
        if key in policy and policy[key] is not None:
            cfg[key] = policy[key]
    store.update_world(world_id, configJson=json.dumps(cfg))
    return cfg
