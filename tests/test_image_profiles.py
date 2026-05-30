"""Image profile registry and resolver tests."""

from pathlib import Path

import pytest
import yaml

from altrasia.inference.comfyui.profiles import (
    ImageConfig,
    ImageProfileRegistry,
    resolve_image_profile_id,
)


def test_builtin_profiles_load() -> None:
    reg = ImageProfileRegistry(Path.home() / ".altrasia-test-unused")
    profiles = reg.list_profiles(refresh=True)
    ids = {p.profile_id for p in profiles}
    assert "sdxl-default" in ids
    assert "z-image-turbo-default" in ids


def test_resolve_profile_request_override() -> None:
    pid = resolve_image_profile_id(
        "character_portrait",
        request_profile_id="flux-nf4",
        image_config=ImageConfig(),
        world_config={},
    )
    assert pid == "flux-nf4"


def test_resolve_profile_world_override(tmp_path: Path) -> None:
    cfg = ImageConfig(default_profile_id="sdxl-default")
    wc = {
        "imageUseOperatorDefaults": False,
        "imageWorkflowProfiles": {"scene_establishing": "z-image-turbo-default"},
    }
    pid = resolve_image_profile_id(
        "scene_establishing",
        request_profile_id=None,
        image_config=cfg,
        world_config=wc,
    )
    assert pid == "z-image-turbo-default"


def test_user_profile_crud(tmp_path: Path) -> None:
    reg = ImageProfileRegistry(tmp_path)
    prof = reg.save_user_profile(
        {
            "profileId": "sdxl-custom",
            "family": "sdxl",
            "displayName": "Custom",
            "peakMemoryGb": 8,
            "comfy": {"checkpoint": "custom.safetensors"},
            "supportedWorkflows": ["character_portrait"],
        }
    )
    assert prof.profile_id == "sdxl-custom"
    path = tmp_path / "image-profiles" / "sdxl-custom.yaml"
    assert path.is_file()
    assert reg.delete_user_profile("sdxl-custom")
    assert not path.is_file()


def test_cannot_delete_builtin(tmp_path: Path) -> None:
    reg = ImageProfileRegistry(tmp_path)
    assert not reg.delete_user_profile("sdxl-default")
