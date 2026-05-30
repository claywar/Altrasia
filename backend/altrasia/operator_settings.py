from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from altrasia.config import Settings

import yaml


@dataclass
class HeartbeatConfig:
    enabled: bool = False
    intervalSeconds: int = 60

    def normalized(self) -> "HeartbeatConfig":
        return HeartbeatConfig(
            enabled=self.enabled,
            intervalSeconds=max(5, int(self.intervalSeconds)),
        )


@dataclass
class InferenceConfig:
    """Operator overrides for primary chat and embedding endpoints (persisted in config.yaml)."""

    primaryBaseUrl: str = ""
    primaryModel: str = ""
    embeddingBaseUrl: str = ""
    embeddingModel: str = ""

    def normalized(self) -> "InferenceConfig":
        return InferenceConfig(
            primaryBaseUrl=self.primaryBaseUrl.strip(),
            primaryModel=self.primaryModel.strip(),
            embeddingBaseUrl=self.embeddingBaseUrl.strip(),
            embeddingModel=self.embeddingModel.strip(),
        )


@dataclass
class ImageSettings:
    """Operator ComfyUI / image profile defaults (persisted in config.yaml)."""

    comfyBaseUrl: str = ""
    memoryBudgetGb: int = 70
    defaultProfileId: str = "sdxl-default"
    workflowProfiles: dict[str, str] | None = None

    def normalized(self) -> "ImageSettings":
        wf: dict[str, str] = {}
        for k, v in (self.workflowProfiles or {}).items():
            if v:
                wf[str(k)] = str(v).strip()
        return ImageSettings(
            comfyBaseUrl=self.comfyBaseUrl.strip(),
            memoryBudgetGb=max(16, int(self.memoryBudgetGb or 70)),
            defaultProfileId=(self.defaultProfileId or "sdxl-default").strip(),
            workflowProfiles=wf,
        )


@dataclass
class OperatorSettings:
    heartbeat: HeartbeatConfig
    enableServerPlugins: bool = False
    lastHeartbeatAt: str | None = None
    inference: InferenceConfig | None = None
    image: ImageSettings | None = None

    def to_api(self, env: "Settings | None" = None) -> dict[str, Any]:
        inf = (self.inference or InferenceConfig()).normalized()
        img = (self.image or ImageSettings()).normalized()
        payload: dict[str, Any] = {
            "heartbeat": asdict(self.heartbeat.normalized()),
            "enableServerPlugins": self.enableServerPlugins,
            "lastHeartbeatAt": self.lastHeartbeatAt,
            "inference": asdict(inf),
            "image": {
                "comfyBaseUrl": img.comfyBaseUrl,
                "memoryBudgetGb": img.memoryBudgetGb,
                "defaultProfileId": img.defaultProfileId,
                "workflowProfiles": dict(img.workflowProfiles or {}),
            },
        }
        if env is not None:
            effective = resolve_inference(env, self)
            payload["inferenceEffective"] = effective
            payload["envDefaults"] = {
                "primaryBaseUrl": env.llm_base_url,
                "primaryModel": env.llm_model,
                "embeddingBaseUrl": env.embed_base_url,
                "embeddingModel": env.embed_model,
                "mockLlm": env.mock_llm,
                "comfyBaseUrl": env.comfy_url,
            }
            payload["imageEffective"] = resolve_image_effective(env, self)
        return payload


def get_image_config(op: OperatorSettings) -> "ImageConfig":
    from altrasia.inference.comfyui.profiles import ImageConfig

    img = (op.image or ImageSettings()).normalized()
    return ImageConfig(
        comfy_base_url=img.comfyBaseUrl,
        memory_budget_gb=img.memoryBudgetGb,
        default_profile_id=img.defaultProfileId,
        workflow_profiles=dict(img.workflowProfiles or {}),
    )


def resolve_image_effective(env: "Settings", op: OperatorSettings) -> dict[str, Any]:
    img = get_image_config(op)
    base = img.comfy_base_url or (env.comfy_url or "")
    return {
        "comfyBaseUrl": base.strip(),
        "memoryBudgetGb": img.memory_budget_gb,
        "defaultProfileId": img.default_profile_id,
        "workflowProfiles": dict(img.workflow_profiles),
    }


def resolve_inference(env: "Settings", op: OperatorSettings) -> dict[str, Any]:
    """Merge operator overrides with ALTRASIA_* environment defaults."""
    inf = (op.inference or InferenceConfig()).normalized()
    primary_base = inf.primaryBaseUrl or env.llm_base_url
    primary_model = inf.primaryModel or env.llm_model
    embed_base = inf.embeddingBaseUrl or env.embed_base_url
    embed_model = inf.embeddingModel or env.embed_model
    return {
        "primaryBaseUrl": primary_base,
        "primaryModel": primary_model,
        "embeddingBaseUrl": embed_base,
        "embeddingModel": embed_model,
        "mockLlm": bool(env.mock_llm and not primary_base),
    }


class OperatorSettingsStore:
    """Global operator settings (HB-3) — persisted under data_dir/config.yaml."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> OperatorSettings:
        if not self.path.exists():
            return OperatorSettings(
                heartbeat=HeartbeatConfig(),
                inference=InferenceConfig(),
                image=ImageSettings(),
            )
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        hb = raw.get("heartbeat") or {}
        inf_raw = raw.get("inference") or {}
        img_raw = raw.get("image") or {}
        wf_raw = img_raw.get("workflowProfiles") or {}
        return OperatorSettings(
            heartbeat=HeartbeatConfig(
                enabled=bool(hb.get("enabled", False)),
                intervalSeconds=int(hb.get("intervalSeconds", 60)),
            ),
            enableServerPlugins=bool(raw.get("enableServerPlugins", False)),
            lastHeartbeatAt=raw.get("lastHeartbeatAt"),
            inference=InferenceConfig(
                primaryBaseUrl=str(inf_raw.get("primaryBaseUrl") or ""),
                primaryModel=str(inf_raw.get("primaryModel") or ""),
                embeddingBaseUrl=str(inf_raw.get("embeddingBaseUrl") or ""),
                embeddingModel=str(inf_raw.get("embeddingModel") or ""),
            ),
            image=ImageSettings(
                comfyBaseUrl=str(img_raw.get("comfyBaseUrl") or ""),
                memoryBudgetGb=int(img_raw.get("memoryBudgetGb") or 70),
                defaultProfileId=str(img_raw.get("defaultProfileId") or "sdxl-default"),
                workflowProfiles={
                    str(k): str(v) for k, v in wf_raw.items() if v is not None
                },
            ),
        )

    def save(self, settings: OperatorSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        inf = (settings.inference or InferenceConfig()).normalized()
        img = (settings.image or ImageSettings()).normalized()
        payload = {
            "heartbeat": asdict(settings.heartbeat.normalized()),
            "enableServerPlugins": settings.enableServerPlugins,
            "lastHeartbeatAt": settings.lastHeartbeatAt,
            "inference": asdict(inf),
            "image": {
                "comfyBaseUrl": img.comfyBaseUrl,
                "memoryBudgetGb": img.memoryBudgetGb,
                "defaultProfileId": img.defaultProfileId,
                "workflowProfiles": dict(img.workflowProfiles or {}),
            },
        }
        self.path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def patch(self, updates: dict[str, Any]) -> OperatorSettings:
        current = self.load()
        if "heartbeat" in updates and isinstance(updates["heartbeat"], dict):
            hb = updates["heartbeat"]
            if "enabled" in hb:
                current.heartbeat.enabled = bool(hb["enabled"])
            if "intervalSeconds" in hb:
                current.heartbeat.intervalSeconds = int(hb["intervalSeconds"])
        if "enableServerPlugins" in updates:
            current.enableServerPlugins = bool(updates["enableServerPlugins"])
        if "inference" in updates and isinstance(updates["inference"], dict):
            if current.inference is None:
                current.inference = InferenceConfig()
            inf = updates["inference"]
            if "primaryBaseUrl" in inf:
                current.inference.primaryBaseUrl = str(inf["primaryBaseUrl"] or "")
            if "primaryModel" in inf:
                current.inference.primaryModel = str(inf["primaryModel"] or "")
            if "embeddingBaseUrl" in inf:
                current.inference.embeddingBaseUrl = str(inf["embeddingBaseUrl"] or "")
            if "embeddingModel" in inf:
                current.inference.embeddingModel = str(inf["embeddingModel"] or "")
        if "image" in updates and isinstance(updates["image"], dict):
            if current.image is None:
                current.image = ImageSettings()
            img = updates["image"]
            if "comfyBaseUrl" in img:
                current.image.comfyBaseUrl = str(img["comfyBaseUrl"] or "")
            if "memoryBudgetGb" in img:
                current.image.memoryBudgetGb = int(img["memoryBudgetGb"] or 70)
            if "defaultProfileId" in img:
                current.image.defaultProfileId = str(img["defaultProfileId"] or "sdxl-default")
            if "workflowProfiles" in img and isinstance(img["workflowProfiles"], dict):
                current.image.workflowProfiles = {
                    str(k): str(v) for k, v in img["workflowProfiles"].items() if v
                }
        self.save(current)
        return current

    def load_plugins_enabled(self, settings: Any) -> bool:
        return self.load().enableServerPlugins

    def record_heartbeat(self) -> str:
        current = self.load()
        current.lastHeartbeatAt = datetime.now(timezone.utc).isoformat()
        self.save(current)
        return current.lastHeartbeatAt
