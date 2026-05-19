from __future__ import annotations

import asyncio
from typing import Any

import httpx

_RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})


def world_generation_policy(cfg: dict[str, Any]) -> dict[str, Any]:
    """Resolve generation retry/timeout knobs from world config."""
    return {
        "max_retries": max(0, int(cfg.get("generationMaxRetries", 2))),
        "backoff_seconds": max(0.0, float(cfg.get("generationRetryBackoffSeconds", 3.0))),
        "inference_timeout_seconds": max(
            30.0, float(cfg.get("inferenceTimeoutSeconds", 180.0))
        ),
        "max_continue_depth": max(0, int(cfg.get("maxContinueDepth", 2))),
        "max_tool_rounds_per_job": max(1, int(cfg.get("maxToolRoundsPerJob", 5))),
    }


def is_retryable_generation_error(exc: BaseException) -> bool:
    """Transient failures worth re-running the full generation."""
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code in _RETRYABLE_HTTP_STATUS
    if isinstance(exc, ValueError) and str(exc) == "Model returned empty content":
        return True
    return False
