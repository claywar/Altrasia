# Changelog

All notable changes to Altrasia are documented here.

## [Unreleased]

### Added

- Spec gaps plan implementation: Playwright e2e in CI, map artifacts API (004 migration), plugin/FS/ComfyUI tests, speak_intent tie-break, embed rerank hook.
- [docs/SPEC-GAPS.md](docs/SPEC-GAPS.md) living tracker; BACKLOG T-100+ phases.
- AO-17/18 `score_speakers` with FTS speak-readiness probe (`orchestrator/speaker_selection.py`).
- Embedding pipeline (`memory/embeddings.py`) and hybrid search when `ALTRASIA_EMBED_BASE_URL` is set.
- SSRF-safe `web_fetch`, FS agent tools, scheduler stub, `scene_exit_set_state` (CC-11c).
- Plugin loader + reference `plugins/web-tools` and `plugins/comfyui-media`.
- ComfyUI portrait API stub; `WorldMapCanvas`, mini-map shapes/envelopes.
- Playwright smoke tests (`web/e2e/smoke.spec.ts`).
- Nightly workflow, OpenAPI export (`packages/openapi/altrasia-v1.json`), `SECURITY.md`, `CONTRIBUTING.md`.

### Note

- Swipe/regenerate on committed messages remains deferred per UI-REG (streaming cancel only).
- Git release tag: create on operator request (`T-082`).

### Changed

- Documentation aligned with shipped Alpha (ROADMAP, IMPLEMENTATION-CHECKLIST, BACKLOG).

## [0.1.0-alpha] — 2026-05-18

### Added

- Python backend (`altrasia serve`) with SQLite persistence, memory (FTS + mandatory recall), GpuResourceQueue, mock/real LLM adapter.
- Web UI SPA: spatial play, Observer Studio, commissions, debate, MapDraft, character draft, world package import/export.
- Phone play, global heartbeat, approvals, evidence, world commons, briefing board.
- Demo world `demo-spatial-v1` via `fixtureId` or `altrasia load-demo`.
- 58+ pytest covering golden path, memory perf, in-world acceptance.
