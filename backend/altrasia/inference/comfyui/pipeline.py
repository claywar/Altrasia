from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from altrasia.inference.comfyui.client import ComfyUiClient
from altrasia.inference.comfyui.profiles import (
    ImageConfig,
    ImageProfile,
    ImageProfileRegistry,
    resolve_comfy_url,
    resolve_image_profile_id,
)
from altrasia.inference.comfyui.workflows import build_prompt_for_profile
from altrasia.memory.strip_reasoning import strip_reasoning
from altrasia.world_config import get_world_config

log = logging.getLogger(__name__)

WORKFLOW_IDS = frozenset(
    {"character_portrait", "scene_establishing", "fixture_icon", "map_thumbnail"}
)


def _operator_image_config(services: Any) -> ImageConfig:
    from altrasia.operator_settings import get_image_config

    return get_image_config(services.operator_settings.load())


def _profile_registry(services: Any) -> ImageProfileRegistry:
    return ImageProfileRegistry(services.settings.data_dir)


def resolve_profile_for_request(
    services: Any,
    *,
    world_id: str,
    workflow_id: str,
    model_profile_id: str | None = None,
    reference_asset_id: str | None = None,
) -> ImageProfile:
    if workflow_id not in WORKFLOW_IDS:
        raise ValueError(f"workflow denylist: {workflow_id}")
    wc = get_world_config(services.store, world_id)
    op_cfg = _operator_image_config(services)
    pid = resolve_image_profile_id(
        workflow_id,
        request_profile_id=model_profile_id,
        image_config=op_cfg,
        world_config=wc,
    )
    reg = _profile_registry(services)
    profile = reg.get(pid)
    if not profile:
        raise ValueError(f"unknown modelProfileId: {pid}")
    if workflow_id not in profile.supported_workflows:
        raise ValueError(f"profile {pid} does not support workflow {workflow_id}")
    if reference_asset_id and not profile.capabilities.get("referenceImage"):
        raise ValueError("profile does not support referenceImage; use SDXL or FLUX")
    budget = op_cfg.memory_budget_gb
    if profile.peak_memory_gb > budget:
        log.warning(
            "image profile %s peakMemoryGb=%s exceeds budget %s",
            pid,
            profile.peak_memory_gb,
            budget,
        )
    return profile


def _assets_root(services: Any) -> Path:
    root = services.settings.data_dir / "assets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_media_asset(
    services: Any,
    *,
    world_id: str,
    png_bytes: bytes,
    workflow_id: str,
    model_profile_id: str,
    character_id: str | None = None,
    scene_id: str | None = None,
    source_job_id: str | None = None,
) -> dict[str, Any]:
    asset_id = str(uuid.uuid4())
    sha = hashlib.sha256(png_bytes).hexdigest()
    if character_id:
        rel_dir = Path(world_id) / "characters" / character_id
    elif scene_id:
        rel_dir = Path(world_id) / "scenes" / scene_id
    else:
        rel_dir = Path(world_id) / "media"
    dest_dir = _assets_root(services) / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{asset_id}.png"
    full_path = dest_dir / filename
    full_path.write_bytes(png_bytes)
    rel_path = (rel_dir / filename).as_posix()
    now = datetime.now(timezone.utc).isoformat()
    services.store.insert_media_asset(
        asset_id=asset_id,
        world_id=world_id,
        path=rel_path,
        sha256=sha,
        workflow_id=workflow_id,
        model_profile_id=model_profile_id,
        character_id=character_id,
        source_job_id=source_job_id,
        created_at=now,
    )
    return {
        "assetId": asset_id,
        "path": rel_path,
        "sha256": sha,
        "url": f"/api/v1/worlds/{world_id}/assets/{asset_id}",
    }


def write_image_locus(
    services: Any,
    *,
    locus_key: str,
    owner_id: str,
    caption: str,
    asset_id: str,
    pool: str = "world",
) -> None:
    cleaned = strip_reasoning(caption)
    payload = json.dumps({"assetId": asset_id, "caption": cleaned[:2000]})
    services.memory.memory_store(pool=pool, owner_id=owner_id, locus_key=locus_key, value=payload)


async def run_image_workflow(
    services: Any,
    *,
    world_id: str,
    workflow_id: str,
    prompt: str,
    model_profile_id: str | None = None,
    reference_asset_id: str | None = None,
    job_id: str | None = None,
    negative_prompt: str = "blurry, low quality",
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    op_cfg = _operator_image_config(services)
    base = resolve_comfy_url(services.settings.comfy_url, op_cfg)
    if not base:
        return {
            "ok": True,
            "mock": True,
            "message": "ComfyUI not configured — gray placeholder only",
        }

    profile = resolve_profile_for_request(
        services,
        world_id=world_id,
        workflow_id=workflow_id,
        model_profile_id=model_profile_id,
        reference_asset_id=reference_asset_id,
    )
    jid = job_id or str(uuid.uuid4())
    services.gpu_queue.set_image_job_meta(
        {
            "workflowId": workflow_id,
            "modelProfileId": profile.profile_id,
            "peakMemoryGb": profile.peak_memory_gb,
        }
    )

    async def work() -> dict[str, Any]:
        client = ComfyUiClient(base)
        _, comfy_prompt = build_prompt_for_profile(
            workflow_id,
            profile,
            positive_prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=width,
            height=height,
        )
        png = await client.run_prompt_to_image(comfy_prompt)
        await client.free_memory()
        return {"png": png, "profileId": profile.profile_id}

    try:
        result = await services.gpu_queue.run(jid, "image", work)
        return {
            "ok": True,
            "mock": False,
            "jobId": jid,
            "workflowId": workflow_id,
            "modelProfileId": result["profileId"],
            "png": result["png"],
        }
    except Exception as exc:
        log.warning("image workflow failed: %s", exc)
        comfy = ComfyUiClient(base)
        await comfy.free_memory()
        return {"ok": False, "error": str(exc), "jobId": jid}
    finally:
        services.gpu_queue.clear_image_job_meta()


async def generate_portrait(
    services: Any,
    *,
    world_id: str,
    character_id: str,
    prompt: str,
    job_id: str | None = None,
    model_profile_id: str | None = None,
    reference_asset_id: str | None = None,
) -> dict[str, Any]:
    gen = await run_image_workflow(
        services,
        world_id=world_id,
        workflow_id="character_portrait",
        prompt=prompt,
        model_profile_id=model_profile_id,
        reference_asset_id=reference_asset_id,
        job_id=job_id,
    )
    if gen.get("mock"):
        return {
            "ok": True,
            "mock": True,
            "portraitUrl": None,
            "message": gen.get("message"),
        }
    if not gen.get("ok"):
        return gen
    asset = save_media_asset(
        services,
        world_id=world_id,
        png_bytes=gen["png"],
        workflow_id="character_portrait",
        model_profile_id=gen["modelProfileId"],
        character_id=character_id,
        source_job_id=gen.get("jobId"),
    )
    write_image_locus(
        services,
        locus_key=f"character:{character_id}:portrait",
        owner_id=world_id,
        caption=prompt,
        asset_id=asset["assetId"],
        pool="world",
    )
    return {
        "ok": True,
        "mock": False,
        "assetId": asset["assetId"],
        "portraitUrl": asset["url"],
        "url": asset["url"],
        "modelProfileId": gen["modelProfileId"],
    }


async def comfy_health(services: Any) -> dict[str, Any]:
    op_cfg = _operator_image_config(services)
    base = resolve_comfy_url(services.settings.comfy_url, op_cfg)
    if not base:
        return {"ok": False, "mock": True, "reachable": False, "message": "ComfyUI URL not set"}
    client = ComfyUiClient(base)
    result = await client.health_check()
    result["mock"] = False
    return result
