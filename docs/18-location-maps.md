# 18 — Location Maps (Future)

**Status:** Post-v1. Normative target so implementation aligns with core GPU, memory, and Observer rules.

## 1. Goal

Operator gets a **spatial feel** when moving between scenes—interactive maps in Web UI, grounded in world state ([20-product-principles.md](20-product-principles.md) spatial wedge).

## 2. Requirements

| ID | Requirement |
|----|-------------|
| MAP-1 | Each `sceneId` MAY have `mapArtifact`: versioned JSON (grid/vector), layers, legend, bounds—not reasoning dumps. |
| MAP-2 | World overview links scenes via `exits[]` and world pool loci. |
| MAP-3 | Tools: `map_generate`, `map_update_region`, `map_set_hotspot` — JSON output only; MP-14. |
| MAP-4 | Hotspots bind to fixtures, exit `targetSceneId`, or operator actions. |
| MAP-5 | Web UI: pan/zoom, scene picker, hotspot → fixture / persona move on exit. |
| MAP-6 | Map gen reads scene framing + world loci; memory tools if blocking on (MP-10). |
| MAP-7 | Regen MUST NOT silently retcon fixtures—diff and operator ack. |
| MAP-8 | Optional fog: cast framing may show reduced map; operator sees full map. |

## 3. Shared rules

| Rule | Application |
|------|-------------|
| GpuResourceQueue | Layout LLM uses `chat`; illustration uses `image` (ComfyUI) |
| MP-8–MP-19 | Store map JSON and captions only |
| MP-1 | Hidden rooms stay in mind pool, not world map layer |
| OBS-2, OBS-5 | Observer/location admin initiates; tools for mutations |
| Approvals | `requireApprovalForMapOverwrite` optional |
| stripReasoning | Prompt summary loci stripped |

## 4. Storage

- `map_artifacts` table or blob column per sceneId
- Thumbnail via ComfyUI or static render under `assets/{worldId}/maps/`

## 5. v1

Maps are **not implemented** in v1. `exits[]` and spatial-graph API (CC-1) prepare data for MAP-2.

**v1 Web UI bridge:** read-only `SpatialGraphMiniMap` — structured layout (§21.1), architectural footprints (§21.2), **building envelopes** (§21.3: outer boundaries, interior vs exterior exits, navigation breadcrumb). Scene switching in right rail **Places** (UI-LAY-2, §20–§21).

**Post-v1:** `mapArtifact` (MAP-1) MAY supply full floor plans; mini-map shows a **simplified footprint** derived from the artifact; `MapCanvas` (MAP-5) is the interactive editor.

## Related documents

- [21-cross-scene-awareness.md](21-cross-scene-awareness.md)
- [19-comfyui-media.md](19-comfyui-media.md)
- [14-web-ui.md](14-web-ui.md)
