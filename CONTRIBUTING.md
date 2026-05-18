# Contributing to Altrasia

Thank you for helping improve Altrasia.

## Development setup

```bash
cd backend && pip install -e ".[dev]"
cd ../web && npm install
```

Run backend: `altrasia serve --port 8787`  
Run Web UI: `npm run dev` (from `web/`)

Default tests use **mock LLM** (no GPU required).

## Tests

```bash
cd backend && pytest ../tests -v
pytest ../tests/test_memory_perf.py -m slow   # reference scale
```

## Pull requests

1. One logical change per PR (see [docs/BACKLOG.md](docs/BACKLOG.md) task IDs when applicable)
2. All CI tests must pass (`pytest`, `npm run build`)
3. Update docs if behavior or API changes
4. Do not commit secrets (`.env`, API keys)

## Code style

- Match existing module layout under `backend/altrasia/`
- Python 3.11+; type hints where already used
- Web UI: React + TypeScript in `web/src/`

## Specs

Normative behavior: [docs/README.md](docs/README.md). Implementation checklist: [docs/IMPLEMENTATION-CHECKLIST.md](docs/IMPLEMENTATION-CHECKLIST.md).
