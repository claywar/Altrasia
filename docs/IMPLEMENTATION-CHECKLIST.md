# Implementation Checklist

Links **Sprint 1/2** work to the **spatial golden path** and **fixture paths**. Normative behavior remains in numbered specs; this is an implementer onboarding aid.

**Status:** v1 + v1.1 **feature-complete**; Phase 3–6 wedge (commissions, debate, MapDraft, approvals, evidence, briefing, policy UI, reflection, idle social). **224 pytest** collected (1 `slow` deselected; CI subset may exclude slow) + golden path 1–8 + Playwright e2e in CI.

**Outstanding (full spec depth):** see [SPEC-GAPS.md](SPEC-GAPS.md) and [BACKLOG.md](BACKLOG.md) T-100+.

### Doc vs implementation (v1 wedge)

| Spec ID | Requirement | Status |
|---------|-------------|--------|
| GP 1–8 | Spatial golden path | Done (`tests/test_golden_path.py`) |
| MP-1 | Mind pool isolation | Done |
| MP-9 | First call memory tools only when blocking | Done (`orchestrator/engine.py`, `test_mp9_ao4.py`) |
| MP-20 | Group diary fan-out | Done |
| AO-4 | Weighted idle/banter selection (AO-4 / AO-4w) | Done (`social_selection.py`, `idle_scheduler.py`, tab-visible via WS) |
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
| UI-D3 | Character profile summary modal (click name/avatar) | Done (`CharacterProfileModal`, `CastRow`) |
| CC-11b | Dismiss knock signal | Done (PATCH signal) |
| CC-6 / OBS-6 | Observer digest (signals + channels) | Done (`GET .../observer/digest`, Observer Studio UI) |
| First-run UX pass | guides/first-run-experience.md | Done (launcher steps + `test_first_run_experience_api`) |

### Remaining for v1 tag

| Area | Status |
|------|--------|
| WebSocket events + `eventSeq` | Done |
| UI cancel generation (UI-REG-1) | Done |
| Whisper/DM target picker | Done |
| Mermaid in transcript (UI-R2/R5) | Done |
| MP-9 blocking memory tools on first turn | Done |
| MEM-PERF / scale fixtures | Done (`tests/test_memory_perf.py`, `memory-scale/`) |
| Idle weighted selection (AO-4) | Done (tab-visible) |
| v1.1 heartbeat | Done (settings UI + HB-1) |
| DM-4 | World package export/import | Done (`world_package.py`, `test_world_package.py`) |
| CC-8–CC-13 phone play | Done (`communication/phone.py`, `test_phone.py`) |
| CHAR-1–CHAR-5 | Character draft API + Settings UI | Done (`character_authoring.py`, `test_character_authoring.py`) |
| UI-CHAR-2 | Observer + Settings draft entry | Done |
| LP-1 / roster | Unplaced cast + summon/leave UI | Done (`PeopleRail`, `test_presence_roster.py`) |
| Architect World (Phase 3) | Scene CRUD + lock geography + launcher | Done (`world_geography.py`, `SceneGeographyPanel`) |
| MAP-GROW-1/2 | In-map scene growth after lock (connected exits) | Done |
| GET /characters | World cast list | Done |
| Commissions (v1.5 schema) | CRUD API + Settings UI | Done (`commissions.py`, `CommissionsPanel`) |
| COM-6 / commission_started | Presence gate + start + mind deliverable | Done (`commission_runner.py`) |
| Phase 4+ commission_tick | Scheduler poll while running | Done (`tick_running_commissions`, idle/heartbeat) |
| Commission pause | Defer start during persona dialogue at target | Done (`persona_dialogue_active_at_scene`) |
| UI-C1 | Per-world pause in top bar | Done (`POST .../pause`, top bar Pause/Resume) |
| OBS-6 commissions | Open errands in Observer digest + Start from digest | Done |
| Phase 3+ MapDraft | LLM layout draft + commit | Done (`map_authoring.py`, `MapDraftPanel`) |
| Debate activity | scene.activity DEB-1/2 + UI | Done (`debate_activity.py`, `DebatePanel`) |
| Commission web tools | allowedTools + mock webtools_invoke | Done |
| First-run UX pass | guides/first-run-experience.md | Done |
| MP-21 EvidenceRecord | Provenance on commission / memory_store | Done (`evidence.py`) |
| APR-1 Approvals | Web tool approval queue + UI banner | Done (`approvals.py`, `ApprovalsBanner`) |
| UI-MAP-W3 | World map overlay (Phase 6 minimal) | Done (`WorldMapOverlay`) |
| World policy UI | PATCH `/policy`, Settings toggles | Done (`WorldPolicyPanel`) |
| Briefing fixtures | Scene board + world pool | Done (`briefing.py`, `BriefingPanel`) |
| UI-M4 evidence | Provenance in Memory inspector | Done |
| COM-4 | `world_pool_at_target` / `both` deliverables | Done (`commissions.py`) |
| COM-ACC-1/3, DEB-ACC-1 | Post-v1 acceptance paths | Done (`test_in_world_acceptance.py`) |
| POST force-complete | API sketch §10 | Done |
| MP-22 world commons | Gated recall + PUT/GET API | Done API (`commons.py`, `test_commons.py`); **Web UI panel not in tree** |
| citeProvenanceInPrompt | World policy + prompt inject | Done (`world_config`, `engine.py`) |

### Alpha wedge — additional shipped features

| Spec ID | Requirement | Status |
|---------|-------------|--------|
| AO-8 | Reflection nightly + on-demand | Done (`reflection/`, migration 007, `test_reflection.py`) — `reflectionEnabled` off by default |
| AO-4c / AO-22 wedge | Idle social / banter dyads | Done (`banter_runner.py`, `banter_gates.py`, `test_idle_social.py`) |
| — | Discussion deliverables | Done (`discussion_deliverables.py`, `test_discussion_deliverables.py`) |
| AO-17 | speak_intent tie-break | Done (`engine.py`, `test_speak_intent.py`) |
| — | Embedding rerank in recall | Done (`memory/service.py`) |

### Spec target — not in tree

Operator loci PATCH, `map_generate` / `map_set_hotspot`, live ComfyUI pipeline, commons Web UI, real scheduler beyond stub — see [SPEC-GAPS.md](SPEC-GAPS.md).

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
- [x] Operator can complete [guides/first-run-experience.md](guides/first-run-experience.md) without reading normative specs (launcher walkthrough + automated API tests)

## Originally deferred in Sprint 2 (now in tree)

| Capability | Phase | Status |
|------------|-------|--------|
| Phone, global heartbeat, world package | v1.1 | Done |
| MapDraft, minimal world map | Phase 6 wedge | Done; full canvas in BACKLOG |
| Character authoring UI | Phase 3 | Done |
| Commissions / debate runtime | Phase 4+ | Done |

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
