from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import httpx

_DEFAULT_ALLOWLIST = {"localhost", "127.0.0.1", "example.com", "www.example.org"}
_MAX_BYTES = 512_000
_TIMEOUT = 15.0


def _host_allowed(host: str, allowlist: set[str]) -> bool:
    if not host:
        return False
    host = host.lower().split(":")[0]
    if host in allowlist:
        return True
    for entry in allowlist:
        if entry.startswith("*.") and host.endswith(entry[1:]):
            return True
    return False


def _blocked_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


async def safe_fetch(
    url: str,
    *,
    allowlist: set[str] | None = None,
    max_bytes: int = _MAX_BYTES,
) -> dict[str, Any]:
    """SSRF-safe fetch (WEB-*): allowlist hosts, size cap, no private IPs unless allowlisted."""
    allow = _DEFAULT_ALLOWLIST if allowlist is None else allowlist
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        return {"ok": False, "error": "only http(s) supported"}
    host = parsed.hostname or ""
    if _blocked_ip(host):
        if host.lower() not in allow and "127.0.0.1" not in allow:
            return {"ok": False, "error": "private or loopback hosts blocked"}
    if not _host_allowed(host, allow):
        return {"ok": False, "error": f"host not in allowlist: {host}"}
    full_url = parsed.geturl()
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
        r = await client.get(full_url)
        r.raise_for_status()
        body = r.content[:max_bytes]
        text = body.decode("utf-8", errors="replace")
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return {
            "ok": True,
            "url": full_url,
            "status": r.status_code,
            "summary": text[:4000],
        }
