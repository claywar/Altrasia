# Getting started

Run Altrasia locally (v1 spatial wedge).

## Prerequisites

- Python 3.11+
- Node.js 20+ (Web UI)
- Optional: local [llama.cpp](https://github.com/ggerganov/llama.cpp) server for real inference

## 1. Backend

```bash
cd backend
pip install -e ".[dev]"
altrasia serve --port 8787
```

Default uses **mock LLM** (no GPU). Health: http://127.0.0.1:8787/api/v1/health

## 2. Web UI

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173 → **Load demo world** → play as persona in the Hall.

## 3. Real inference (optional)

Start llama.cpp with an OpenAI-compatible API, then:

```bash
export ALTRASIA_MOCK_LLM=false
export ALTRASIA_LLM_BASE_URL=http://127.0.0.1:8080
export ALTRASIA_LLM_MODEL=Qwen3.6-35B-A3B
altrasia serve
```

Model profile: [config/models/qwen3.6-35b-a3b.yaml](../../config/models/qwen3.6-35b-a3b.yaml)

## 4. API quick test

```bash
curl -X POST http://127.0.0.1:8787/api/v1/worlds \
  -H "Content-Type: application/json" \
  -d '{"fixtureId":"demo-spatial-v1"}'
```

## 5. Tests

```bash
cd backend && pytest ../tests -v
```

## Next

- Spatial golden path: [17-acceptance-criteria.md](../17-acceptance-criteria.md)
- First session UX: [first-run-experience.md](first-run-experience.md)
