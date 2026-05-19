from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from concurrent.futures import CancelledError as FuturesCancelledError
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.presence import PERSONA_ID
from altrasia.inference.queue import TokenStream
from altrasia.inference.tool_calls import normalize_assistant_message
from altrasia.memory.strip_reasoning import strip_from_message_payload
from altrasia.tools.registry import ToolContext
from altrasia.world_geography import lock_geography_on_first_play

ISO = lambda: datetime.now(timezone.utc).isoformat()

log = logging.getLogger(__name__)


def _merge_tool_calls_rationale(
    selection_rationale_json: str | None, tool_log: list[dict[str, Any]]
) -> str:
    try:
        rationale = json.loads(selection_rationale_json or "{}")
    except (json.JSONDecodeError, TypeError):
        rationale = {}
    if not isinstance(rationale, dict):
        rationale = {}
    rationale["toolCalls"] = tool_log
    return json.dumps(rationale)


def _scene_message_meta(job: dict[str, Any]) -> dict[str, Any]:
    """Communication + orchestration metadata stored on scene messages (UI-AMB)."""
    meta: dict[str, Any] = {"communication": {"scope": "public"}}
    trigger = job.get("trigger")
    if trigger:
        orch: dict[str, Any] = {"trigger": trigger}
        try:
            rationale = json.loads(job.get("selectionRationaleJson") or "{}")
        except (json.JSONDecodeError, TypeError):
            rationale = {}
        if trigger == "idle_timer" and rationale.get("idle_source"):
            orch["idleSource"] = rationale["idle_source"]
        if trigger == "discussion_deliverable":
            if rationale.get("deliverableKind"):
                orch["deliverableKind"] = rationale["deliverableKind"]
            if rationale.get("deliverableId"):
                orch["deliverableId"] = rationale["deliverableId"]
        meta["orchestration"] = orch
    return meta


_GENERATION_FAILED_TEXT = (
    "Generation failed. Check inference logs or the ⓘ job details."
)

_AGENT_CONTINUE_TRIGGERS = frozenset({"persona_message", "agent_continue"})


def _generation_error_text(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return text[:200]
    return f"{type(exc).__name__} (no message)"


def _message_meta_with_generation_error(job: dict[str, Any], exc: BaseException) -> str:
    meta = _scene_message_meta(job)
    meta["generationError"] = _generation_error_text(exc)
    return json.dumps(meta)


class Orchestrator:
    def __init__(self, services: Any) -> None:
        self.svc = services
        self._workers: dict[str, asyncio.Task] = {}
        self._scene_chain_active: set[str] = set()

    def _emit(self, world_id: str, event: str, data: dict[str, Any]) -> None:
        self.svc.event_bus.emit(self.svc.store, world_id, event, data)

    def _emit_queue(self, world_id: str) -> None:
        jobs = self.svc.store.list_queued_jobs(world_id)
        gpu = self.svc.gpu_queue.snapshot()
        self._emit(
            world_id,
            "queue.updated",
            {
                "busy": gpu["busy"] or bool(jobs),
                "depth": len(jobs),
                "currentJob": jobs[0] if jobs else None,
            },
        )

    def cancel_job(self, job_id: str) -> bool:
        task = self._workers.pop(job_id, None)
        job = self.svc.store.get_job(job_id)
        if task and not task.done():
            task.cancel()
        if job:
            self.svc.store.update_job(job_id, status="cancelled")
            row = self.svc.store.fetchone(
                "SELECT messageId, metaJson FROM Message WHERE generationJobId = ?",
                (job_id,),
            )
            if row:
                try:
                    meta = json.loads(row["metaJson"] or "{}")
                except json.JSONDecodeError:
                    meta = {}
                meta["generationError"] = "Generation cancelled."
                self.svc.store.update_message(
                    row["messageId"],
                    streamStatus="interrupted",
                    outputText=_GENERATION_FAILED_TEXT,
                    metaJson=json.dumps(meta),
                )
            self._emit_queue(job["worldId"])
            return True
        return False

    def _world_config(self, world_id: str) -> dict[str, Any]:
        world = self.svc.store.get_world(world_id)
        if not world:
            return {}
        return json.loads(world.get("configJson") or "{}")

    def _max_continue_depth(self, world_id: str) -> int:
        from altrasia.orchestrator.generation_policy import world_generation_policy

        return world_generation_policy(self._world_config(world_id))["max_continue_depth"]

    def _generation_policy(self, world_id: str) -> dict[str, Any]:
        from altrasia.orchestrator.generation_policy import world_generation_policy

        return world_generation_policy(self._world_config(world_id))

    def _agent_continue_enabled(self, world_id: str) -> bool:
        return bool(self._world_config(world_id).get("agentContinueEnabled", True))

    def _is_retryable_generation(self, exc: BaseException) -> bool:
        from altrasia.orchestrator.generation_policy import is_retryable_generation_error

        return is_retryable_generation_error(exc)

    async def _maybe_recover_generation(self, job: dict[str, Any], exc: BaseException) -> None:
        """One deferred re-run after retries are exhausted (timeouts / transport blips)."""
        cfg = self._world_config(job["worldId"])
        if not cfg.get("generationRecoveryEnabled", True):
            return
        if not self._is_retryable_generation(exc):
            return
        try:
            rationale = json.loads(job.get("selectionRationaleJson") or "{}")
        except json.JSONDecodeError:
            rationale = {}
        if rationale.get("generation_recovery"):
            return
        trigger = str(job.get("trigger") or "")
        if trigger == "debate_turn":
            from altrasia.debate_runner import enqueue_debate_turn

            log.info(
                "scheduling debate turn recovery scene=%s character=%s",
                job["sceneId"],
                job.get("characterId"),
            )
            await enqueue_debate_turn(self.svc, job["sceneId"])
            return
        if trigger not in _AGENT_CONTINUE_TRIGGERS:
            return
        depth = int(job.get("continueDepth") or 0)
        log.info(
            "scheduling agent_continue recovery scene=%s character=%s depth=%s",
            job["sceneId"],
            job.get("characterId"),
            depth,
        )
        recovery_rationale = json.dumps(
            {
                **rationale,
                "pick": trigger,
                "characterId": job["characterId"],
                "generation_recovery": True,
            }
        )
        job_id = str(uuid.uuid4())
        self.svc.store.insert_job(
            {
                "jobId": job_id,
                "worldId": job["worldId"],
                "characterId": job["characterId"],
                "sceneId": job["sceneId"],
                "trigger": trigger,
                "priority": 10 - depth,
                "observerMode": job.get("observerMode"),
                "status": "queued",
                "continueDepth": depth,
                "triggerMessageId": job.get("triggerMessageId"),
                "selectionRationaleJson": recovery_rationale,
                "createdAt": ISO(),
            }
        )
        self._scene_chain_active.add(job["sceneId"])
        stream = TokenStream()
        self.svc.streams[job_id] = stream
        task = asyncio.create_task(self._run_job(job_id, stream))
        self._workers[job_id] = task
        self._emit_queue(job["worldId"])

    async def _continue_depth_limit(
        self, job: dict[str, Any]
    ) -> tuple[int, str | None, dict[str, Any]]:
        """Max continueDepth for the *next* step; optional stop reason and assessment detail."""
        cfg = self._world_config(job["worldId"])
        depth = int(job.get("continueDepth") or 0)
        from altrasia.orchestrator.conversation_resolution import effective_continue_depth_limit
        from altrasia.orchestrator.discussion_judgement import assess_discussion_continuation

        unresolved, resolution_reason, detail = await assess_discussion_continuation(
            self.svc,
            world_id=job["worldId"],
            scene_id=job["sceneId"],
            cfg=cfg,
            current_depth=depth,
        )
        addressing = self._addressing_for_job(job)
        addressing_mode = addressing.mode if addressing else "open"
        detail["addressingMode"] = addressing_mode
        from altrasia.orchestrator.speaker_selection import addressee_ids_for

        addressee_count = len(addressee_ids_for(addressing)) if addressing else 1
        detail["addresseeCount"] = addressee_count
        limit = effective_continue_depth_limit(
            cfg,
            depth,
            unresolved=unresolved,
            addressing_mode=addressing_mode,
            directed_addressee_count=max(1, addressee_count),
        )
        stop_reason: str | None = None
        if depth + 1 > limit:
            if cfg.get("continueUntilResolved", True) and depth >= int(
                cfg.get("maxContinueDepth", 2)
            ):
                if unresolved:
                    stop_reason = "depth_cap_unresolved"
                else:
                    stop_reason = "conversation_resolved"
            else:
                stop_reason = "max_continue_depth"
        detail["depthLimit"] = limit
        detail["stopReason"] = stop_reason
        return limit, stop_reason if depth + 1 > limit else None, detail

    def _should_enqueue_agent_continue(
        self,
        job: dict[str, Any],
        *,
        debate_active: bool,
        tool_log: list[dict[str, Any]],
        depth_limit: int,
        next_character_id: str | None = None,
    ) -> bool:
        if not self._agent_continue_enabled(job["worldId"]):
            return False
        if str(job.get("trigger") or "") not in _AGENT_CONTINUE_TRIGGERS:
            return False
        depth = int(job.get("continueDepth") or 0)
        if depth + 1 > depth_limit:
            return False
        if debate_active:
            return False
        from altrasia.orchestrator.briefing_chain import movement_tools_ran

        if movement_tools_ran(tool_log):
            return False
        addressing = self._addressing_for_job(job)
        if addressing and addressing.mode == "clarification":
            return False
        if addressing and addressing.mode == "directed":
            if next_character_id is None:
                return False
            from altrasia.orchestrator.speaker_selection import (
                addressee_ids_for,
                is_multi_directed,
            )

            ids = addressee_ids_for(addressing)
            if is_multi_directed(addressing):
                if depth >= max(0, len(ids) - 1):
                    return False
            else:
                directed_max = int(
                    self._world_config(job["worldId"]).get("directedReplyMaxDepth", 1)
                )
                if depth >= directed_max:
                    return False
        return True

    def _mandatory_recall_blocking(self, world_id: str) -> bool:
        cfg = self._world_config(world_id)
        return cfg.get("mandatoryRecallBlocking", cfg.get("mandatoryRecallEnabled", True))

    def _memory_tool_names(self) -> set[str]:
        names: set[str] = set()
        for t in self.svc.tools.list_openai_tools():
            n = t["function"]["name"]
            if n.startswith("memory_") or n.startswith("diary_"):
                names.add(n)
        return names

    def _filter_tools(self, all_tools: list[dict], allowed: set[str]) -> list[dict]:
        return [t for t in all_tools if t["function"]["name"] in allowed]

    def _tools_for_job(
        self, job: dict[str, Any], all_tools: list[dict], memory_only: set[str]
    ) -> list[dict]:
        try:
            rationale = json.loads(job.get("selectionRationaleJson") or "{}")
        except json.JSONDecodeError:
            rationale = {}
        if str(job.get("trigger", "")) == "discussion_deliverable":
            return self._filter_tools(all_tools, memory_only)
        com_id = rationale.get("commissionId")
        if com_id and str(job.get("trigger", "")).startswith("commission"):
            from altrasia.commissions import parse_allowed_tools

            row = self.svc.store.get_commission(com_id)
            allowed = parse_allowed_tools(row)
            if allowed is not None:
                allowed = set(allowed) | memory_only
                return self._filter_tools(all_tools, allowed)
        from altrasia.tools.cast_tools import (
            OBSERVER_ONLY_SCENE_TOOLS,
            cast_allowed_tool_names,
        )

        cast_scene = cast_allowed_tool_names(
            self.svc.store, job["worldId"], job["characterId"]
        )
        cast_tools = {
            t["function"]["name"]
            for t in all_tools
            if not t["function"]["name"].startswith("map_")
            and t["function"]["name"] not in OBSERVER_ONLY_SCENE_TOOLS
            and (
                not t["function"]["name"].startswith("scene_")
                or (cast_scene and t["function"]["name"] in cast_scene)
            )
        }
        if cast_scene:
            cast_tools |= memory_only
        else:
            cast_tools = {
                t["function"]["name"]
                for t in all_tools
                if not t["function"]["name"].startswith("scene_")
                and not t["function"]["name"].startswith("map_")
            }
        return self._filter_tools(all_tools, cast_tools)

    def pick_reactive_character(
        self,
        world_id: str,
        scene_id: str,
        trigger_text: str,
        *,
        trigger_message_id: str | None = None,
        target_character_id: str | None = None,
        addressing: Any | None = None,
    ) -> tuple[str | None, dict]:
        """AO-17/18: scoreSpeakers with debate/activity overrides."""
        from altrasia.debate_activity import debate_current_speaker, parse_activity
        from altrasia.orchestrator.speaker_selection import (
            addressee_ids_for,
            addressing_to_dict,
            parse_addressing,
            score_speakers,
        )

        scene = self.svc.store.get_scene(scene_id)
        present = json.loads(scene["presentJson"])
        cast = [c for c in present if c not in (PERSONA_ID,)]
        if not cast:
            return None, {}
        activity = parse_activity(scene)
        if activity and activity.get("kind") in ("debate", "conversation", "banter"):
            speaker = debate_current_speaker(activity)
            if speaker and speaker in cast:
                return speaker, {
                    "pick": activity.get("kind"),
                    "phase": activity.get("phase"),
                    "characterId": speaker,
                }
        chars = {c["characterId"]: c for c in self.svc.store.list_world_characters(world_id)}
        if addressing is None:
            from altrasia.orchestrator.operator_aliases import operator_alias_map

            cfg = self._world_config(world_id)
            addressing = parse_addressing(
                trigger_text,
                cast,
                chars,
                target_character_id=target_character_id,
                fuzzy_enabled=bool(cfg.get("addressingFuzzyEnabled", True)),
                fuzzy_max_distance=int(cfg.get("addressingFuzzyMaxDistance", 2)),
                operator_alias_map=operator_alias_map(self.svc.store, world_id),
            )
        if addressing.mode == "clarification" and addressing.clarifier_id:
            clarifier = addressing.clarifier_id
            rationale = {
                "pick": "clarification",
                "characterId": clarifier,
                "addressing": addressing_to_dict(addressing),
                "candidateIds": addressing.candidate_ids,
            }
            return clarifier, rationale
        ids = addressee_ids_for(addressing)
        if addressing.mode == "directed" and ids:
            primary = ids[0]
            rationale = {
                "pick": "addressed_multi" if len(ids) > 1 else "addressed",
                "characterId": primary,
                "addresseeIds": ids,
                "addressing": addressing_to_dict(addressing),
                "scores": {primary: {"total": 1.0, "addressed": 1.0}},
            }
            return primary, rationale
        pick = score_speakers(
            self.svc,
            world_id=world_id,
            scene_id=scene_id,
            trigger_text=trigger_text,
            eligible=cast,
            target_character_id=target_character_id,
            trigger_message_id=trigger_message_id,
        )
        if not pick:
            return None, {}
        rationale = {**pick.rationale, "addressing": addressing_to_dict(addressing)}
        return pick.character_id, rationale

    async def pick_reactive_character_async(
        self,
        world_id: str,
        scene_id: str,
        trigger_text: str,
        *,
        trigger_message_id: str | None = None,
        target_character_id: str | None = None,
        addressing: Any | None = None,
    ) -> tuple[str | None, dict]:
        """AO-17 v1.1: optional speak_intent LLM resolve on score tie."""
        from altrasia.orchestrator.speaker_selection import resolve_speak_intent_tie
        from altrasia.world_config import get_world_config

        cid, rationale = self.pick_reactive_character(
            world_id,
            scene_id,
            trigger_text,
            trigger_message_id=trigger_message_id,
            target_character_id=target_character_id,
            addressing=addressing,
        )
        if not cid:
            return None, {}
        cfg = get_world_config(self.svc.store, world_id)
        if not cfg.get("speakIntentOnTie"):
            return cid, rationale
        scores = rationale.get("scores") or {}
        if len(scores) < 2:
            return cid, rationale
        totals = [(c, float(v.get("total", 0))) for c, v in scores.items()]
        top = max(t for _, t in totals)
        tied = [c for c, t in totals if top - t <= 0.05]
        if len(tied) <= 1:
            return cid, rationale
        chars = {c["characterId"]: c for c in self.svc.store.list_world_characters(world_id)}
        resolved = await resolve_speak_intent_tie(
            self.svc.llm,
            trigger_text=trigger_text,
            tied=tied,
            chars=chars,
        )
        if resolved and resolved != cid:
            rationale = {
                **rationale,
                "pick": "speak_intent",
                "characterId": resolved,
                "tiedCandidates": tied,
            }
            return resolved, rationale
        return cid, rationale

    def _cast_spoke_in_scene(self, world_id: str, scene_id: str) -> set[str]:
        spoke: set[str] = set()
        for m in self.svc.store.list_messages(world_id, scene_id=scene_id):
            if (
                m.get("role") == "assistant"
                and m.get("characterId")
                and m.get("streamStatus") == "final"
                and (m.get("outputText") or "").strip()
            ):
                spoke.add(m["characterId"])
        return spoke

    def _cast_spoke_on_trigger(
        self, world_id: str, scene_id: str, operator_message_id: str | None
    ) -> set[str]:
        if not operator_message_id:
            return set()
        spoke: set[str] = set()
        jobs = self.svc.store.conn.execute(
            """SELECT characterId FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ?
                 AND status = 'done' AND characterId IS NOT NULL""",
            (world_id, scene_id, operator_message_id),
        ).fetchall()
        for row in jobs:
            spoke.add(row[0])
        return spoke

    def _operator_line_for_job(self, job: dict[str, Any]) -> str:
        op_id = job.get("triggerMessageId")
        if not op_id:
            return ""
        row = self.svc.store.fetchone(
            "SELECT outputText, metaJson FROM Message WHERE messageId = ?",
            (op_id,),
        )
        if not row:
            return ""
        return (row.get("outputText") or "").strip()

    def _addressing_from_message_row(self, row: dict[str, Any] | None) -> Any | None:
        if not row:
            return None
        from altrasia.orchestrator.speaker_selection import addressing_from_dict

        try:
            meta = json.loads(row.get("metaJson") or "{}")
        except json.JSONDecodeError:
            return None
        orch = meta.get("orchestration") or {}
        return addressing_from_dict(orch.get("addressing"))

    def _addressing_for_job(self, job: dict[str, Any]) -> Any | None:
        op_id = job.get("triggerMessageId")
        if not op_id:
            return None
        row = self.svc.store.fetchone(
            "SELECT metaJson FROM Message WHERE messageId = ?",
            (op_id,),
        )
        return self._addressing_from_message_row(row)

    def _persist_message_addressing(
        self, message_id: str, addressing: Any
    ) -> None:
        from altrasia.orchestrator.speaker_selection import addressing_to_dict

        row = self.svc.store.fetchone(
            "SELECT metaJson FROM Message WHERE messageId = ?",
            (message_id,),
        )
        if not row:
            return
        try:
            meta = json.loads(row.get("metaJson") or "{}")
        except json.JSONDecodeError:
            meta = {}
        orch = meta.setdefault("orchestration", {})
        orch["addressing"] = addressing_to_dict(addressing)
        self.svc.store.update_message(message_id, metaJson=json.dumps(meta))

    def _pick_continue_character(
        self,
        world_id: str,
        scene_id: str,
        exclude_id: str,
        *,
        trigger_text: str = "",
        trigger_message_id: str | None = None,
        addressing: Any | None = None,
    ) -> str | None:
        """AO-19: scoreSpeakers for agent_continue."""
        from altrasia.orchestrator.speaker_selection import (
            addressee_ids_for,
            is_multi_directed,
            pick_directed_witness,
            score_speakers,
        )

        scene = self.svc.store.get_scene(scene_id)
        present = json.loads(scene["presentJson"])
        cast = [c for c in present if c not in (PERSONA_ID,)]
        spoke_on_trigger = self._cast_spoke_on_trigger(
            world_id, scene_id, trigger_message_id
        )
        if addressing is None and trigger_message_id:
            row = self.svc.store.fetchone(
                "SELECT metaJson FROM Message WHERE messageId = ?",
                (trigger_message_id,),
            )
            addressing = self._addressing_from_message_row(row)

        op_text = trigger_text or self._operator_line_for_job(
            {"triggerMessageId": trigger_message_id, "worldId": world_id, "sceneId": scene_id}
        )

        if addressing and addressing.mode == "directed" and is_multi_directed(addressing):
            for aid in addressee_ids_for(addressing):
                if aid not in spoke_on_trigger:
                    return aid
            return None

        if addressing and addressing.mode == "directed" and addressing.unresolved_name_tokens:
            from altrasia.orchestrator.operator_aliases import operator_alias_map
            from altrasia.orchestrator.speaker_selection import _resolve_token

            cfg = self._world_config(world_id)
            op_map = operator_alias_map(self.svc.store, world_id)
            scene_chars = {
                c["characterId"]: c
                for c in self.svc.store.list_world_characters(world_id)
                if c["characterId"] in cast
            }

            for token in addressing.unresolved_name_tokens:
                ids, _, _ = _resolve_token(
                    token,
                    cast,
                    scene_chars,
                    fuzzy_enabled=bool(cfg.get("addressingFuzzyEnabled", True)),
                    fuzzy_max_distance=int(cfg.get("addressingFuzzyMaxDistance", 2)),
                    operator_alias_map=op_map,
                )
                if len(ids) == 1 and ids[0] not in spoke_on_trigger:
                    return ids[0]

        if addressing and addressing.mode == "directed" and addressing.primary_id:
            cfg = self._world_config(world_id)
            rel_min = float(cfg.get("directedWitnessRelevanceMin", 0.55))
            witness = pick_directed_witness(
                self.svc,
                world_id=world_id,
                scene_id=scene_id,
                trigger_text=op_text or "continue",
                primary_id=addressing.primary_id,
                eligible=cast,
                exclude_ids=spoke_on_trigger,
                trigger_message_id=trigger_message_id,
                relevance_min=rel_min,
                require_mention=bool(cfg.get("directedWitnessRequireMention", True)),
                fuzzy_enabled=bool(cfg.get("addressingFuzzyEnabled", True)),
                fuzzy_max_distance=int(cfg.get("addressingFuzzyMaxDistance", 2)),
            )
            return witness.character_id if witness else None

        pick = score_speakers(
            self.svc,
            world_id=world_id,
            scene_id=scene_id,
            trigger_text=op_text or "continue",
            eligible=cast,
            exclude_id=exclude_id,
            exclude_ids=spoke_on_trigger,
            last_speaker_id=exclude_id,
            trigger_message_id=trigger_message_id,
            session_spoke=self._cast_spoke_in_scene(world_id, scene_id),
        )
        return pick.character_id if pick else None

    async def _preempt_scene_for_operator_line(
        self,
        world_id: str,
        scene_id: str,
        operator_message_id: str,
        addressing: Any,
    ) -> None:
        """Cancel in-flight scene jobs that conflict with a new operator line."""
        from altrasia.orchestrator.addressing_policy import list_scene_jobs

        cfg = self._world_config(world_id)
        for row in list_scene_jobs(self.svc.store, world_id, scene_id):
            job = self.svc.store.get_job(row["jobId"])
            if not job:
                continue
            if addressing.mode in ("directed", "clarification"):
                if row.get("triggerMessageId") != operator_message_id:
                    self.cancel_job(row["jobId"])
                    continue
            eval_job = {**job, "triggerMessageId": operator_message_id}
            from altrasia.orchestrator.addressing_policy import may_character_generate

            allowed, _ = may_character_generate(self.svc, eval_job, cfg)
            if not allowed:
                self.cancel_job(row["jobId"])

    async def enqueue_generation(
        self,
        *,
        world_id: str,
        scene_id: str,
        character_id: str,
        trigger: str,
        continue_depth: int = 0,
        trigger_message_id: str | None = None,
        observer_mode: str | None = None,
        idle_source: str | None = None,
        commission_id: str | None = None,
        deliverable_id: str | None = None,
        deliverable_kind: str | None = None,
        deliverable_instruction: str | None = None,
    ) -> dict[str, Any] | None:
        if world_id in self.svc.paused_worlds:
            return None
        job_id = str(uuid.uuid4())
        rationale_obj: dict[str, Any] = {"pick": trigger, "characterId": character_id}
        if commission_id:
            rationale_obj["commissionId"] = commission_id
        if deliverable_id:
            rationale_obj["deliverableId"] = deliverable_id
        if deliverable_kind:
            rationale_obj["deliverableKind"] = deliverable_kind
        if deliverable_instruction:
            rationale_obj["deliverableInstruction"] = deliverable_instruction
        if idle_source:
            rationale_obj["idle_source"] = idle_source
        rationale = json.dumps(rationale_obj)
        priority = 10 - continue_depth
        if trigger == "commission_tick":
            priority = 7
        elif trigger == "commission_started":
            priority = 8
        self.svc.store.insert_job(
            {
                "jobId": job_id,
                "worldId": world_id,
                "characterId": character_id,
                "sceneId": scene_id,
                "trigger": trigger,
                "priority": priority,
                "observerMode": observer_mode,
                "status": "queued",
                "continueDepth": continue_depth,
                "triggerMessageId": trigger_message_id,
                "selectionRationaleJson": rationale,
                "createdAt": ISO(),
            }
        )
        self._scene_chain_active.add(scene_id)
        stream = TokenStream()
        self.svc.streams[job_id] = stream
        task = asyncio.create_task(self._run_job(job_id, stream))
        self._workers[job_id] = task
        self._emit_queue(world_id)
        return {"jobId": job_id, "status": "queued"}

    async def _run_job(self, job_id: str, stream: TokenStream) -> None:
        job = self.svc.store.get_job(job_id)
        if not job:
            return
        cfg = self._world_config(job["worldId"])
        from altrasia.orchestrator.addressing_policy import may_character_generate

        allowed, suppress_reason = may_character_generate(self.svc, job, cfg)
        if not allowed:
            log.info(
                "generation suppressed job=%s character=%s trigger=%s reason=%s",
                job_id,
                job.get("characterId"),
                job.get("trigger"),
                suppress_reason,
            )
            try:
                rationale = json.loads(job.get("selectionRationaleJson") or "{}")
            except json.JSONDecodeError:
                rationale = {}
            rationale["suppressed"] = suppress_reason
            self.svc.store.update_job(
                job_id,
                status="cancelled",
                selectionRationaleJson=json.dumps(rationale),
            )
            await stream.close()
            if not self._scene_has_pending_jobs(job["worldId"], job["sceneId"]):
                self._scene_chain_active.discard(job["sceneId"])
            self._emit_queue(job["worldId"])
            return
        self.svc.store.update_job(job_id, status="running")
        msg_id = str(uuid.uuid4())
        self.svc.store.insert_message(
            {
                "messageId": msg_id,
                "worldId": job["worldId"],
                "channelKind": "scene",
                "sceneId": job["sceneId"],
                "role": "assistant",
                "characterId": job["characterId"],
                "outputText": "",
                "reasoning": None,
                "streamStatus": "streaming",
                "generationJobId": job_id,
                "metaJson": json.dumps(_scene_message_meta(job)),
                "createdAt": ISO(),
            }
        )
        await stream.push("generation.start", {"jobId": job_id, "messageId": msg_id})
        self._emit(
            job["worldId"],
            "generation.start",
            {"jobId": job_id, "messageId": msg_id},
        )

        tool_log: list[dict[str, Any]] = []
        policy = self._generation_policy(job["worldId"])
        max_attempts = policy["max_retries"] + 1
        last_exc: BaseException | None = None
        failed_exc: BaseException | None = None

        async def work() -> str:
            return await self._generate_text(job, msg_id, tool_log)

        try:
            for attempt in range(max_attempts):
                try:
                    text = await self.svc.gpu_queue.run(job_id, "chat", work)
                    cleaned = strip_from_message_payload({"content": text})
                    if tool_log:
                        self.svc.store.update_job(
                            job_id,
                            selectionRationaleJson=_merge_tool_calls_rationale(
                                job.get("selectionRationaleJson"), tool_log
                            ),
                        )
                    self.svc.store.update_message(
                        msg_id,
                        outputText=cleaned,
                        streamStatus="final",
                    )
                    await stream.push(
                        "generation.token",
                        {"jobId": job_id, "messageId": msg_id, "delta": cleaned},
                    )
                    self._emit(
                        job["worldId"],
                        "generation.token",
                        {"jobId": job_id, "messageId": msg_id, "delta": cleaned},
                    )
                    await stream.push("generation.done", {"jobId": job_id, "messageId": msg_id})
                    self._emit(
                        job["worldId"],
                        "generation.done",
                        {"jobId": job_id, "messageId": msg_id},
                    )
                    self.svc.store.update_job(job_id, status="done")
                    if not (cleaned or "").strip():
                        raise ValueError("Model returned empty content")
                    await self._after_reply(job, msg_id, cleaned, tool_log=tool_log)
                    last_exc = None
                    break
                except (asyncio.CancelledError, FuturesCancelledError):
                    raise
                except Exception as exc:
                    last_exc = exc
                    if attempt + 1 < max_attempts and self._is_retryable_generation(exc):
                        wait = policy["backoff_seconds"] * (attempt + 1)
                        log.warning(
                            "generation retry job=%s character=%s attempt=%s/%s after %s; wait %.1fs",
                            job_id,
                            job.get("characterId"),
                            attempt + 2,
                            max_attempts,
                            _generation_error_text(exc),
                            wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise
            if last_exc is not None:
                raise last_exc
        except (asyncio.CancelledError, FuturesCancelledError):
            self.svc.store.update_message(
                msg_id,
                streamStatus="interrupted",
                outputText=_GENERATION_FAILED_TEXT,
                metaJson=_message_meta_with_generation_error(
                    job, RuntimeError("Generation cancelled")
                ),
            )
            self.svc.store.update_job(job_id, status="cancelled")
            raise
        except Exception as exc:
            failed_exc = exc
            err_text = _generation_error_text(exc)
            log.warning(
                "generation failed job=%s character=%s: %s",
                job_id,
                job.get("characterId"),
                err_text,
            )
            self.svc.store.update_message(
                msg_id,
                streamStatus="interrupted",
                outputText=_GENERATION_FAILED_TEXT,
                metaJson=_message_meta_with_generation_error(job, exc),
            )
            self.svc.store.update_job(job_id, status="cancelled")
            await stream.push("generation.error", {"jobId": job_id, "error": err_text})
            self._emit(
                job["worldId"],
                "generation.error",
                {"jobId": job_id, "message": err_text},
            )
        finally:
            if not self._scene_has_pending_jobs(job["worldId"], job["sceneId"]):
                self._scene_chain_active.discard(job["sceneId"])
            self._emit_queue(job["worldId"])
            await stream.close()
            if failed_exc is not None:
                await self._maybe_recover_generation(job, failed_exc)

    def _scene_has_pending_jobs(self, world_id: str, scene_id: str) -> bool:
        for j in self.svc.store.list_queued_jobs(world_id):
            if j["sceneId"] == scene_id:
                return True
        row = self.svc.store.fetchone(
            """SELECT 1 FROM GenerationJob WHERE worldId = ? AND sceneId = ?
               AND status = 'running' LIMIT 1""",
            (world_id, scene_id),
        )
        return row is not None

    async def _generate_text(
        self, job: dict, msg_id: str, tool_log: list[dict[str, Any]] | None = None
    ) -> str:
        ch = self.svc.store.get_character(job["characterId"])
        cfg = self._world_config(job["worldId"])
        inference_timeout = self._generation_policy(job["worldId"])["inference_timeout_seconds"]
        max_recall = int(cfg.get("mandatoryRecallMaxChars", 12000))
        recall = self.svc.memory.build_mandatory_recall(
            character_id=job["characterId"],
            scene_id=job["sceneId"],
            world_id=job["worldId"],
            max_chars=max_recall,
        )
        scene = self.svc.store.get_scene(job["sceneId"])
        from altrasia.inference.profiles import quality_addendum
        from altrasia.prompt.scene_framing import build_scene_framing
        from altrasia.tools.cast_tools import cast_allowed_tool_names

        addendum = quality_addendum(self.svc.settings, ch.get("modelProfile", "qwen3.6-35b-a3b"))
        try:
            definition = json.loads(ch.get("definitionJson") or "{}")
        except json.JSONDecodeError:
            definition = {}
        persona = (definition.get("persona") or "").strip()
        instructions = (definition.get("instructions") or "").strip()
        system = (
            f"You are {ch['displayName']}. Stay in character.\n\n"
            f"Scene: {scene['locationName']}\n\n{recall}"
        )
        if persona:
            system += f"\n\nPersona: {persona}"
        if instructions:
            system += f"\n\nInstructions: {instructions}"
        if cfg.get("sceneFramingEnabled", True):
            framing = build_scene_framing(
                self.svc.store,
                self.svc.presence,
                world_id=job["worldId"],
                character_id=job["characterId"],
                scene_id=job["sceneId"],
            )
            if framing:
                system += f"\n\n{framing}"
        cast_scene_tools = cast_allowed_tool_names(
            self.svc.store, job["worldId"], job["characterId"]
        )
        if cast_scene_tools:
            system += (
                "\n\nWhen you commit to gathering people or moving to a meeting, "
                "you MUST call scene_summon or scene_join with real characterIds from "
                "character_list. Do not claim people are coming without those tool calls."
            )
        if addendum:
            system += f"\n\n{addendum}"
        present_ids = [
            c for c in json.loads(scene["presentJson"]) if c not in (PERSONA_ID,)
        ]
        members = {m["characterId"]: m for m in self.svc.store.list_world_characters(job["worldId"])}
        other_names = [
            members[c]["displayName"]
            for c in present_ids
            if c != job["characterId"] and c in members
        ]
        from altrasia.orchestrator.single_speaker import (
            operator_trigger_text,
            single_speaker_system_addendum,
            trigger_invites_ensemble,
        )

        history_rows = self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])
        op_trigger = operator_trigger_text(history_rows)
        ensemble_invited = trigger_invites_ensemble(op_trigger)
        addressing = self._addressing_for_job(job)
        from altrasia.orchestrator.speaker_selection import (
            addressee_ids_for,
            is_multi_directed,
        )

        directed_witness = False
        directed_addressee_name: str | None = None
        directed_co_addressees: list[str] | None = None
        clarification_names: list[str] | None = None
        absent_scene_names: list[str] | None = None
        operator_nicknames: list[str] | None = None
        from altrasia.orchestrator.operator_aliases import operator_aliases_for_character

        op_nicks = operator_aliases_for_character(
            self.svc.store, job["worldId"], job["characterId"]
        )
        if op_nicks:
            operator_nicknames = op_nicks
        if addressing and addressing.mode == "clarification":
            if addressing.match_reason == "not_in_scene":
                absent_scene_names = list(addressing.absent_names)
            else:
                clarification_names = [
                    members[c]["displayName"]
                    for c in addressing.candidate_ids
                    if c in members
                ]
        elif addressing and addressing.mode == "directed":
            ids = addressee_ids_for(addressing)
            if is_multi_directed(addressing):
                co = [
                    members[c]["displayName"]
                    for c in ids
                    if c != job["characterId"] and c in members
                ]
                directed_co_addressees = co
            elif addressing.primary_id:
                primary_ch = members.get(addressing.primary_id) or {}
                directed_addressee_name = primary_ch.get("displayName")
                depth = int(job.get("continueDepth") or 0)
                if (
                    depth > 0
                    and job.get("characterId") != addressing.primary_id
                ):
                    directed_witness = True
        system += f"\n\n{single_speaker_system_addendum(
            ch['displayName'],
            other_names=other_names,
            ensemble_invited=ensemble_invited,
            directed_addressee_name=directed_addressee_name,
            directed_witness=directed_witness,
            directed_co_addressees=directed_co_addressees,
            clarification_names=clarification_names,
            absent_scene_names=absent_scene_names,
            operator_nicknames=operator_nicknames,
        )}"
        if ensemble_invited and cfg.get("discussionSignalsEnabled", True):
            system += (
                "\n\nIf important aspects of the operator's question are still missing "
                "from the discussion, call discussion_signal with sufficient=false and "
                "list gaps. If your perspective is fully on the table, you may call "
                "discussion_signal with sufficient=true."
            )
        if cfg.get("citeProvenanceInPrompt"):
            prov = self.svc.store.fetchall(
                """SELECT locusKey, sourceKind, sourceRef FROM EvidenceRecord
                   WHERE pool = 'mind' AND ownerId = ? ORDER BY retrievedAt DESC LIMIT 8""",
                (job["characterId"],),
            )
            if prov:
                system += "\n\n## Source provenance (cite when using these facts)"
                for row in prov:
                    ref = row["sourceRef"] or ""
                    system += f"\n- {row['locusKey']} ({row['sourceKind']}: {ref[:120]})"
        try:
            rationale = json.loads(job.get("selectionRationaleJson") or "{}")
        except json.JSONDecodeError:
            rationale = {}
        com_id = rationale.get("commissionId")
        if com_id and str(job.get("trigger", "")).startswith("commission"):
            com_row = self.svc.store.get_commission(com_id)
            if com_row:
                summary_key = f"{com_row.get('deliverableLocusPrefix', '')}summary"
                system += (
                    f"\n\nCommission errand — operator brief:\n{com_row['brief']}\n"
                    f"When finished, call memory_store on your mind pool with key "
                    f'"{summary_key}" containing your findings.'
                )
        if str(job.get("trigger", "")) == "discussion_deliverable":
            from altrasia.orchestrator.discussion_judgement import _transcript_excerpt

            kind = str(rationale.get("deliverableKind") or "report")
            instruction = str(rationale.get("deliverableInstruction") or op_trigger)
            locus = (
                f"discussion:{job['sceneId']}:{job['characterId']}:{kind}"
            )
            transcript = _transcript_excerpt(
                self.svc.store, job["worldId"], job["sceneId"], limit=20
            )
            system += (
                f"\n\nPost-discussion deliverable — operator asked:\n{instruction}\n\n"
                f"You are {ch['displayName']}. The group discussion has concluded. "
                f"Deliver a single public {kind} to the operator synthesizing the discussion. "
                "Speak directly to the operator; do not re-enact the full debate or write "
                "lines for other cast members.\n"
                f"You MUST call memory_store on your mind pool with locusKey "
                f'"{locus}" containing the full {kind} text.\n\n'
                f"## Discussion transcript (recent)\n{transcript[:8000]}"
            )
        if str(job.get("trigger", "")) == "debate_turn":
            from altrasia.debate_activity import parse_activity

            activity = parse_activity(scene)
            if activity:
                phase = activity.get("phase", "opening")
                system += (
                    f"\n\nDebate phase: {phase}. Give a concise in-character public argument. "
                    "Stay within the debate; do not invent new locations."
                )
                if phase == "synthesis":
                    system += (
                        "\nSynthesize positions for all debaters; your line is the public summary."
                    )
        from altrasia.orchestrator.chat_messages import scene_messages_for_llm

        messages = [{"role": "system", "content": system}]
        history = history_rows
        present = present_ids
        messages.extend(
            scene_messages_for_llm(
                history,
                viewer_id=job["characterId"],
                present=present,
                viewer_scene_id=job["sceneId"],
            )
        )
        all_tools = self.svc.tools.list_openai_tools()
        memory_only = self._memory_tool_names()
        job_tools = self._tools_for_job(job, all_tools, memory_only)
        blocking = self._mandatory_recall_blocking(job["worldId"])
        memory_gate_open = False
        ctx = ToolContext(
            world_id=job["worldId"],
            scene_id=job["sceneId"],
            character_id=job["characterId"],
            services=self.svc,
            commission_id=com_id,
            message_id=msg_id,
        )
        depth = 0
        is_commission = str(job.get("trigger", "")).startswith("commission")
        max_tool_rounds = int(self._generation_policy(job["worldId"])["max_tool_rounds_per_job"])
        while depth < max_tool_rounds:
            if is_commission:
                tools_payload = job_tools
            elif depth == 0 and blocking and not memory_gate_open:
                tools_payload = self._filter_tools(job_tools, memory_only)
            else:
                tools_payload = job_tools
            resp = await self.svc.llm.chat(
                messages, tools_payload, timeout=inference_timeout
            )
            msg = normalize_assistant_message(resp["choices"][0]["message"])
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append(msg)
                for tc in tool_calls:
                    fn = tc["function"]
                    name = fn["name"]
                    if name in memory_only:
                        memory_gate_open = True
                    args = json.loads(fn.get("arguments") or "{}")
                    result = await self.svc.tools.invoke(name, args, ctx)
                    if tool_log is not None:
                        preview = result if len(result) <= 500 else f"{result[:500]}…"
                        tool_log.append(
                            {"name": name, "arguments": args, "result": preview}
                        )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        }
                    )
                depth += 1
                continue
            from altrasia.orchestrator.single_speaker import enforce_single_speaker_output

            raw = msg.get("content") or ""
            return enforce_single_speaker_output(raw, ch["displayName"], other_names)
        return ""

    async def _fulfill_discussion_deliverable(
        self,
        job: dict[str, Any],
        msg_id: str,
        text: str,
        tool_log: list[dict[str, Any]],
    ) -> None:
        from altrasia.commissions import create_commission, patch_commission
        from altrasia.orchestrator.discussion_deliverables import (
            mark_deliverable_done,
            maybe_clear_ensemble_if_complete,
            mind_locus_for_deliverable,
        )

        try:
            rationale = json.loads(job.get("selectionRationaleJson") or "{}")
        except json.JSONDecodeError:
            rationale = {}
        deliverable_id = rationale.get("deliverableId")
        kind = str(rationale.get("deliverableKind") or "report")
        instruction = str(rationale.get("deliverableInstruction") or "")
        locus = mind_locus_for_deliverable(job["sceneId"], job["characterId"], kind)

        if not any(t.get("name") == "memory_store" for t in tool_log):
            cleaned = (text or "").strip()
            if cleaned:
                self.svc.memory.memory_store(
                    pool="mind",
                    owner_id=job["characterId"],
                    locus_key=locus,
                    value=cleaned[:4000],
                )
                self.svc.embeddings.schedule_embed(
                    owner_scope="mind",
                    owner_id=job["characterId"],
                    source_type="locus",
                    source_ref=locus,
                    text=cleaned[:4000],
                )

        commission_id: str | None = None
        try:
            com = create_commission(
                self.svc.store,
                job["worldId"],
                assignee_character_id=job["characterId"],
                target_scene_id=job["sceneId"],
                brief=instruction or f"Post-discussion {kind} for the operator",
            )
            commission_id = com["commissionId"]
            patch_commission(
                self.svc.store,
                commission_id,
                status="done",
                deliverable_locus_keys=[locus],
                force_complete_reason="discussion_deliverable",
            )
            self._emit(
                job["worldId"],
                "commission.updated",
                {"commissionId": commission_id, "status": "done"},
            )
        except Exception as exc:
            log.warning("discussion deliverable commission record failed: %s", exc)

        if deliverable_id:
            mark_deliverable_done(
                self.svc.store,
                job["sceneId"],
                str(deliverable_id),
                fulfillment_message_id=msg_id,
                commission_id=commission_id,
            )

        self._emit(
            job["worldId"],
            "conversation.deliverable_done",
            {
                "sceneId": job["sceneId"],
                "characterId": job["characterId"],
                "messageId": msg_id,
                "commissionId": commission_id,
                "kind": kind,
            },
        )
        maybe_clear_ensemble_if_complete(self.svc.store, job["sceneId"])

    async def _after_reply(
        self,
        job: dict,
        msg_id: str,
        text: str,
        *,
        tool_log: list[dict[str, Any]] | None = None,
    ) -> None:
        tool_log = tool_log or []
        cfg = self._world_config(job["worldId"])
        from altrasia.domain.narrative_presence import (
            apply_narrative_presence,
            detect_narrative_presence,
        )
        from altrasia.orchestrator.briefing_chain import movement_tools_ran
        from altrasia.orchestrator.discussion_deliverables import (
            bootstrap_ensemble_discussion,
            enqueue_pending_deliverables,
            mark_deliverable_done,
            maybe_clear_ensemble_if_complete,
            mind_locus_for_deliverable,
        )
        from altrasia.orchestrator.discussion_judgement import apply_tool_log_signals
        from altrasia.orchestrator.single_speaker import (
            operator_trigger_text,
            trigger_invites_ensemble,
        )

        if str(job.get("trigger") or "") == "discussion_deliverable":
            await self._fulfill_discussion_deliverable(job, msg_id, text, tool_log)
            return

        apply_tool_log_signals(
            self.svc.store,
            job["sceneId"],
            job["characterId"],
            tool_log,
            message_id=msg_id,
        )

        if not movement_tools_ran(tool_log):
            detection = detect_narrative_presence(
                self.svc,
                world_id=job["worldId"],
                speaker_id=job["characterId"],
                scene_id=job["sceneId"],
                output_text=text,
                cfg=cfg,
            )
            if detection:
                await apply_narrative_presence(
                    self.svc,
                    world_id=job["worldId"],
                    detection=detection,
                    speaker_id=job["characterId"],
                    source_scene_id=job["sceneId"],
                )
                for act in detection.get("actions") or []:
                    if act.get("kind") == "summon":
                        tool_log.append(
                            {
                                "name": "scene_summon",
                                "arguments": {
                                    "targetSceneId": act["targetSceneId"],
                                    "characterIds": act["characterIds"],
                                },
                                "result": "narrative_presence",
                            }
                        )

        if any(e.get("name") == "scene_summon" for e in tool_log):
            from altrasia.domain.presence_announce import maybe_announce_summons_from_tool_log

            await maybe_announce_summons_from_tool_log(
                self.svc, job, tool_log, related_message_id=msg_id
            )

        scene = self.svc.store.get_scene(job["sceneId"])
        present = [c for c in json.loads(scene["presentJson"]) if c != PERSONA_ID]
        recent = self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])[-6:]
        snippet = "\n".join(
            f"{m.get('characterId') or 'persona'}: {m['outputText']}" for m in recent
        )
        self.svc.memory.capture_diary_fanout(
            scene_id=job["sceneId"],
            present_ids=present,
            snippet=snippet,
            message_ids=[m["messageId"] for m in recent],
        )

        if str(job.get("trigger", "")).startswith("commission"):
            try:
                rationale = json.loads(job.get("selectionRationaleJson") or "{}")
            except json.JSONDecodeError:
                rationale = {}
            com_id = rationale.get("commissionId")
            if com_id:
                from altrasia.commissions import (
                    commission_deliverable_keys,
                    complete_commission_with_output,
                    mind_deliverable_exists,
                    patch_commission,
                )

                com_row = self.svc.store.get_commission(com_id)
                finished = False
                try:
                    if com_row and mind_deliverable_exists(self.svc.store, com_row):
                        keys = commission_deliverable_keys(
                            self.svc.store, self.svc.memory, com_row
                        )
                        patch_commission(
                            self.svc.store,
                            com_id,
                            status="done",
                            deliverable_locus_keys=keys,
                        )
                        finished = True
                    elif job.get("trigger") == "commission_tick":
                        pass
                    else:
                        complete_commission_with_output(
                            self.svc.store, self.svc.memory, com_id, text
                        )
                        finished = True
                    if finished:
                        self._emit(
                            job["worldId"],
                            "commission.updated",
                            {"commissionId": com_id, "status": "done"},
                        )
                except Exception as exc:
                    if job.get("trigger") != "commission_tick":
                        self.svc.store.update_commission(
                            com_id, status="failed", updatedAt=ISO()
                        )
                        log.warning("commission finalize failed %s: %s", com_id, exc)

        if job.get("trigger") == "debate_turn":
            from altrasia.debate_activity import (
                clear_debate,
                finalize_debate_synthesis,
                parse_activity,
            )

            scene_row = self.svc.store.get_scene(job["sceneId"])
            activity = parse_activity(scene_row) if scene_row else None
            if activity:
                if activity.get("phase") == "synthesis":
                    finalize_debate_synthesis(
                        self.svc.memory, job["sceneId"], activity, text
                    )
                    clear_debate(self.svc.store, job["sceneId"])
                    self._emit(
                        job["worldId"],
                        "scene.changed",
                        {"sceneId": job["sceneId"], "debate": "ended"},
                    )
                else:
                    self._emit(
                        job["worldId"],
                        "scene.changed",
                        {"sceneId": job["sceneId"], "debate": "turn_done"},
                    )

        if movement_tools_ran(tool_log):
            from altrasia.orchestrator.discussion_judgement import clear_ensemble_discussion

            clear_ensemble_discussion(self.svc.store, job["sceneId"])
        elif str(job.get("trigger") or "") == "persona_message":
            history = self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])
            op_text = operator_trigger_text(history)
            if trigger_invites_ensemble(op_text):
                bootstrap_ensemble_discussion(
                    self.svc.store,
                    job["sceneId"],
                    operator_text=op_text,
                    operator_message_id=job.get("triggerMessageId"),
                    world_id=job["worldId"],
                    cfg=cfg,
                )

        depth = int(job.get("continueDepth") or 0)
        limit, stop_reason, judgement_detail = await self._continue_depth_limit(job)
        scene_for_continue = self.svc.store.get_scene(job["sceneId"])
        from altrasia.debate_activity import parse_activity as _parse_act

        debate_active = bool(
            scene_for_continue and _parse_act(scene_for_continue)
            and _parse_act(scene_for_continue).get("kind") == "debate"
        )
        from altrasia.orchestrator.briefing_chain import maybe_enqueue_briefing_followups

        await maybe_enqueue_briefing_followups(self, job, tool_log)

        operator_msg_id = job.get("triggerMessageId")
        addressing = self._addressing_for_job(job)
        op_line = self._operator_line_for_job(job)
        nxt = self._pick_continue_character(
            job["worldId"],
            job["sceneId"],
            job["characterId"],
            trigger_text=op_line,
            trigger_message_id=operator_msg_id,
            addressing=addressing,
        )
        if self._should_enqueue_agent_continue(
            job,
            debate_active=debate_active,
            tool_log=tool_log,
            depth_limit=limit,
            next_character_id=nxt,
        ):
            if nxt:
                await self.enqueue_generation(
                    world_id=job["worldId"],
                    scene_id=job["sceneId"],
                    character_id=nxt,
                    trigger="agent_continue",
                    continue_depth=depth + 1,
                    trigger_message_id=operator_msg_id,
                )
        elif stop_reason:
            log.info(
                "agent_continue stopped scene=%s depth=%s reason=%s limit=%s",
                job["sceneId"],
                depth,
                stop_reason,
                limit,
            )
            await enqueue_pending_deliverables(self, job, stop_reason)
            maybe_clear_ensemble_if_complete(self.svc.store, job["sceneId"])
            self._emit(
                job["worldId"],
                "conversation.chain_stopped",
                {
                    "sceneId": job["sceneId"],
                    "continueDepth": depth,
                    "reason": stop_reason,
                    "depthLimit": limit,
                    "judgement": judgement_detail,
                },
            )
            self._emit(
                job["worldId"],
                "conversation.judgement",
                {
                    "sceneId": job["sceneId"],
                    **judgement_detail,
                },
            )

    async def on_phone_persona_message(
        self, world_id: str, channel_id: str, speaker_scene_id: str, message_id: str
    ) -> dict | None:
        """CC-12: enqueue phone_target for participant at other endpoint."""
        if world_id in self.svc.paused_worlds:
            return None
        target = self.svc.phone.phone_target_at_other_end(channel_id, speaker_scene_id)
        if not target:
            return None
        cid, remote_scene = target
        if remote_scene in self._scene_chain_active:
            return None
        return await self.enqueue_generation(
            world_id=world_id,
            scene_id=remote_scene,
            character_id=cid,
            trigger="phone_target",
            trigger_message_id=message_id,
        )

    async def on_knock_answered(
        self, world_id: str, scene_id: str, character_id: str, signal_id: str
    ) -> dict | None:
        """CC-11 / CC-12: explicit operator answer at target scene."""
        return await self.enqueue_generation(
            world_id=world_id,
            scene_id=scene_id,
            character_id=character_id,
            trigger="knock_answered",
            trigger_message_id=signal_id,
        )

    def _persona_message_job(self, world_id: str, message_id: str) -> dict[str, Any] | None:
        row = self.svc.store.fetchone(
            """SELECT jobId, status FROM GenerationJob
               WHERE worldId = ? AND triggerMessageId = ? AND trigger = 'persona_message'
               LIMIT 1""",
            (world_id, message_id),
        )
        if not row:
            return None
        return {"jobId": row["jobId"], "status": row["status"]}

    async def on_persona_message(
        self,
        world_id: str,
        scene_id: str,
        message_id: str,
        text: str,
        *,
        target_character_id: str | None = None,
    ) -> dict | None:
        """AO-20: exactly one reactive job per persona line."""
        lock_geography_on_first_play(self.svc.store, world_id)
        if world_id in self.svc.paused_worlds:
            return None
        existing = self._persona_message_job(world_id, message_id)
        if existing:
            return existing
        job: dict[str, Any] | None = None
        try:
            from altrasia.orchestrator.addressing_policy import (
                pending_clarification_for_reply,
                pending_directed_followup_for_reply,
            )
            from altrasia.orchestrator.operator_aliases import (
                apply_operator_alias_declaration,
                operator_alias_map,
            )
            from altrasia.orchestrator.speaker_selection import (
                addressee_ids_for,
                parse_addressing,
                resolve_directed_followup_reply,
            )

            cfg = self._world_config(world_id)
            scene = self.svc.store.get_scene(scene_id)
            present = json.loads(scene["presentJson"])
            cast = [c for c in present if c not in (PERSONA_ID,)]
            chars = {
                c["characterId"]: c
                for c in self.svc.store.list_world_characters(world_id)
            }
            scene_chars = {
                cid: chars[cid] for cid in cast if cid in chars
            }
            pending_clarification = pending_clarification_for_reply(
                self.svc.store, world_id, scene_id, message_id
            )
            directed_followup = pending_directed_followup_for_reply(
                self.svc.store, world_id, scene_id, message_id
            )
            fuzzy_on = bool(cfg.get("addressingFuzzyEnabled", True))
            fuzzy_dist = int(cfg.get("addressingFuzzyMaxDistance", 2))
            op_map = operator_alias_map(self.svc.store, world_id)
            alias_registered = apply_operator_alias_declaration(
                self.svc.store,
                world_id,
                text,
                cast,
                chars,
                fuzzy_enabled=fuzzy_on,
                fuzzy_max_distance=fuzzy_dist,
            )
            if alias_registered:
                op_map = operator_alias_map(self.svc.store, world_id)
            addressing = None
            if directed_followup:
                prior_addr, prior_id = directed_followup
                addressing = resolve_directed_followup_reply(
                    text,
                    cast,
                    scene_chars,
                    prior_addr,
                    prior_id,
                    self.svc.store,
                    world_id,
                    scene_id,
                    fuzzy_enabled=fuzzy_on,
                    fuzzy_max_distance=fuzzy_dist,
                    operator_alias_map=op_map,
                )
            if addressing is None:
                addressing = parse_addressing(
                    text,
                    cast,
                    chars,
                    target_character_id=target_character_id,
                    fuzzy_enabled=fuzzy_on,
                    fuzzy_max_distance=fuzzy_dist,
                    pending_clarification=pending_clarification,
                    operator_alias_map=op_map,
                )
            self._persist_message_addressing(message_id, addressing)
            if alias_registered:
                cid_reg, alias_reg = alias_registered
                row = self.svc.store.fetchone(
                    "SELECT metaJson FROM Message WHERE messageId = ?",
                    (message_id,),
                )
                try:
                    meta = json.loads(row["metaJson"] or "{}") if row else {}
                except json.JSONDecodeError:
                    meta = {}
                orch = meta.setdefault("orchestration", {})
                orch["operatorAliasRegistered"] = {
                    "characterId": cid_reg,
                    "alias": alias_reg,
                }
                self.svc.store.conn.execute(
                    "UPDATE Message SET metaJson = ? WHERE messageId = ?",
                    (json.dumps(meta), message_id),
                )
                self.svc.store.conn.commit()
            await self._preempt_scene_for_operator_line(
                world_id, scene_id, message_id, addressing
            )
            self._scene_chain_active.add(scene_id)
            cid, rationale = await self.pick_reactive_character_async(
                world_id,
                scene_id,
                text,
                trigger_message_id=message_id,
                target_character_id=target_character_id,
                addressing=addressing,
            )
            if not cid:
                return None
            if addressing.mode == "clarification" and addressing.clarifier_id:
                cid = addressing.clarifier_id
                rationale = {
                    **rationale,
                    "pick": "clarification",
                    "characterId": cid,
                    "candidateIds": addressing.candidate_ids,
                }
            else:
                ids = addressee_ids_for(addressing)
                if addressing.mode == "directed" and ids:
                    cid = ids[0]
                    rationale = {
                        **rationale,
                        "pick": "addressed_multi" if len(ids) > 1 else "addressed",
                        "characterId": cid,
                        "addresseeIds": ids,
                    }
            job = await self.enqueue_generation(
                world_id=world_id,
                scene_id=scene_id,
                character_id=cid,
                trigger="persona_message",
                trigger_message_id=message_id,
            )
            if not job:
                return None
            self.svc.store.update_job(
                job["jobId"], selectionRationaleJson=json.dumps(rationale)
            )
            return job
        finally:
            if job is None:
                self._scene_chain_active.discard(scene_id)
