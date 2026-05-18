"""RW-* filesystem agent jail tests."""

from pathlib import Path

import pytest

from altrasia.tools.fs_agent import FsAgent


def test_read_write_round_trip(tmp_path: Path) -> None:
    agent = FsAgent(tmp_path)
    w = agent.write("notes.txt", "hello world")
    assert w["ok"] is True
    r = agent.read("notes.txt")
    assert r["ok"] is True
    assert r["content"] == "hello world"


def test_blocks_path_traversal(tmp_path: Path) -> None:
    agent = FsAgent(tmp_path)
    with pytest.raises(PermissionError):
        agent.read("../../outside.txt")


def test_not_found(tmp_path: Path) -> None:
    agent = FsAgent(tmp_path)
    r = agent.read("missing.txt")
    assert r["ok"] is False
