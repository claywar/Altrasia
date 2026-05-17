from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from altrasia.config import Settings


def load_model_profile(settings: Settings, profile_id: str = "qwen3.6-35b-a3b") -> dict[str, Any]:
    path = settings.models_dir / f"{profile_id}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def quality_addendum(settings: Settings, profile_id: str = "qwen3.6-35b-a3b") -> str:
    """OQ-1: roleplay profile includes quality addendum when present."""
    profile = load_model_profile(settings, profile_id)
    return str(profile.get("qualityAddendum") or "").strip()
