#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to packages/openapi/altrasia-v1.json."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from altrasia.api.app import create_app  # noqa: E402
from altrasia.config import Settings  # noqa: E402


def main() -> int:
    out = ROOT / "packages" / "openapi" / "altrasia-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    db = Path(tempfile.gettempdir()) / "altrasia-openapi-export.db"
    app = create_app(Settings(mock_llm=True, db_path=db))
    schema = app.openapi()
    out.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
