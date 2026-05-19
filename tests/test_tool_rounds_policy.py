"""Tool rounds per job are separate from agent_continue speaker depth."""

from __future__ import annotations

from altrasia.orchestrator.generation_policy import world_generation_policy


def test_max_tool_rounds_from_config() -> None:
    cfg = {"maxToolRoundsPerJob": 7, "maxContinueDepth": 2}
    policy = world_generation_policy(cfg)
    assert policy["max_tool_rounds_per_job"] == 7
    assert policy["max_continue_depth"] == 2
