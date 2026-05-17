# Map reference images (non-normative)

Visual targets for **LLM-generated map layouts** and implementer QA. Normative layout rules: [14-web-ui.md](../../14-web-ui.md) §21, [18-location-maps.md](../../18-location-maps.md) §12.

These images are checked into the repo as **reference artifacts**—not runtime assets. Phase 6 MAY also store operator-specific renders under `assets/{worldId}/maps/` ([11-data-model.md](../../11-data-model.md) DM-2).

## Index

| File | Wireframe | Depicts |
|------|-----------|---------|
| [worldengine-structured-minimap.png](worldengine-structured-minimap.png) | WF-2 (partial) | Structured mini-map: compass, `travelSteps`, north-aligned rooms |
| [worldengine-building-envelope-minimap.png](worldengine-building-envelope-minimap.png) | WF-2 | Building **outer boundary** + interior rooms + knock exit |
| [worldengine-architecture-diagram-minimap.png](worldengine-architecture-diagram-minimap.png) | WF-2 | Shapes: circle keep, rect manor, orthogonal edges |
| [worldengine-world-map-overlay-example.png](worldengine-world-map-overlay-example.png) | **WF-14** | **WorldMapCanvas** site view: multiple structures, terrain, mini-map inset |
| [worldengine-level-stack-example.png](worldengine-level-stack-example.png) | **WF-15** | **LevelStackView**: exploded floors, stairs/ladder connectors |

## Use in development

| Consumer | How to use |
|----------|------------|
| **LLM map tools** | Include thumbnails or paths in eval prompts; model output JSON MUST validate then render to comparable diagrams ([18-location-maps.md](../../18-location-maps.md) MAP-GEN-*) |
| **CI / acceptance** | Optional visual regression against simplified SVG render of parsed JSON (MAP-GEN-ACC-3) |
| **Implementers** | Side-by-side while building `SpatialGraphMiniMap`, `WorldMapCanvas`, `LevelStackView` |

## Regenerating

Images were produced as design mockups (May 2026). Replacements MUST preserve the same **information architecture** (envelopes, levels, site scale)—not necessarily pixel-identical art.
