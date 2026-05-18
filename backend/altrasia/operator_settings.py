from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

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
class OperatorSettings:
    heartbeat: HeartbeatConfig
    enableServerPlugins: bool = False
    lastHeartbeatAt: str | None = None

    def to_api(self) -> dict[str, Any]:
        return {
            "heartbeat": asdict(self.heartbeat.normalized()),
            "enableServerPlugins": self.enableServerPlugins,
            "lastHeartbeatAt": self.lastHeartbeatAt,
        }


class OperatorSettingsStore:
    """Global operator settings (HB-3) — persisted under data_dir/config.yaml."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> OperatorSettings:
        if not self.path.exists():
            return OperatorSettings(heartbeat=HeartbeatConfig())
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        hb = raw.get("heartbeat") or {}
        return OperatorSettings(
            heartbeat=HeartbeatConfig(
                enabled=bool(hb.get("enabled", False)),
                intervalSeconds=int(hb.get("intervalSeconds", 60)),
            ),
            enableServerPlugins=bool(raw.get("enableServerPlugins", False)),
            lastHeartbeatAt=raw.get("lastHeartbeatAt"),
        )

    def save(self, settings: OperatorSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "heartbeat": asdict(settings.heartbeat.normalized()),
            "enableServerPlugins": settings.enableServerPlugins,
            "lastHeartbeatAt": settings.lastHeartbeatAt,
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
        self.save(current)
        return current

    def load_plugins_enabled(self, settings: Any) -> bool:
        return self.load().enableServerPlugins

    def record_heartbeat(self) -> str:
        current = self.load()
        current.lastHeartbeatAt = datetime.now(timezone.utc).isoformat()
        self.save(current)
        return current.lastHeartbeatAt
