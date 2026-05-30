# Spec gaps tracker

Living index of normative requirements **not yet fully accomplished** vs docs `00`–`26`. v1/v1.1 release gates are met in pytest; this tracks **implementation depth** and UI automation still open.

**Relationship to [BACKLOG.md](BACKLOG.md):** Phase B (T-100+) marks **engineering milestones** completed in tree. This document tracks **normative spec depth** that remains open—not doc-sync work.

**Milestone tiers:** Beta (Phases 0–2, 7) → Production-local (+3) → Full spatial (+5) → Media-complete (+4).

## Status summary

| Area | Spec | Wedge in tree | Full spec + CI |
|------|------|---------------|------------------|
| Spatial golden path | [17](17-acceptance-criteria.md) §2 | Yes (mock LLM) | Nightly real LLM optional |
| Web UI acceptance | [14](14-web-ui.md), [17](17-acceptance-criteria.md) §3 | Playwright e2e in CI | Full UI-MAP-ACC5–8 manor fixture in demo |
| Web / FS / plugins | [06](06-web-tools.md), [08](08-real-world-capabilities.md), [15](15-plugin-platform.md) | Tests + allowlist config; mock defaults | Production SSRF matrix expansion |
| ComfyUI | [19](19-comfyui-media.md) | Live client, profiles, workflows, `image_generate`, Media settings UI | IP-Adapter reference pipeline depth; production checkpoint validation |
| Phase 6 maps | [18](18-location-maps.md), [25](25-map-authoring.md) | MapArtifact API, MapDraft, 3D explorer | MAP-ACC-1–6 full UI; layout-draft `sync`/`preview.svg`/etc. |
| Reflection (AO-8) | [16-learning.md](16-learning.md) §6 | Pipeline + UI + tests; default off | Operator guide in doc 16 §6.4 |
| Commons (MP-22) | [23-in-world-work.md](23-in-world-work.md) | GET/PUT API | Web UI panel |
| Orchestration | [13](13-agent-orchestration.md) | speak_intent, embed rerank, banter wedge, AO-22-full **done** | — |
| Scene framing / cast summon | [03](03-locations-and-presence.md), [10](10-prompt-injection.md), [05](05-tool-calling.md) | inventory, fixture/stash tools, framing summaries, narrative pickup/llm, outfit presets **done** | — |
| Memory operator tools | [02](02-memory.md), [12-api-sketch.md](12-api-sketch.md) §9 | World-scoped mind/diary/evidence inspector | `PATCH .../loci/{key}`; `GET /scenes/{id}/loci` |

## Phases (implementation — not doc sync)

See [BACKLOG.md](BACKLOG.md) for task IDs. Remaining **implementation** work: production web/FS, live ComfyUI, MAP-ACC UI gates, commons panel, scene tool suite.

## Related

- [ROADMAP.md](ROADMAP.md)
- [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
