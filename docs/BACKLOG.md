# Implementation backlog

**Last completed:** T-204 (documentation sync)

## Phase A — Wedge (T-001–T-081)

Alpha spatial wedge shipped in tree. See [CHANGELOG.md](../CHANGELOG.md).

| Phase | Tasks | Status |
|-------|-------|--------|
| 0 Alignment | T-001–T-004 | done |
| 1 CI / release | T-010–T-016 | done |
| 2 Orchestration / memory | T-020–T-026 | done |
| 3 Real-world tools | T-030–T-034 | wedge |
| 4 Plugins | T-040–T-044 | wedge |
| 5 Maps | T-050–T-055 | wedge |
| 6 ComfyUI | T-060–T-063 | wedge |
| 7 UI QA | T-070–T-075 | wedge |
| 8 Ship gate | T-080–T-082 | done (tag optional) |

## Phase B — Spec depth (T-100+)

Per [SPEC-GAPS.md](SPEC-GAPS.md).

| Phase | Tasks | Status |
|-------|-------|--------|
| 0 Doc sync | T-100–T-104 | done |
| 1 UI acceptance + CI | T-110–T-119 | done |
| 2 Real LLM nightly | T-120–T-126 | done |
| 3 Tools + plugins | T-130–T-139 | done |
| 4 ComfyUI | T-150–T-157 | done |
| 5 Phase 6 maps | T-160–T-173 | done (API + tests; full MAP-ACC UI depth ongoing) |
| 6 Orchestration polish | T-180–T-184 | done |
| 7 Release + guides | T-190–T-195 | done (git tag T-190 on operator request) |

## Phase C — Documentation sync (T-200+)

Align normative docs with Alpha wedge in tree. Open **implementation** gaps remain in [SPEC-GAPS.md](SPEC-GAPS.md).

| Task | Description | Status |
|------|-------------|--------|
| T-200 | Scope/terminology — docs/README, 20-product-principles, 18-location-maps, root README | done |
| T-201 | Tracking indexes — IMPLEMENTATION-CHECKLIST, REQUIREMENTS-INDEX, ROADMAP, SPEC-GAPS | done |
| T-202 | API sketch + tool registry — 12-api-sketch, 05-tool-calling | done |
| T-203 | Normative reconciliation — 13, 16, 17, 14-web-ui | done |
| T-204 | Operator guides + CHANGELOG | done |

## Related

- [ROADMAP.md](ROADMAP.md)
- [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md)
- [SPEC-GAPS.md](SPEC-GAPS.md)
