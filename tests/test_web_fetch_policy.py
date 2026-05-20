"""Live web fetch URL resolution, allowlist, and approval prompt summaries."""

from pathlib import Path

import pytest

from altrasia.approvals import (
    effective_web_allowlist,
    resolve_fetch_url,
    web_approval_summary_for_prompt,
)
from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.services import AppServices
from tests.conftest import make_test_settings


def test_resolve_fetch_url_no_example_fallback() -> None:
    assert resolve_fetch_url({"url": "soylentnews.org"}) == "https://soylentnews.org"
    assert resolve_fetch_url({"query": "soylentnews.org"}) == "https://soylentnews.org"
    assert resolve_fetch_url({"query": "top news today"}) is None


def test_web_approval_summary_failed_fetch() -> None:
    text = web_approval_summary_for_prompt(
        {"ok": False, "error": "host not in allowlist: soylentnews.org"}
    )
    assert "Web fetch failed" in text
    assert "soylentnews.org" in text
    assert "Do not invent" in text


def test_effective_web_allowlist_merges_world_policy(tmp_path: Path) -> None:
    settings = make_test_settings(tmp_path, "allow.db")
    svc = AppServices.create(settings)
    world_id = svc.store.conn.execute("SELECT worldId FROM World LIMIT 1").fetchone()
    if not world_id:
        from altrasia.fixtures.loader import load_fixture_by_id

        meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
        world_id = (meta["worldId"],)
    else:
        world_id = (world_id[0],)
    w = svc.store.get_world(world_id[0])
    cfg = {"webAllowlistHosts": "soylentnews.org"}
    svc.store.conn.execute(
        "UPDATE World SET configJson = ? WHERE worldId = ?",
        (__import__("json").dumps(cfg), world_id[0]),
    )
    svc.store.conn.commit()
    hosts = effective_web_allowlist(svc, world_id[0])
    assert "soylentnews.org" in hosts
    assert "example.com" in hosts


def test_diary_fanout_allows_second_reply_same_scene(tmp_path: Path) -> None:
    settings = make_test_settings(tmp_path, "diary.db")
    svc = AppServices.create(settings)
    from altrasia.fixtures.loader import load_fixture_by_id

    meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    scene_id = meta["activeSceneId"]
    cid = "char-jordan-reyes"
    msg_a = "msg-a"
    msg_b = "msg-b"
    svc.memory.capture_diary_fanout(
        scene_id=scene_id,
        present_ids=[cid],
        snippet="line one",
        message_ids=[msg_a],
        reply_message_id="reply-1",
    )
    svc.memory.capture_diary_fanout(
        scene_id=scene_id,
        present_ids=[cid],
        snippet="line two",
        message_ids=[msg_a],
        reply_message_id="reply-2",
    )
    assert len(svc.store.list_diary(cid)) == 2
