# 20 — Product Principles

North-star journey, v1 wedge, presets, metrics, and operator onboarding.

## 1. Positioning

> **A persistent stage for AI characters—memory-grounded, spatial, operator-run.**

Altrasia is not a chat skin (SillyTavern) or a coding agent (Hermes). It is a **single-machine narrative studio** with durable geography and memory discipline. The same stage supports **in-world work**—research commissions, deliberation at locations, team focus areas—without a separate product mode or bypassing spatial rules ([23-in-world-work.md](23-in-world-work.md)) — **Act 3**, not v1.

### Product narrative (Acts)

| Act | Milestone | Outcome |
|-----|-----------|---------|
| **Act 1** | **v1** | Spatial wedge — multi-scene play, presence, memory, persona-first UI |
| **Act 2** | **v1.1** | Persistence layer — heartbeat when UI away, phone, world package |
| **Act 3** | Phase 4+ | In-world work — commissions, debate, commons |

Detail: [ROADMAP.md](ROADMAP.md). Personas: [personas.md](personas.md).

### Planned capability by milestone

| Milestone | Operator expectation |
|-----------|---------------------|
| **v1** | Spatial play while the application is running; tab-visible idle ticks acceptable when global heartbeat is off |
| **v1.1** | World continues idle orchestration when UI disconnected; phone; portable world packages |
| **Rationale** | Scope and risk for first implementation—not a retreat from “persistent world” vision |

A world that only runs while the Web UI tab is open is an **anti-pattern** for long-term vision; v1 **MAY** use tab-visible idle until heartbeat ships in v1.1 ([08-real-world-capabilities.md](08-real-world-capabilities.md) §8).

## 2. Primary operator (confirmed)

| Aspect | Choice |
|--------|--------|
| Play style | **Solo player** — persona is main voice |
| Tuning | **Observer side-chat** in Studio slide-over |
| UI hierarchy | Persona transcript hero; Observer secondary |

## 3. v1 wedge (confirmed)

**Spatial world** — multi-scene, presence, movement, scoped comms feel tangible.

Release-critical: Phase 2 spatial features before polish layers. Maps ([18-location-maps.md](18-location-maps.md)) accelerate wedge in v1.1+.

## 4. UX principles

| ID | Principle |
|----|-----------|
| UI-1 | **Legible causality** — show memory tools, framing, queue. |
| UI-2 | **Queue honesty** — GPU busy and wait visible. |
| UI-3 | **Scope clarity** — comm scopes and narrator visually distinct. |

## 5. Golden path

### v1 (spatial)

1. World with ≥2 scenes, linked exits, 2+ NPCs, persona in scene A
2. Public line → NPC reply; whisper isolated in prompts
3. Persona moves to scene B; elsewhere roster correct
4. Knock signal tracked (CC-2, CC-11a); emergent response optional; v1.1 adds phone play
5. Observer meta-chat or tools update world; framing reflects
6. Restart → state hydrates (MP-11)
7. Group scene: both NPCs retain witnessed dialogue in diary after restart (MP-20)

### v1.1 addendum

Phone with per-endpoint speakerphone: bystanders overhear **one side** by default; speakerphone toggled **per scene** (not auto-both-rooms). Mirror stubs, knock→answer ([04-communication.md](04-communication.md) §3, [21-cross-scene-awareness.md](21-cross-scene-awareness.md)).

See [17-acceptance-criteria.md](17-acceptance-criteria.md).

## 6. Presets

| Preset | Idle activity | `agentContinue` | `maxContinueDepth` | Default for |
|--------|---------------|-----------------|-------------------|-------------|
| **Solo story** | Moderate | on | 2 | v1 default |
| **Writer** | Off | on | 3 | Focused drafting |
| **Aquarium** | Higher | off or 1 | 1 | Watch agents; requires queue honesty UI |

Orchestration detail: [13-agent-orchestration.md](13-agent-orchestration.md) §6.2.

## 7. Success metrics (targets)

**Design-phase note:** Targets below are **design goals**. Baselines (reference GPU profile, measured p95) are **TBD at implementation**. Where metrics surface (CI, in-app queue strip) is deferred until a runnable build exists — see [ROADMAP.md](ROADMAP.md).

| Metric | Target |
|--------|--------|
| Golden path pass rate | 100% on reference GPU before v1 tag |
| p95 persona → grounded NPC reply | Document per hardware; show queue wait |
| Restart continuity | MP-11 scenarios pass |
| MP-1 leakage | Zero failures in CI |
| OQ-1 / OQ-3 | Pass in v1 CI integration layer ([17-acceptance-criteria.md](17-acceptance-criteria.md) §2b) |

## 8. Onboarding

### v1 — demo world (before wizard)

Operators SHOULD reach first play without manual world construction:

1. Open or import bundled **demo world** fixture `demo-spatial-v1` ([tests/fixtures/demo-world/README.md](../tests/fixtures/demo-world/README.md))
2. Run spatial golden path or exploratory play
3. Optional: `POST /api/v1/worlds` with `{ "fixtureId": "demo-spatial-v1" }`

No wizard UI is required for v1 beyond **load demo**.

### Architect World (Phase 3)

**Architect World** — fast path to playable spatial wedge:

1. Define initial scene graph (fixture, template, or manual seed)
2. Grow scenes and exits while `layoutDesignMode` is true
3. CharacterDraft cast ([24-character-authoring.md](24-character-authoring.md))
4. Test generation and settings

No LLM MapDraft. Geography locks on **Lock geography** or **first play** ([25-map-authoring.md](25-map-authoring.md) MAP-AUTH-LOCK-*).

### World builder (Phase 6)

**World builder** — full spatial authoring wizard:

1. World name
2. **Required** MapDraft `mini` layout + operator approve ([25-map-authoring.md](25-map-authoring.md))
3. Optional cascade: site → stack layouts
4. CharacterDraft cast
5. Test generation and defaults

### Evolving worlds (post-lock)

> A persistent stage that grows with your story—new places enter the world when you and the Observer author them, never when NPCs hallucinate them.

After geography lock, Observer/Architect MAY **add locations in-map** and characters move via presence/exits ([25-map-authoring.md](25-map-authoring.md) MAP-GROW-*, MAP-MOVE-*). **Enhance layout** (Phase 6) runs optional MapDraft on any existing world; never required for worlds already in play.

## 9. Data safety

| Feature | Description |
|---------|-------------|
| World package | Zip: `altrasia.db` + `assets/` — export + import gate **v1.1** ([11-data-model.md](11-data-model.md) DM-4) |
| Auto-backup | On world save (implementation) |

## 10. v1 scope

### MUST ship

- Spatial golden path
- Memory subsystem + mandatory recall + blocking
- GpuResourceQueue + streaming UI
- Observer Studio meta-chat + Narrate
- Cross-scene tracking (CC-1–CC-7, CC-11a–CC-11d)
- Demo world fixture `demo-spatial-v1`
- Output quality CI (OQ-1, OQ-3)

### SHOULD NOT ship (v1 release gate)

Historical v1 gate intent — these were excluded from the **v1 CI release gate**:

- FS, scheduler, web-tools
- Semantic embeddings, reflection
- Plugins, maps, ComfyUI
- Phone play (v1.1)

### Alpha wedge (local tree)

The following exist in the Alpha tree with mock, stub, or off-by-default behavior. They are **not v1 CI blockers**; production depth is tracked in [SPEC-GAPS.md](SPEC-GAPS.md).

| Capability | Alpha wedge status | Caveat |
|------------|-------------------|--------|
| Web-tools | Wedge | Mock fetch by default (`webToolsMock`) |
| FS agent | Wedge | Approval on write; jail path |
| Scheduler | Stub | `schedule_create` records stub only |
| Reflection (AO-8) | Wedge | `reflectionEnabled: false` by default |
| Embeddings / rerank | Wedge | Hybrid search when embed URL set |
| Plugins | Wedge | `enableServerPlugins` off by default |
| MapDraft / map artifacts | Wedge | MAP-ACC UI depth open |
| ComfyUI | Stub | Portrait endpoint; mock without ComfyUI URL |
| Commissions / debate / commons API | Wedge | Commons has no Web UI panel |
| Idle social / banter | Wedge | Policy-gated dyad sessions |

### Deferred but intentional (not dropped)

These capabilities are specified for later phases; they preserve prior design intent from the custom SillyTavern deployment and OldPlans:

| Capability | Spec | Why deferred for v1 |
|------------|------|---------------------|
| **World heartbeat** — global `idle_timer` when UI disconnected | [08-real-world-capabilities.md](08-real-world-capabilities.md) §8 | **v1.1** prerequisite (HB-1–HB-5); v1 uses tab-visible idle when heartbeat off |
| **Scheduled tasks** — webhooks, cron, architect_fs jobs | [08-real-world-capabilities.md](08-real-world-capabilities.md) §2 | Phase 4+; distinct from world heartbeat |
| Filesystem / web-tools | [07-approvals.md](07-approvals.md), [08-real-world-capabilities.md](08-real-world-capabilities.md) | Risk surface; Phase 4+ |
| Phone play | [04-communication.md](04-communication.md), [21-cross-scene-awareness.md](21-cross-scene-awareness.md) | v1.1 bundle with heartbeat and world package |
| World package import/export | [11-data-model.md](11-data-model.md) DM-4 | v1.1 |

Operators enable global heartbeat in **server settings** when v1.1 ships (default off at first v1.1 release). See **Planned capability by milestone** above.

## 11. Implementation phases

| Phase | Focus |
|-------|--------|
| 1 | Inference + memory spike (CLI) |
| 2 | Spatial wedge + Web UI streaming |
| 2.5 | **v1.1** — phone, global heartbeat, world package, CC-11 phone/knock answer |
| 3 | Observer polish, approvals, inspector, character authoring |
| 3.5 | In-world work — **runtime + UI wedge shipped**; production depth in [SPEC-GAPS.md](SPEC-GAPS.md) |
| 4+ | Web/FS tools, commission depth, embeddings |
| 4.5 | Debate acceptance paths — wedge shipped |
| 6 | Maps, ComfyUI — **Alpha wedge shipped**; MAP-ACC / live ComfyUI depth open |

### In-world work (Alpha wedge vs spec depth)

| Capability | Spec | Status |
|------------|------|--------|
| Commissions (research errands; default deliverable → assignee mind pool) | [23-in-world-work.md](23-in-world-work.md) | **Alpha wedge** — runtime + UI; live web/FS depth open |
| Debate `scene.activity` | [23-in-world-work.md](23-in-world-work.md) | **Alpha wedge** — runtime + UI |
| World commons, provenance on external facts | [02-memory.md](02-memory.md) MP-21–MP-22 | **API wedge** — no Web UI panel |
| Reflection, MemoryLink, PersonaProposal | [16-learning.md](16-learning.md) §6 | **Alpha wedge** — default off |
| Idle social / banter | [13-agent-orchestration.md](13-agent-orchestration.md) §5 | **Alpha wedge** |

v1 golden path and MUST-ship list are **unchanged**. In-world work MUST NOT dilute spatial wedge acceptance.

## Related documents

- [ROADMAP.md](ROADMAP.md)
- [personas.md](personas.md)
- [guides/first-run-experience.md](guides/first-run-experience.md)
- [14-web-ui.md](14-web-ui.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
- [23-in-world-work.md](23-in-world-work.md)
- [24-character-authoring.md](24-character-authoring.md)
- [README.md](README.md)
