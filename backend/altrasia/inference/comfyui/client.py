from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import httpx

log = logging.getLogger(__name__)


class ComfyUiClient:
    def __init__(self, base_url: str, *, timeout: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def submit_prompt(self, prompt: dict[str, Any], *, client_id: str | None = None) -> str:
        payload: dict[str, Any] = {"prompt": prompt}
        if client_id:
            payload["client_id"] = client_id
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/prompt", json=payload)
            r.raise_for_status()
            data = r.json()
            if data.get("node_errors"):
                raise RuntimeError(f"ComfyUI node errors: {data['node_errors']}")
            prompt_id = data.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI missing prompt_id: {data}")
            return str(prompt_id)

    async def wait_for_completion(
        self,
        prompt_id: str,
        *,
        poll_interval: float = 0.5,
        max_wait: float = 180.0,
    ) -> dict[str, Any]:
        elapsed = 0.0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while elapsed < max_wait:
                r = await client.get(f"{self.base_url}/history/{prompt_id}")
                r.raise_for_status()
                data = r.json()
                if prompt_id in data:
                    return data[prompt_id]
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {max_wait}s")

    async def fetch_image_bytes(
        self,
        filename: str,
        *,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> bytes:
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/view", params=params)
            r.raise_for_status()
            return r.content

    async def free_memory(self, *, unload_models: bool = True) -> None:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{self.base_url}/free",
                    json={"unload_models": unload_models, "free_memory": True},
                )
        except Exception as exc:
            log.warning("ComfyUI /free failed: %s", exc)

    async def interrupt(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(f"{self.base_url}/interrupt")
        except Exception as exc:
            log.warning("ComfyUI /interrupt failed: %s", exc)

    async def health_check(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self.base_url}/system_stats")
                ok = r.status_code == 200
                return {"ok": ok, "reachable": ok, "baseUrl": self.base_url}
        except Exception as exc:
            return {"ok": False, "reachable": False, "baseUrl": self.base_url, "error": str(exc)}

    @staticmethod
    def extract_output_images(history_entry: dict[str, Any]) -> list[dict[str, str]]:
        outputs = history_entry.get("outputs") or {}
        images: list[dict[str, str]] = []
        for node_out in outputs.values():
            for img in node_out.get("images") or []:
                if isinstance(img, dict) and img.get("filename"):
                    images.append(
                        {
                            "filename": str(img["filename"]),
                            "subfolder": str(img.get("subfolder") or ""),
                            "type": str(img.get("type") or "output"),
                        }
                    )
        return images

    async def run_prompt_to_image(self, prompt: dict[str, Any]) -> bytes:
        client_id = str(uuid.uuid4())
        prompt_id = await self.submit_prompt(prompt, client_id=client_id)
        history = await self.wait_for_completion(prompt_id)
        images = self.extract_output_images(history)
        if not images:
            raise RuntimeError("ComfyUI produced no output images")
        first = images[0]
        return await self.fetch_image_bytes(
            first["filename"],
            subfolder=first.get("subfolder", ""),
            folder_type=first.get("type", "output"),
        )
