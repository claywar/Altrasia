# 23 — In-World Work

Commissions, debate activity, briefing fixtures, and world commons extend the spatial world model for research, deliberation, and team focus—**without** a separate product mode or bypassing presence, perception, or MP-1.

> **Not a second product.** In-world work uses the same worlds, scenes, cast, orchestrator, and memory pools as narrative play ([01-world-model.md](01-world-model.md), [02-memory.md](02-memory.md)).

## 1. Scope and phases

| Phase | What ships |
|-------|------------|
| **v1** | Unchanged spatial wedge ([20-product-principles.md](20-product-principles.md)) |
| **v1.5 (spec)** | `Commission`, `EvidenceRecord`, `scene.activity`, commons schema; manual operator `memory_store` |
| **Phase 4+** | Web/FS tools + commission triggers + provenance |
| **Phase 4.5** | Debate activity runtime + acceptance paths |

## 2. Commissions

A **Commission** is a diegetic errand the operator assigns to a cast member—research, fact-check, draft a memo—in service of the same world.

### 2.1 Entity

| Field | Description |
|-------|-------------|
| `commissionId` | Stable id |
| `worldId` | Container |
| `assigneeCharacterId` | Agent who performs the work |
| `targetSceneId` | Scene where work is grounded (library, archives, lab)—required |
| `brief` | Operator instruction (OOC or in-fiction label) |
| `status` | `queued` \| `running` \| `blocked` \| `done` \| `failed` |
| `deliverablePolicy` | `mind` (default) \| `world_pool_at_target` \| `both` |
| `deliverableLocusPrefix` | Default `commission:{commissionId}:` |
| `deliverableLocusKeys` | Populated on `done` (COM-3) |
| `allowedTools` | Subset when web/FS enabled |
| `forceCompletedAt` | Optional; operator skip with audit reason |

Persistence: [11-data-model.md](11-data-model.md) §3.14.

### 2.2 Deliverable policy (vital)

Unless the operator sets `deliverablePolicy` to `world_pool_at_target` or `both`, research MUST be persisted to the **assignee mind pool** via `memory_store` (pool `mind`). Mind is global per `characterId`; mandatory recall searches it in any scene.

| ID | Requirement |
|----|-------------|
| **COM-1** | `deliverablePolicy` defaults to `mind` when omitted on create. |
| **COM-2** | Status `done` MUST NOT be set until ≥1 successful `memory_store` to the assignee mind pool under `deliverableLocusPrefix`, unless operator **Force complete** records an explicit skip reason. Transcript-only completion is forbidden. |
| **COM-3** | On `done`, record `deliverableLocusKeys[]` on the commission. |
| **COM-4** | World-pool or commons writes occur only when `deliverablePolicy` is `world_pool_at_target` or `both`. For `both`, COM-2 mind-store requirement still applies. |
| **COM-5** | Post-completion Q&A: assignee with mandatory recall on SHOULD hit commission loci before re-fetching web ([06-web-tools.md](06-web-tools.md) §5). |
| **COM-6** | Assignee MUST be **present** at `targetSceneId` for commission work to run. Status stays `queued` or `blocked` until presence matches. No headless research while elsewhere. |

**Overrides:**

- `world_pool_at_target` — findings on briefing fixture / world pool at target scene; assignee SHOULD still receive a mind summary when away from that scene.
- `both` — mind notes plus shared world pool at `targetSceneId`.

### 2.3 Orchestration

Triggers ([13-agent-orchestration.md](13-agent-orchestration.md)):

| Trigger | Description |
|---------|-------------|
| `commission_started` | Operator or API started work |
| `commission_tick` | Scheduler poll while `running` |

- Priority below `operator_message` and `whisper_target`.
- Generation context uses `targetSceneId` for framing and world-pool writes.
- MAY pause when persona has active dialogue at the same scene (world config).

**RP beat:** Persona sends NPC to archives; NPC joins archives scene; commission runs; NPC returns and speaks findings, or operator syncs a briefing fixture.

### 2.4 Force complete

Operator **Force complete** MAY set `done` without COM-2 when documented (e.g. abandoned errand). UI MUST warn; `deliverableLocusKeys` MAY be empty.

## 3. Debate activity

Debate is a **`scene.activity`** overlay—not a separate application.

### 3.1 Scene header shape

```yaml
activity:
  kind: debate
  phase: opening | cross | rebuttal | closing | synthesis
  speakingOrder: [characterId, ...]
  currentIndex: 0
  debateDeliverablePolicy: mind_per_participant  # default
```

### 3.2 Rules

| ID | Requirement |
|----|-------------|
| **DEB-1** | At `synthesis` phase, MUST `memory_store` to **each** `speakingOrder` participant mind pool under `debate:{sceneId}:` unless `debateDeliverablePolicy: world_pool_at_scene`. |
| **DEB-2** | Only `speakingOrder[currentIndex]` MAY be scheduled for debate turns (overrides idle round-robin, `agent_continue`, and AO-18 scoring at that scene). |
| **DEB-3** | Speech uses `channelKind=scene`, scope `public` (or whisper per [04-communication.md](04-communication.md)). MP-20 fan-out applies. |
| **DEB-4** | Moderator: Observer **Narrate** or designated cast character—no new meta product. |

Synthesis generation: public line plus per-participant mind loci (positions, arguments, conclusions).

## 4. Briefing fixtures

Scene fixtures with `kind: briefing` (or equivalent) MAY mirror one-way into world pool loci:

| Key pattern | Content |
|-------------|---------|
| `briefing:{sceneId}:{fixtureKey}` | Shared board text at that location |

Same one-way invariant as location mirror (MP-2). Cast treat posted facts as in-fiction only when perceivable at the scene or communicated in play (ROLE-1).

## 5. World commons

Optional **world commons** loci in world aggregate ([01-world-model.md](01-world-model.md)):

| Key pattern | Example |
|-------------|---------|
| `world:{worldId}:commons:{key}` | Institutional record |

Recall: [02-memory.md](02-memory.md) MP-22. Diegesis: [09-roles-and-privilege.md](09-roles-and-privilege.md) ROLE-6.

## 6. Team focus areas

Character definition MAY include `focusTags[]` (e.g. `legal`, `engineering`). Commissions MAY filter assignees by tag. No new RBAC tier.

## 7. Provenance

External facts stored via commission or Architect tools SHOULD attach **EvidenceRecord** metadata ([11-data-model.md](11-data-model.md) §3.15, MP-21). Operator inspector shows provenance; prompt cites sources only when `citeProvenanceInPrompt` is enabled on the world.

## 8. Acceptance (post-v1)

| ID | Scenario |
|----|----------|
| **COM-ACC-1** | Repo research commission `done`; ask assignee a **stored** detail in a **different** scene → answer grounded from mind pool. |
| **DEB-ACC-1** | Debate completes; ask debater in another scene about their position → grounded from `debate:{sceneId}:` mind loci. |

See [17-acceptance-criteria.md](17-acceptance-criteria.md) §10.

## 9. Requirements summary

| ID | Requirement |
|----|-------------|
| COM-1–COM-6 | Commission deliverables, presence, completion |
| DEB-1–DEB-4 | Debate activity |
| COM-ACC-1, DEB-ACC-1 | Post-v1 golden paths |

## Related documents

- [02-memory.md](02-memory.md) — pools, MP-21, MP-22
- [04-communication.md](04-communication.md) — debate turns and scopes
- [06-web-tools.md](06-web-tools.md) — web after memory
- [08-real-world-capabilities.md](08-real-world-capabilities.md) — FS, scheduler
- [11-data-model.md](11-data-model.md) — SQLite entities
- [13-agent-orchestration.md](13-agent-orchestration.md) — triggers, debate gating, `agent_continue`, `scoreSpeakers`

**Post-v1:** Optional `scene.activity.kind` values `conversation` and `banter` (AO-22) are lighter than debate; v1 ensemble dialogue uses `agent_continue` + AO-18 only.
- [14-web-ui.md](14-web-ui.md) — commission queue, evidence inspector
- [17-acceptance-criteria.md](17-acceptance-criteria.md) — test matrix
