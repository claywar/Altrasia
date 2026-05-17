# Map regen conflict fixture (MAP-7, MAP-AUTH-CONFLICT-1)

Used for partial-commit and per-conflict resolver UI tests ([25-map-authoring.md](../../../docs/25-map-authoring.md) §6).

## Scenario

World has `scene-hall` with a fixture-bound hotspot. Proposed layout draft moves the hall footprint such that the hotspot drifts (`fixture_drift` — soft warn + apply) while also attempting to remove a referenced exit (`exit_target_invalid` — hard).

## Files

| File | Role |
|------|------|
| `world-before.json` | Current spatial-graph / scene layout snapshot |
| `draft-proposed.json` | Layout draft that triggers mixed conflicts |
| `expected-conflicts.json` | Expected `conflicts[]` after partial commit |

Populate when implementation begins; structure documented in doc 25.
