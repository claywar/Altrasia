# Altrasia

**A persistent stage for AI characters—memory-grounded, spatial, operator-run.**

Altrasia is a **single-machine narrative studio**: multi-scene worlds where characters hold private and shared memory, occupy locations, and communicate under explicit scopes. You play as the **persona**; NPCs are the cast; the **Observer** is your studio side-channel for tuning—not the main play voice.

Product principles, personas, and milestones: [docs/20-product-principles.md](docs/20-product-principles.md) · [docs/personas.md](docs/personas.md) · [docs/ROADMAP.md](docs/ROADMAP.md)

## Who this is for

- **Solo operator** with a local GPU running a reference LLM (Qwen3.6-35B-A3B via llama.cpp)
- **Not** a SillyTavern fork, extension, or coding agent
- **Not** multi-tenant SaaS or game-engine level design tooling

## Status

| | |
|--|--|
| **Design specifications** | Complete (normative docs `00`–`25`) |
| **Implementation** | **v1 + v1.1 feature-complete** — see [docs/IMPLEMENTATION-CHECKLIST.md](docs/IMPLEMENTATION-CHECKLIST.md) |
| **Shipped** | **Alpha** — golden path 1–8, heartbeat, world package, phone play, observer digest, 34+ pytest |

Run locally: [docs/guides/getting-started.md](docs/guides/getting-started.md). First-session UX checklist: [docs/guides/first-run-experience.md](docs/guides/first-run-experience.md).

### Planned capability by milestone

| Milestone | What it means |
|-----------|----------------|
| **v1** | Spatial play while the application is running; tab-visible idle acceptable |
| **v1.1** | Global heartbeat when UI is away, phone play, world package export/import |
| **Post-v1** | In-world work (commissions, debate), maps, ComfyUI, external tools |

Scope sequencing—not a retreat from the persistent-world vision. Detail: [docs/ROADMAP.md](docs/ROADMAP.md).

## Documentation

| Audience | Start here |
|----------|------------|
| Stakeholders / PM | [docs/ROADMAP.md](docs/ROADMAP.md), [docs/20-product-principles.md](docs/20-product-principles.md) |
| Future operators | [docs/guides/first-run-experience.md](docs/guides/first-run-experience.md) |
| Implementers | [docs/README.md](docs/README.md), [docs/IMPLEMENTATION-CHECKLIST.md](docs/IMPLEMENTATION-CHECKLIST.md) |

All normative specifications live under [`docs/`](docs/README.md). **Stack:** Python-first extensible backend + professional Web UI — [docs/26-system-architecture.md](docs/26-system-architecture.md). Extended topics: inference runtime (`00`), data model (`11`), API sketch (`12`), orchestration (`13`), Web UI (`14`), acceptance (`17`), output quality (`22`), in-world work (`23`), character authoring (`24`), map authoring (`25`). Requirement IDs: [docs/REQUIREMENTS-INDEX.md](docs/REQUIREMENTS-INDEX.md).

Concepts were extracted from a prior SillyTavern deployment and reframed greenfield. Lineage (implementers): [`docs/appendix-provenance.md`](docs/appendix-provenance.md).

## Reference model

Primary LLM: **Qwen3.6-35B-A3B** via local llama.cpp router ([`config/models/qwen3.6-35b-a3b.yaml`](config/models/qwen3.6-35b-a3b.yaml)).

## Run locally

See [docs/guides/getting-started.md](docs/guides/getting-started.md).

```bash
# Terminal 1
cd backend && pip install -e ".[dev]" && altrasia serve

# Terminal 2
cd web && npm install && npm run dev
```

**Architecture:** [docs/26-system-architecture.md](docs/26-system-architecture.md) — Python backend (`backend/altrasia/…`) + Web UI SPA (`web/`).

Build order (Sprint 1/2):

### Sprint 1 — inference + memory spike

De-risk GPU queue, tool loop, and memory before Web UI.

1. SQLite migration 001 + `PersistencePort` per [docs/11-data-model.md](docs/11-data-model.md) (`backend/altrasia/persistence/`)
2. Memory subsystem per [docs/02-memory.md](docs/02-memory.md)
3. GpuResourceQueue per [docs/00-inference-runtime.md](docs/00-inference-runtime.md)
4. llama.cpp adapter with profile `qwen3.6-35b-a3b`
5. Tool registry + invoke loop per [docs/05-tool-calling.md](docs/05-tool-calling.md)
6. `stripReasoning` + mandatory recall per [docs/16-learning.md](docs/16-learning.md)
7. Single scene, one NPC, CLI or `POST /api/v1/worlds/{id}/generate`

### Sprint 2 — spatial wedge

Two scenes, presence, whisper perception, elsewhere roster, **Web UI** with streaming ([docs/14-web-ui.md](docs/14-web-ui.md)) against the Python API ([docs/12-api-sketch.md](docs/12-api-sketch.md)).

**First run (when built):** load demo world `demo-spatial-v1` ([tests/fixtures/demo-world/README.md](tests/fixtures/demo-world/README.md)).

### Acceptance

Release gate: [docs/17-acceptance-criteria.md](docs/17-acceptance-criteria.md) spatial golden path + output quality (OQ-1, OQ-3).

### v1.1 (shipped in tree)

Phone play, global heartbeat, world package export/import ([docs/ROADMAP.md](docs/ROADMAP.md)). CLI: `altrasia load-demo`, `altrasia worlds`.

## License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). Copyright (c) 2026 Altrasia Contributors.
