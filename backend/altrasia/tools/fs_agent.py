from __future__ import annotations

from pathlib import Path
from typing import Any


class FsAgent:
    """RW-*: path-jailed read/write under world data directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, rel_path: str) -> Path:
        rel = rel_path.lstrip("/").replace("..", "")
        target = (self.root / rel).resolve()
        if not str(target).startswith(str(self.root)):
            raise PermissionError("path escapes world jail")
        return target

    def read(self, path: str) -> dict[str, Any]:
        target = self._resolve(path)
        if not target.is_file():
            return {"ok": False, "error": "not found"}
        return {"ok": True, "path": path, "content": target.read_text(encoding="utf-8")[:100_000]}

    def write(self, path: str, content: str) -> dict[str, Any]:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": path, "bytes": len(content.encode())}
