import type { SpatialGraph } from "../../api/client";
import {
  activeStructureId,
  levelLabelFor,
  levelsForStructure,
  type MapViewMode,
} from "../maps/floorLevels";
import { viewModeDescription, type MapViewCapabilities } from "../maps/mapNavigation";
import type { MapGraph } from "../maps/types";

type Props = {
  graph: SpatialGraph;
  cameraContext: MapViewMode;
  previewLevel: number;
  caps: MapViewCapabilities;
  layoutIncomplete: boolean;
  showEnhance: boolean;
  floorPlanOpen: boolean;
  viewScope?: "site" | "building";
  onLevelChange: (level: number) => void;
  onToggleFloorPlan: () => void;
  onSeeAll?: () => void;
  onEnhance: () => void;
  onClose: () => void;
};

function breadcrumb(graph: SpatialGraph, ctx: MapViewMode, level: number): string {
  const mg = graph as MapGraph;
  const active = mg.nodes.find((n) => n.isActive);
  const parts = ["Site"];
  const structId = active?.structureId;
  if (structId && ctx !== "site") {
    const st = graph.structures?.find((s) => s.structureId === structId);
    parts.push(st?.displayName ?? structId);
  }
  if (structId && (ctx === "floor" || ctx === "stack")) {
    parts.push(levelLabelFor(mg.nodes, structId, level));
  } else if (ctx === "stack") {
    parts.push("All floors");
  }
  return parts.join(" › ");
}

export function MapFloatingHud({
  graph,
  cameraContext,
  previewLevel,
  caps,
  layoutIncomplete,
  showEnhance,
  floorPlanOpen,
  viewScope = "site",
  onLevelChange,
  onToggleFloorPlan,
  onSeeAll,
  onEnhance,
  onClose,
}: Props) {
  const mg = graph as MapGraph;
  const structId = activeStructureId(mg);
  const levels = structId ? levelsForStructure(mg.nodes, structId) : [];
  const ctxDesc = viewModeDescription(cameraContext, caps);

  return (
    <header className="map-floating-hud" data-testid="map-floating-hud">
      <div className="map-floating-hud__left">
        <h2 className="map-floating-hud__title">World map</h2>
        <p className="map-floating-hud__crumb">{breadcrumb(graph, cameraContext, previewLevel)}</p>
        {!floorPlanOpen && (
          <span className="map-floating-hud__context" title={ctxDesc.subtitle}>
            {ctxDesc.title}
          </span>
        )}
      </div>
      <div className="map-floating-hud__center">
        {!floorPlanOpen && levels.length > 1 && structId && (
          <div className="map-floating-hud__levels" aria-label="Floor">
            <button
              type="button"
              disabled={previewLevel <= levels[0]}
              onClick={() => {
                const idx = levels.indexOf(previewLevel);
                if (idx > 0) onLevelChange(levels[idx - 1]);
              }}
              aria-label="Previous floor"
            >
              −
            </button>
            <span>{levelLabelFor(mg.nodes, structId, previewLevel)}</span>
            <button
              type="button"
              disabled={previewLevel >= levels[levels.length - 1]}
              onClick={() => {
                const idx = levels.indexOf(previewLevel);
                if (idx >= 0 && idx < levels.length - 1) onLevelChange(levels[idx + 1]);
              }}
              aria-label="Next floor"
            >
              +
            </button>
          </div>
        )}
      </div>
      <div className="map-floating-hud__actions">
        {layoutIncomplete && <span className="map-floating-hud__banner">Layout incomplete</span>}
        {showEnhance && (
          <button type="button" className="map-floating-hud__ghost" onClick={onEnhance}>
            Enhance map
          </button>
        )}
        {!floorPlanOpen && viewScope === "building" && onSeeAll && (
          <button type="button" className="map-floating-hud__ghost" onClick={onSeeAll}>
            See all
          </button>
        )}
        <button
          type="button"
          className={floorPlanOpen ? "map-floating-hud__active" : undefined}
          onClick={onToggleFloorPlan}
        >
          {floorPlanOpen ? "3D view" : "Floor plan"}
        </button>
        <button type="button" onClick={onClose} aria-label="Close map">
          Close (M)
        </button>
      </div>
    </header>
  );
}
