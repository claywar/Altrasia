from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BUILTIN_PROFILES = _REPO_ROOT / "config" / "models" / "image"

WORKFLOW_IDS = (
    "character_portrait",
    "scene_establishing",
    "fixture_icon",
    "map_thumbnail",
)

_PROFILE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass
class ImageProfile:
    profile_id: str
    family: str
    display_name: str
    peak_memory_gb: float
    comfy: dict[str, str]
    defaults: dict[str, Any]
    capabilities: dict[str, bool]
    supported_workflows: list[str]
    builtin: bool = False
    source_path: Path | None = None

    def to_api(self) -> dict[str, Any]:
        return {
            "profileId": self.profile_id,
            "family": self.family,
            "displayName": self.display_name,
            "peakMemoryGb": self.peak_memory_gb,
            "comfy": dict(self.comfy),
            "defaults": dict(self.defaults),
            "capabilities": dict(self.capabilities),
            "supportedWorkflows": list(self.supported_workflows),
            "builtin": self.builtin,
        }


@dataclass
class ImageConfig:
    comfy_base_url: str = ""
    memory_budget_gb: int = 70
    default_profile_id: str = "sdxl-default"
    workflow_profiles: dict[str, str] = field(default_factory=dict)

    def normalized(self) -> "ImageConfig":
        wf: dict[str, str] = {}
        for k, v in (self.workflow_profiles or {}).items():
            if v:
                wf[str(k)] = str(v).strip()
        return ImageConfig(
            comfy_base_url=self.comfy_base_url.strip(),
            memory_budget_gb=max(16, int(self.memory_budget_gb or 70)),
            default_profile_id=(self.default_profile_id or "sdxl-default").strip(),
            workflow_profiles=wf,
        )


def user_profiles_dir(data_dir: Path) -> Path:
    return data_dir / "image-profiles"


def _parse_profile(raw: dict[str, Any], path: Path, *, builtin: bool) -> ImageProfile:
    profile_id = str(raw.get("profileId") or path.stem)
    return ImageProfile(
        profile_id=profile_id,
        family=str(raw.get("family") or "sdxl"),
        display_name=str(raw.get("displayName") or profile_id),
        peak_memory_gb=float(raw.get("peakMemoryGb") or 8),
        comfy={str(k): str(v) for k, v in (raw.get("comfy") or {}).items()},
        defaults=dict(raw.get("defaults") or {}),
        capabilities={
            "referenceImage": bool((raw.get("capabilities") or {}).get("referenceImage")),
        },
        supported_workflows=[str(w) for w in (raw.get("supportedWorkflows") or [])],
        builtin=builtin or bool(raw.get("builtin")),
        source_path=path,
    )


def load_profile_yaml(path: Path) -> ImageProfile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    builtin = path.parent == _BUILTIN_PROFILES or _BUILTIN_PROFILES in path.parents
    return _parse_profile(raw, path, builtin=builtin)


class ImageProfileRegistry:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._cache: dict[str, ImageProfile] | None = None

    def _load_all(self) -> dict[str, ImageProfile]:
        profiles: dict[str, ImageProfile] = {}
        if _BUILTIN_PROFILES.is_dir():
            for path in sorted(_BUILTIN_PROFILES.glob("*.yaml")):
                prof = load_profile_yaml(path)
                profiles[prof.profile_id] = prof
        user_dir = user_profiles_dir(self.data_dir)
        if user_dir.is_dir():
            for path in sorted(user_dir.glob("*.yaml")):
                prof = load_profile_yaml(path)
                profiles[prof.profile_id] = prof
        return profiles

    def list_profiles(self, *, refresh: bool = False) -> list[ImageProfile]:
        if refresh or self._cache is None:
            self._cache = self._load_all()
        return sorted(self._cache.values(), key=lambda p: p.profile_id)

    def get(self, profile_id: str) -> ImageProfile | None:
        if self._cache is None:
            self._cache = self._load_all()
        return self._cache.get(profile_id)

    def invalidate(self) -> None:
        self._cache = None

    def save_user_profile(self, data: dict[str, Any]) -> ImageProfile:
        profile_id = str(data.get("profileId") or "").strip()
        if not _PROFILE_ID_RE.match(profile_id):
            raise ValueError("profileId must be a lowercase slug (a-z0-9, hyphen, underscore)")
        existing = self.get(profile_id)
        if existing and existing.builtin:
            raise ValueError("cannot overwrite built-in profile")
        payload = {
            "profileId": profile_id,
            "family": data.get("family") or "sdxl",
            "displayName": data.get("displayName") or profile_id,
            "peakMemoryGb": float(data.get("peakMemoryGb") or 8),
            "comfy": data.get("comfy") or {},
            "defaults": data.get("defaults") or {},
            "capabilities": data.get("capabilities") or {},
            "supportedWorkflows": data.get("supportedWorkflows") or [],
        }
        user_dir = user_profiles_dir(self.data_dir)
        user_dir.mkdir(parents=True, exist_ok=True)
        path = user_dir / f"{profile_id}.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        self.invalidate()
        return load_profile_yaml(path)

    def delete_user_profile(self, profile_id: str) -> bool:
        prof = self.get(profile_id)
        if not prof or prof.builtin:
            return False
        if prof.source_path and prof.source_path.is_file():
            prof.source_path.unlink()
            self.invalidate()
            return True
        return False


def resolve_comfy_url(env_comfy: str | None, image_config: ImageConfig | None) -> str | None:
    cfg = (image_config or ImageConfig()).normalized()
    url = cfg.comfy_base_url or (env_comfy or "")
    return url.strip() or None


def resolve_image_profile_id(
    workflow_id: str,
    *,
    request_profile_id: str | None,
    image_config: ImageConfig | None,
    world_config: dict[str, Any] | None,
) -> str:
    if request_profile_id:
        return request_profile_id.strip()
    wc = world_config or {}
    if wc.get("imageUseOperatorDefaults") is False:
        wf_map = wc.get("imageWorkflowProfiles") or {}
        if isinstance(wf_map, dict) and wf_map.get(workflow_id):
            return str(wf_map[workflow_id])
        world_default = wc.get("imageDefaultProfileId")
        if world_default:
            return str(world_default)
    cfg = (image_config or ImageConfig()).normalized()
    if cfg.workflow_profiles.get(workflow_id):
        return cfg.workflow_profiles[workflow_id]
    return cfg.default_profile_id or "sdxl-default"
