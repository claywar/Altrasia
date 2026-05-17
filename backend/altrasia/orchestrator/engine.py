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

    def pick_reactive_character(
        self, world_id: str, scene_id: str, trigger_text: str
    ) -> tuple[str | None, dict]:
        """AO-18 simplified: @mention, addressed name, else highest speechWeight present."""
        scene = self.svc.store.get_scene(scene_id)
        present = json.loads(scene["presentJson"])
        cast = [c for c in present if c not in (PERSONA_ID,)]
        if not cast:
            return None, {}
        mention = re.search(r"@(\w+)", trigger_text)
        chars = {c["characterId"]: c for c in self.svc.store.list_world_characters(world_id)}
        if mention:
            name = mention.group(1).lower()
            for cid in cast:
                ch = chars.get(cid, {})
                if name in ch.get("displayName", "").lower():
                    return cid, {"pick": "mention", "scores": {cid: {"total": 1.0}}}
        best = max(cast, key=lambda c: float(chars.get(c, {}).get("speechWeight", 0.5)))
        return best, {"pick": "speechWeight", "scores": {best: {"total": 0.8}}}

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
    ) -> dict[str, Any]:
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
        stream = TokenStream()
        self.svc.streams[job_id] = stream
        task = asyncio.create_task(self._run_job(job_id, stream))
        self._workers[job_id] = task
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
            await stream.push("generation.done", {"jobId": job_id, "messageId": msg_id})
            self.svc.store.update_job(job_id, status="done")
            await self._after_reply(job, msg_id, cleaned)
        except Exception as exc:
            self.svc.store.update_message(msg_id, streamStatus="interrupted")
            self.svc.store.update_job(job_id, status="cancelled")
            await stream.push("generation.error", {"jobId": job_id, "error": str(exc)})
        finally:
            await stream.close()

    async def _generate_text(self, job: dict, msg_id: str) -> str:
        ch = self.svc.store.get_character(job["characterId"])
        recall = self.svc.memory.build_mandatory_recall(
            character_id=job["characterId"], scene_id=job["sceneId"]
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
        tools = self.svc.tools.list_openai_tools()
        ctx = ToolContext(
            world_id=job["worldId"],
            scene_id=job["sceneId"],
            character_id=job["characterId"],
            services=self.svc,
        )
        depth = 0
        while depth < 5:
            resp = await self.svc.llm.chat(messages, tools if depth == 0 else None)
            msg = resp["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append(msg)
                for tc in tool_calls:
                    fn = tc["function"]
                    args = json.loads(fn.get("arguments") or "{}")
                    result = await self.svc.tools.invoke(fn["name"], args, ctx)
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
        recent = self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])[-4:]
        snippet = "\n".join(f"{m.get('characterId') or 'persona'}: {m['outputText']}" for m in recent)
        self.svc.memory.capture_diary_fanout(
            scene_id=job["sceneId"],
            present_ids=present,
            snippet=snippet,
            message_ids=[m["messageId"] for m in recent],
        )
        if job["continueDepth"] == 0 and job["trigger"] == "persona_message":
            trigger_msg = job.get("triggerMessageId")
            msgs = self.svc.store.list_messages(job["worldId"], scene_id=job["sceneId"])
            persona_line = next(
                (m for m in reversed(msgs) if m["messageId"] == trigger_msg),
                None,
            )
            if persona_line:
                other = [c for c in present if c != job["characterId"]]
                if other:
                    await self.enqueue_generation(
                        world_id=job["worldId"],
                        scene_id=job["sceneId"],
                        character_id=other[0],
                        trigger="agent_continue",
                        continue_depth=1,
                        trigger_message_id=msg_id,
                    )

    async def on_persona_message(
        self, world_id: str, scene_id: str, message_id: str, text: str
    ) -> dict | None:
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
