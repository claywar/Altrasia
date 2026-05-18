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
class OperatorSettings:
    heartbeat: HeartbeatConfig
    enableServerPlugins: bool = False
    lastHeartbeatAt: str | None = None
    inference: InferenceConfig | None = None

    def to_api(self, env: "Settings | None" = None) -> dict[str, Any]:
        inf = (self.inference or InferenceConfig()).normalized()
        payload: dict[str, Any] = {
            "heartbeat": asdict(self.heartbeat.normalized()),
            "enableServerPlugins": self.enableServerPlugins,
            "lastHeartbeatAt": self.lastHeartbeatAt,
            "inference": asdict(inf),
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
            }
        return payload


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
            return OperatorSettings(heartbeat=HeartbeatConfig(), inference=InferenceConfig())
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        hb = raw.get("heartbeat") or {}
        inf_raw = raw.get("inference") or {}
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
        )

    def save(self, settings: OperatorSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        inf = (settings.inference or InferenceConfig()).normalized()
        payload = {
            "heartbeat": asdict(settings.heartbeat.normalized()),
            "enableServerPlugins": settings.enableServerPlugins,
            "lastHeartbeatAt": settings.lastHeartbeatAt,
            "inference": asdict(inf),
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
        self.save(current)
        return current

    def load_plugins_enabled(self, settings: Any) -> bool:
        return self.load().enableServerPlugins

    def record_heartbeat(self) -> str:
        current = self.load()
        current.lastHeartbeatAt = datetime.now(timezone.utc).isoformat()
        self.save(current)
        return current.lastHeartbeatAt
