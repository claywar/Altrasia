# Altrasia Roadmap

Single-page view of milestones, repository status, and what ships when. Normative behavior remains in numbered specs `00`–`25`.

## Repository status

| Layer | Status |
|-------|--------|
| **Design specifications** | Complete (docs `00`–`25`, appendices, acceptance criteria) |
| **Implementation** | **Alpha** — Python backend, Web UI SPA, demo fixture; mock LLM default ([getting-started.md](guides/getting-started.md)) |
| **Shipped product** | **Nothing** — release gates in [17-acceptance-criteria.md](17-acceptance-criteria.md) apply when code exists |

Specs describe **MUST** behavior for a future build. Passing the spatial golden path is the first **v1** ship criterion.

## Product narrative (Acts)

Long-term vision spans three acts. Only **Act 1** is the v1 implementation target.

| Act | Milestone | User-visible outcome |
|-----|-----------|----------------------|
| **Act 1** | **v1** | Spatial world — multi-scene play, presence, scoped comms, memory discipline, persona-first UI |
| **Act 2** | **v1.1** | Persistence layer — global heartbeat when UI is away, phone play, world package export/import |
| **Act 3** | **Phase 4+** | In-world work — commissions, debate at locations, commons ([23-in-world-work.md](23-in-world-work.md)) |

Act 3 is fully specified for later phases; it is **not** part of the v1 release gate. See [personas.md](personas.md) and [20-product-principles.md](20-product-principles.md).

## Milestones

### v1 — spatial wedge (first implementation target)

**Outcome:** A solo operator can play as the persona across two or more scenes, with NPCs that respect presence, scoped communication, and memory privacy, while the application is running.

**Release gate:** Spatial golden path + OQ-1/OQ-3 ([17-acceptance-criteria.md](17-acceptance-criteria.md)).

**Planned first-run:** Load fixture `demo-spatial-v1` (specified, not yet bundled) — [guides/first-run-experience.md](guides/first-run-experience.md).

**v1 persistence note:** Worlds run while the app is open; tab-visible idle ticks are acceptable. Global heartbeat when the UI is disconnected ships in **v1.1** (see below)—this is scope sequencing, not a retreat from the persistent-world vision.

### v1.1 — persistence layer (Phase 2.5 in specs)

**Outcome:** World continues idle orchestration when the operator is away; phone/speakerphone flows; portable world packages.

| Capability | Primary spec |
|------------|--------------|
| Phone, speakerphone, mirror stubs | [04-communication.md](04-communication.md), [21-cross-scene-awareness.md](21-cross-scene-awareness.md) |
| Global server heartbeat | [08-real-world-capabilities.md](08-real-world-capabilities.md) §8 |
| World package export/import | [11-data-model.md](11-data-model.md) DM-4 |
| Explicit knock/phone answer flows | [21-cross-scene-awareness.md](21-cross-scene-awareness.md) |

### Post-v1 (design complete; implementation later)

| Theme | Phase (spec) | Primary spec |
|-------|--------------|--------------|
| Observer polish, approvals, inspector | 3 | [07-approvals.md](07-approvals.md), [14-web-ui.md](14-web-ui.md) |
| In-world work schema | 3.5 | [23-in-world-work.md](23-in-world-work.md) |
| Commission runtime, web/FS tools | 4+ | [06-web-tools.md](06-web-tools.md), [08-real-world-capabilities.md](08-real-world-capabilities.md) |
| Debate `scene.activity` | 4.5 | [23-in-world-work.md](23-in-world-work.md) |
| Maps, ComfyUI | 6 | [18-location-maps.md](18-location-maps.md), [19-comfyui-media.md](19-comfyui-media.md) |

## Feature matrix

| User-visible capability | v1 | v1.1 | Post-v1 | Spec |
|-------------------------|:--:|:----:|:-------:|------|
| Multi-scene + exits + presence | yes | | | [03](03-locations-and-presence.md), [01](01-world-model.md) |
| Public / whisper / DM | yes | | | [04](04-communication.md) |
| Cross-scene knock signals | yes | | | [21](21-cross-scene-awareness.md) |
| Memory + mandatory recall + MP-1 privacy | yes | | | [02](02-memory.md) |
| GpuResourceQueue + streaming UI | yes | | | [00](00-inference-runtime.md), [14](14-web-ui.md) |
| Observer Studio + narrator | yes | | | [09](09-roles-and-privilege.md), [14](14-web-ui.md) |
| Demo world `demo-spatial-v1` | yes | | | [20](20-product-principles.md) §8, [fixture](../tests/fixtures/demo-world/README.md) |
| Output quality CI (OQ-1, OQ-3) | yes | | | [22](22-output-quality.md), [17](17-acceptance-criteria.md) |
| Phone play | | yes | | [04](04-communication.md), [21](21-cross-scene-awareness.md) |
| Global heartbeat (UI disconnected) | | yes | | [08](08-real-world-capabilities.md) §8 |
| World package import/export | | yes | | [11](11-data-model.md) |
| Character authoring UI wizard | | | Phase 3 | [24](24-character-authoring.md) |
| Commissions / in-world work runtime | | | Phase 4+ | [23](23-in-world-work.md) |
| Filesystem / web-tools / scheduler | | | Phase 4+ | [06](06-web-tools.md), [08](08-real-world-capabilities.md) |
| Mini-map (structured layout) | yes | | | [14](14-web-ui.md) §21.1 |
| Mini-map (shapes, building envelopes) | | yes | | [14](14-web-ui.md) §21.2–§21.3 |
| Architect World onboarding | | | Phase 3 | [20](20-product-principles.md) §8, [25](25-map-authoring.md) |
| MapDraft + World builder wizard | | | Phase 6 | [25](25-map-authoring.md), [14](14-web-ui.md) §21.5 |
| Enhance layout (existing worlds) | | | Phase 6 | [25](25-map-authoring.md) |
| Evolving geography (in-map add) | | | Phase 6 | [25](25-map-authoring.md), [01](01-world-model.md) |
| World map + floor plans (Phase 6a) | | | Phase 6 | [18](18-location-maps.md) §7, [14](14-web-ui.md) §21.4 |
| Multi-level stack + vertical exits (Phase 6b) | | | Phase 6 | [18](18-location-maps.md) §8 |
| ComfyUI, plugins | | | Phase 6+ | [19](19-comfyui-media.md), [15](15-plugin-platform.md) |

## Phase number glossary

Specs use both **version tags** and **implementation phase** numbers:

| Version tag | Spec phase | Focus |
|-------------|------------|--------|
| **v1** | Phase 1–2 | Inference spike + spatial wedge + Web UI |
| **v1.1** | Phase 2.5 | Phone, heartbeat, world package |
| — | Phase 3 | Observer polish, approvals, **Architect World** wizard |
| — | Phase 3.5 | In-world work schema (no v1 runtime) |
| — | Phase 4+ | Tools, commission runtime, embeddings |
| — | Phase 4.5 | Debate activity |
| — | Phase 6 | Maps, MapDraft, **World builder**, ComfyUI |

## Planned build order (not started)

**Stack:** [26-system-architecture.md](26-system-architecture.md) (Python backend + Web UI SPA).

Proposed sequence for the first implementation — see root [README.md](../README.md):

1. **Sprint 1** — SQLite, memory, GpuResourceQueue, llama.cpp adapter, tool loop, CLI or single-scene API
2. **Sprint 2** — Spatial wedge, Web UI streaming, demo world load path

Acceptance for v1 tag: golden path in [17-acceptance-criteria.md](17-acceptance-criteria.md).

### Product definition of done (v1 tag)

When implementation begins, add validation that:

- Operator completes golden path steps 1–7 without reading normative specs
- `demo-spatial-v1` loads on reference hardware within a documented time budget
- Known v1 boundaries are documented (no phone, no global heartbeat, no world import)

*Cannot be validated in the design-only phase.*

## Out of scope for v1

Reuse of [20-product-principles.md](20-product-principles.md) §10:

- SillyTavern-compatible UI or character card PNG format
- Phone play, global heartbeat, world package (**v1.1**)
- Image generation, location maps (**future**)
- Vector RAG as primary episodic memory
- Multi-tenant accounts
- Required plugins
- FS / scheduler / web-tools (**Phase 4+**)
- Commissions runtime, debate activity, world commons (**post-v1**)

## Deferred until implementation

| Artifact | Trigger |
|----------|---------|
| [guides/getting-started.md](guides/getting-started.md) (install/run) | First runnable Python API + Web UI or CLI |
| `CHANGELOG.md` | First merged implementation PR |
| Measured p95 / reference hardware profile | First benchmark on reference GPU |
| OpenAPI from code | API implemented per [12-api-sketch.md](12-api-sketch.md) |
| `SECURITY.md` | Network exposure or external security process |
| `CONTRIBUTING.md` | Accepting external PRs |
| Screenshots in guides | UI per [14-web-ui.md](14-web-ui.md); Stitch mockups from [guides/stitch-handoff.md](guides/stitch-handoff.md) Pack A |
| Stitch Pack A wireframes | **Complete** — WF-1–12, WF-17–21; [guides/web-ui-wireframes.md](guides/web-ui-wireframes.md), [guides/design-tokens.yaml](guides/design-tokens.yaml) |
| Checked-in `demo-spatial-v1.sqlite` or seed script | Fixture implementation per [demo-world README](../tests/fixtures/demo-world/README.md) |

## Related documents

- [20-product-principles.md](20-product-principles.md) — PM brief, golden path, metrics
- [personas.md](personas.md) — operator personas and jobs-to-be-done
- [guides/first-run-experience.md](guides/first-run-experience.md) — target first session (design)
- [README.md](README.md) — spec index and reading order
