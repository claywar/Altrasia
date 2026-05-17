from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.presence import PERSONA_ID
from altrasia.inference.queue import TokenStream
from altrasia.memory.strip_reasoning import strip_from_message_payload
from altrasia.tools.registry import ToolContext

ISO = lambda: datetime.now(timezone.utc).isoformat()


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

    def pick_reactive_character(
        self, world_id: str, scene_id: str, trigger_text: str
    ) -> tuple[str | None, dict]:
        """AO-18: @mention, name in text, else highest speechWeight among present cast."""
        scene = self.svc.store.get_scene(scene_id)
        present = json.loads(scene["presentJson"])
        cast = [c for c in present if c not in (PERSONA_ID,)]
        if not cast:
            return None, {}
        chars = {c["characterId"]: c for c in self.svc.store.list_world_characters(world_id)}
        lower = trigger_text.lower()

        mention = re.search(r"@(\w+)", trigger_text, re.I)
        if mention:
            name = mention.group(1).lower()
            for cid in cast:
                if name in chars.get(cid, {}).get("displayName", "").lower():
                    return cid, {"pick": "mention", "scores": {cid: {"total": 1.0}}}

        for cid in cast:
            display = chars.get(cid, {}).get("displayName", "")
            if display and display.lower() in lower:
                return cid, {"pick": "addressed", "scores": {cid: {"total": 0.95}}}

        best = max(cast, key=lambda c: float(chars.get(c, {}).get("speechWeight", 0.5)))
        return best, {"pick": "speechWeight", "scores": {best: {"total": 0.8}}}

    def _pick_continue_character(
        self, world_id: str, scene_id: str, exclude_id: str
    ) -> str | None:
        """AO-19: next cast member for agent_continue after reactive reply."""
        scene = self.svc.store.get_scene(scene_id)
        present = json.loads(scene["presentJson"])
        cast = [c for c in present if c not in (PERSONA_ID, exclude_id)]
        if not cast:
            return None
        chars = {c["characterId"]: c for c in self.svc.store.list_world_characters(world_id)}
        return max(cast, key=lambda c: float(chars.get(c, {}).get("speechWeight", 0.5)))

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
    ) -> dict[str, Any] | None:
        if world_id in self.svc.paused_worlds:
            return None
        job_id = str(uuid.uuid4())
        rationale = json.dumps({"pick": trigger, "characterId": character_id})
        self.svc.store.insert_job(
            {
                "jobId": job_id,
                "worldId": world_id,
                "characterId": character_id,
                "sceneId": scene_id,
                "trigger": trigger,
                "priority": 10 - continue_depth,
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
        messages = [{"role": "system", "content": system}]
        for m in self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])[-12:]:
            role = "assistant" if m["role"] == "assistant" else "user"
            messages.append({"role": role, "content": m["outputText"]})
        all_tools = self.svc.tools.list_openai_tools()
        memory_only = self._memory_tool_names()
        blocking = self._mandatory_recall_blocking(job["worldId"])
        memory_gate_open = False
        ctx = ToolContext(
            world_id=job["worldId"],
            scene_id=job["sceneId"],
            character_id=job["characterId"],
            services=self.svc,
        )
        depth = 0
        while depth < 5:
            if depth == 0 and blocking and not memory_gate_open:
                tools_payload = self._filter_tools(all_tools, memory_only)
            else:
                tools_payload = all_tools if depth == 0 else None
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

        depth = int(job.get("continueDepth") or 0)
        max_depth = self._max_continue_depth(job["worldId"])
        # AO-19: reactive (depth 0) → one agent_continue (depth 1) when another cast present
        if (
            depth == 0
            and job["trigger"] == "persona_message"
            and depth + 1 <= max_depth
        ):
            nxt = self._pick_continue_character(
                job["worldId"], job["sceneId"], job["characterId"]
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

    async def on_persona_message(
        self, world_id: str, scene_id: str, message_id: str, text: str
    ) -> dict | None:
        """AO-20: exactly one reactive job per persona line."""
        if world_id in self.svc.paused_worlds:
            return None
        if scene_id in self._scene_chain_active:
            return None
        cid, rationale = self.pick_reactive_character(world_id, scene_id, text)
        if not cid:
            return None
        job = await self.enqueue_generation(
            world_id=world_id,
            scene_id=scene_id,
            character_id=cid,
            trigger="persona_message",
            trigger_message_id=message_id,
        )
        self.svc.store.update_job(
            job["jobId"], selectionRationaleJson=json.dumps(rationale)
        )
        return job
