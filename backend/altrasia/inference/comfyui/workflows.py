from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from altrasia.inference.comfyui.profiles import ImageProfile, WORKFLOW_IDS

_REPO_ROOT = Path(__file__).resolve().parents[4]
_WORKFLOWS_DIR = _REPO_ROOT / "data" / "workflows"

ALLOWED_WORKFLOW_IDS = frozenset(WORKFLOW_IDS)


def workflow_api_path(workflow_id: str, family: str) -> Path:
    if workflow_id not in ALLOWED_WORKFLOW_IDS:
        raise ValueError(f"unknown workflowId: {workflow_id}")
    return _WORKFLOWS_DIR / workflow_id / f"{family}.api.json"


def load_workflow_file(workflow_id: str, family: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = workflow_api_path(workflow_id, family)
    if not path.is_file():
        raise FileNotFoundError(f"workflow not found: {workflow_id}/{family}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = dict(raw.get("_altrasia") or {})
    prompt = {k: v for k, v in raw.items() if k != "_altrasia"}
    return meta, prompt


def _set_node_input(prompt: dict[str, Any], node_id: str, key: str, value: Any) -> None:
    node = prompt.get(node_id)
    if not node or not isinstance(node, dict):
        return
    inputs = node.setdefault("inputs", {})
    inputs[key] = value


def inject_workflow(
    prompt: dict[str, Any],
    meta: dict[str, Any],
    profile: ImageProfile,
    *,
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality",
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    out = copy.deepcopy(prompt)
    inject = meta.get("inject") or {}
    defaults = {**dict(meta.get("defaults") or {}), **profile.defaults}

    if inject.get("promptNode"):
        _set_node_input(out, str(inject["promptNode"]), "text", positive_prompt[:2000])
    if inject.get("negativePromptNode"):
        _set_node_input(out, str(inject["negativePromptNode"]), "text", negative_prompt[:500])
    if inject.get("seedNode") and seed is not None:
        _set_node_input(out, str(inject["seedNode"]), "seed", int(seed))
    if inject.get("latentNode"):
        w = width or int(defaults.get("width") or 1024)
        h = height or int(defaults.get("height") or 1024)
        _set_node_input(out, str(inject["latentNode"]), "width", w)
        _set_node_input(out, str(inject["latentNode"]), "height", h)
    if inject.get("seedNode"):
        steps = int(defaults.get("steps") or 20)
        cfg = float(defaults.get("cfg") or 7.0)
        _set_node_input(out, str(inject["seedNode"]), "steps", steps)
        _set_node_input(out, str(inject["seedNode"]), "cfg", cfg)

    family = profile.family
    comfy = profile.comfy
    if family == "sdxl" and inject.get("checkpointNode") and comfy.get("checkpoint"):
        _set_node_input(out, str(inject["checkpointNode"]), "ckpt_name", comfy["checkpoint"])
    elif family == "flux":
        if inject.get("unetNode") and comfy.get("unet"):
            _set_node_input(out, str(inject["unetNode"]), "unet_name", comfy["unet"])
        if inject.get("clipNode") and comfy.get("clip_l"):
            _set_node_input(out, str(inject["clipNode"]), "clip_name1", comfy["clip_l"])
            if comfy.get("clip_t5"):
                _set_node_input(out, str(inject["clipNode"]), "clip_name2", comfy["clip_t5"])
        if inject.get("vaeNode") and comfy.get("vae"):
            _set_node_input(out, str(inject["vaeNode"]), "vae_name", comfy["vae"])
    elif family == "z_image_turbo":
        if inject.get("diffusionModelNode") and comfy.get("diffusionModel"):
            _set_node_input(
                out, str(inject["diffusionModelNode"]), "unet_name", comfy["diffusionModel"]
            )
        if inject.get("textEncoderNode") and comfy.get("textEncoder"):
            _set_node_input(out, str(inject["textEncoderNode"]), "clip_name", comfy["textEncoder"])
        if inject.get("vaeNode") and comfy.get("vae"):
            _set_node_input(out, str(inject["vaeNode"]), "vae_name", comfy["vae"])

    return out


def build_prompt_for_profile(
    workflow_id: str,
    profile: ImageProfile,
    *,
    positive_prompt: str,
    negative_prompt: str = "blurry, low quality",
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    meta, prompt = load_workflow_file(workflow_id, profile.family)
    injected = inject_workflow(
        prompt,
        meta,
        profile,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        width=width,
        height=height,
    )
    return meta, injected
