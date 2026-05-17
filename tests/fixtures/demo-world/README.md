# Demo world fixture — `demo-spatial-v1`

Normative reference world for v1 spatial golden path and first-session onboarding ([20-product-principles.md](../../../docs/20-product-principles.md) §8, [17-acceptance-criteria.md](../../../docs/17-acceptance-criteria.md) GP-SETUP).

## Fixture id

`demo-spatial-v1`

## Seed spec (design phase)

Machine-readable world definition: [`demo-spatial-v1.json`](demo-spatial-v1.json). Implementations SHOULD load this file in seed scripts and API fixture loaders.

## Load paths (implementation)

| Method | Description |
|--------|-------------|
| Seed script | `scripts/seed-demo-world.ts` reads `demo-spatial-v1.json` → operator SQLite |
| Snapshot | `demo-spatial-v1.sqlite` in this directory (optional checked-in snapshot) |
| API | `POST /api/v1/worlds` with body `{ "fixtureId": "demo-spatial-v1" }` |

## World

| Field | Value |
|-------|-------|
| `name` | Demo Spatial World |
| `defaultModelProfile` | `qwen3.6-35b-a3b` |
| Preset | **Solo story** ([20-product-principles.md](../../../docs/20-product-principles.md) §6) |

**`configJson`:**

```json
{
  "agentContinueEnabled": true,
  "maxContinueDepth": 2
}
```

## Scenes

| sceneId | locationName | persona start |
|---------|--------------|---------------|
| `scene-hall` | Hall | yes (`activeSceneId`) |
| `scene-kitchen` | Kitchen | no |

**Exit (Hall → Kitchen):**

```json
{
  "exitId": "hall-kitchen-door",
  "label": "Door to kitchen",
  "targetSceneId": "scene-kitchen",
  "kind": "door",
  "doorState": "closed"
}
```

Reverse exit on Kitchen → Hall with matching `doorState`.

## Cast

| characterId | displayName | speechWeight | notes |
|-------------|-------------|--------------|-------|
| `char-alice` | Alice | 0.6 | Present in Hall initially |
| `char-bob` | Bob | 0.4 | Present in Kitchen initially |
| `observer` | Observer | — | Meta channel only |

Pre-seeded `definitionJson` for Alice and Bob (minimal persona + instructions). v1 golden path does not require AI character draft ([24-character-authoring.md](../../../docs/24-character-authoring.md)).

## Presence (initial)

- `scene-hall`: `__persona__`, `char-alice`
- `scene-kitchen`: `char-bob`

## Non-goals

- No phone metadata in seed messages
- No commission or debate activity rows

## Acceptance

Golden path steps 1–8 ([17-acceptance-criteria.md](../../../docs/17-acceptance-criteria.md) §2) MAY start from this fixture via GP-SETUP.
