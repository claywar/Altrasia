# Spec gaps tracker

Living index of normative requirements **not yet fully accomplished** vs docs `00`–`25`. v1/v1.1 release gates are met in pytest; this tracks depth and UI automation.

**Milestone tiers:** Beta (Phases 0–2, 7) → Production-local (+3) → Full spatial (+5) → Media-complete (+4).

## Status summary

| Area | Spec | Wedge in tree | Full spec + CI |
|------|------|---------------|------------------|
| Spatial golden path | [17](17-acceptance-criteria.md) §2 | Yes (mock LLM) | Nightly real LLM optional |
| Web UI acceptance | [14](14-web-ui.md), [17](17-acceptance-criteria.md) §3 | Playwright e2e in CI | Full UI-MAP-ACC5–8 manor fixture in demo |
| Web / FS / plugins | [06](06-web-tools.md), [08](08-real-world-capabilities.md), [15](15-plugin-platform.md) | Tests + allowlist config | Production SSRF matrix expansion |
| ComfyUI | [19](19-comfyui-media.md) | Stub + workflows + tests | Live ComfyUI server integration |
| Phase 6 maps | [18](18-location-maps.md), [25](25-map-authoring.md) | MapArtifact API + tests | MAP-ACC-1–6 full UI (LevelStack, FloorPlan) |
| Orchestration polish | [13](13-agent-orchestration.md) | speak_intent, embed rerank | AO-22 full activity overlays |

## Phases (T-100+)

See [BACKLOG.md](BACKLOG.md) for task IDs. Implement in order: doc sync → UI CI → nightly LLM → tools → ComfyUI/maps → orchestration → release tag.

## Related

- [ROADMAP.md](ROADMAP.md)
- [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
