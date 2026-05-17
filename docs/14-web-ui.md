# 14 — Web UI

Professional **operator console** for WorldEngine. **Persona-first** play; **Observer Studio** for tuning and world control.

## 1. Design principles (UI-*)

| ID | Principle |
|----|-----------|
| UI-1 | **Legible causality** — show why a character spoke (memory tools, framing, queue position, **selection rationale** from `GenerationJob.selectionRationaleJson`). |
| UI-2 | **Queue honesty** — visible GPU busy state and wait (INF-5f). |
| UI-3 | **Scope clarity** — public / whisper / DM visually distinct; narrator lines distinct. |

## 2. Layout

```mermaid
flowchart LR
  subgraph main [Main]
    Transcript[Scene transcript + persona compose]
    Sidebar[Scene list + roster]
  end
  subgraph overlays [Overlays]
    Studio[Observer Studio slide-over]
    Approvals[Approval drawer]
    Queue[GPU queue strip]
  end
  Sidebar --> Transcript
  Studio -.-> Transcript
```

| Region | Priority |
|--------|----------|
| **Center** | Active scene transcript + persona compose (hero) |
| **Sidebar** | Scene switcher, presence roster, elsewhere list |
| **Slide-over** | Observer Studio (meta chat + modes) |
| **Strip** | GPU queue status; per-job trigger, `continueDepth`, selection rationale summary (UI-1) |
| **Drawer** | Approvals |

## 3. Persona compose

| ID | Requirement |
|----|-------------|
| UI-P1 | Scope selector: **v1** public, whisper, DM ([04-communication.md](04-communication.md)). |
| UI-P2 | v1.1 adds phone; **per-scene speakerphone toggle** (not global); bystanders see one-sided overhear unless speakerphone on at their scene ([04-communication.md](04-communication.md) §3). |
| UI-P3 | Persona speak guard feedback when not present ([09-roles-and-privilege.md](09-roles-and-privilege.md)). |
| UI-P4 | Send enqueues cast reply generation after persona message. |
| UI-Q1 | Queue strip shows `trigger`, `continueDepth`, and collapsed selection rationale (AO-18, UI-1). |

## 4. Scene switcher (spatial wedge)

| ID | Requirement |
|----|-------------|
| UI-S1 | World scene list with present / elsewhere badges (CC-3). |
| UI-S2 | One-click switch active scene; persona auto-join policy visible. |
| UI-S3 | "Knock on [exit]" creates `CrossSceneSignal`; target scene banner (CC-2). Operator MAY dismiss/expire signal (CC-11b). **No** v1 control that auto-triggers NPC generation on knock (CC-11a). |
| UI-S4 | Signal list on digest/sidebar: pending knocks with dismiss/expire actions. |

## 5. Observer Studio (UI-OBS-CHAT)

| ID | Requirement |
|----|-------------|
| UI-O1 | Separate thread from scene transcript (`channelKind=meta`). |
| UI-O2 | Modes: Watch, Narrate, Intervene, Direct ([09-roles-and-privilege.md](09-roles-and-privilege.md)). |
| UI-O3 | Show memory-tool trace before Observer reply when blocking on (MP-9). |
| UI-O4 | World edits route through Observer tools (OBS-2). |

Narrate/Intervene in play appear in **scene** transcript with `narrator` scope—not in meta thread.

## 6. Watch mode and streaming

| ID | Requirement |
|----|-------------|
| UI-W1 | WebSocket/SSE: `generation.token`, tool calls, memory ops, presence, approvals. |
| UI-W2 | Label operator-only affordances ("Operator / Observer view"). |
| UI-W3 | Partial text while `streamStatus=streaming`; finalize to `outputText` on done (STR-*). |
| UI-W4 | `interrupted` styling + optional resume/cancel. |
| UI-W5 | Reasoning debug toggle for current session only—not in loci/diary inspector. |

## 7. Digest and roster

| ID | Requirement |
|----|-------------|
| UI-D1 | Multi-scene digest panel (OBS-6); pending signals and channel summary. |
| UI-D2 | Elsewhere roster: character + `presentSceneId` label. |

## 8. Memory inspector

| ID | Requirement |
|----|-------------|
| UI-M1 | Per-character mind loci, per-scene world loci, diary timeline. |
| UI-M2 | Output text only in inspector (MP-14). |
| UI-M3 | MP-1: no cross-mind display. |

## 9. Controls

| ID | Requirement |
|----|-------------|
| UI-C1 | Pause world / scene. |
| UI-C2 | Approve/deny ([07-approvals.md](07-approvals.md)). |
| UI-C3 | "Restart-safe" when durable memory hydrated (MP-11). |
| UI-C4 | Cancel in-flight generation (INF-5g). |

## 10. Operator / server settings (v1.1 heartbeat)

| ID | Requirement |
|----|-------------|
| UI-H1 | Global **heartbeat** toggle, interval, `lastHeartbeatAt` ([08-real-world-capabilities.md](08-real-world-capabilities.md) HB-4, HB-5) — not per-world wizard field |
| UI-H2 | Queue strip labels `idle_source=server_heartbeat` when applicable (UI-2) |

Per-world **pause** remains UI-C1; distinct from global heartbeat.

## 11. Character authoring (Phase 3 UI)

| ID | Requirement |
|----|-------------|
| UI-CHAR-1 | Shared **CharacterDraft** flow: natural-language brief → LLM draft → preview → approve ([24-character-authoring.md](24-character-authoring.md)) |
| UI-CHAR-2 | Entry points: **Observer Studio** and **world settings**; Phase 3 wizard step 3 embeds same component |
| UI-CHAR-3 | Draft holds GpuResourceQueue slot in queue strip (CHAR-4) |

v1 play MAY use demo pre-seeded cast without this UI.

## 12. In-world work (post-v1 UI)

| ID | Requirement |
|----|-------------|
| UI-WK-1 | **Commission queue** in Observer slide-over or sidebar: status, assignee, `targetSceneId`, deliverable policy, `deliverableLocusKeys`. |
| UI-WK-2 | Create commission: brief, assignee, target scene, optional `deliverablePolicy` (default **mind**). |
| UI-WK-3 | **Evidence inspector** on memory rows: `sourceKind`, `sourceRef`, `retrievedAt` (MP-21). |
| UI-WK-4 | **Debate controls** when `scene.activity.kind=debate`: phase, speaking order, advance phase, current speaker highlight. |
| UI-WK-5 | Force complete with required reason when COM-2 not satisfied. |
| UI-WK-6 | Filter commission list by character `focusTags[]`. |

In-world work UI is an **affordance** on the operator console—not a separate application shell. Persona transcript remains hero (UI hierarchy unchanged).

## 13. Non-goals (v1 UI)

- SillyTavern preset matrix or PNG character cards
- Expression sprites
- Full map editor ([18-location-maps.md](18-location-maps.md) future)

## 14. API binding

See [12-api-sketch.md](12-api-sketch.md). Desktop-first; responsive layout SHOULD be usable on large tablets.

## Related documents

- [12-api-sketch.md](12-api-sketch.md)
- [09-roles-and-privilege.md](09-roles-and-privilege.md)
- [20-product-principles.md](20-product-principles.md)
- [23-in-world-work.md](23-in-world-work.md)
- [24-character-authoring.md](24-character-authoring.md)
