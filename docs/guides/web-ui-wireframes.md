# Web UI Wireframes (non-normative)

ASCII wireframes for the operator console. Normative requirements: [14-web-ui.md](../14-web-ui.md).

**Visual reference images** (WF-2, WF-2b, WF-14, WF-15): [reference-images/README.md](reference-images/README.md). **Stitch Pack A:** [stitch-handoff.md](stitch-handoff.md).

### Wireframes (v1 layout)

Low-fidelity ASCII wireframes for the **right-primary** shell. Proportions are approximate; center column is the flexible grow region.

#### WF-1 — Desktop default (left spatial collapsed, right rail open)

Typical play session: transcript is widest column; world controls on the right.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ WorldEngine · Demo Spatial World          [||] Pause   ● Connected   ⚙ Settings  👁 Obs  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ GPU ▓▓▓▓░░  Generating · Alice · trigger: persona_message · depth 1 · ~12s    [Cancel]   │
├────────────────────────────────────────────────────────────────────────────┬─────────────┤
│                                                                            │   PLACES    │
│  ┌─ Hall ──────────────────────────────────────────────────────────────┐  │  ● Hall     │
│  │  Grand hall · chandelier, front door north                          │  │    Kitchen  │
│  │  [≡ Spatial]  Fixtures: table, door→Kitchen                          │  │             │
│  └─────────────────────────────────────────────────────────────────────┘  │   PEOPLE    │
│                                                                            │  Here       │
│  ┌ transcript ─────────────────────────────────────────────────────────┐  │   ● You     │
│  │ You (public)                                                          │  │   ● Alice   │
│  │   "Anyone home?"                                                      │  │  Elsewhere  │
│  │                                                                       │  │   Bob @ Kit.│
│  │ Alice (public)                                    [why spoke? ⓘ]      │  │             │
│  │   "I've been waiting. The kettle is on."                              │  │  SIGNALS    │
│  │                                                                       │  │  (none)     │
│  │ Alice (whisper → you)                                                 │  │             │
│  │   "Don't mention the key."                                            │  │  [◀ collapse]│
│  └─────────────────────────────────────────────────────────────────────┘  │             │
│                                                                            │             │
│  Scope [Public ▼]  To [—]     ┌──────────────────────────────────┐ Send  │             │
│                               │ Type as persona…                 │       │             │
│                               └──────────────────────────────────┘       │             │
├────────────────────────────────────────────────────────────────────────────┴─────────────┤
│                                                                    [ spatial panel ◀ ]   │
└──────────────────────────────────────────────────────────────────────────────────────────┘
     ▲ center (min ~640px)                                              ▲ right rail ~260px
     ▲ left edge: spatial toggle only (panel hidden)
```

#### WF-2 — Desktop with left spatial panel expanded (v1)

**v1 — Stitch Pack A.** Rectangular nodes only; no `structures[]` envelopes or `mapShape` primitives ([14-web-ui.md](../14-web-ui.md) §21.1). For envelopes and shapes see **WF-2b** (v1.1).

Opened via `[≡ Spatial]` in scene header or top-bar toggle. Use when knocking, reading exits, or viewing mini-map.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ TopBar + GPU queue strip (same as WF-1)                                                  │
├──────────────────┬─────────────────────────────────────────────────────┬─────────────┤
│ SPATIAL          │              CENTER (narrower)                      │ RIGHT RAIL  │
│                  │  Hall · fixtures summary                            │ (unchanged) │
│  ┌─ mini-map (structured layout, v1) ──────────────┐  │  transcript…       │ Places      │
│  │        N ↑                                        │  │  compose…          │ People      │
│  │                                                   │  │                    │ Signals     │
│  │         ┌─────────┐                               │  │                    │             │
│  │         │ Kitchen │                               │  │                    │             │
│  │         └────┬────┘                               │  │                    │             │
│  │              │ door (travelSteps: 1)              │  │                    │             │
│  │         ┌────▼────────┐  ● HALL (you are here)    │  │                    │             │
│  │         │    HALL     │                           │  │                    │             │
│  │         └─────────────┘                           │  │                    │             │
│  └──────────────────────────────────────────────────┘  │                    │             │
│  SceneHeader: Hall                                     │  │                    │             │
│                  │                                                   │             │
│  Exits           │                                                   │             │
│  ● Door → Kit.   │                                                   │             │
│    [Knock]       │                                                   │             │
│  ○ Window (N)    │                                                   │             │
│                  │                                                   │             │
│  Fixtures        │                                                   │             │
│  [table] [door]  │                                                   │             │
│                  │                                                   │             │
│  [▶ collapse]    │                                                   │             │
├──────────────────┴─────────────────────────────────────────────────────┴─────────────┤
```

Ref: [worldengine-structured-minimap.png](reference-images/worldengine-structured-minimap.png) (v1 mini-map).

#### WF-2b — Spatial panel with building envelopes (v1.1)

**v1.1 — Stitch Pack B.** Building envelopes, `mapShape` primitives, structure breadcrumb ([14-web-ui.md](../14-web-ui.md) §21.2–§21.3). Not v1 Sprint 2.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ TopBar + GPU queue strip (same as WF-1)                                                  │
├──────────────────┬─────────────────────────────────────────────────────┬─────────────┤
│ SPATIAL          │              CENTER (narrower)                      │ RIGHT RAIL  │
│                  │  Hall · fixtures summary                            │ (unchanged) │
│  ┌─ mini-map (building envelopes) ─────────────────┐  │  transcript…       │ Places      │
│  │        N ↑                                        │  │  compose…          │ People      │
│  │  ╔══ Manor House ══════════════════════╗         │  │                    │ Signals     │
│  │  ║  ┌─────────┐                         ║         │  │                    │             │
│  │  ║  │ Kitchen │                         ║         │  │                    │             │
│  │  ║  └────┬────┘  interior door          ║         │  │                    │             │
│  │  ║  ┌────▼────────┐  ● HALL (you are here)║         │  │                    │             │
│  │  ║  │    HALL     │                     ║         │  │                    │             │
│  │  ║  └──────┬──────┘                     ║         │  │                    │             │
│  │  ╚═════════╪════════════════════════════╝         │  │                    │             │
│  │           ║ gate (crossesStructure)              │  │                    │             │
│  │      ┌────▼────┐    ○ Round Keep (separate ╔══╗   │  │                    │             │
│  │      │  Bailey │       envelope)           ║  ║   │  │                    │             │
│  │      └─────────┘                           ╚══╝   │  │                    │             │
│  └──────────────────────────────────────────────────┘  │                    │             │
│  SceneHeader: Manor House › Hall                       │  │                    │             │
│  Exits · Fixtures · [▶ collapse] (same as WF-2)        │  │                    │             │
├──────────────────┴─────────────────────────────────────────────────────┴─────────────┤
```

Refs: [worldengine-building-envelope-minimap.png](reference-images/worldengine-building-envelope-minimap.png), [worldengine-architecture-diagram-minimap.png](reference-images/worldengine-architecture-diagram-minimap.png) (v1.1).

#### WF-3 — Right rail icon-collapsed (max transcript width)

Right rail collapses to icons only; tooltips on hover. Left spatial still optional.

```
├──────────────────────────────────────────────────────────────────────────┬──┤
│                         CENTER (widest)                                  │📍│
│                         transcript + compose                             │👥│
│                                                                          │🔔│
│                                                                          │▶│
└──────────────────────────────────────────────────────────────────────────┴──┘
```

#### WF-4 — Tablet / narrow (<1280px): right rail as drawer

Center is full width; world controls behind a tab or hamburger on the **right edge**.

```
┌────────────────────────────────────────────┐
│ TopBar                          [World ≡]  │  ← opens right drawer
├────────────────────────────────────────────┤
│ GPU queue strip                            │
├────────────────────────────────────────────┤
│ Hall · [≡ Spatial sheet]                   │
│ transcript (full width)                    │
│ compose                                    │
└────────────────────────────────────────────┘

        ┌─ drawer (slides from right) ─────┐
        │ PLACES / PEOPLE / SIGNALS        │
        │ (accordion sections)             │
        └──────────────────────────────────┘
```

#### WF-5 — Message bubble (markdown + Mermaid)

Streaming shows plain text; finalized messages run markdown pass.

```
┌─ Alice (public) ──────────────────────────────── 14:32 ─ [ⓘ rationale] ─┐
│ The plan has three steps:                                               │
│                                                                         │
│ 1. Check the hall                                                       │
│ 2. Signal the kitchen                                                   │
│ 3. Regroup                                                              │
│                                                                         │
│ ┌─ mermaid diagram ─────────────────────────────────────────────────┐  │
│ │     [Hall] ---- knock ----> [Kitchen]                             │  │
│ │        |                              |                           │  │
│ │     [You]                          [Bob]                          │  │
│ └───────────────────────────────────────────────────────────────────┘  │
│                                                          [⤢ expand diag] │
└─────────────────────────────────────────────────────────────────────────┘

┌─ Narrator ─────────────────────────────────────────────────────────────┐
│  *The lights dim.*                          ← distinct italic styling   │
└─────────────────────────────────────────────────────────────────────────┘

┌─ whisper (dimmed if not your thread) ──────────────────────────────────┐
│  "..."                                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### WF-6 — Persona compose bar

Sits at bottom of center column; scope controls always visible (UI-P1, UI-3).

```
┌─ compose ──────────────────────────────────────────────────────────────┐
│  Scope   [ Public ▼ ]   Whisper to [ Alice ▼ ]              [ MD preview ]│
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                              [ Send ⏎ ]  Shift+⏎ newline │
└──────────────────────────────────────────────────────────────────────────┘
     Guard banner (if persona not present): "Join Hall to speak publicly."
```

#### WF-7 — Observer Studio (slide-over from left)

Does not cover the right rail; meta chat separate from scene transcript (UI-O1).

```
┌──────────────── Observer Studio ────────────────┬────────────────────────┐
│ Modes [Watch][Narrate][Intervene][Direct]       │  (center dimmed)         │
│ ─────────────────────────────────────────────  │                          │
│ Meta thread (channelKind=meta)                  │  right rail still usable │
│ ┌────────────────────────────────────────────┐ │                          │
│ │ Op: Rename fixture "table" → "oak table"   │ │                          │
│ │ Tool trace: scene_fixture_rename ✓         │ │                          │
│ │ Obs: Done. Framing updated.                │ │                          │
│ └────────────────────────────────────────────┘ │                          │
│ Digest · queue · multi-scene summary (UI-D1)   │                          │
│ ┌────────────────────────────────────────────┐ │                          │
│ │ Operator message…                          │ │                          │
│ └────────────────────────────────────────────┘ │                          │
│                                    [Close ✕]    │                          │
└─────────────────────────────────────────────────┴──────────────────────────┘
```

#### WF-8 — Pending knock (signal banner + right Signals section)

Knock does not auto-trigger NPC speech (CC-11a).

```
CENTER header:
┌─ Kitchen ────────────────────────────────────────────────────────────────┐
│  ⚠ Knock from Hall (exit: door) — pending     [Dismiss]  [Expire]        │
└──────────────────────────────────────────────────────────────────────────┘

RIGHT rail · SIGNALS:
┌─────────────────────────────────┐
│ ● Hall → Kitchen (door)         │
│   pending · 2m ago              │
│   [Dismiss]  [Expire]           │
└─────────────────────────────────┘
```

#### WF-9 — First run / empty state

Before a world is loaded ([first-run-experience.md](first-run-experience.md)).

```
┌──────────────────────────────────────────────────────────────────────────┐
│ WorldEngine                                    ⚙ Settings                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                    ┌────────────────────────────────┐                    │
│                    │   Load demo world              │                    │
│                    │   demo-spatial-v1              │                    │
│                    └────────────────────────────────┘                    │
│                                                                          │
│                    Hall + Kitchen · Alice + Bob                          │
│                    Or: POST /worlds { fixtureId }                        │
│                                                                          │
│              LLM status: ● Ready  /  ○ Configure model                   │
└──────────────────────────────────────────────────────────────────────────┘
```

#### WF-10 — Settings modal (overlay)

Infrequent; does not replace right rail.

```
                    ┌──────── Settings ────────────────────┐
                    │ [World][Persona][Scene][Inference] │
                    │ ─────────────────────────────────── │
                    │ Preset: (•) Solo story              │
                    │         ( ) Writer                  │
                    │         ( ) Aquarium                │
                    │ agentContinue: on  maxDepth: 2      │
                    │                                     │
                    │ Persona auto-join on scene switch ☑ │
                    │ Require present to speak public ☐   │
                    │                          [Cancel][Save]│
                    └─────────────────────────────────────┘
```

#### WF-11 — Approvals drawer (bottom)

Side-effecting Observer tools (UI-C2).

```
┌──────────────────────────────────────────────────────────────────────────┐
│ … transcript …                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ ▲ Approvals (1)                                                          │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ scene_fixture_rename: "table" → "oak table"   [Deny]  [Approve]      │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

#### WF-17 — Memory inspector (v1)

Right slide-over from **People** roster (UI-M4). Read-only mind/world loci and diary (UI-M1–M3, UI-TRN-4). Esc closes (UI-M5).

```
┌──────────────────────── Memory · Alice ──────────────────────── [×] ─┐
│  Hall · mind pool                                                    │
│  [ Mind loci ● ] [ World loci (Hall) ] [ Diary ]                     │
│  ─────────────────────────────────────────────────────────────────── │
│  Search loci…                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ key: kettle-location          updated 2h ago                   │  │
│  │   "Alice knows the kettle is on in the kitchen."               │  │
│  │ key: secret-key               updated 1d ago                   │  │
│  │   "Don't mention the key to visitors."                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  (no edit / delete on rows)                                          │
│  [ Open from rationale popover → ]                                   │
└──────────────────────────────────────────────────────────────────────┘
     ▲ right edge slide-over; center + left spatial dimmed; right rail usable
```

#### WF-18 — Streaming message (v1)

`streamStatus=streaming` — plain text only; markdown/Mermaid after finalize (UI-R3, UI-W7).

```
┌─ Alice (public) ──────────────────────────────── 14:32 ─ generating ────┐
│ I've been waiting. The kettle is on█                                    │
│                                                                         │
│ Generating…                                    [Cancel]  ← UI-C4        │
└─────────────────────────────────────────────────────────────────────────┘
     ▲ thin streaming caret at end; scope badge unchanged; no ⓘ until final
```

#### WF-19 — Interrupted message (v1)

`streamStatus=interrupted` — partial text retained; no markdown pass (UI-W4, UI-W6, UI-R8).

```
┌─ Alice (public) ─────────────────── 14:32 ─ Interrupted ────────────────┐
│ I've been waiting. The ket█                                             │
│                                                                         │
│ Generation stopped. Partial reply kept.                                 │
└─────────────────────────────────────────────────────────────────────────┘
     ▲ dashed border or destructive-muted label; no Dismiss required in v1
```

#### WF-20 — GpuQueueStrip states (v1)

Extends WF-1 top strip (UI-Q1, UI-2).

**Idle:**

```
│ GPU idle · depth 0 · no active job                                                    │
```

**Busy:**

```
│ GPU ▓▓▓▓░░  Generating · Alice · trigger: persona_message · depth 1 · ~12s  [Cancel]   │
```

**Busy + expanded selection rationale:**

```
│ GPU ▓▓▓▓░░  Generating · Alice · trigger: persona_message · depth 1 · ~12s  [Cancel]   │
│ pick: addressed  [▼ scores]  char-alice 0.92  char-bob 0.41                            │
```

#### WF-21 — Selection rationale popover (v1)

From message `[ⓘ]` (WF-5) or queue strip chevron. Data: `GET .../generations/{jobId}` (UI-1).

```
                    ┌─ Why Alice spoke ──────────────────────┐
                    │ Pick: addressed (persona whisper)      │
                    │ Scores:                              │
                    │   alice  total 0.92  relevance 0.82    │
                    │   bob    total 0.41  relevance 0.12    │
                    │ ─────────────────────────────────────  │
                    │ Memory tools:                        │
                    │   memory_search  "kettle"  ✓         │
                    │ Framing: Hall · mandatory recall on  │
                    │ [ View in Memory inspector ]         │
                    └──────────────────────────────────────┘
```

#### WF-14 — World map overlay (Phase 6a, UI-MAP-W*)

**Phase 6 — not Stitch Pack A.**

Large-scale site view over dimmed play shell. Normative: [18-location-maps.md](../18-location-maps.md) §7, [14-web-ui.md](../14-web-ui.md) §21.4.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ WorldEngine · Demo World     [||] Pause   ● Connected   [⌖ Map ●]  ⚙   👁 Obs          │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ GPU queue strip (dimmed)                                                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░  ┌─ World map ──────────────────────────────────────────────── [site|structure|floor] ░ │
│ ░  │  N ↑    ~~~~~~~~ terrain / road ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~              [Fit][Esc] ░ │
│ ░  │         ╔════════ Manor House ════════╗      ○ Round Keep                      ░ │
│ ░  │         ║  Hall ●  Kitchen            ║         (circle)                         ░ │
│ ░  │         ╚═══════════════════════════╝                                          ░ │
│ ░  │              ┌─────────┐                                                       ░ │
│ ░  │              │  Bailey │                                                       ░ │
│ ░  │              └─────────┘     ┌── mini-map inset ──┐                            ░ │
│ ░  │                              │ viewport rectangle  │                            ░ │
│ ░  └──────────────────────────────└─────────────────────┘                            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ (transcript + rails dimmed behind overlay)                                               │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

#### WF-15 — Level stack (Phase 6b, UI-MAP-L*)

**Phase 6 — not Stitch Pack A.** Exploded vertical view for one structure. Normative: [18-location-maps.md](../18-location-maps.md) §8.

```
┌─ Level stack · Manor House ────────────────────────────────────────── [stack|floor|site] ─┐
│  Levels:  [ B1 ]  [ Ground ● ]  [ Upper ]                                              │
│                                                                                         │
│       ┌──────────────────┐   Level +1  Upper gallery                                  │
│       │    (scene plate)   │                                                            │
│       └─────────┬──────────┘                                                            │
│                 │  ▲ stairs                                                             │
│       ┌─────────▼──────────┐   Level  0  Ground                                       │
│       │ Hall ●   Kitchen   │   ● you are here                                           │
│       └─────────┬──────────┘                                                            │
│                 │  ▼ ladder                                                             │
│       ┌─────────▼──────────┐   Level -1  Cellar                                         │
│       │    (scene plate)   │                                                            │
│       └────────────────────┘                                                            │
│                                                                                         │
│  [ Go to scene ]  [ Close ]                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Wireframe index

| ID | Pack | State | Purpose |
|----|------|-------|---------|
| WF-1 | v1 | Default desktop | Primary play layout |
| WF-2 | v1 | Left spatial open | Rect mini-map, exits, knock, fixtures |
| WF-2b | v1.1 | Left spatial open | Envelopes + shapes mini-map |
| WF-3 | v1 | Right rail collapsed | Wide transcript / diagrams |
| WF-4 | v1 | Tablet | Drawer pattern |
| WF-5 | v1 | Message bubble | Markdown + Mermaid + scopes (finalized) |
| WF-6 | v1 | Compose | Persona input + scope selector |
| WF-7 | v1 | Observer | Left slide-over + meta thread |
| WF-8 | v1 | Knock signal | Banner + Signals section |
| WF-9 | v1 | Empty | Demo world CTA |
| WF-10 | v1 | Settings | Modal tabs |
| WF-11 | v1 | Approvals | Bottom drawer |
| WF-12 | v1 | World entry | Simple load menu (UI-WLD-1) |
| WF-17 | v1 | Memory inspector | Right slide-over; loci + diary |
| WF-18 | v1 | Streaming message | Plain text + caret while generating |
| WF-19 | v1 | Interrupted message | Partial text + interrupted styling |
| WF-20 | v1 | Queue strip | Idle / busy / expanded rationale |
| WF-21 | v1 | Rationale popover | Why spoke; scores + tool trace |
| WF-13 | post-v1 | ComfyUI media | Portraits + scene shot (UI-IMG) |
| WF-14 | Phase 6 | World map overlay | Site-scale WorldMapCanvas |
| WF-15 | Phase 6 | Level stack | Multi-floor LevelStackView |
| WF-16 | Phase 6 | Map layout preview | MapDraft / Observer layout ack |

#### WF-16 — Map layout preview (Phase 6, UI-MAP-P*)

**Phase 6 — not Stitch Pack A.**

Map preview panel — not the FS/web approval drawer ([07-approvals.md](../07-approvals.md) APR-MAP-1).

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Map layout preview                                    revision 2 ▼  [×]  │
├──────────────────────────────┬───────────────────────────────────────────┤
│  BEFORE (SVG)                │  AFTER (SVG)                              │
│  ┌────┐     ┌────┐           │  ┌────┐     ┌────┐      ┌────────┐       │
│  │Hall│─────│Kit.│           │  │Hall│─────│Kit.│──────│Garden│       │
│  └────┘     └────┘           │  └────┘     └────┘      └────────┘       │
├──────────────────────────────┴───────────────────────────────────────────┤
│ Changes:  + scene-garden  + exit hall-garden  ~ hall position moved      │
│ Conflicts: (none)  or  [fixture_drift hearth] Accept Revert Skip         │
├──────────────────────────────────────────────────────────────────────────┤
│ [Visual ●] [JSON]     Sync required banner if tabs diverge                │
│ [Fix validation] [Describe change]  [Discard]  [Approve] → [Confirm?]  │
└──────────────────────────────────────────────────────────────────────────┘
```

#### WF-12 — Simple world entry (v1, UI-WLD-1)

No multi-world dashboard; one active world at a time.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ WorldEngine                                    ⚙ Settings                │
├──────────────────────────────────────────────────────────────────────────┤
│  Active: Demo Spatial World ▼     (only when a world is loaded)         │
│            ├─ Load demo world (demo-spatial-v1)                          │
│            ├─ Open world file…                                           │
│            └─ Recent: (empty on first run)                               │
│                                                                          │
│  … main play UI when loaded …                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

#### WF-13 — Character in scene (future ComfyUI, UI-IMG)

```
RIGHT rail · PEOPLE                    CENTER message
┌─────────────────────┐               ┌─ Alice ─────────────────────────┐
│ [portrait] Alice    │               │ [thumb] "I've been waiting…"  │
│ [portrait] You      │               └─────────────────────────────────┘
│ Elsewhere…          │
└─────────────────────┘
Scene header: [ establishing shot ]  Hall · fixtures…
Observer: Regenerate portrait (queue: image job)
```
