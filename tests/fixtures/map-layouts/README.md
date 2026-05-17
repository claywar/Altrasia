# Map layout fixtures (Phase 6)

Hand-authored layout JSON for CI ([18-location-maps.md](../../../docs/18-location-maps.md) MAP-24, MAP-GEN-ACC-*). Validated against [`packages/schemas/map-layout-v1.schema.json`](../../../packages/schemas/map-layout-v1.schema.json).

| Fixture | Scope | Reference image |
|---------|-------|-----------------|
| [demo-spatial-mini.json](demo-spatial-mini.json) | `mini` | Hall + Kitchen (`demo-spatial-v1`) |
| [demo-mini-layout.json](demo-mini-layout.json) | `mini` | Same topology as demo-spatial-mini (MAP-GEN-ACC-1) |
| [demo-site-layout.json](demo-site-layout.json) | `site` | [worldengine-world-map-overlay-example.png](../../../docs/guides/reference-images/worldengine-world-map-overlay-example.png) |
| [demo-stack-layout.json](demo-stack-layout.json) | `stack` | [worldengine-level-stack-example.png](../../../docs/guides/reference-images/worldengine-level-stack-example.png) |

Partial-commit conflicts: [../map-regen-conflict/](../map-regen-conflict/).

Optional golden SVG renders MAY be added for visual regression (non-normative).
