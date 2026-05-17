# WorldEngine

**A persistent stage for AI characters—memory-grounded, spatial, operator-run.**

WorldEngine is a **single-machine narrative studio**: multi-scene worlds where characters hold private and shared memory, occupy locations, and communicate under explicit scopes. You play as the **persona**; NPCs are the cast; the **Observer** is your studio side-channel for tuning—not the main play voice.

Product principles, personas, and milestones: [docs/20-product-principles.md](docs/20-product-principles.md) · [docs/personas.md](docs/personas.md) · [docs/ROADMAP.md](docs/ROADMAP.md)

## Who this is for

- **Solo operator** with a local GPU running a reference LLM (Qwen3.6-35B-A3B via llama.cpp)
- **Not** a SillyTavern fork, extension, or coding agent
- **Not** multi-tenant SaaS or game-engine level design tooling

## Status

| | |
|--|--|
| **Design specifications** | Complete (normative docs `00`–`24`) |
| **Implementation** | **Not started** — no runnable app, API, or bundled demo database in this repo |
| **Shipped** | **Nothing** — golden path in [docs/17-acceptance-criteria.md](docs/17-acceptance-criteria.md) is the future v1 gate |

This repository is a **greenfield design specification**, not a product you can install today. Target first session (when built): [docs/guides/first-run-experience.md](docs/guides/first-run-experience.md).

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
| Implementers | [docs/README.md](docs/README.md) — reading order, architecture, v1 scope |

All normative specifications live under [`docs/`](docs/README.md). Extended topics: inference runtime (`00`), data model (`11`), API sketch (`12`), orchestration (`13`), Web UI (`14`), acceptance (`17`), output quality (`22`), in-world work (`23`), character authoring (`24`).

Concepts were extracted from a prior SillyTavern deployment and reframed greenfield. Lineage (implementers): [`docs/appendix-provenance.md`](docs/appendix-provenance.md).

## Reference model

Primary LLM: **Qwen3.6-35B-A3B** via local llama.cpp router ([`config/models/qwen3.6-35b-a3b.yaml`](config/models/qwen3.6-35b-a3b.yaml)).

## Planned implementation (not started)

Proposed build order when implementation begins:

### Sprint 1 — inference + memory spike

De-risk GPU queue, tool loop, and memory before Web UI.

1. SQLite migration 001 per [docs/11-data-model.md](docs/11-data-model.md) and [packages/persistence](packages/persistence/README.md)
2. Memory subsystem per [docs/02-memory.md](docs/02-memory.md)
3. GpuResourceQueue per [docs/00-inference-runtime.md](docs/00-inference-runtime.md)
4. llama.cpp adapter with profile `qwen3.6-35b-a3b`
5. Tool registry + invoke loop per [docs/05-tool-calling.md](docs/05-tool-calling.md)
6. `stripReasoning` + mandatory recall per [docs/16-learning.md](docs/16-learning.md)
7. Single scene, one NPC, CLI or `POST /api/v1/worlds/{id}/generate`

Suggested monorepo layout: `packages/domain, memory, perception, orchestrator, inference, tools, persistence, api`

### Sprint 2 — spatial wedge

Two scenes, presence, whisper perception, elsewhere roster, Web UI with streaming ([docs/14-web-ui.md](docs/14-web-ui.md)).

**First run (when built):** load demo world `demo-spatial-v1` ([tests/fixtures/demo-world/README.md](tests/fixtures/demo-world/README.md)).

### Acceptance

Release gate: [docs/17-acceptance-criteria.md](docs/17-acceptance-criteria.md) spatial golden path + output quality (OQ-1, OQ-3).

### v1.1 (after v1 tag)

Phone play, global heartbeat, world package export/import ([docs/ROADMAP.md](docs/ROADMAP.md)).

## License

[MIT](LICENSE)
