from __future__ import annotations

import asyncio
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from altrasia.api.deps import get_services, verify_auth
from altrasia.config import Settings, get_settings
from altrasia.domain.presence import PERSONA_ID, PresenceService
from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.perception.scope import can_perceive
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.services import AppServices
from altrasia.world_package import export_world_package, import_world_package

ISO = lambda: datetime.now(timezone.utc).isoformat()


class CreateWorldBody(BaseModel):
    name: str | None = None
    fixtureId: str | None = None


class PostMessageBody(BaseModel):
    text: str
    scope: str = "public"
    participants: list[str] = Field(default_factory=list)
    asPersona: bool = True


class PresenceBody(BaseModel):
    characterId: str


class SignalBody(BaseModel):
    kind: str = "knock"
    sourceSceneId: str
    targetSceneId: str
    fromCharacterId: str | None = None


class SignalPatch(BaseModel):
    status: str


class GenerateBody(BaseModel):
    characterId: str | None = None
    sceneId: str | None = None
    trigger: str = "manual"


class MetaMessageBody(BaseModel):
    text: str


class SummonBody(BaseModel):
    characterIds: list[str]
    targetSceneId: str


class HeartbeatPatch(BaseModel):
    enabled: bool | None = None
    intervalSeconds: int | None = None


class OperatorSettingsPatch(BaseModel):
    heartbeat: HeartbeatPatch | None = None


def _emit(svc: AppServices, world_id: str, event: str, data: dict[str, Any]) -> None:
    svc.event_bus.emit(svc.store, world_id, event, data)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    services = AppServices.create(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services.idle_scheduler:
            services.idle_scheduler.start()
        yield
        if services.idle_scheduler and services.idle_scheduler._task:
            services.idle_scheduler._task.cancel()

    app = FastAPI(title="Altrasia", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.services = services

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/worlds", dependencies=[Depends(verify_auth)])
    def list_worlds(svc: AppServices = Depends(get_services)) -> list[dict]:
        out = []
        for w in svc.store.list_worlds():
            row = dict(w)
            row["paused"] = w["worldId"] in svc.paused_worlds
            out.append(row)
        return out

    @app.post("/api/v1/worlds", dependencies=[Depends(verify_auth)])
    def create_world(
        body: CreateWorldBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        if body.fixtureId:
            return load_fixture_by_id(svc.store, svc.settings.fixtures_dir, body.fixtureId)
        world_id = str(uuid.uuid4())
        now = ISO()
        scene_id = str(uuid.uuid4())
        svc.store.insert_world(
            {
                "worldId": world_id,
                "name": body.name or "New World",
                "activeSceneId": scene_id,
                "defaultModelProfile": "qwen3.6-35b-a3b",
                "configJson": "{}",
                "worldMapJson": None,
                "eventSeq": 0,
                "createdAt": now,
                "updatedAt": now,
            }
        )
        svc.store.insert_scene(
            {
                "sceneId": scene_id,
                "worldId": world_id,
                "structureId": None,
                "mapLevel": 0,
                "levelLabel": None,
                "planPositionJson": None,
                "mapArtifactJson": None,
                "locationName": "Starting Scene",
                "locationDescription": "",
                "presentJson": json.dumps([PERSONA_ID]),
                "fixturesJson": "{}",
                "exitsJson": "[]",
                "activityJson": None,
                "roundRobinIndex": 0,
                "layoutHintsJson": json.dumps({"mapPosition": {"x": 50, "y": 50}}),
                "updatedAt": now,
            }
        )
        svc.presence.join(scene_id, PERSONA_ID)
        return {"worldId": world_id, "activeSceneId": scene_id}

    @app.get("/api/v1/worlds/{world_id}", dependencies=[Depends(verify_auth)])
    def get_world(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        w = svc.store.get_world(world_id)
        if not w:
            raise HTTPException(404, "world not found")
        out = dict(w)
        out["paused"] = world_id in svc.paused_worlds
        return out

    @app.patch("/api/v1/worlds/{world_id}", dependencies=[Depends(verify_auth)])
    def patch_world(
        world_id: str, body: dict[str, Any], svc: AppServices = Depends(get_services)
    ) -> dict:
        allowed = {k: v for k, v in body.items() if k in ("name", "activeSceneId", "configJson")}
        if "activeSceneId" in allowed:
            svc.presence.join(allowed["activeSceneId"], PERSONA_ID)
            _emit(svc, world_id, "scene.changed", {"sceneId": allowed["activeSceneId"]})
        svc.store.update_world(world_id, **allowed, updatedAt=ISO())
        return svc.store.get_world(world_id)  # type: ignore

    @app.get("/api/v1/worlds/{world_id}/scenes", dependencies=[Depends(verify_auth)])
    def list_scenes(world_id: str, svc: AppServices = Depends(get_services)) -> list[dict]:
        return svc.store.list_scenes(world_id)

    @app.get(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}", dependencies=[Depends(verify_auth)]
    )
    def get_scene(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        return sc

    @app.get(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/messages",
        dependencies=[Depends(verify_auth)],
    )
    def list_messages(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> list[dict]:
        scene = svc.store.get_scene(scene_id)
        if not scene:
            raise HTTPException(404, "scene not found")
        present = PresenceService.parse_present(scene["presentJson"])
        out = []
        for m in svc.store.list_messages(world_id, scene_id=scene_id):
            row = dict(m)
            row["perceivedByPersona"] = can_perceive(
                viewer_id=PERSONA_ID, message=m, present=present
            )
            out.append(row)
        return out

    @app.get(
        "/api/v1/worlds/{world_id}/characters/{character_id}/diary",
        dependencies=[Depends(verify_auth)],
    )
    def character_diary(
        world_id: str, character_id: str, svc: AppServices = Depends(get_services)
    ) -> list[dict]:
        return svc.memory.store.list_diary(character_id, limit=30)

    @app.get(
        "/api/v1/worlds/{world_id}/characters/{character_id}/mind",
        dependencies=[Depends(verify_auth)],
    )
    def character_mind(
        world_id: str, character_id: str, svc: AppServices = Depends(get_services)
    ) -> list[dict]:
        cur = svc.store.conn.execute(
            """SELECT locusKey, value, updatedAt FROM Locus
               WHERE pool = 'mind' AND ownerId = ? ORDER BY updatedAt DESC LIMIT 40""",
            (character_id,),
        )
        return [
            {"locusKey": row[0], "value": row[1], "updatedAt": row[2]}
            for row in cur.fetchall()
        ]

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/messages",
        dependencies=[Depends(verify_auth)],
    )
    async def post_message(
        world_id: str,
        scene_id: str,
        body: PostMessageBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        msg_id = str(uuid.uuid4())
        meta = {
            "communication": {
                "scope": body.scope,
                "participants": body.participants,
            }
        }
        svc.store.insert_message(
            {
                "messageId": msg_id,
                "worldId": world_id,
                "channelKind": "scene",
                "sceneId": scene_id,
                "role": "user",
                "characterId": None,
                "outputText": body.text,
                "reasoning": None,
                "streamStatus": "final",
                "generationJobId": None,
                "metaJson": json.dumps(meta),
                "createdAt": ISO(),
            }
        )
        job = None
        if body.asPersona:
            job = await svc.orchestrator.on_persona_message(
                world_id, scene_id, msg_id, body.text
            )
        return {"messageId": msg_id, "generationJob": job}

    @app.get(
        "/api/v1/worlds/{world_id}/observer/meta-messages",
        dependencies=[Depends(verify_auth)],
    )
    def meta_messages(world_id: str, svc: AppServices = Depends(get_services)) -> list[dict]:
        return svc.store.list_messages(world_id, channel_kind="meta")

    @app.post(
        "/api/v1/worlds/{world_id}/observer/meta-messages",
        dependencies=[Depends(verify_auth)],
    )
    def post_meta(world_id: str, body: MetaMessageBody, svc: AppServices = Depends(get_services)) -> dict:
        msg_id = str(uuid.uuid4())
        svc.store.insert_message(
            {
                "messageId": msg_id,
                "worldId": world_id,
                "channelKind": "meta",
                "sceneId": None,
                "role": "user",
                "characterId": None,
                "outputText": body.text,
                "reasoning": None,
                "streamStatus": "final",
                "generationJobId": None,
                "metaJson": "{}",
                "createdAt": ISO(),
            }
        )
        reply_id = str(uuid.uuid4())
        svc.store.insert_message(
            {
                "messageId": reply_id,
                "worldId": world_id,
                "channelKind": "meta",
                "sceneId": None,
                "role": "assistant",
                "characterId": None,
                "outputText": "Observer noted. Use scene tools to apply world changes.",
                "reasoning": None,
                "streamStatus": "final",
                "generationJobId": None,
                "metaJson": "{}",
                "createdAt": ISO(),
            }
        )
        return {"messageId": msg_id, "replyId": reply_id}

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/presence/join",
        dependencies=[Depends(verify_auth)],
    )
    def presence_join(
        world_id: str, scene_id: str, body: PresenceBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        svc.presence.join(scene_id, body.characterId)
        _emit(
            svc,
            world_id,
            "presence.changed",
            {"sceneId": scene_id, "characterId": body.characterId, "action": "join"},
        )
        return {"ok": True}

    @app.post(
        "/api/v1/worlds/{world_id}/presence/summon",
        dependencies=[Depends(verify_auth)],
    )
    def presence_summon(
        world_id: str, body: SummonBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        for cid in body.characterIds:
            svc.presence.join(body.targetSceneId, cid)
            _emit(
                svc,
                world_id,
                "presence.changed",
                {"sceneId": body.targetSceneId, "characterId": cid, "action": "summon"},
            )
        return {"ok": True, "targetSceneId": body.targetSceneId}

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/presence/leave",
        dependencies=[Depends(verify_auth)],
    )
    def presence_leave(
        world_id: str, scene_id: str, body: PresenceBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        svc.presence.leave(scene_id, body.characterId)
        return {"ok": True}

    @app.get("/api/v1/worlds/{world_id}/roster", dependencies=[Depends(verify_auth)])
    def roster(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        return svc.presence.roster(world_id)

    @app.get("/api/v1/worlds/{world_id}/spatial-graph", dependencies=[Depends(verify_auth)])
    def spatial_graph(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        return build_spatial_graph(svc.store, world_id)

    @app.get("/api/v1/worlds/{world_id}/signals", dependencies=[Depends(verify_auth)])
    def list_signals(world_id: str, svc: AppServices = Depends(get_services)) -> list[dict]:
        return svc.store.list_signals(world_id, status="pending")

    @app.post("/api/v1/worlds/{world_id}/signals", dependencies=[Depends(verify_auth)])
    def create_signal(
        world_id: str, body: SignalBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        sid = str(uuid.uuid4())
        svc.store.insert_signal(
            {
                "signalId": sid,
                "worldId": world_id,
                "kind": body.kind,
                "sourceSceneId": body.sourceSceneId,
                "targetSceneId": body.targetSceneId,
                "fromCharacterId": body.fromCharacterId,
                "status": "pending",
                "createdAt": ISO(),
            }
        )
        _emit(
            svc,
            world_id,
            "signal.created",
            {"signalId": sid, "targetSceneId": body.targetSceneId},
        )
        return {"signalId": sid, "status": "pending"}

    @app.patch(
        "/api/v1/worlds/{world_id}/signals/{signal_id}",
        dependencies=[Depends(verify_auth)],
    )
    def patch_signal(
        world_id: str,
        signal_id: str,
        body: SignalPatch,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        svc.store.update_signal(signal_id, status=body.status)
        svc.event_bus.emit(
            svc.store,
            world_id,
            "signal.updated",
            {"signalId": signal_id, "status": body.status},
        )
        return {"signalId": signal_id, "status": body.status}

    @app.post("/api/v1/worlds/{world_id}/generate", dependencies=[Depends(verify_auth)])
    async def generate(
        world_id: str, body: GenerateBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        world = svc.store.get_world(world_id)
        if not world:
            raise HTTPException(404)
        scene_id = body.sceneId or world["activeSceneId"]
        chars = json.loads(svc.store.get_scene(scene_id)["presentJson"])
        cast = [c for c in chars if c not in (PERSONA_ID,)]
        cid = body.characterId or (cast[0] if cast else None)
        if not cid:
            raise HTTPException(400, "no character to generate")
        return await svc.orchestrator.enqueue_generation(
            world_id=world_id,
            scene_id=scene_id,
            character_id=cid,
            trigger=body.trigger,
        )

    @app.get("/api/v1/worlds/{world_id}/queue", dependencies=[Depends(verify_auth)])
    def queue_snapshot(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        jobs = svc.store.list_queued_jobs(world_id)
        gpu = svc.gpu_queue.snapshot()
        current = jobs[0] if jobs else None
        return {
            "busy": gpu["busy"] or bool(jobs),
            "depth": len(jobs),
            "estimatedWaitMs": len(jobs) * 5000,
            "currentJob": current,
            "gpu": gpu,
        }

    @app.get(
        "/api/v1/worlds/{world_id}/generations/{job_id}",
        dependencies=[Depends(verify_auth)],
    )
    def get_generation(
        world_id: str, job_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        job = svc.store.get_job(job_id)
        if not job:
            raise HTTPException(404)
        return job

    @app.get(
        "/api/v1/worlds/{world_id}/generations/{job_id}/stream",
        dependencies=[Depends(verify_auth)],
    )
    async def stream_generation(
        world_id: str, job_id: str, svc: AppServices = Depends(get_services)
    ) -> StreamingResponse:
        stream = svc.streams.get(job_id)
        if not stream:

            async def empty():
                yield "event: generation.error\ndata: {\"error\":\"unknown job\"}\n\n"

            return StreamingResponse(empty(), media_type="text/event-stream")

        async def gen():
            async for ev in stream.iter_events():
                payload = json.dumps(ev.data)
                yield f"event: {ev.event}\ndata: {payload}\n\n"
                await asyncio.sleep(0)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.delete("/api/v1/inference/queue/{job_id}", dependencies=[Depends(verify_auth)])
    def cancel_job(job_id: str, svc: AppServices = Depends(get_services)) -> dict:
        ok = svc.orchestrator.cancel_job(job_id)
        if not ok:
            raise HTTPException(404, "job not found")
        return {"jobId": job_id, "status": "cancelled"}

    @app.get(
        "/api/v1/worlds/{world_id}/package/export",
        dependencies=[Depends(verify_auth)],
    )
    def export_package(world_id: str, svc: AppServices = Depends(get_services)) -> Response:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        assets = svc.settings.data_dir / "assets"
        try:
            blob = export_world_package(svc.store, world_id, assets_dir=assets)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        safe_name = world_id[:8]
        return Response(
            content=blob,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="altrasia-world-{safe_name}.zip"'
            },
        )

    @app.post("/api/v1/worlds/import", dependencies=[Depends(verify_auth)])
    async def import_package(
        file: UploadFile = File(...), svc: AppServices = Depends(get_services)
    ) -> dict:
        data = await file.read()
        if not data:
            raise HTTPException(400, "empty package")
        assets = svc.settings.data_dir / "assets"
        try:
            return import_world_package(svc.store, data, assets_dir=assets)
        except (ValueError, zipfile.BadZipFile, KeyError) as exc:
            raise HTTPException(400, f"invalid package: {exc}") from exc

    @app.get("/api/v1/operator/settings", dependencies=[Depends(verify_auth)])
    def get_operator_settings(svc: AppServices = Depends(get_services)) -> dict:
        return svc.operator_settings.load().to_api()

    @app.patch("/api/v1/operator/settings", dependencies=[Depends(verify_auth)])
    def patch_operator_settings(
        body: OperatorSettingsPatch, svc: AppServices = Depends(get_services)
    ) -> dict:
        updates: dict[str, Any] = {}
        if body.heartbeat is not None:
            hb: dict[str, Any] = {}
            if body.heartbeat.enabled is not None:
                hb["enabled"] = body.heartbeat.enabled
            if body.heartbeat.intervalSeconds is not None:
                hb["intervalSeconds"] = body.heartbeat.intervalSeconds
            updates["heartbeat"] = hb
        return svc.operator_settings.patch(updates).to_api()

    @app.post("/api/v1/worlds/{world_id}/pause", dependencies=[Depends(verify_auth)])
    def pause_world(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        svc.paused_worlds.add(world_id)
        return {"worldId": world_id, "paused": True}

    @app.post("/api/v1/worlds/{world_id}/resume", dependencies=[Depends(verify_auth)])
    def resume_world(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        svc.paused_worlds.discard(world_id)
        return {"worldId": world_id, "paused": False}

    @app.get("/api/v1/health/llm")
    def health_llm(svc: AppServices = Depends(get_services)) -> dict:
        return {"mock": svc.settings.mock_llm, "baseUrl": svc.settings.llm_base_url}

    @app.websocket("/api/v1/worlds/{world_id}/events")
    async def world_events(websocket: WebSocket, world_id: str) -> None:
        await websocket.accept()
        svc: AppServices = websocket.app.state.services  # type: ignore[attr-defined]
        if svc.idle_scheduler:
            svc.idle_scheduler.mark_world_active(world_id)
        q = svc.event_bus.subscribe(world_id)
        try:
            while True:
                payload = await q.get()
                await websocket.send_json(payload)
        except WebSocketDisconnect:
            svc.event_bus.unsubscribe(world_id, q)
            if svc.idle_scheduler and not svc.event_bus.subscriber_count(world_id):
                svc.idle_scheduler.mark_world_inactive(world_id)

    @app.delete(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}",
        dependencies=[Depends(verify_auth)],
    )
    def delete_scene(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        scenes = svc.store.list_scenes(world_id)
        if len(scenes) <= 1:
            raise HTTPException(400, "cannot delete last scene (W-1)")
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        world = svc.store.get_world(world_id)
        svc.store.conn.execute("DELETE FROM Scene WHERE sceneId = ?", (scene_id,))
        svc.store.conn.commit()
        if world and world.get("activeSceneId") == scene_id:
            remaining = [s for s in scenes if s["sceneId"] != scene_id]
            svc.store.update_world(world_id, activeSceneId=remaining[0]["sceneId"])
        return {"deleted": scene_id}

    return app
