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
from altrasia.domain.navigation import (
    execute_travel,
    navigation_summary,
    plan_route,
    reachable_from,
)
from altrasia.domain.spatial_graph import build_spatial_graph
from altrasia.perception.scope import can_perceive
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.services import AppServices
from altrasia.commission_notify import refresh_commissions
from altrasia.commission_runner import start_commission as run_start_commission
from altrasia.commissions import create_commission, list_commissions, patch_commission
from altrasia.debate_activity import (
    advance_debate_phase,
    advance_debate_speaker,
    clear_debate,
    parse_activity,
    start_debate,
)
from altrasia.debate_runner import enqueue_debate_turn
from altrasia.approvals import list_approvals, resolve_approval
from altrasia.briefing import set_briefing_fixture
from altrasia.commons import list_commons, set_commons
from altrasia.world_config import get_world_config, merge_world_policy
from altrasia.map_authoring import (
    commit_layout_draft,
    create_layout_draft,
    get_layout_draft,
    repair_layout_draft,
    update_draft_proposed,
)
from altrasia.character_authoring import (
    approve_character_draft,
    create_character_draft,
    discard_character_draft,
    get_character_draft,
)
from altrasia.world_geography import (
    create_scene as geo_create_scene,
    geography_status,
    layout_design_mode,
    lock_geography,
    lock_geography_on_first_play,
)
from altrasia.world_package import export_world_package, import_world_package

ISO = lambda: datetime.now(timezone.utc).isoformat()


class CreateWorldBody(BaseModel):
    name: str | None = None
    fixtureId: str | None = None


class PostMessageBody(BaseModel):
    text: str
    scope: str = "public"
    participants: list[str] = Field(default_factory=list)
    channelId: str | None = None
    asPersona: bool = True


class CreatePhoneChannelBody(BaseModel):
    sceneIdA: str
    characterIdA: str
    sceneIdB: str
    characterIdB: str


class SpeakerphonePatch(BaseModel):
    speakerphone: bool


class SignalAnswerBody(BaseModel):
    characterId: str
    targetSceneId: str | None = None


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


class InferencePatch(BaseModel):
    primaryBaseUrl: str | None = None
    primaryModel: str | None = None
    embeddingBaseUrl: str | None = None
    embeddingModel: str | None = None


class OperatorSettingsPatch(BaseModel):
    heartbeat: HeartbeatPatch | None = None
    enableServerPlugins: bool | None = None
    inference: InferencePatch | None = None


class ExitStateBody(BaseModel):
    doorState: str


class CharacterDraftCreateBody(BaseModel):
    brief: str


class CharacterApproveBody(BaseModel):
    draftId: str
    definitionJson: dict[str, Any] | None = None
    displayName: str | None = None
    worldId: str | None = None


class WorldMemberBody(BaseModel):
    characterId: str


class CreateSceneBody(BaseModel):
    locationName: str
    locationDescription: str = ""
    connectFromSceneId: str | None = None
    exitLabel: str = "Door"
    reverseExitLabel: str | None = None


class PatchSceneBody(BaseModel):
    locationName: str | None = None
    locationDescription: str | None = None


class CreateCommissionBody(BaseModel):
    assigneeCharacterId: str
    targetSceneId: str
    brief: str
    deliverablePolicy: str = "mind"
    allowedTools: list[str] | None = None


class LayoutDraftCreateBody(BaseModel):
    brief: str
    scope: str = "mini"


class UnifiedLayoutDraftBody(BaseModel):
    brief: str


class LayoutPatchBody(BaseModel):
    nodes: list[dict] | None = None
    edges: list[dict] | None = None


class WorldBootstrapCreateBody(BaseModel):
    description: str
    connectFromSceneId: str | None = None


class NavigationTravelBody(BaseModel):
    toSceneId: str
    fromSceneId: str | None = None
    mode: str = "route"  # route | step | jump


class DebateStartBody(BaseModel):
    speakingOrder: list[str]
    phase: str = "opening"


class WorldPolicyPatch(BaseModel):
    requireWebToolApproval: bool | None = None
    auditWebTools: bool | None = None
    pauseCommissionsDuringPersonaDialogue: bool | None = None
    citeProvenanceInPrompt: bool | None = None
    commonsAccessIds: list[str] | None = None


class CommonsBody(BaseModel):
    key: str
    text: str


class ForceCompleteBody(BaseModel):
    reason: str


class BriefingBody(BaseModel):
    fixtureKey: str = "board"
    text: str


class PatchCommissionBody(BaseModel):
    status: str | None = None
    deliverableLocusKeys: list[str] | None = None
    forceCompleteReason: str | None = None


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
            if not svc.store.list_scenes(w["worldId"]):
                continue
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
                "configJson": json.dumps({"layoutDesignMode": True}),
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
        try:
            out["policy"] = json.loads(w.get("configJson") or "{}")
        except json.JSONDecodeError:
            out["policy"] = {}
        return out

    @app.get("/api/v1/worlds/{world_id}/policy", dependencies=[Depends(verify_auth)])
    def get_world_policy(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        return get_world_config(svc.store, world_id)

    @app.patch("/api/v1/worlds/{world_id}/policy", dependencies=[Depends(verify_auth)])
    def patch_world_policy(
        world_id: str, body: WorldPolicyPatch, svc: AppServices = Depends(get_services)
    ) -> dict:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        policy = body.model_dump(exclude_none=True)
        cfg = merge_world_policy(svc.store, world_id, policy)
        _emit(svc, world_id, "world.updated", {"policy": cfg})
        return cfg

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
        "/api/v1/worlds/{world_id}/characters",
        dependencies=[Depends(verify_auth)],
    )
    def list_world_characters(
        world_id: str, svc: AppServices = Depends(get_services)
    ) -> list[dict]:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        rows = svc.store.list_world_characters(world_id)
        out = []
        for c in rows:
            entry = {
                "characterId": c["characterId"],
                "displayName": c["displayName"],
                "modelProfile": c.get("modelProfile"),
                "speechWeight": c.get("speechWeight"),
                "muted": bool(c.get("muted")),
                "disabled": bool(c.get("disabled")),
            }
            try:
                entry["definition"] = json.loads(c.get("definitionJson") or "{}")
            except json.JSONDecodeError:
                entry["definition"] = {}
            out.append(entry)
        return out

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
        "/api/v1/worlds/{world_id}/geography",
        dependencies=[Depends(verify_auth)],
    )
    def get_geography(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        try:
            return geography_status(svc.store, world_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/geography/lock",
        dependencies=[Depends(verify_auth)],
    )
    def post_geography_lock(
        world_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        try:
            return lock_geography(svc.store, world_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/scenes",
        dependencies=[Depends(verify_auth)],
    )
    def post_scene(
        world_id: str, body: CreateSceneBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        in_design = layout_design_mode(svc.store, world_id)
        if not in_design and not body.connectFromSceneId:
            raise HTTPException(
                403,
                "geography locked — new scenes must connect from an existing location (MAP-GROW)",
            )
        if not body.locationName.strip():
            raise HTTPException(400, "locationName required")
        try:
            sc = geo_create_scene(
                svc.store,
                world_id,
                location_name=body.locationName.strip(),
                location_description=body.locationDescription,
                connect_from_scene_id=body.connectFromSceneId,
                exit_label=body.exitLabel,
                reverse_exit_label=body.reverseExitLabel,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(
            svc,
            world_id,
            "scene.created",
            {"sceneId": sc["sceneId"], "locationName": sc["locationName"]},
        )
        return sc

    @app.patch(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}",
        dependencies=[Depends(verify_auth)],
    )
    def patch_scene(
        world_id: str,
        scene_id: str,
        body: PatchSceneBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        fields: dict[str, Any] = {"updatedAt": ISO()}
        if body.locationName is not None:
            fields["locationName"] = body.locationName
        if body.locationDescription is not None:
            fields["locationDescription"] = body.locationDescription
        svc.store.update_scene(scene_id, **fields)
        _emit(svc, world_id, "scene.changed", {"sceneId": scene_id})
        return svc.store.get_scene(scene_id)  # type: ignore[return-value]

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/debate",
        dependencies=[Depends(verify_auth)],
    )
    async def post_debate_start(
        world_id: str,
        scene_id: str,
        body: DebateStartBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        try:
            activity = start_debate(
                svc.store, scene_id, speaking_order=body.speakingOrder, phase=body.phase
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "scene.changed", {"sceneId": scene_id, "debate": "started"})
        job = await enqueue_debate_turn(svc, scene_id)
        return {"activity": activity, "generationJob": job}

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/debate/advance-speaker",
        dependencies=[Depends(verify_auth)],
    )
    async def post_debate_advance_speaker(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        try:
            activity = advance_debate_speaker(svc.store, scene_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "scene.changed", {"sceneId": scene_id})
        job = await enqueue_debate_turn(svc, scene_id)
        return {"activity": activity, "generationJob": job}

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/debate/advance-phase",
        dependencies=[Depends(verify_auth)],
    )
    async def post_debate_advance_phase(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        try:
            activity = advance_debate_phase(svc.store, scene_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "scene.changed", {"sceneId": scene_id})
        job = await enqueue_debate_turn(svc, scene_id)
        return {"activity": activity, "generationJob": job}

    @app.delete(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/debate",
        dependencies=[Depends(verify_auth)],
    )
    def delete_debate(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        clear_debate(svc.store, scene_id)
        _emit(svc, world_id, "scene.changed", {"sceneId": scene_id, "debate": "cleared"})
        return {"sceneId": scene_id, "activity": None}

    @app.get(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/debate",
        dependencies=[Depends(verify_auth)],
    )
    def get_debate(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        return {"activity": parse_activity(sc)}

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
        channels = {c["channelId"]: c for c in svc.phone.list_active(world_id)}
        out = []
        for m in svc.store.list_messages(world_id, scene_id=scene_id):
            row = dict(m)
            comm = json.loads(m.get("metaJson") or "{}").get("communication", {})
            ch_id = comm.get("channelId")
            ch = channels.get(ch_id) if ch_id else None
            row["perceivedByPersona"] = can_perceive(
                viewer_id=PERSONA_ID,
                message=m,
                present=present,
                viewer_scene_id=scene_id,
                channel=ch,
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

    @app.get(
        "/api/v1/worlds/{world_id}/characters/{character_id}/evidence",
        dependencies=[Depends(verify_auth)],
    )
    def character_evidence(
        world_id: str,
        character_id: str,
        locusKey: str | None = None,
        svc: AppServices = Depends(get_services),
    ) -> list[dict]:
        if locusKey:
            rows = svc.store.list_evidence_for_locus("mind", character_id, locusKey)
        else:
            cur = svc.store.conn.execute(
                """SELECT * FROM EvidenceRecord WHERE pool = 'mind' AND ownerId = ?
                   ORDER BY retrievedAt DESC LIMIT 40""",
                (character_id,),
            )
            rows = [dict(r) for r in cur.fetchall()]
        return rows

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/briefing",
        dependencies=[Depends(verify_auth)],
    )
    def post_briefing(
        world_id: str,
        scene_id: str,
        body: BriefingBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        sc = svc.store.get_scene(scene_id)
        if not sc or sc["worldId"] != world_id:
            raise HTTPException(404, "scene not found")
        try:
            out = set_briefing_fixture(
                svc.store,
                svc.memory,
                scene_id=scene_id,
                fixture_key=body.fixtureKey,
                text=body.text,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "scene.changed", {"sceneId": scene_id, "briefing": body.fixtureKey})
        return out

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
        now = ISO()
        job = None
        if body.scope == "phone":
            if not body.channelId:
                raise HTTPException(400, "channelId required for phone scope")
            ch = svc.phone.get(body.channelId)
            if not ch or ch["worldId"] != world_id:
                raise HTTPException(404, "phone channel not found")
            msg_id, mirror_ids = svc.phone.insert_phone_line(
                world_id=world_id,
                speaker_scene_id=scene_id,
                channel_id=body.channelId,
                text=body.text,
                created_at=now,
            )
            _emit(
                svc,
                world_id,
                "channel.message",
                {"channelId": body.channelId, "messageId": msg_id, "mirrors": mirror_ids},
            )
            if body.asPersona:
                job = await svc.orchestrator.on_phone_persona_message(
                    world_id, body.channelId, scene_id, msg_id
                )
            return {"messageId": msg_id, "generationJob": job, "mirrorIds": mirror_ids}

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
                "createdAt": now,
            }
        )
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

    @app.get(
        "/api/v1/worlds/{world_id}/observer/digest",
        dependencies=[Depends(verify_auth)],
    )
    def observer_digest(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        """CC-6 / OBS-6: pending signals and channel summary for Observer Studio."""
        world = svc.store.get_world(world_id)
        if not world:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "not_found", "message": "World not found"}},
            )
        scenes_out: list[dict] = []
        for s in svc.store.list_scenes(world_id):
            try:
                present = json.loads(s.get("presentJson") or "[]")
            except json.JSONDecodeError:
                present = []
            scenes_out.append(
                {
                    "sceneId": s["sceneId"],
                    "locationName": s.get("locationName", ""),
                    "presentCharacterIds": present,
                    "presentCount": len(present),
                }
            )
        pending = svc.store.list_signals(world_id, status="pending")
        channels = svc.phone.list_active(world_id)
        from altrasia.commissions import list_commissions

        commissions = [
            c
            for c in list_commissions(svc.store, world_id)
            if c["status"] not in ("done", "failed")
        ]
        from altrasia.debate_activity import parse_activity

        debates = []
        for s in svc.store.list_scenes(world_id):
            act = parse_activity(s)
            if act:
                debates.append(
                    {
                        "sceneId": s["sceneId"],
                        "locationName": s.get("locationName", ""),
                        "phase": act.get("phase"),
                        "speakingOrder": act.get("speakingOrder", []),
                    }
                )
        pending_approvals = list_approvals(svc.store, world_id, state="pending")
        return {
            "worldId": world_id,
            "worldName": world.get("name"),
            "activeSceneId": world["activeSceneId"],
            "paused": world_id in svc.paused_worlds,
            "scenes": scenes_out,
            "pendingSignals": pending,
            "activeChannels": channels,
            "commissions": commissions,
            "debates": debates,
            "pendingApprovals": pending_approvals,
            "summary": (
                f"{len(pending)} pending signal(s); "
                f"{len(channels)} active phone channel(s); "
                f"{len(commissions)} open commission(s); "
                f"{len(debates)} active debate(s); "
                f"{len(pending_approvals)} pending approval(s)"
            ),
        }

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
    async def presence_join(
        world_id: str, scene_id: str, body: PresenceBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        svc.presence.join(scene_id, body.characterId)
        _emit(
            svc,
            world_id,
            "presence.changed",
            {"sceneId": scene_id, "characterId": body.characterId, "action": "join"},
        )
        await refresh_commissions(svc, world_id)
        return {"ok": True}

    @app.post(
        "/api/v1/worlds/{world_id}/presence/summon",
        dependencies=[Depends(verify_auth)],
    )
    async def presence_summon(
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
        await refresh_commissions(svc, world_id)
        return {"ok": True, "targetSceneId": body.targetSceneId}

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/presence/leave",
        dependencies=[Depends(verify_auth)],
    )
    async def presence_leave(
        world_id: str, scene_id: str, body: PresenceBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        svc.presence.leave(scene_id, body.characterId)
        await refresh_commissions(svc, world_id)
        return {"ok": True}

    @app.post(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/exits/{exit_id}/state",
        dependencies=[Depends(verify_auth)],
    )
    async def set_exit_state(
        world_id: str,
        scene_id: str,
        exit_id: str,
        body: ExitStateBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        from altrasia.tools.registry import ToolContext

        ctx = ToolContext(
            world_id=world_id,
            scene_id=scene_id,
            character_id="__observer__",
            services=svc,
        )
        raw = await svc.tools.invoke(
            "scene_exit_set_state",
            {"exitId": exit_id, "doorState": body.doorState},
            ctx,
        )
        return json.loads(raw)

    @app.get("/api/v1/worlds/{world_id}/roster", dependencies=[Depends(verify_auth)])
    def roster(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        return svc.presence.roster(world_id)

    @app.get("/api/v1/worlds/{world_id}/spatial-graph", dependencies=[Depends(verify_auth)])
    def spatial_graph(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        return build_spatial_graph(svc.store, world_id)

    @app.get("/api/v1/worlds/{world_id}/navigation/summary", dependencies=[Depends(verify_auth)])
    def navigation_summary_route(
        world_id: str,
        fromSceneId: str | None = None,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        try:
            return navigation_summary(svc.store, world_id, fromSceneId)
        except ValueError as e:
            raise HTTPException(404, str(e)) from e

    @app.get("/api/v1/worlds/{world_id}/navigation/route", dependencies=[Depends(verify_auth)])
    def navigation_route(
        world_id: str,
        fromSceneId: str,
        toSceneId: str,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        graph = build_spatial_graph(svc.store, world_id)
        return plan_route(graph, fromSceneId, toSceneId)

    @app.post("/api/v1/worlds/{world_id}/navigation/travel", dependencies=[Depends(verify_auth)])
    def navigation_travel(
        world_id: str,
        body: NavigationTravelBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        try:
            result = execute_travel(
                svc.store,
                world_id,
                from_scene_id=body.fromSceneId,
                to_scene_id=body.toSceneId,
                mode=body.mode,
            )
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        _emit(svc, world_id, "scene.changed", {"activeSceneId": result["activeSceneId"]})
        return result

    @app.get("/api/v1/worlds/{world_id}/map-artifacts/site", dependencies=[Depends(verify_auth)])
    def map_site_artifact(world_id: str, svc: AppServices = Depends(get_services)) -> dict:
        from altrasia.map_artifacts import get_world_site_artifact

        art = get_world_site_artifact(svc.store, world_id)
        return {"artifact": art}

    @app.get(
        "/api/v1/worlds/{world_id}/scenes/{scene_id}/map-artifact",
        dependencies=[Depends(verify_auth)],
    )
    def map_scene_artifact(
        world_id: str, scene_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        from altrasia.map_artifacts import get_scene_artifact

        art = get_scene_artifact(svc.store, world_id, scene_id)
        return {"artifact": art}

    def _channel_payload(ch: dict) -> dict:
        return {
            "channelId": ch["channelId"],
            "worldId": ch["worldId"],
            "active": bool(ch.get("active")),
            "participants": json.loads(ch.get("participantsJson") or "[]"),
            "endpoints": json.loads(ch.get("endpointsJson") or "[]"),
        }

    @app.get("/api/v1/worlds/{world_id}/channels", dependencies=[Depends(verify_auth)])
    def list_channels(world_id: str, svc: AppServices = Depends(get_services)) -> list[dict]:
        return [_channel_payload(c) for c in svc.phone.list_active(world_id)]

    @app.post("/api/v1/worlds/{world_id}/channels", dependencies=[Depends(verify_auth)])
    def create_phone_channel(
        world_id: str, body: CreatePhoneChannelBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        ch = svc.phone.create_channel(
            world_id=world_id,
            scene_a=body.sceneIdA,
            character_a=body.characterIdA,
            scene_b=body.sceneIdB,
            character_b=body.characterIdB,
        )
        _emit(svc, world_id, "channel.created", {"channelId": ch["channelId"]})
        return _channel_payload(ch)

    @app.patch(
        "/api/v1/worlds/{world_id}/channels/{channel_id}/endpoints/{scene_id}",
        dependencies=[Depends(verify_auth)],
    )
    def patch_speakerphone(
        world_id: str,
        channel_id: str,
        scene_id: str,
        body: SpeakerphonePatch,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        ch = svc.phone.get(channel_id)
        if not ch or ch["worldId"] != world_id:
            raise HTTPException(404, "channel not found")
        updated = svc.phone.set_speakerphone(channel_id, scene_id, body.speakerphone)
        _emit(
            svc,
            world_id,
            "channel.updated",
            {"channelId": channel_id, "sceneId": scene_id},
        )
        return _channel_payload(updated)

    @app.post(
        "/api/v1/worlds/{world_id}/channels/{channel_id}/end",
        dependencies=[Depends(verify_auth)],
    )
    def end_phone_channel(
        world_id: str, channel_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        ch = svc.phone.get(channel_id)
        if not ch or ch["worldId"] != world_id:
            raise HTTPException(404, "channel not found")
        svc.phone.end_channel(channel_id)
        _emit(svc, world_id, "channel.ended", {"channelId": channel_id})
        return {"channelId": channel_id, "active": False}

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

    @app.post(
        "/api/v1/worlds/{world_id}/signals/{signal_id}/answer",
        dependencies=[Depends(verify_auth)],
    )
    async def answer_signal(
        world_id: str,
        signal_id: str,
        body: SignalAnswerBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        sig = svc.store.get_signal(signal_id)
        if not sig or sig["worldId"] != world_id:
            raise HTTPException(404, "signal not found")
        svc.store.update_signal(signal_id, status="acknowledged")
        scene_id = body.targetSceneId or sig["targetSceneId"]
        job = await svc.orchestrator.on_knock_answered(
            world_id, scene_id, body.characterId, signal_id
        )
        _emit(
            svc,
            world_id,
            "signal.updated",
            {"signalId": signal_id, "status": "acknowledged"},
        )
        return {"signalId": signal_id, "status": "acknowledged", "generationJob": job}

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

    @app.post("/api/v1/characters/draft", dependencies=[Depends(verify_auth)])
    async def post_character_draft(
        body: CharacterDraftCreateBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        if not body.brief.strip():
            raise HTTPException(400, "brief is required")
        try:
            return await create_character_draft(svc, body.brief.strip())
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.get(
        "/api/v1/characters/draft/{draft_id}",
        dependencies=[Depends(verify_auth)],
    )
    def get_character_draft_route(
        draft_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        row = get_character_draft(svc, draft_id)
        if not row:
            raise HTTPException(404, "draft not found")
        return row

    @app.delete(
        "/api/v1/characters/draft/{draft_id}",
        dependencies=[Depends(verify_auth)],
    )
    def delete_character_draft_route(
        draft_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        if not discard_character_draft(svc, draft_id):
            raise HTTPException(404, "draft not found or already approved")
        return {"draftId": draft_id, "status": "discarded"}

    @app.post("/api/v1/characters", dependencies=[Depends(verify_auth)])
    def post_character_from_draft(
        body: CharacterApproveBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        try:
            return approve_character_draft(
                svc,
                body.draftId,
                definition_override=body.definitionJson,
                display_name=body.displayName,
                world_id=body.worldId,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/layout-bootstrap-drafts",
        dependencies=[Depends(verify_auth)],
    )
    async def post_world_bootstrap_draft(
        world_id: str,
        body: WorldBootstrapCreateBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        from altrasia.map_world_bootstrap import create_world_bootstrap_draft

        if not body.description.strip():
            raise HTTPException(400, "description is required")
        try:
            return await create_world_bootstrap_draft(
                svc,
                world_id,
                body.description.strip(),
                connect_from_scene_id=body.connectFromSceneId,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/layout-drafts",
        dependencies=[Depends(verify_auth)],
    )
    async def post_layout_draft(
        world_id: str,
        body: LayoutDraftCreateBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        if not body.brief.strip():
            raise HTTPException(400, "brief is required")
        try:
            return await create_layout_draft(
                svc, world_id, body.brief.strip(), scope=body.scope
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/layout-drafts/unified",
        dependencies=[Depends(verify_auth)],
    )
    async def post_unified_layout_draft(
        world_id: str,
        body: UnifiedLayoutDraftBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        from altrasia.map_authoring import create_unified_layout_draft

        if not body.brief.strip():
            raise HTTPException(400, "brief is required")
        try:
            return await create_unified_layout_draft(svc, world_id, body.brief.strip())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/layout-patch",
        dependencies=[Depends(verify_auth)],
    )
    def post_layout_patch(
        world_id: str,
        body: LayoutPatchBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        from altrasia.map_authoring import patch_layout_safe

        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        patch: dict = {}
        if body.nodes:
            patch["nodes"] = body.nodes
        if body.edges:
            patch["edges"] = body.edges
        if not patch:
            raise HTTPException(400, "nodes or edges required")
        result = patch_layout_safe(svc, world_id, patch)
        build_spatial_graph(svc.store, world_id)
        return result

    @app.get(
        "/api/v1/worlds/{world_id}/layout-drafts/{draft_id}",
        dependencies=[Depends(verify_auth)],
    )
    def get_layout_draft_route(
        world_id: str, draft_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        row = get_layout_draft(svc, draft_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "draft not found")
        return row

    @app.post(
        "/api/v1/worlds/{world_id}/layout-drafts/{draft_id}/commit",
        dependencies=[Depends(verify_auth)],
    )
    def post_layout_draft_commit(
        world_id: str, draft_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        row = get_layout_draft(svc, draft_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "draft not found")
        try:
            result = commit_layout_draft(svc, draft_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "scene.changed", {"layoutDraftId": draft_id})
        return result

    @app.post(
        "/api/v1/worlds/{world_id}/layout-drafts/{draft_id}/repair",
        dependencies=[Depends(verify_auth)],
    )
    async def post_layout_draft_repair(
        world_id: str,
        draft_id: str,
        body: dict,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        row = get_layout_draft(svc, draft_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "draft not found")
        feedback = (body.get("feedback") or body.get("brief") or "").strip()
        if not feedback:
            raise HTTPException(400, "feedback is required")
        try:
            return await repair_layout_draft(
                svc, draft_id, feedback, mode=body.get("mode", "describe-change")
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.patch(
        "/api/v1/worlds/{world_id}/layout-drafts/{draft_id}",
        dependencies=[Depends(verify_auth)],
    )
    def patch_layout_draft_route(
        world_id: str,
        draft_id: str,
        body: dict,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        row = get_layout_draft(svc, draft_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "draft not found")
        proposed = body.get("proposed")
        if not isinstance(proposed, dict):
            raise HTTPException(400, "proposed object required")
        try:
            return update_draft_proposed(svc, draft_id, proposed)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get(
        "/api/v1/worlds/{world_id}/commissions",
        dependencies=[Depends(verify_auth)],
    )
    def get_commissions(world_id: str, svc: AppServices = Depends(get_services)) -> list[dict]:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        return list_commissions(svc.store, world_id)

    @app.post(
        "/api/v1/worlds/{world_id}/commissions",
        dependencies=[Depends(verify_auth)],
    )
    async def post_commission(
        world_id: str, body: CreateCommissionBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        try:
            com = create_commission(
                svc.store,
                world_id,
                assignee_character_id=body.assigneeCharacterId,
                target_scene_id=body.targetSceneId,
                brief=body.brief.strip(),
                deliverable_policy=body.deliverablePolicy,
                allowed_tools=body.allowedTools,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        commission_id = com["commissionId"]
        await refresh_commissions(svc, world_id)
        for row in list_commissions(svc.store, world_id):
            if row["commissionId"] == commission_id:
                return row
        return com

    @app.post(
        "/api/v1/worlds/{world_id}/commissions/{commission_id}/start",
        dependencies=[Depends(verify_auth)],
    )
    async def post_commission_start(
        world_id: str, commission_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        row = svc.store.get_commission(commission_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "commission not found")
        try:
            return await run_start_commission(svc, commission_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.patch(
        "/api/v1/worlds/{world_id}/commissions/{commission_id}",
        dependencies=[Depends(verify_auth)],
    )
    def patch_commission_route(
        world_id: str,
        commission_id: str,
        body: PatchCommissionBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        row = svc.store.get_commission(commission_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "commission not found")
        try:
            com = patch_commission(
                svc.store,
                commission_id,
                status=body.status,
                deliverable_locus_keys=body.deliverableLocusKeys,
                force_complete_reason=body.forceCompleteReason,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "commission.updated", {"commissionId": commission_id})
        return com

    @app.post(
        "/api/v1/worlds/{world_id}/commissions/{commission_id}/force-complete",
        dependencies=[Depends(verify_auth)],
    )
    def post_commission_force_complete(
        world_id: str,
        commission_id: str,
        body: ForceCompleteBody,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        row = svc.store.get_commission(commission_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "commission not found")
        reason = body.reason.strip()
        if not reason:
            raise HTTPException(400, "reason required")
        try:
            com = patch_commission(
                svc.store,
                commission_id,
                status="done",
                force_complete_reason=reason,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "commission.updated", {"commissionId": commission_id})
        return com

    @app.get(
        "/api/v1/worlds/{world_id}/commons",
        dependencies=[Depends(verify_auth)],
    )
    def get_world_commons(world_id: str, svc: AppServices = Depends(get_services)) -> list[dict]:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        return list_commons(svc.store, world_id)

    @app.put(
        "/api/v1/worlds/{world_id}/commons",
        dependencies=[Depends(verify_auth)],
    )
    def put_world_commons(
        world_id: str, body: CommonsBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        try:
            return set_commons(svc.memory, svc.store, world_id, key=body.key, text=body.text)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post(
        "/api/v1/worlds/{world_id}/members",
        dependencies=[Depends(verify_auth)],
    )
    def add_world_member(
        world_id: str, body: WorldMemberBody, svc: AppServices = Depends(get_services)
    ) -> dict:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        if not svc.store.get_character(body.characterId):
            raise HTTPException(404, "character not found")
        svc.store.add_world_member(world_id, body.characterId)
        return {"worldId": world_id, "characterId": body.characterId}

    @app.get("/api/v1/operator/settings", dependencies=[Depends(verify_auth)])
    def get_operator_settings(svc: AppServices = Depends(get_services)) -> dict:
        return svc.operator_settings.load().to_api(svc.settings)

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
        if body.enableServerPlugins is not None:
            updates["enableServerPlugins"] = body.enableServerPlugins
        if body.inference is not None:
            inf: dict[str, Any] = {}
            if body.inference.primaryBaseUrl is not None:
                inf["primaryBaseUrl"] = body.inference.primaryBaseUrl
            if body.inference.primaryModel is not None:
                inf["primaryModel"] = body.inference.primaryModel
            if body.inference.embeddingBaseUrl is not None:
                inf["embeddingBaseUrl"] = body.inference.embeddingBaseUrl
            if body.inference.embeddingModel is not None:
                inf["embeddingModel"] = body.inference.embeddingModel
            updates["inference"] = inf
        patched = svc.operator_settings.patch(updates)
        svc.apply_inference_config()
        return patched.to_api(svc.settings)

    @app.get("/api/v1/operator/inference/models", dependencies=[Depends(verify_auth)])
    async def list_inference_models(
        target: str,
        baseUrl: str | None = None,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        from altrasia.inference.model_catalog import list_openai_models
        from altrasia.operator_settings import resolve_inference

        if target not in ("primary", "embedding"):
            raise HTTPException(400, "target must be primary or embedding")
        eff = resolve_inference(svc.settings, svc.operator_settings.load())
        url = (baseUrl or "").strip() or (
            eff["primaryBaseUrl"] if target == "primary" else eff["embeddingBaseUrl"]
        )
        result = await list_openai_models(url)
        return {"target": target, "baseUrl": url, **result}

    @app.post(
        "/api/v1/worlds/{world_id}/characters/{character_id}/portrait/generate",
        dependencies=[Depends(verify_auth)],
    )
    async def post_portrait_generate(
        world_id: str,
        character_id: str,
        svc: AppServices = Depends(get_services),
    ) -> dict:
        from altrasia.inference.comfyui import generate_portrait

        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        ch = svc.store.get_character(character_id)
        if not ch:
            raise HTTPException(404, "character not found")
        prompt = f"Portrait of {ch.get('displayName', character_id)}, character study"
        return await generate_portrait(svc, character_id=character_id, prompt=prompt)

    @app.get("/api/v1/worlds/{world_id}/approvals", dependencies=[Depends(verify_auth)])
    def get_approvals(
        world_id: str,
        state: str | None = "pending",
        svc: AppServices = Depends(get_services),
    ) -> list[dict]:
        if not svc.store.get_world(world_id):
            raise HTTPException(404, "world not found")
        return list_approvals(svc.store, world_id, state=state)

    @app.post(
        "/api/v1/worlds/{world_id}/approvals/{approval_id}/approve",
        dependencies=[Depends(verify_auth)],
    )
    def post_approval_approve(
        world_id: str, approval_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        row = svc.store.get_approval(approval_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "approval not found")
        try:
            out = resolve_approval(svc.store, approval_id, approve=True)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        from altrasia.approvals import mark_approval_applied

        mark_approval_applied(svc.store, approval_id)
        _emit(svc, world_id, "approval.updated", {"approvalId": approval_id, "state": "applied"})
        return out

    @app.post(
        "/api/v1/worlds/{world_id}/approvals/{approval_id}/deny",
        dependencies=[Depends(verify_auth)],
    )
    def post_approval_deny(
        world_id: str, approval_id: str, svc: AppServices = Depends(get_services)
    ) -> dict:
        row = svc.store.get_approval(approval_id)
        if not row or row["worldId"] != world_id:
            raise HTTPException(404, "approval not found")
        try:
            out = resolve_approval(svc.store, approval_id, approve=False)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        _emit(svc, world_id, "approval.updated", {"approvalId": approval_id, "state": "denied"})
        return out

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
        from altrasia.operator_settings import resolve_inference

        eff = resolve_inference(svc.settings, svc.operator_settings.load())
        return {
            "mock": eff["mockLlm"],
            "baseUrl": eff["primaryBaseUrl"],
            "model": eff["primaryModel"],
            "embeddingBaseUrl": eff["embeddingBaseUrl"],
            "embeddingModel": eff["embeddingModel"],
        }

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
        if not layout_design_mode(svc.store, world_id):
            raise HTTPException(403, "geography locked — cannot delete scenes (MAP-AUTH-LOCK-2)")
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
