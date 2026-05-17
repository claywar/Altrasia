# Map reference images (non-normative)

**Design mockups only** — not runtime assets and **not** sent to the LLM. Normative layout rules and operator flows: [25-map-authoring.md](../../25-map-authoring.md), [14-web-ui.md](../../14-web-ui.md) §21, [18-location-maps.md](../../18-location-maps.md) §12.

Runtime preview and CI compare **SVG rendered from layout JSON** ([25-map-authoring.md](../../25-map-authoring.md) MAP-AUTH-PREVIEW-1). Structural topology MUST match these diagrams; pixel identity is non-normative.

Phase 6 MAY store operator-specific renders under `assets/{worldId}/maps/` ([11-data-model.md](../../11-data-model.md) DM-2).

## Index

| File | Pack | Wireframe | Depicts |
|------|------|-----------|---------|
| [altrasia-structured-minimap.png](altrasia-structured-minimap.png) | **v1** (Stitch Pack A) | WF-2 | Structured mini-map: compass, `travelSteps`, north-aligned rect rooms |
| [altrasia-building-envelope-minimap.png](altrasia-building-envelope-minimap.png) | **v1.1** (Pack B) | WF-2b | Building **outer boundary** + interior rooms + knock exit |
| [altrasia-architecture-diagram-minimap.png](altrasia-architecture-diagram-minimap.png) | **v1.1** (Pack B) | WF-2b | Shapes: circle keep, rect manor, orthogonal edges |
| [altrasia-world-map-overlay-example.png](altrasia-world-map-overlay-example.png) | **Phase 6** | WF-14 | **WorldMapCanvas** site view: multiple structures, terrain, mini-map inset |
| [altrasia-level-stack-example.png](altrasia-level-stack-example.png) | **Phase 6** | WF-15 | **LevelStackView**: exploded floors, stairs/ladder connectors |

## Use in development

| Consumer | How to use |
|----------|------------|
| **LLM map tools** | Use `referenceDiagramId` text enum only ([18-location-maps.md](../../18-location-maps.md) §12.8); output JSON → SVG |
| **CI / acceptance** | Validate JSON against `packages/schemas/map-layout-v1.schema.json`; optional SVG topology compare (MAP-GEN-ACC-*) |
| **Implementers** | Side-by-side while building `SpatialGraphMiniMap`, `WorldMapCanvas`, `LevelStackView` |

## Regenerating

Images were produced as design mockups (May 2026). Replacements MUST preserve the same **information architecture** (envelopes, levels, site scale)—not necessarily pixel-identical art.
