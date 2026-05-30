#!/usr/bin/env python3
"""Smoke-test ComfyUI image workflows (IMG-2)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "backend") not in sys.path:
    sys.path.insert(0, str(_REPO / "backend"))

from altrasia.config import Settings
from altrasia.inference.comfyui.client import ComfyUiClient
from altrasia.inference.comfyui.profiles import ImageProfileRegistry, resolve_comfy_url
from altrasia.inference.comfyui.workflows import build_prompt_for_profile
from altrasia.operator_settings import OperatorSettingsStore, get_image_config


async def main() -> int:
    parser = argparse.ArgumentParser(description="ComfyUI workflow smoke test")
    parser.add_argument("--workflow", default="scene_establishing")
    parser.add_argument("--profile", default="sdxl-default")
    parser.add_argument("--prompt", default="test scene, cinematic lighting")
    parser.add_argument("--base-url", default="")
    args = parser.parse_args()

    settings = Settings()
    op = OperatorSettingsStore(settings.data_dir / "config.yaml").load()
    base = args.base_url or resolve_comfy_url(settings.comfy_url, get_image_config(op))
    if not base:
        print("ComfyUI URL not configured (ALTRASIA_COMFY_URL or Settings → Media)")
        return 1

    reg = ImageProfileRegistry(settings.data_dir)
    profile = reg.get(args.profile)
    if not profile:
        print(f"Unknown profile: {args.profile}")
        return 1

    budget = get_image_config(op).memory_budget_gb
    print(f"Profile {profile.profile_id} peakMemoryGb={profile.peak_memory_gb} budget={budget}GB")
    if profile.peak_memory_gb > budget:
        print("WARNING: profile exceeds operator memory budget")

    _, prompt = build_prompt_for_profile(
        args.workflow,
        profile,
        positive_prompt=args.prompt,
    )
    client = ComfyUiClient(base)
    health = await client.health_check()
    if not health.get("ok"):
        print(f"ComfyUI unreachable at {base}: {health}")
        return 1

    print(f"Submitting {args.workflow}/{profile.family} to {base}…")
    png = await client.run_prompt_to_image(prompt)
    await client.free_memory()
    out = settings.data_dir / "smoke-test.png"
    out.write_bytes(png)
    print(f"OK — wrote {len(png)} bytes to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
