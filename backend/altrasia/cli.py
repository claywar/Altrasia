from __future__ import annotations

import argparse

import uvicorn

from altrasia.api.app import create_app
from altrasia.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="altrasia")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="Run API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if args.cmd == "serve":
        settings = get_settings()
        app = create_app(settings)
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    main()
