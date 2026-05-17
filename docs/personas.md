# Operator Personas

Non-normative product context for who Altrasia is for and what jobs it solves. Normative requirements remain in numbered specs and [20-product-principles.md](20-product-principles.md).

**Repository status:** design specifications only; no runnable product yet. See [ROADMAP.md](ROADMAP.md).

## Primary audience

Altrasia targets a **solo operator** on a **single local machine** with a capable GPU (reference: Qwen3.6-35B-A3B via llama.cpp). You play as the **persona**; NPCs are the cast; the **Observer** is a secondary studio channel for tuning—not the main play voice.

This is not aimed at game-design teams building levels in an engine, multi-tenant SaaS operators, or casual chat-only users.

## Personas

### Solo storyteller

| | |
|--|--|
| **Job-to-be-done** | I want NPCs who remember what happened *where*, across sessions, without re-prompting the same facts every time I open the app. |
| **Typical session** | Load a world, speak in public at one scene, move to another, return later and have cast recall witnessed events with spatial discipline. |
| **Success signal** | Golden path steps 1–7 ([17-acceptance-criteria.md](17-acceptance-criteria.md)); restart continuity (MP-11, MP-20). |
| **Preset** | **Solo story** (v1 default) — moderate idle, `agentContinue` on, `maxContinueDepth` 2 |

### World tuner

| | |
|--|--|
| **Job-to-be-done** | I want to adjust scenes, fixtures, and cast through the Observer without breaking diegesis or leaking private memory across characters. |
| **Typical session** | Observer Studio meta-chat or tools rename a scene; framing updates in play; cast prompts never include Observer digest (ROLE-1). |
| **Success signal** | Golden path step 5; OBS-2 world edits via tools only. |
| **Preset** | **Writer** — idle off, deeper continue chain for focused drafting |

### Watch-mode operator

| | |
|--|--|
| **Job-to-be-done** | I want agents to act while I observe, with fair scheduling and visible GPU queue state—not silent starvation or opaque picks. |
| **Typical session** | Aquarium-style preset; queue strip shows trigger, `continueDepth`, selection rationale (UI-1, UI-2). |
| **Success signal** | AO-19 continue chains; INF-5 queue honesty in UI. |
| **Preset** | **Aquarium** — higher idle, limited `agentContinue`; requires queue honesty UI |

## Preset mapping

From [20-product-principles.md](20-product-principles.md) §6:

| Preset | Idle activity | `agentContinue` | `maxContinueDepth` | Best for |
|--------|---------------|-----------------|-------------------|----------|
| **Solo story** | Moderate | on | 2 | Default narrative play |
| **Writer** | Off | on | 3 | Focused drafting, minimal idle noise |
| **Aquarium** | Higher | off or 1 | 1 | Watching agents interact |

Orchestration detail: [13-agent-orchestration.md](13-agent-orchestration.md) §6.2.

## What v1 is not (for these personas)

- **Not** SillyTavern — no card PNG ecosystem or extension marketplace ([20-product-principles.md](20-product-principles.md) §1).
- **Not** a coding agent — real-world tools are deferred and approval-gated ([08-real-world-capabilities.md](08-real-world-capabilities.md)).
- **Not** in-world research teams in v1 — commissions and debate runtime are **Act 3** ([ROADMAP.md](ROADMAP.md), [23-in-world-work.md](23-in-world-work.md)).

## Related documents

- [ROADMAP.md](ROADMAP.md) — milestones and Acts 1–3
- [guides/first-run-experience.md](guides/first-run-experience.md) — intended first session
- [20-product-principles.md](20-product-principles.md) — wedge, golden path, onboarding
