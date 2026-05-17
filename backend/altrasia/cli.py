from __future__ import annotations

import argparse
import sys

import uvicorn

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.persistence.sqlite_store import SqlitePersistence


def _cmd_serve(args: argparse.Namespace) -> None:
    settings = Settings()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _cmd_worlds_list(_args: argparse.Namespace) -> None:
    settings = Settings()
    store = SqlitePersistence(settings.sqlite_path)
    store.migrate()
    rows = store.list_worlds()
    if not rows:
        print("No saved worlds.", file=sys.stderr)
        return
    for w in rows:
        print(f"{w['worldId']}\t{w['name']}\tactive={w['activeSceneId']}")


def _cmd_load_demo(args: argparse.Namespace) -> None:
    settings = Settings()
    store = SqlitePersistence(settings.sqlite_path)
    store.migrate()
    result = load_fixture_by_id(store, settings.fixtures_dir, args.fixture)
    print(result["worldId"])


def main() -> None:
    parser = argparse.ArgumentParser(prog="altrasia")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="Run API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_cmd_serve)

    worlds = sub.add_parser("worlds", help="List saved worlds")
    worlds.set_defaults(func=_cmd_worlds_list)

    load_demo = sub.add_parser("load-demo", help="Load demo-spatial-v1 into the local DB")
    load_demo.add_argument(
        "--fixture",
        default="demo-spatial-v1",
        help="Fixture id under tests/fixtures (default: demo-spatial-v1)",
    )
    load_demo.set_defaults(func=_cmd_load_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
