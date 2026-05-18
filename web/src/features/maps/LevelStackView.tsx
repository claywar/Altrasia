import { useMemo } from "react";
import type { SpatialGraph } from "../../api/client";
import { DiagramPlate } from "./DiagramPlate";
import { DIAGRAM_PROFILES } from "./diagramProfiles";
import {
  stackPlatesForStructure,
  verticalLinksForStructure,
} from "./floorLevels";
import { IsoDiagramPlate } from "./IsoDiagramPlate";
import { resolveArchitectureStyle, styleTokens } from "./mapStyle";
import {
  layoutStackPlates,
  stackConnectors,
  type StackLayoutResult,
} from "./stackGeometry";
import type { MapEdge, MapGraph } from "./types";
import type { StackPlate } from "./floorLevels";
import { VerticalConnectorGlyph } from "./VerticalConnectorGlyph";

type Props = {
  graph: SpatialGraph | null;
  structureId?: string;
  focusLevel: number;
  stackLayout?: StackLayoutResult | null;
  plates?: StackPlate[];
  vertical?: MapEdge[];
  selectedSceneId?: string | null;
  onSelectScene?: (sceneId: string) => void;
  onTravelVertical?: (exitId: string) => void;
};

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

export function LevelStackView({
  graph,
  structureId,
  focusLevel,
  stackLayout: stackLayoutProp,
  plates: platesProp,
  vertical: verticalProp,
  selectedSceneId = null,
  onSelectScene,
  onTravelVertical,
}: Props) {
  const mg = graph ? toMapGraph(graph) : null;
  const sid = structureId;
  const projection = DIAGRAM_PROFILES.stack.projection;
  const archStyle = resolveArchitectureStyle(graph);
  const tokens = styleTokens(archStyle, true);

  const plates = useMemo(
    () => platesProp ?? (mg && sid ? stackPlatesForStructure(mg, sid) : []),
    [platesProp, mg, sid]
  );
  const vertical = useMemo(
    () => verticalProp ?? (mg && sid ? verticalLinksForStructure(mg, sid) : []),
    [verticalProp, mg, sid]
  );

  const stackLayout = useMemo(
    () =>
      stackLayoutProp ??
      (plates.length ? layoutStackPlates(plates, vertical, projection) : null),
    [stackLayoutProp, plates, vertical, projection]
  );

  const nodeById = useMemo(
    () => new Map((mg?.nodes ?? []).map((n) => [n.sceneId, n])),
    [mg]
  );

  const connectors = useMemo(
    () =>
      stackLayout
        ? stackConnectors(stackLayout.layouts, vertical, nodeById, projection)
        : [],
    [stackLayout, vertical, nodeById, projection]
  );

  const structure = mg?.structures?.find((s) => s.structureId === sid);

  if (!stackLayout || plates.length === 0) {
    return null;
  }

  const rootVb = `0 0 ${stackLayout.rootW} ${stackLayout.rootH}`;
  const PlateRenderer = projection === "iso" ? IsoDiagramPlate : DiagramPlate;

  return (
    <svg viewBox={rootVb} className="level-stack__svg" role="img" aria-label="Level stack diagram">
      {stackLayout.layouts.map((layout) => {
        const isFocusPlate = layout.level === focusLevel;
        return (
          <g
            key={layout.level}
            data-stack-level={layout.level}
            className={`level-stack-plate${isFocusPlate ? " level-stack-plate--focus" : ""}`}
            transform={`translate(${6}, ${6 + layout.y}) scale(${layout.scale}) translate(${-layout.vb.x}, ${-layout.vb.y})`}
          >
            <PlateRenderer
              nodes={layout.nodes}
              edges={layout.plate.edges}
              structure={structure}
              tokens={tokens}
              dimmed={!isFocusPlate}
              interactive={Boolean(onSelectScene)}
              selectedSceneId={selectedSceneId}
              onSceneClick={onSelectScene}
              idPrefix={`stack-${layout.level}`}
            />
          </g>
        );
      })}
      {connectors.map((c) => (
        <VerticalConnectorGlyph
          key={c.edge.exitId}
          connector={c}
          onClick={onTravelVertical}
        />
      ))}
    </svg>
  );
}
