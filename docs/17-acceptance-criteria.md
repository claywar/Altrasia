# 17 — Acceptance Criteria

Test matrix mapping requirement IDs to verifiable scenarios. v1 release gate: **spatial golden path** + inference spike tests.

## 1. Test layers

| Layer | Runs in CI | Runs nightly |
|-------|-----------|--------------|
| Unit | Yes | Yes |
| Integration | Yes (mock LLM) | Yes |
| Golden path e2e | No | Yes (real llama.cpp, Qwen3.6-35B-A3B) |

Reference model profile: `qwen3.6-35b-a3b` / router id `Qwen3.6-35B-A3B`.

### GP-SETUP (optional helper)

Golden path steps MAY start from fixture `demo-spatial-v1` ([tests/fixtures/demo-world/demo-spatial-v1.json](../tests/fixtures/demo-world/demo-spatial-v1.json)) instead of manual world construction. Not a separate release blocker if manual setup is documented.

## 2. Spatial golden path (v1 release)

| Step | Verifies |
|------|----------|
| 1 | Create world with ≥2 scenes, exits, 2 NPCs, persona in scene A |
| 2 | Public line → NPC reply; whisper does not leak in other cast prompts |
| 3 | Move persona to scene B; elsewhere roster shows NPC + scene label |
| 4 | Knock on exit → `CrossSceneSignal` `pending`; target scene banner; persists after restart (CC-2, CC-11d). No auto-generation on knock create (CC-11a) |
| 5 | Observer meta-chat renames scene / fixture; framing updates (OBS-2, UI-OBS-CHAT) |
| 6 | Restart server; presence, exits, signals hydrate (MP-11, CC-2) |
| 7 | Group scene: Alice and Bob present; Alice public line → Bob replies; restart → Bob mandatory recall diary contains Alice's line (MP-6, MP-17, MP-20) |
| 8 | Same scene + Carol present: Alice public → Bob reactive; Bob line → Alice `agent_continue` before Carol idle (AO-19) |

## 2b. Output quality (v1 blocking)

| ID | Test |
|----|------|
| OQ-1 | Roleplay model profile includes quality addendum when enabled |
| OQ-3 | Reasoning blocks absent from next-turn visible transcript after strip |

Fixtures: `tests/fixtures/output-quality/` (see §10). Integration CI MUST run OQ-1 prompt assertion with mock LLM; OQ-3 MAY share `tests/fixtures/strip-reasoning/`.

## 3. Requirement matrix

### World and presence

| ID | Test |
|----|------|
| W-1 | Delete last scene rejected |
| W-3 | Character cannot be present in two scenes |
| LP-1 | Join removes from other scene present list |
| CC-1 | exitsJson round-trip |
| CC-3 | Elsewhere roster includes presentSceneId |
| CC-11a | POST knock does not enqueue GenerationJob |
| CC-11b | PATCH signal acknowledge/expire does not append NPC scene line |
| CC-11c | Door `broken` + join requires explicit tool path; no silent fixture retcon |
| CC-11d | Knock banner visible at target scene after persona switch |

### Memory

| ID | Test |
|----|------|
| MP-1 | Mind search for Alice never returns Bob mind loci |
| MP-8 | Observer generation includes mandatory recall block |
| MP-9 | First model call with blocking on has only memory_* tools |
| MP-11 | After restart, recall contains loci not lost transcript-only facts |
| MP-6 | Diary segment text includes witnessed persona/cast lines in rolling window, not speaker-only |
| MP-17 | Diary snippet uses stripped outputText per line; think blocks absent |
| MP-20 | After Alice speaks and Bob replies in group scene, both diaries contain same dedupeKey segment |
| MP-20b | After restart, Bob mandatory recall includes Alice's public line from diary without full transcript |
| MP-14–MP-18 | stripReasoning fixtures: think tags not in diary/loci |
| MP-16 | memory_store with reasoning-only rejected |
| MEM-ACC-1 | 10k randomized hybrid searches: zero Bob mind-pool hits when querying as Alice |
| MEM-ACC-2 | Mandatory recall diary tail ordering matches newest `createdAt` within budget |
| MEM-ACC-5 | Assembled mandatory recall char length ≤ `mandatoryRecallMaxChars` |

### Memory performance (v1 gate)

| ID | Test |
|----|------|
| MEM-PERF-1 | Tool search uses FTS path (no full scan — assert via query plan or mock counter) |
| MEM-PERF-2 | On reference scale fixture: p95 `memory_search` / `diary_search` &lt;50ms |
| MEM-PERF-3 | On reference scale fixture: p95 mandatory recall assembly (cache miss) &lt;100ms |
| MEM-PERF-4 | Recall assembly SQL/API calls scoped to single `characterId` + active `sceneId` only |

### Observer and roles

| ID | Test |
|----|------|
| ROLE-1 | Cast prompt assembly excludes observer digest |
| OBS-5 | World fixture change without tool not persisted |
| OBS-4 | narrator scope visible to present cast only |

### Inference and queue

| ID | Test |
|----|------|
| INF-5 | Two simultaneous unqueued GPU calls impossible |
| INF-5a | Tool recurse holds same lease |
| INF-5d | At maxDepth, idle job not enqueued |
| INF-2 | Change modelProfile without server restart |
| STR-1–STR-4 | Stream events received; final DB row post-strip |
| — | Router model id matches `Qwen3.6-35B-A3B` |

### Orchestration

| ID | Test |
|----|------|
| AO-11 | Second job waits until lease released |
| AO-12 | Idle tick skipped when queue full |
| AO-4a | After operator public line, reactive job characterId is **not** chosen by `Scene.roundRobinIndex` advance alone |
| AO-19 | Alice public → Bob reactive (`continueDepth=0`); Bob line → Alice `agent_continue` (`continueDepth=1`); Carol not scheduled until chain ends or idle tick |
| AO-19a | While continue chain active at scene, `idle_timer` does not enqueue for that scene |
| AO-20 | Single operator public line → exactly one reactive GenerationJob |
| AO-17 / AO-18 | Classroom: Teacher asks "capital of France"; Student A has matching mind locus, Student B does not → reactive job schedules Student A; `selectionRationaleJson` includes relevance factor |
| AO-4 | Scene with 3+ eligible NPCs: consecutive `idle_timer` ticks pick among eligible cast via weighted random (not strict round-robin); `Scene.roundRobinIndex` MUST NOT drive selection |
| AO-18a | Operator line "@Bob …" → Bob scheduled when eligible regardless of lower `speechWeight` |

### Communication (v1)

| ID | Test |
|----|------|
| — | canPerceive table: public, whisper, DM, narrator |
| CC-5 | Message with phone metadata parses; UI does not send phone in v1 |
| — | Meta messages excluded from cast prompt assembly |

### Web UI (v1 — when implemented)

Normative UI requirements: [14-web-ui.md](14-web-ui.md). Wireframes: [guides/web-ui-wireframes.md](guides/web-ui-wireframes.md).

| ID | Test |
|----|------|
| UI-LAY-6 | Scene switch updates center header and right rail Places/People |
| UI-R1–R2 | Markdown list and mermaid diagram render in finalized NPC message |
| UI-R3 | During streaming, transcript shows plain text; markdown after finalize |
| UI-R5 | Invalid mermaid shows fallback text, not blank bubble |
| UI-TRN-1 | No delete or edit control on committed message bubbles |
| UI-REG-1 | Cancel in-flight generation via queue strip; no regen on committed lines |
| UI-2 | GPU enqueue shows visible wait within 500ms |
| UI-SET-* | Change world preset and persona auto-join without editing raw JSON |
| UI-WLD-1 | One active world; load demo without multi-world home |
| UI-S4 / CC-11a | Knock shows banner + Signals; no auto NPC line on knock create |
| UI-MAP-ACC1–4 | Mini-map structured layout: two-scene demo, travelSteps edge length, direction placement, exit↔edge highlight ([14-web-ui.md](14-web-ui.md) §21.1) |
| UI-MAP-ACC5 | v1.1: `mapShape: circle` renders circular footprint; `exitAnchor` on correct rim ([14-web-ui.md](14-web-ui.md) §21.2) |
| UI-MAP-ACC6–8 | v1.1: building envelope around grouped scenes; exterior exit crosses wall; SceneHeader `Structure › Scene` breadcrumb ([14-web-ui.md](14-web-ui.md) §21.3) |

### Meta channel

| ID | Test |
|----|------|
| — | POST meta-message not returned in scene transcript GET |
| — | Cast canPerceive false for channelKind=meta |

## 2c. Reflection smoke (non-blocking)

Optional Alpha wedge validation; **not** a v1 release gate. References `tests/test_reflection.py`.

| Step | Expected |
|------|----------|
| Enable `reflectionEnabled` on demo world policy | Policy PATCH succeeds |
| POST on-demand reflect for one character with diary input | `reflection-runs` row with `status: done` or documented skip |
| PersonaProposal approve/reject | Character definition updates only after operator approve |

## 4. v1.1 gate (addendum)

Single milestone: phone, global heartbeat, world package, full knock/phone answer ([20-product-principles.md](20-product-principles.md) Phase 2.5).

| ID | Test |
|----|------|
| C-9 / CC-8 | Kitchen bystander hears Alice phone lines only, not Bob leg (handset) |
| C-10 / CC-9 | Speakerphone on kitchen only: kitchen bystanders hear both sides; hall bystanders still one side |
| C-11 | Speakerphone on both ends independently toggled |
| C-5 / CC-10 | Mirror stub on remote transcript; perception rules apply |
| CC-11 | Knock/phone answer may enqueue generation or join (operator-initiated) |
| CC-12 | AO-2 `phone_target` / `knock_answered` triggers enabled |
| HB-1 | With global heartbeat on and no WebSocket clients, `idle_timer` fires |
| HB-2 | Heartbeat idle respects GpuResourceQueue (AO-12 when full) |
| HB-3 | Heartbeat configured in server settings only |
| HB-4 | UI shows global heartbeat state and last tick |
| HB-5 | Default heartbeat off until operator enables |
| DM-4 | World package export + import round-trip |

## 5. Character authoring (Phase 3 gate)

| ID | Test |
|----|------|
| CHAR-1 | Draft generation not in scene transcript |
| CHAR-2 | Draft not in world membership until approve |
| CHAR-3 | Approve uses character API not fs_write |
| CHAR-4 | Draft holds GpuResourceQueue lease |
| CHAR-5 | No auto-persist on stream complete without approve |

v1 spatial gate uses demo pre-seeded cast only ([24-character-authoring.md](24-character-authoring.md)).

## 6. Future (non-blocking v1)

| ID | Test |
|----|------|
| AO-22-wedge | Idle social banter dyads + `DiarySegment.kind=banter` — Alpha wedge; covered by `tests/test_idle_social.py`; not v1 CI blocker |
| AO-22-full | Structured `scene.activity.kind=conversation` or `banter` overlays — spec target |
| AO-17 | `speak_intent` tie-break on score tie — **done** (`tests/test_speak_intent.py`) |
| MAP-7 | Map regen fixture diff surfaces conflict |
| MAP-ACC-1–6 | Phase 6: world map, level stack, floor plan, vertical exits, mini-map level ghosts ([18-location-maps.md](18-location-maps.md) §11) |
| MAP-GEN-ACC-1–4 | LLM `map_layout_generate` valid JSON; topology matches [reference-images](guides/reference-images/README.md) (§12) |
| MAP-GROW-ACC-1 | Post-lock in-map add + ack → scene on spatial-graph ([25-map-authoring.md](25-map-authoring.md)) |
| MAP-MOVE-ACC-1–3 | Movement and missing-destination flow ([25-map-authoring.md](25-map-authoring.md) §10) |
| IMG-1, IMG-8 | ComfyUI via queue; yields to Observer Direct |

## 7. Reference scale fixture (memory performance)

CI MUST include a synthetic dataset at approximately:

| Dimension | Size |
|-----------|------|
| Characters | 24 |
| Diary segments (total) | 12,000 |
| Mind loci per character | ~200 keys, ~2MB aggregate text |
| World loci per scene | ~100 keys |

Path: `tests/fixtures/memory-scale/` ([generator-spec.json](../tests/fixtures/memory-scale/generator-spec.json) + seed script; optional SQLite snapshot).

Performance tests (MEM-PERF-2, MEM-PERF-3) run against this fixture on every CI integration job. Leakage tests (MEM-ACC-1) run 10k randomized queries.

## 8. In-world work (post-v1, non-blocking v1)

| ID | Test |
|----|------|
| COM-ACC-1 | Commission (e.g. GitHub repo research) reaches `done` with mind-pool loci; ask assignee a **stored** detail in a **different** scene → grounded answer from mind pool (not transcript-only). |
| COM-ACC-2 | Commission does not run until assignee present at `targetSceneId` (COM-6). |
| COM-ACC-3 | `done` rejected without mind `memory_store` unless force-complete with reason. |
| DEB-ACC-1 | Debate completes; ask debater in another scene about their position → grounded from `debate:{sceneId}:` mind loci. |

See [23-in-world-work.md](23-in-world-work.md).

## 9. stripReasoning fixtures

Maintain `tests/fixtures/strip-reasoning/` with:

- Raw Qwen output samples (with think blocks)
- Expected `outputText`
- Profile `qwen3.6-35b-a3b`

## 10. Output quality fixtures

Maintain `tests/fixtures/output-quality/` with:

- Short multi-turn script for loop spot-check (nightly e2e)
- Mock-LLM prompt snapshot asserting quality addendum when OQ-1 enabled

## Related documents

- [02-memory.md](02-memory.md)
- [11-data-model.md](11-data-model.md)
- [20-product-principles.md](20-product-principles.md)
- [00-inference-runtime.md](00-inference-runtime.md)
- [16-learning.md](16-learning.md)
- [23-in-world-work.md](23-in-world-work.md)
- [24-character-authoring.md](24-character-authoring.md)
