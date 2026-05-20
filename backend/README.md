# Altrasia backend

Python 3.11+ API server. See [docs/26-system-architecture.md](../docs/26-system-architecture.md).

## Setup

```bash
cd backend
pip install -e ".[dev]"
```

## Run

```bash
altrasia serve --port 8787
```

Environment:

| Variable | Default |
|----------|---------|
| `ALTRASIA_MOCK_LLM` | `false` (tests set `true`) |
| `ALTRASIA_WEB_TOOLS_MOCK` | `false` (tests set `true`) |
| `ALTRASIA_WEB_ALLOWLIST` | `example.com,www.example.org` (add hosts for live fetch, e.g. `soylentnews.org`) |
| `ALTRASIA_LLM_BASE_URL` | unset (configure for live inference) |
| `ALTRASIA_DATA_DIR` | `~/.altrasia` |
| `ALTRASIA_API_TOKEN` | unset (no auth) |

Real llama.cpp (OpenAI-compatible):

```bash
export ALTRASIA_MOCK_LLM=false
export ALTRASIA_LLM_BASE_URL=http://127.0.0.1:8080
altrasia serve
```

## Tests

From repo root:

```bash
cd backend && pip install -e ".[dev]"
pytest ../tests -v
```
