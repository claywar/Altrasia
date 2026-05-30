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
# optional: seed demo without the Web UI
altrasia load-demo
altrasia worlds   # list saved worlds
```

Default uses **mock LLM** (no GPU). Health: http://127.0.0.1:8787/api/v1/health

## 2. Web UI

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173 → **Load demo world** → play as persona in the Hall.

Optional: **Settings** → **Server** → enable **Server heartbeat** for NPC idle when the browser tab is closed (saved in `~/.altrasia/config.yaml`).

**Remote inference:** **Settings** → **Server** → **Inference endpoints** — set primary and embedding base URLs and model ids (saved in `~/.altrasia/config.yaml`). Use **List models** to query `/v1/models` from a llama.cpp router. Empty fields use `ALTRASIA_LLM_*` / `ALTRASIA_EMBED_*` environment variables.

**World package:** Settings → **World** → **Export world package** (`.zip`); import via **Import package** or `POST /api/v1/worlds/import`.

**Settings categories:** **World** (policy, activity status, package, briefing), **Scenes & layout** (geography, map layout), **Cast** (list, AI character draft), **Operations** (commissions), **Server** (heartbeat, plugins). **Play UI:** debate panel (right sidebar), tactical **Map** console (Top bar **Map**, scene chip, or **M** — pan/zoom, layers, click rooms to travel), approvals banner. **Observer Studio:** digest with signals, commissions, debates, approvals.

**Alpha wedge defaults:** Reflection and nightly learning are **off** until enabled in World policy. Idle social/banter is policy-gated. Web-tools and ComfyUI portrait generation use **mock/stub** behavior unless you configure live endpoints (`ALTRASIA_LLM_*`, ComfyUI URL, web-tools allowlist). Server plugins default off. See [SPEC-GAPS.md](../SPEC-GAPS.md) for production-hardening gaps.

## 3. Real inference (optional)

Start llama.cpp with an OpenAI-compatible API, then:

```bash
export ALTRASIA_MOCK_LLM=false
export ALTRASIA_LLM_BASE_URL=http://127.0.0.1:8080
export ALTRASIA_LLM_MODEL=Qwen3.6-35B-A3B
altrasia serve
```

Model profile: [config/models/qwen3.6-35b-a3b.yaml](../../config/models/qwen3.6-35b-a3b.yaml)

**Thinking mode (Qwen / llama.cpp):** If your server runs with `enable_thinking`, it cannot accept prior assistant turns in the chat prompt (“assistant prefill”). Altrasia sends completed cast lines as user `[Scene] …` context; only the live NPC generation is assistant. Keep thinking enabled on the router—no server change required.

## 4. API quick test

```bash
curl -X POST http://127.0.0.1:8787/api/v1/worlds \
  -H "Content-Type: application/json" \
  -d '{"fixtureId":"demo-spatial-v1"}'
```

## 5. Tests

```bash
cd backend && pytest ../tests -v
# optional reference-scale memory perf (slower):
cd backend && pytest ../tests/test_memory_perf.py -v -m slow
```

## 6. Nightly (real LLM)

On reference hardware with [llama.cpp](https://github.com/ggerganov/llama.cpp) serving Qwen3.6-35B-A3B:

```bash
export ALTRASIA_MOCK_LLM=false
export ALTRASIA_LLM_BASE_URL=http://127.0.0.1:8080
export ALTRASIA_LLM_MODEL=Qwen3.6-35B-A3B
pytest tests/test_golden_path.py tests/test_output_quality.py -v
```

GitHub Actions: `.github/workflows/nightly.yml` (requires `ALTRASIA_LLM_BASE_URL` secret).

## 7. Web E2E (Playwright)

```bash
cd web && npm install && npx playwright install chromium
npx playwright test
```

## 8. Demo world (canonical)

- **API:** `POST /api/v1/worlds` with `{"fixtureId":"demo-spatial-v1"}`
- **CLI:** `altrasia load-demo` (persists under `~/.altrasia/`)

## 9. OpenAPI export

Regenerate the API contract after backend route changes:

```bash
python scripts/export_openapi.py
```

Artifact: [packages/openapi/altrasia-v1.json](../../packages/openapi/altrasia-v1.json). CI fails if the export drifts from committed JSON.

## Next

- Spatial golden path: [17-acceptance-criteria.md](../17-acceptance-criteria.md)
- First session UX: [first-run-experience.md](first-run-experience.md)
- Spec gaps tracker: [SPEC-GAPS.md](../SPEC-GAPS.md)
