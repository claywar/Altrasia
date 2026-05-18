import { useMemo } from "react";
import type { LayoutDraft, SpatialGraph } from "../../api/client";
import { activeStructureId, prepareGraphForView } from "./floorLevels";
import { LevelStackPanel } from "./LevelStackPanel";
import { ensurePlanPositions, mergeDraftToGraph } from "./layoutDraftMerge";
import { MapRenderer } from "./MapRenderer";
import type { MapGraph } from "./types";

import refMiniEnvelope from "../../../../docs/guides/reference-images/altrasia-building-envelope-minimap.png";
import refMiniShapes from "../../../../docs/guides/reference-images/altrasia-architecture-diagram-minimap.png";
import refSiteOverlay from "../../../../docs/guides/reference-images/altrasia-world-map-overlay-example.png";
import refLevelStack from "../../../../docs/guides/reference-images/altrasia-level-stack-example.png";

const REFERENCE_IMAGES: Record<string, string> = {
  mini_envelope: refMiniEnvelope,
  mini_shapes: refMiniShapes,
  site_overlay: refSiteOverlay,
  level_stack: refLevelStack,
};

type Props = {
  scope: string;
  draft: LayoutDraft | null;
  baseGraph: SpatialGraph | null;
  referenceDiagramId?: string | null;
};

function asMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

export function LayoutDraftPreview({
  scope,
  draft,
  baseGraph,
  referenceDiagramId,
}: Props) {
  const refId =
    referenceDiagramId ??
    (draft?.proposed as { referenceDiagramId?: string } | null)?.referenceDiagramId ??
    (scope === "site"
      ? "site_overlay"
      : scope === "stack"
        ? "level_stack"
        : "mini_envelope");

  const previewGraph = useMemo(() => {
    const merged = mergeDraftToGraph(draft?.proposed ?? null, baseGraph);
    if (!merged) return null;
    return scope === "stack" ? ensurePlanPositions(merged) : merged;
  }, [draft?.proposed, baseGraph, scope]);

  const prepared = useMemo(() => {
    if (!previewGraph) return null;
    const mg = asMapGraph(previewGraph);
    if (scope === "site") return prepareGraphForView(mg, "site");
    if (scope === "floor" && activeStructureId(mg)) {
      return prepareGraphForView(mg, "floor");
    }
    return null;
  }, [previewGraph, scope]);

  if (!previewGraph) {
    return <p className="map-draft-preview__empty">Generate a draft to preview.</p>;
  }

  const refSrc = REFERENCE_IMAGES[refId];
  const mg = asMapGraph(previewGraph);

  return (
    <div className="map-draft-preview">
      {refSrc && (
        <figure className="map-draft-preview__reference">
          <img src={refSrc} alt={`Reference: ${refId}`} />
          <figcaption>Reference — {refId.replace(/_/g, " ")}</figcaption>
        </figure>
      )}

      <div className="map-draft-preview__canvas">
        {scope === "stack" ? (
          <LevelStackPanel
            graph={previewGraph}
            structureId={activeStructureId(mg)}
            focusLevel={0}
            onFocusLevel={() => {}}
          />
        ) : scope === "site" || scope === "floor" ? (
          <MapRenderer
            graph={
              prepared
                ? ({
                    ...previewGraph,
                    nodes: prepared.graph.nodes,
                    edges: prepared.graph.edges,
                    structures: prepared.graph.structures,
                  } as SpatialGraph)
                : previewGraph
            }
            viewFit="full"
            showSiteUnderlay={scope === "site"}
            showEnvelopes
            showEdges
            showLabels
            worldMap={previewGraph.worldMap}
            className="map-draft-preview__map"
          />
        ) : (
          <MapRenderer
            graph={previewGraph}
            viewFit="neighborhood"
            showEnvelopes
            showEdges
            showLabels
            className="map-draft-preview__map"
          />
        )}
      </div>
    </div>
  );
}
