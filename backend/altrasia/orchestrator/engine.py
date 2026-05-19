from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
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
        if trigger == "idle_timer":
            try:
                rationale = json.loads(job.get("selectionRationaleJson") or "{}")
            except (json.JSONDecodeError, TypeError):
                rationale = {}
            if rationale.get("idle_source"):
                orch["idleSource"] = rationale["idle_source"]
        meta["orchestration"] = orch
    return meta


_GENERATION_FAILED_TEXT = (
    "Generation failed. Check inference logs or the ⓘ job details."
)

_AGENT_CONTINUE_TRIGGERS = frozenset({"persona_message", "agent_continue"})


def _message_meta_with_generation_error(job: dict[str, Any], exc: Exception) -> str:
    meta = _scene_message_meta(job)
    meta["generationError"] = str(exc)[:200]
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
        return int(self._world_config(world_id).get("maxContinueDepth", 2))

    def _agent_continue_enabled(self, world_id: str) -> bool:
        return bool(self._world_config(world_id).get("agentContinueEnabled", True))

    def _should_enqueue_agent_continue(
        self,
        job: dict[str, Any],
        *,
        debate_active: bool,
        tool_log: list[dict[str, Any]],
        max_depth: int,
    ) -> bool:
        if not self._agent_continue_enabled(job["worldId"]):
            return False
        if str(job.get("trigger") or "") not in _AGENT_CONTINUE_TRIGGERS:
            return False
        depth = int(job.get("continueDepth") or 0)
        if depth + 1 > max_depth:
            return False
        if debate_active:
            return False
        from altrasia.orchestrator.briefing_chain import movement_tools_ran

        if movement_tools_ran(tool_log):
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
    ) -> tuple[str | None, dict]:
        """AO-17/18: scoreSpeakers with debate/activity overrides."""
        from altrasia.debate_activity import debate_current_speaker, parse_activity
        from altrasia.orchestrator.speaker_selection import score_speakers
        from altrasia.world_config import get_world_config

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
        return pick.character_id, pick.rationale

    async def pick_reactive_character_async(
        self,
        world_id: str,
        scene_id: str,
        trigger_text: str,
        *,
        trigger_message_id: str | None = None,
        target_character_id: str | None = None,
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

    def _pick_continue_character(
        self,
        world_id: str,
        scene_id: str,
        exclude_id: str,
        *,
        trigger_text: str = "",
        trigger_message_id: str | None = None,
    ) -> str | None:
        """AO-19: scoreSpeakers for agent_continue."""
        from altrasia.orchestrator.speaker_selection import score_speakers

        scene = self.svc.store.get_scene(scene_id)
        present = json.loads(scene["presentJson"])
        cast = [c for c in present if c not in (PERSONA_ID, exclude_id)]
        pick = score_speakers(
            self.svc,
            world_id=world_id,
            scene_id=scene_id,
            trigger_text=trigger_text or "continue",
            eligible=cast,
            exclude_id=exclude_id,
            last_speaker_id=exclude_id,
            trigger_message_id=trigger_message_id,
            session_spoke=self._cast_spoke_in_scene(world_id, scene_id),
        )
        return pick.character_id if pick else None

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
    ) -> dict[str, Any] | None:
        if world_id in self.svc.paused_worlds:
            return None
        job_id = str(uuid.uuid4())
        rationale_obj: dict[str, Any] = {"pick": trigger, "characterId": character_id}
        if commission_id:
            rationale_obj["commissionId"] = commission_id
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

        async def work() -> str:
            return await self._generate_text(job, msg_id, tool_log)

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
            await stream.push("generation.token", {"jobId": job_id, "messageId": msg_id, "delta": cleaned})
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
        except asyncio.CancelledError:
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
            log.warning("generation failed job=%s character=%s: %s", job_id, job.get("characterId"), exc)
            self.svc.store.update_message(
                msg_id,
                streamStatus="interrupted",
                outputText=_GENERATION_FAILED_TEXT,
                metaJson=_message_meta_with_generation_error(job, exc),
            )
            self.svc.store.update_job(job_id, status="cancelled")
            await stream.push("generation.error", {"jobId": job_id, "error": str(exc)})
            self._emit(
                job["worldId"],
                "generation.error",
                {"jobId": job_id, "message": str(exc)},
            )
        finally:
            if not self._scene_has_pending_jobs(job["worldId"], job["sceneId"]):
                self._scene_chain_active.discard(job["sceneId"])
            self._emit_queue(job["worldId"])
            await stream.close()

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
        system += f"\n\n{single_speaker_system_addendum(
            ch['displayName'],
            other_names=other_names,
            ensemble_invited=trigger_invites_ensemble(op_trigger),
        )}"
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
        )
        depth = 0
        is_commission = str(job.get("trigger", "")).startswith("commission")
        while depth < 5:
            if is_commission:
                tools_payload = job_tools
            elif depth == 0 and blocking and not memory_gate_open:
                tools_payload = self._filter_tools(job_tools, memory_only)
            else:
                tools_payload = job_tools
            resp = await self.svc.llm.chat(messages, tools_payload)
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
                    self.svc, world_id=job["worldId"], detection=detection
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

        depth = int(job.get("continueDepth") or 0)
        max_depth = self._max_continue_depth(job["worldId"])
        scene_for_continue = self.svc.store.get_scene(job["sceneId"])
        from altrasia.debate_activity import parse_activity as _parse_act

        debate_active = bool(
            scene_for_continue and _parse_act(scene_for_continue)
            and _parse_act(scene_for_continue).get("kind") == "debate"
        )
        from altrasia.orchestrator.briefing_chain import maybe_enqueue_briefing_followups

        await maybe_enqueue_briefing_followups(self, job, tool_log)

        if self._should_enqueue_agent_continue(
            job,
            debate_active=debate_active,
            tool_log=tool_log,
            max_depth=max_depth,
        ):
            nxt = self._pick_continue_character(
                job["worldId"],
                job["sceneId"],
                job["characterId"],
                trigger_text=text,
                trigger_message_id=msg_id,
            )
            if nxt:
                await self.enqueue_generation(
                    world_id=job["worldId"],
                    scene_id=job["sceneId"],
                    character_id=nxt,
                    trigger="agent_continue",
                    continue_depth=depth + 1,
                    trigger_message_id=msg_id,
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
        self, world_id: str, scene_id: str, message_id: str, text: str
    ) -> dict | None:
        """AO-20: exactly one reactive job per persona line."""
        lock_geography_on_first_play(self.svc.store, world_id)
        if world_id in self.svc.paused_worlds:
            return None
        existing = self._persona_message_job(world_id, message_id)
        if existing:
            return existing
        if scene_id in self._scene_chain_active:
            return None
        self._scene_chain_active.add(scene_id)
        job: dict[str, Any] | None = None
        try:
            cid, rationale = await self.pick_reactive_character_async(
                world_id, scene_id, text, trigger_message_id=message_id
            )
            if not cid:
                return None
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
