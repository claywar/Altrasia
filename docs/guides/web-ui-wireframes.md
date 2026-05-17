# Web UI Wireframes (non-normative)

ASCII wireframes for the operator console. Normative requirements: [14-web-ui.md](../14-web-ui.md).

**Visual reference images** (WF-14, WF-15, mini-map): [reference-images/README.md](reference-images/README.md).

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

#### WF-2 — Desktop with left spatial panel expanded

Opened via `[≡ Spatial]` in scene header or top-bar toggle. Use when knocking, reading exits, or viewing mini-map.

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

#### WF-14 — World map overlay (Phase 6a, UI-MAP-W*)

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

Exploded vertical view for one structure. Normative: [18-location-maps.md](../18-location-maps.md) §8.

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

| ID | State | Purpose |
|----|-------|---------|
| WF-1 | Default desktop | Primary play layout |
| WF-2 | Left spatial open | Map, exits, knock, fixtures |
| WF-3 | Right rail collapsed | Wide transcript / diagrams |
| WF-4 | Tablet | Drawer pattern |
| WF-5 | Message bubble | Markdown + Mermaid + scopes |
| WF-6 | Compose | Persona input + scope selector |
| WF-7 | Observer | Left slide-over + meta thread |
| WF-8 | Knock signal | Banner + Signals section |
| WF-9 | Empty | Demo world CTA |
| WF-10 | Settings | Modal tabs |
| WF-11 | Approvals | Bottom drawer |
| WF-12 | World entry | Simple load menu (UI-WLD-1) |
| WF-13 | ComfyUI media | Portraits + scene shot (UI-IMG, future) |
| WF-14 | World map overlay | Site-scale WorldMapCanvas (Phase 6a) |
| WF-15 | Level stack | Multi-floor LevelStackView (Phase 6b) |

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
