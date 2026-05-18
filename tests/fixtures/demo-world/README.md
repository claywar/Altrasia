# Demo world fixture `demo-spatial-v1`

**Altrasia Manor — Demo** — showcase map for the spatial UI: manor envelope (hall, kitchen, pantry), **Round Keep** (circle), **Outer Bailey** (courtyard), compass-aligned exits, mixed `travelSteps`, and `worldMap` site placements.

Load via API:

```http
POST /api/v1/worlds
{ "fixtureId": "demo-spatial-v1" }
```

Or Web UI **Load demo world**, or CLI:

```bash
altrasia load-demo
```

**Map highlights:** structure boundaries, `mapShape` rect/circle/corridor, north-aligned edges, 1-step vs 2-step travel, cross-structure gates (knock), ground-floor zones.

Spec: [demo-spatial-v1.json](demo-spatial-v1.json). Target load time: under 2s on reference dev hardware.
