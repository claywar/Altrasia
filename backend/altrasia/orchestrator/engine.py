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
from altrasia.memory.strip_reasoning import strip_from_message_payload
from altrasia.tools.registry import ToolContext
from altrasia.world_geography import lock_geography_on_first_play

ISO = lambda: datetime.now(timezone.utc).isoformat()

log = logging.getLogger(__name__)


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
        cast_tools = {
            t["function"]["name"]
            for t in all_tools
            if not t["function"]["name"].startswith("scene_")
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
                "metaJson": json.dumps({"communication": {"scope": "public"}}),
                "createdAt": ISO(),
            }
        )
        await stream.push("generation.start", {"jobId": job_id, "messageId": msg_id})
        self._emit(
            job["worldId"],
            "generation.start",
            {"jobId": job_id, "messageId": msg_id},
        )

        async def work() -> str:
            return await self._generate_text(job, msg_id)

        try:
            text = await self.svc.gpu_queue.run(job_id, "chat", work)
            cleaned = strip_from_message_payload({"content": text})
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
            await self._after_reply(job, msg_id, cleaned)
        except Exception as exc:
            self.svc.store.update_message(msg_id, streamStatus="interrupted")
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
        row = self.svc.store.conn.execute(
            """SELECT 1 FROM GenerationJob WHERE worldId = ? AND sceneId = ?
               AND status = 'running' LIMIT 1""",
            (world_id, scene_id),
        ).fetchone()
        return row is not None

    async def _generate_text(self, job: dict, msg_id: str) -> str:
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

        addendum = quality_addendum(self.svc.settings, ch.get("modelProfile", "qwen3.6-35b-a3b"))
        system = (
            f"You are {ch['displayName']}. Stay in character.\n\n"
            f"Scene: {scene['locationName']}\n\n{recall}"
        )
        if addendum:
            system += f"\n\n{addendum}"
        if cfg.get("citeProvenanceInPrompt"):
            prov = self.svc.store.conn.execute(
                """SELECT locusKey, sourceKind, sourceRef FROM EvidenceRecord
                   WHERE pool = 'mind' AND ownerId = ? ORDER BY retrievedAt DESC LIMIT 8""",
                (job["characterId"],),
            ).fetchall()
            if prov:
                system += "\n\n## Source provenance (cite when using these facts)"
                for row in prov:
                    system += f"\n- {row[0]} ({row[1]}: {row[2][:120]})"
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
        messages = [{"role": "system", "content": system}]
        for m in self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])[-12:]:
            role = "assistant" if m["role"] == "assistant" else "user"
            messages.append({"role": role, "content": m["outputText"]})
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
        while depth < 5:
            if depth == 0 and blocking and not memory_gate_open:
                tools_payload = self._filter_tools(job_tools, memory_only)
            else:
                tools_payload = job_tools if depth == 0 else None
            resp = await self.svc.llm.chat(messages, tools_payload)
            msg = resp["choices"][0]["message"]
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
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        }
                    )
                depth += 1
                continue
            return msg.get("content") or ""
        return ""

    async def _after_reply(self, job: dict, msg_id: str, text: str) -> None:
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
        # AO-19: reactive (depth 0) → one agent_continue (depth 1) when another cast present
        scene_for_continue = self.svc.store.get_scene(job["sceneId"])
        from altrasia.debate_activity import parse_activity as _parse_act

        debate_active = bool(
            scene_for_continue and _parse_act(scene_for_continue)
            and _parse_act(scene_for_continue).get("kind") == "debate"
        )
        if (
            depth == 0
            and job["trigger"] == "persona_message"
            and depth + 1 <= max_depth
            and not debate_active
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
        row = self.svc.store.conn.execute(
            """SELECT jobId, status FROM GenerationJob
               WHERE worldId = ? AND triggerMessageId = ? AND trigger = 'persona_message'
               LIMIT 1""",
            (world_id, message_id),
        ).fetchone()
        if not row:
            return None
        return {"jobId": row[0], "status": row[1]}

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
