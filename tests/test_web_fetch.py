"""SSRF-safe web fetch (WEB-*)."""

import pytest

from altrasia.tools.web_fetch import safe_fetch


@pytest.mark.asyncio
async def test_allowlisted_fetch() -> None:
    r = await safe_fetch("https://www.example.org/", allowlist={"www.example.org"})
    assert r.get("ok") is True or "summary" in r


@pytest.mark.asyncio
async def test_blocks_private_ip() -> None:
    r = await safe_fetch("http://127.0.0.1/", allowlist=set())
    assert r.get("ok") is False
    assert "blocked" in (r.get("error") or "").lower() or "allowlist" in (r.get("error") or "").lower()


@pytest.mark.asyncio
async def test_blocks_non_http_scheme() -> None:
    r = await safe_fetch("file:///etc/passwd", allowlist={"example.com"})
    assert r.get("ok") is False


@pytest.mark.asyncio
async def test_blocks_host_not_on_allowlist() -> None:
    r = await safe_fetch("https://evil.example/", allowlist={"example.com"})
    assert r.get("ok") is False
    assert "allowlist" in (r.get("error") or "")


@pytest.mark.asyncio
async def test_wildcard_allowlist_rejects_other_hosts() -> None:
    r = await safe_fetch("https://not-example.com/", allowlist={"*.example.com"})
    assert r.get("ok") is False
