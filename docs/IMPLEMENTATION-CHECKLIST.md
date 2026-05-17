# Implementation Checklist

Links **Sprint 1/2** work to the **spatial golden path** and **fixture paths**. Normative behavior remains in numbered specs; this is an implementer onboarding aid.

**Status:** v1 + v1.1 **feature-complete**; Phase 3 character draft + cast placement UI. **38 pytest** + golden path 1–8.

### Doc vs implementation (v1 wedge)

| Spec ID | Requirement | Status |
|---------|-------------|--------|
| GP 1–8 | Spatial golden path | Done (`tests/test_golden_path.py`) |
| MP-1 | Mind pool isolation | Done |
| MP-9 | First call memory tools only when blocking | Done (`orchestrator/engine.py`, `test_mp9_ao4.py`) |
| MP-20 | Group diary fan-out | Done |
| AO-4 | Idle round-robin per scene | Done (`idle_scheduler.py`, tab-visible via WS) |
| AO-19/19a | agent_continue + idle suppress | Done |
| CC-11a | Knock no auto-gen | Done |
| INF-5 | Single GPU job | Done |
| OQ-1/OQ-3 | Prompt snapshot / strip | Done |
| UI-REG-1 | Cancel generation | Done |
| UI-R2/R5 | Mermaid in transcript | Done (`MarkdownBody.tsx`) |
| W-1 | Cannot delete last scene | Done (`DELETE .../scenes/{id}`) |
| memory_read | Doc 02 tool | Done |
| MEM-PERF | Scale fixtures + perf gates | Done (ci profile; `pytest -m slow` for reference) |
| HB-1 | Global heartbeat idle | Done (`idle_scheduler`, operator settings) |
| diary_read | Doc 02 tool | Done |
| UI-1 / UI-2 | Queue strip + selection rationale | Done (`GpuQueueStrip`, message ⓘ) |
| UI-M4 | Memory inspector from People | Done |
| CC-11b | Dismiss knock signal | Done (PATCH signal) |
| CC-6 / OBS-6 | Observer digest (signals + channels) | Done (`GET .../observer/digest`, Observer Studio UI) |
| First-run UX pass | guides/first-run-experience.md | API automated (`test_first_run_experience_api`); manual UI walkthrough |

### Remaining for v1 tag

| Area | Status |
|------|--------|
| WebSocket events + `eventSeq` | Done |
| UI cancel generation (UI-REG-1) | Done |
| Whisper/DM target picker | Done |
| Mermaid in transcript (UI-R2/R5) | Done |
| MP-9 blocking memory tools on first turn | Done |
| MEM-PERF / scale fixtures | Done (`tests/test_memory_perf.py`, `memory-scale/`) |
| Idle `roundRobin` (AO-4) | Done (tab-visible) |
| v1.1 heartbeat | Done (settings UI + HB-1) |
| DM-4 | World package export/import | Done (`world_package.py`, `test_world_package.py`) |
| CC-8–CC-13 phone play | Done (`communication/phone.py`, `test_phone.py`) |
| CHAR-1–CHAR-5 | Character draft API + Settings UI | Done (`character_authoring.py`, `test_character_authoring.py`) |
| UI-CHAR-2 | Observer + Settings draft entry | Done |
| LP-1 / roster | Unplaced cast + summon/leave UI | Done (`PeopleRail`, `test_presence_roster.py`) |
| Phase 3+ Architect wizard, maps, commissions | Spec only (UI wizard shell deferred) |

## Sprint 1 — inference + memory spike

| Step | Deliverable | Spec | Fixture / test |
|------|-------------|------|----------------|
| 1 | Migration 001 + `PersistencePort` | [11-data-model.md](11-data-model.md), [26-system-architecture.md](26-system-architecture.md) §2.3 | — |
| 2 | Memory: loci, diary, mandatory recall, MP-1 | [02-memory.md](02-memory.md) | [tests/fixtures/memory-scale/](../tests/fixtures/memory-scale/README.md) (later) |
| 3 | `GpuResourceQueue` + llama.cpp adapter | [00-inference-runtime.md](00-inference-runtime.md) | INF-5* integration tests |
| 4 | Tool registry + invoke loop | [05-tool-calling.md](05-tool-calling.md) | Mock LLM |
| 5 | `stripReasoning` before durable writes | [16-learning.md](16-learning.md) | [tests/fixtures/strip-reasoning/](../tests/fixtures/strip-reasoning/README.md) |
| 6 | Single scene, one NPC, CLI or `POST .../generate` | [12-api-sketch.md](12-api-sketch.md) §7 | — |
| 7 | OQ-1 prompt snapshot (mock LLM) | [22-output-quality.md](22-output-quality.md) | [tests/fixtures/output-quality/](../tests/fixtures/output-quality/) |

**Defer Sprint 1:** Character draft API ([24](24-character-authoring.md) §14), MapDraft routes ([25](25-map-authoring.md)), commission runtime ([23](23-in-world-work.md)).

**Embeddings:** `EmbeddingRecord` table in migration 001; debounced embed jobs MAY stub empty until Phase 4+ ([02-memory.md](02-memory.md) §7, INF-13).

## Sprint 2 — spatial wedge (v1 tag)

| Step | Deliverable | Spec | Golden path step |
|------|-------------|------|------------------|
| 1 | Load `demo-spatial-v1` | [tests/fixtures/demo-world/](../tests/fixtures/demo-world/README.md) | GP-SETUP |
| 2 | Two scenes, presence, public/whisper | [03](03-locations-and-presence.md), [04](04-communication.md) | GP 1–2 |
| 3 | Elsewhere roster, scene switch | [14-web-ui.md](14-web-ui.md) §0, §4 | GP 3 |
| 4 | Knock signals (no auto-gen) | [21-cross-scene-awareness.md](21-cross-scene-awareness.md) CC-11a–d | GP 4 |
| 5 | Observer Studio meta + fixture edit | [09](09-roles-and-privilege.md), [14](14-web-ui.md) §5 | GP 5 |
| 6 | Restart hydration | [11](11-data-model.md), MP-11 | GP 6 |
| 7 | Group scene diary fan-out | [02-memory.md](02-memory.md) MP-20 | GP 7 |
| 8 | `agent_continue` chain (AO-19) | [13-agent-orchestration.md](13-agent-orchestration.md) | GP 8 |
| 9 | Web UI streaming + structured mini-map | [14-web-ui.md](14-web-ui.md) §0, §21.1 | UI-MAP-ACC1–4 |
| 10 | OQ-3 strip in transcript/diary | [22](22-output-quality.md) | GP + OQ-3 |

## v1 ship gate

- [x] Golden path steps 1–8 pass (`tests/test_golden_path.py`)
- [x] OQ-1, OQ-3 in CI integration layer
- [ ] Operator can complete [guides/first-run-experience.md](guides/first-run-experience.md) without reading normative specs (manual UX pass)

## Explicitly not Sprint 2

| Capability | Phase | Spec |
|------------|-------|------|
| Phone, global heartbeat, world package | v1.1 | [21](21-cross-scene-awareness.md), [08](08-real-world-capabilities.md), DM-4 |
| MapDraft, WorldMapCanvas | Phase 6 | [18](18-location-maps.md), [25](25-map-authoring.md) |
| Character authoring UI | Phase 3 | [24](24-character-authoring.md) |
| Commissions / debate runtime | Phase 4+ | [23](23-in-world-work.md) |

## Fixture inventory

| Path | Purpose | Status |
|------|---------|--------|
| [tests/fixtures/demo-world/demo-spatial-v1.json](../tests/fixtures/demo-world/demo-spatial-v1.json) | World seed spec | Spec JSON |
| [tests/fixtures/strip-reasoning/](../tests/fixtures/strip-reasoning/) | MP-14–MP-18, OQ-3 | Samples |
| [tests/fixtures/output-quality/](../tests/fixtures/output-quality/) | OQ-1, nightly script | Snapshots |
| [tests/fixtures/memory-scale/](../tests/fixtures/memory-scale/) | MEM-PERF-*, MEM-ACC-1 | Generator spec |
| [tests/fixtures/map-layouts/](../tests/fixtures/map-layouts/) | MAP-GEN-ACC-* | Present |

## Related

- [REQUIREMENTS-INDEX.md](REQUIREMENTS-INDEX.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
- [README.md](../README.md)
