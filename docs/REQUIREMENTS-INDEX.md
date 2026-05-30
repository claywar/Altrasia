# Requirements Index

Reverse lookup for normative requirement IDs (`00`–`26`). **Authoritative definitions** live in the home document for each prefix; this index is for navigation and traceability.

**Test mapping:** [17-acceptance-criteria.md](17-acceptance-criteria.md) (spatial golden path, requirement matrix, future gates).

**Glossary:** [appendix-glossary.md](appendix-glossary.md).

## Prefix → home document

| Prefix | Home spec | Topic |
|--------|-----------|--------|
| `INF-*`, `STR-*` | [00-inference-runtime.md](00-inference-runtime.md) | GPU queue, streaming, model profiles |
| `W-*`, world rules | [01-world-model.md](01-world-model.md) | Worlds, scenes, cast |
| `MP-*`, `MEM-*` | [02-memory.md](02-memory.md) | Loci, diary, recall, performance |
| `LP-*`, `MAP-MOVE-*` | [03-locations-and-presence.md](03-locations-and-presence.md) | Presence, fixtures, movement |
| `CC-*`, comms | [04-communication.md](04-communication.md), [21-cross-scene-awareness.md](21-cross-scene-awareness.md) | Scopes, phone, knock |
| `TC-*`, `TC-MAP-*` | [05-tool-calling.md](05-tool-calling.md) | Tool registry, map tools |
| `WEB-*` | [06-web-tools.md](06-web-tools.md) | Search, fetch, SSRF |
| `APR-*`, `APR-MAP-*` | [07-approvals.md](07-approvals.md) | Approval queue, map ack |
| `RW-*`, `HB-*` | [08-real-world-capabilities.md](08-real-world-capabilities.md) | FS agent, heartbeat |
| `ROLE-*`, `OBS-*` | [09-roles-and-privilege.md](09-roles-and-privilege.md) | Observer, persona |
| `PI-*` | [10-prompt-injection.md](10-prompt-injection.md) | Prompt layers |
| `DM-*` | [11-data-model.md](11-data-model.md) | SQLite entities, migration |
| `API-*` | [12-api-sketch.md](12-api-sketch.md) | REST/WS surfaces |
| `AO-*` | [13-agent-orchestration.md](13-agent-orchestration.md) | Scheduler, jobs, banter, discussion deliverables |
| AO-8 (reflection) | [16-learning.md](16-learning.md) §6 | Reflection, MemoryLink, PersonaProposal |
| `UI-*`, `UI-MAP-*`, `UI-A11Y-*` | [14-web-ui.md](14-web-ui.md) | Operator console (**v1 subset:** §0) |
| `PL-*` | [15-plugin-platform.md](15-plugin-platform.md) | Plugins (post-v1) |
| `SYS-*` | [26-system-architecture.md](26-system-architecture.md) | Python backend, Web UI stack, extensibility |
| (learning) | [16-learning.md](16-learning.md) | stripReasoning, embeddings |
| `CHAR-*` | [24-character-authoring.md](24-character-authoring.md) | Character draft |
| `OQ-*` | [22-output-quality.md](22-output-quality.md) | Output quality policy |
| `COM-*`, `DEB-*` | [23-in-world-work.md](23-in-world-work.md) | Commissions, debate (post-v1) |
| `MAP-*`, `MAP-GEN-*`, `MAP-ACC-*` | [18-location-maps.md](18-location-maps.md) | Location maps (Phase 6) |
| `MAP-AUTH-*`, `MAP-GROW-*` | [25-map-authoring.md](25-map-authoring.md) | MapDraft, geography lock |
| `IMG-*` | [19-comfyui-media.md](19-comfyui-media.md) | ComfyUI (post-v1) |

**Non-normative wireframe IDs:** `WF-*` in [guides/web-ui-wireframes.md](guides/web-ui-wireframes.md) — see mapping in [14-web-ui.md](14-web-ui.md) §0.

**Trigger cross-refs (Alpha wedge):** `banter_turn`, `idle_continue` → [13-agent-orchestration.md](13-agent-orchestration.md) §3, §5; `discussion_deliverable` → §6.3.

## v1 release gate IDs (blocking)

From [17-acceptance-criteria.md](17-acceptance-criteria.md) §2, §2b, §3 (subset):

| Area | IDs |
|------|-----|
| Golden path | Steps 1–8 (W-3, LP-*, CC-*, OBS-*, MP-6/11/17/20, AO-19, …) |
| Output quality | **OQ-1**, **OQ-3** only |
| Memory privacy / perf | MP-1, MP-8–MP-20b, MEM-ACC-1–5, MEM-PERF-1–4 |
| Inference | INF-5*, STR-*, router `Qwen3.6-35B-A3B` |
| Orchestration | AO-4*, AO-11–12, AO-19–20 |
| Web UI (when built) | UI-LAY-6, UI-R*, UI-TRN-1, UI-REG-1, UI-2, UI-SET-*, UI-WLD-1, UI-S4, UI-MAP-ACC1–4, UI-M4–M6, UI-W6–W7, UI-R8 |

**Alpha wedge, not v1 CI blockers:** AO-8 (reflection), idle social/banter (AO-4c / AO-22 wedge), discussion deliverables, speak_intent (AO-17), embedding rerank.

## OQ-2 and OQ-4 (not v1 CI blockers)

| ID | Defined in | v1 CI | Rationale |
|----|------------|-------|-----------|
| OQ-2 | [22-output-quality.md](22-output-quality.md) §6 | No | Sampling defaults live in model profile YAML; verified manually / profile review, not a separate automated gate |
| OQ-4 | [22-output-quality.md](22-output-quality.md) §6 | No | Anti-loop inject follows PI-1 strip pattern; covered indirectly by prompt assembly tests when anti-loop is enabled |

## Regenerating this index

From repo root (PowerShell):

```powershell
Get-ChildItem docs -Recurse -Filter *.md |
  ForEach-Object { Select-String -Path $_.FullName -Pattern '\b([A-Z]{2,}(?:-[A-Z0-9]+)*-[0-9]+[a-z]?)\b' -AllMatches } |
  ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value } |
  Sort-Object -Unique
```

Filter false positives (e.g. `draft-001`, `normalized-0-100`) manually when auditing.

## Related

- [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md)
- [ROADMAP.md](ROADMAP.md)
