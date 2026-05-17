# WorldEngine

Design specification for a **persistent world** platform: multi-scene narrative play with characters that hold private and shared memory, occupy locations, communicate under explicit scopes, and—when authorized—perform real-world actions under operator approval.

This repository is the **normative specification** for a greenfield implementation. It is not a SillyTavern fork or extension.

## Documentation

All specifications live under [`docs/`](docs/README.md). Start with the docs index for reading order, architecture, and v1 scope.

**Magnum opus extensions** (inference runtime, data model, API, orchestration, Web UI, cross-scene roadmap, acceptance criteria) are documented in docs `00` and `11`–`21`.

## Status

- **Specs:** v1 design package complete (docs 00–21)
- **Implementation:** not started — see [Development](#development) below

Concepts were extracted from a prior SillyTavern deployment and reframed greenfield. See [`docs/appendix-provenance.md`](docs/appendix-provenance.md) for source mapping (implementers only).

## Reference model

Primary LLM: **Qwen3.6-35B-A3B** via local llama.cpp router (`config/models/qwen3.6-35b-a3b.yaml`).

## Development

### Sprint 1 — inference + memory spike (recommended first build)

Goal: de-risk GPU queue, tool loop, and memory palace before Web UI.

1. **SQLite** schema per [docs/11-data-model.md](docs/11-data-model.md)
2. **GpuResourceQueue** + lease reaper per [docs/00-inference-runtime.md](docs/00-inference-runtime.md)
3. **llama.cpp adapter** (OpenAI-compatible) with profile `qwen3.6-35b-a3b`
4. Tool registry + invoke loop per [docs/05-tool-calling.md](docs/05-tool-calling.md)
5. `stripReasoning` + mandatory recall + blocking per [docs/16-learning.md](docs/16-learning.md)
6. Single scene, one NPC, CLI or `POST /api/v1/worlds/{id}/generate`

Suggested monorepo layout:

```
packages/domain, memory, perception, orchestrator, inference, tools, persistence, api
```

### Sprint 2 — spatial wedge

Two scenes, presence, whisper perception, elsewhere roster, Web UI with streaming ([docs/14-web-ui.md](docs/14-web-ui.md)).

### Acceptance

Release gate: [docs/17-acceptance-criteria.md](docs/17-acceptance-criteria.md) spatial golden path.

## License

Unspecified — add a license file when the project moves beyond documentation.
