# 20 — Product Principles

North-star journey, v1 wedge, presets, metrics, and operator onboarding.

## 1. Positioning

> **A persistent stage for AI characters—memory-grounded, spatial, operator-run.**

WorldEngine is not a chat skin (SillyTavern) or a coding agent (Hermes). It is a **single-machine narrative studio** with durable geography and memory discipline.

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
4. Knock signal tracked (CC-2); v1.1 adds phone play
5. Observer meta-chat or tools update world; framing reflects
6. Restart → state hydrates (MP-11)

### v1.1 addendum

Phone with per-endpoint speakerphone: bystanders overhear **one side** by default; speakerphone toggled **per scene** (not auto-both-rooms). Mirror stubs, knock→answer ([04-communication.md](04-communication.md) §3, [21-cross-scene-awareness.md](21-cross-scene-awareness.md)).

See [17-acceptance-criteria.md](17-acceptance-criteria.md).

## 6. Presets

| Preset | Idle activity | Default for |
|--------|---------------|-------------|
| **Solo story** | Moderate | v1 default |
| **Writer** | Off | Focused drafting |
| **Aquarium** | Higher | Watch agents; requires queue honesty UI |

## 7. Success metrics (targets)

| Metric | Target |
|--------|--------|
| Golden path pass rate | 100% on reference GPU before v1 tag |
| p95 persona → grounded NPC reply | Document per hardware; show queue wait |
| Restart continuity | MP-11 scenarios pass |
| MP-1 leakage | Zero failures in CI |

## 8. Onboarding

Web UI **world wizard** (Phase 3):

1. World name
2. Two scenes + one exit
3. Two characters + Observer
4. Test generation
5. Set diary window and max context defaults

## 9. Data safety

| Feature | Description |
|---------|-------------|
| World package | Zip: `worldengine.db` + `assets/` |
| Auto-backup | On world save (implementation) |

## 10. v1 scope

### MUST ship

- Spatial golden path
- Memory palace + mandatory recall + blocking
- GpuResourceQueue + streaming UI
- Observer Studio meta-chat + Narrate
- Cross-scene tracking (CC-1–CC-7)

### SHOULD NOT ship (v1)

- FS, scheduler, web-tools
- Semantic embeddings, reflection
- Plugins, maps, ComfyUI
- Phone play (v1.1)

## 11. Implementation phases

| Phase | Focus |
|-------|--------|
| 1 | Inference + memory spike (CLI) |
| 2 | Spatial wedge + Web UI streaming |
| 2.5 | Cross-scene comms (v1.1) |
| 3 | Observer polish, approvals, inspector |
| 4+ | Embeddings, Architect tools, plugins |
| 6 | Maps, ComfyUI |

## Related documents

- [14-web-ui.md](14-web-ui.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
- [README.md](README.md)
