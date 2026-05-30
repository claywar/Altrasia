# Target First-Run Experience

**Non-normative.** Human-readable acceptance walkthrough for the spatial wedge. Install and run: [getting-started.md](getting-started.md).

## Purpose

A solo operator opens Altrasia for the first time and reaches meaningful spatial play **without manual world construction**, using the specified demo fixture `demo-spatial-v1` ([demo-world fixture](../../tests/fixtures/demo-world/README.md)).

The automated release gate is the spatial golden path ([17-acceptance-criteria.md](../17-acceptance-criteria.md) §2). This guide is the **human-readable** version for UX and product acceptance.

## Fixture status

| Item | Design phase | At implementation |
|------|--------------|-------------------|
| `demo-spatial-v1` spec | Documented in fixture README | Seed script and/or `demo-spatial-v1.sqlite` bundled |
| `POST /api/v1/worlds` with `fixtureId` | Specified in [12-api-sketch.md](../12-api-sketch.md) | Implemented |
| Web UI | Specified in [14-web-ui.md](../14-web-ui.md) | Implemented |

## Narrative walkthrough

### 1. Open the demo world

**Operator action:** Launch the app; choose **Load demo world** (or equivalent) for `demo-spatial-v1`.

**Expected state:**

- World name: **Vertex Labs HQ — Demo**
- Persona starts in **Lobby** (`scene-lobby`); Jordan Reyes (CTO) at reception; product and program teams in their studios; engineers in private offices on the engineering wing
- Preset: Solo story

**UI affordances ([14-web-ui.md](../14-web-ui.md)):** Load demo via WF-9 / UI-WLD-1; right rail **Places** + **People**; center transcript + compose.

### 2. Public conversation

**Operator action:** Persona sends a **public** line in the Lobby (scope selector = public).

**Expected:**

- Jordan Reyes (or another eligible NPC present) replies in scene transcript
- GPU queue strip shows job trigger and wait if busy (UI-2, WF-20)
- Selection rationale available via queue strip or message ⓘ popover (UI-1, WF-21)

**Failure modes to design against:**

- Empty or generic reply with no memory grounding visible when blocking is on
- Whisper text leaking into another character’s prompt (MP-1 / golden path step 2)

### 3. Whisper (isolation check)

**Operator action:** Send a **whisper** to one NPC.

**Expected:**

- Only targeted cast receive whisper in assembly; other cast prompts do not contain whisper content

### 4. Move to another scene

**Operator action:** Switch active scene to Kitchen (persona follows join policy).

**Expected:**

- Elsewhere roster still shows Alice in Hall with scene label (CC-3)
- Bob visible in Kitchen transcript context

### 4b. World map navigation

**Operator action:** Press **M** or click **Map** / the scene header map chip. In the **3D world map**, orbit with the mouse, click **Kitchen**, then **Travel route** or **Go** in the inspector.

**Expected:**

- Full-screen **3D map** opens (room boxes, structure volumes, route highlight on multi-hop paths)
- **Diagram** toggle switches to the SVG tactical map (site / structure / floor / stack)
- Travel follows exit topology when geography is locked; **Places** shows **Go** vs **Jump**
- Left **3D minimap** and scene-header compass stay in sync after moves

### 5. Knock on exit

**Operator action:** Use **Knock on [exit]** from Hall toward Kitchen (or reverse).

**Expected:**

- `CrossSceneSignal` created as `pending`; banner at target scene (CC-2, CC-11d)
- **No** automatic NPC generation on knock create (CC-11a)
- Operator may dismiss or expire signal (CC-11b)

### 6. Observer tweak

**Operator action:** Open Observer Studio slide-over; meta-chat or tool renames a fixture or scene label.

**Expected:**

- Scene framing updates on next generation (OBS-2)
- Meta thread separate from scene transcript (UI-O1)
- Optional: open **Memory inspector** for a cast member from People (WF-17, UI-M4)

### 7. Rich message rendering (when UI exists)

**Operator action:** Receive an NPC reply that includes a markdown list or fenced `mermaid` diagram.

**Expected:**

- Finalized message renders markdown (UI-R1)
- Mermaid diagram displays or shows explicit error fallback (UI-R2, UI-R5)
- Streaming shows plain text until finalize (UI-R3)

### 7a. Web research (CTO / directors)

**Operator action:** Ask Jordan Reyes (CTO) or another director to search the web for a fact.

**Expected:**

- Demo world: `cto` and `director` roles default to **Ask each time** via world policy (`defaultWebToolsAccessBySceneRole`); Jordan exposes `webtools_invoke` without manual setup after a fresh demo load.
- First fetch queues an approval in the banner; approve to continue the job with results.
- Override per character under **Settings → Cast → Web tools** (`off`, `ask`, or `allowed`).

**Dev note:** `webToolsMock` may return stub content until live fetch is configured ([06-web-tools.md](../06-web-tools.md)).

### 7b. CTO briefing assembly (leadership summon)

**Operator action:** In the Lobby with Jordan Reyes (CTO), send a public line such as: *Call the members into your conference room so I may observe your briefing and their thoughts. I will meet you there.*

**Expected:**

- Jordan names **real** cast from the Vertex roster (directors such as Sofia Mendez, Liam Park)—not invented names.
- **People** / roster shows summoned members in **Conference Room** (`scene-conference-room`) without manual WorldRail summon.
- Jordan’s generation tool trace includes `scene_summon` (or narrative-presence fallback when prose-only).
- Travel to Conference Room (map or Places) to hear follow-up lines from summoned directors (briefing chain, capped by `briefingMaxReplies`).

**Automated check:** `tests/test_cast_summon.py`.

### 8. Restart continuity

**Operator action:** Restart server or reload world.

**Expected:**

- Presence, exits, pending knock signals hydrate (MP-11, CC-2)
- Group-scene diary: if Alice and Bob witnessed dialogue, both retain segments after restart (MP-20, golden path step 7)

## What “success feels like”

- **Spatial:** Moving between scenes feels like moving between places, not switching chat tabs.
- **Memory:** NPCs refer to witnessed events without the operator pasting history.
- **Trust:** Queue and scope are visible; whispers stay private; Observer edits are intentional.
- **Honesty:** If GPU is busy, wait is shown—not hung UI.

## UX failure modes (design acceptance)

| Symptom | Likely cause | Spec reference |
|---------|--------------|----------------|
| NPC “forgets” public line after restart | Diary / mandatory recall gap | MP-11, MP-20 |
| Bob “knows” Alice’s private mind | MP-1 leakage | MP-1, MEM-ACC-1 |
| Knock instantly spawns NPC speech | Auto-generation on signal create | CC-11a |
| Reasoning blocks in transcript | stripReasoning gap | OQ-3, MP-17 |
| Stuck “generating” with no queue info | Queue honesty missing | UI-2, INF-5 |

## Golden path alignment

| First-run step | Golden path step ([17](../17-acceptance-criteria.md) §2) |
|----------------|----------------------------------------------------------|
| Demo world loaded | GP-SETUP / step 1 |
| Public + whisper | Steps 2 |
| Move scenes | Step 3 |
| Knock | Step 4 |
| Observer tweak | Step 5 |
| Markdown / Mermaid in reply | UI-R (see §7) |
| Restart | Step 6 |
| Group diary (optional extended session) | Step 7 |

Output quality gates OQ-1 and OQ-3 apply at implementation ([22-output-quality.md](../22-output-quality.md)).

## After golden path (Alpha features)

**Non-normative.** Optional exploration after steps 1–8; not part of the release gate.

1. **Reflection (AO-8):** Settings → World → enable **Character reflection** → open a cast member in **Memory inspector** → **Reflection** tab → **Run reflection now**. Review run history; approve or reject persona proposals when offered.
2. **Idle social / banter:** Settings → **Idle social** policy → tune banter gates and tone → use **Show ambient/banter in transcript** if you want dyad lines in the main chronicle.
3. **Maps:** Settings → **Scenes & layout** → MapDraft / geography; Top bar **Map** for the tactical map console and world overlay.

See [IMPLEMENTATION-CHECKLIST.md](../IMPLEMENTATION-CHECKLIST.md) and [SPEC-GAPS.md](../SPEC-GAPS.md) for wedge vs spec-target depth.

## Related documents

- [ROADMAP.md](../ROADMAP.md) — v1 milestone and deferred artifacts
- [personas.md](../personas.md) — who this experience serves
- [20-product-principles.md](../20-product-principles.md) §5, §8 — golden path and onboarding intent
