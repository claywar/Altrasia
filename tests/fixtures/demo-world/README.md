# Demo world fixture `demo-spatial-v1`

**Vertex Labs HQ — Demo** — modern software-company showcase for the spatial UI: lobby hub, team studios, engineering garage and tech lab, engineering wing with twelve private engineer offices, compass-aligned exits, mixed `travelSteps`, and `worldMap` site placement.

Load via API:

```http
POST /api/v1/worlds
{ "fixtureId": "demo-spatial-v1" }
```

Or Web UI **Load demo world**, or CLI:

```bash
altrasia load-demo
```

**Cast:** 27 characters (CTO, four directors, product/program ICs, cloud/QA/mobile/embedded/systems/validation engineers). **Scenes:** 20 (shared workspaces + engineering corridor + offices).

**Map highlights:** single HQ structure envelope, ground floor + engineering wing levels, blueprint style, 1-step vs 2-step travel, stairs to engineering offices.

Spec: [demo-spatial-v1.json](demo-spatial-v1.json). Regenerate with `python tests/fixtures/demo-world/build_vertex_demo.py`. Target load time: under 2s on reference dev hardware.
