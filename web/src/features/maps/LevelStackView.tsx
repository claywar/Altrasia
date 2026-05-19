import { useMemo } from "react";
import type { SpatialGraph } from "../../api/client";
import {
  buildingExtrusionFaces,
  layoutUnifiedBuildingStack,
  LABEL_GUTTER,
  ROOT_MARGIN,
  unifiedStackConnectors,
} from "./buildingStackLayout";
import {
  stackPlatesForStructure,
  verticalLinksForStructure,
} from "./floorLevels";
import { IsoDiagramPlate } from "./IsoDiagramPlate";
import { resolveArchitectureStyle, styleTokens } from "./mapStyle";
import type { MapGraph } from "./types";
import type { StackPlate } from "./floorLevels";
import { VerticalConnectorGlyph } from "./VerticalConnectorGlyph";

type Props = {
  graph: SpatialGraph | null;
  structureId?: string;
  focusLevel: number;
  plates?: StackPlate[];
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
  plates: platesProp,
  selectedSceneId = null,
  onSelectScene,
  onTravelVertical,
}: Props) {
  const mg = graph ? toMapGraph(graph) : null;
  const sid = structureId;

  const plates = useMemo(
    () => platesProp ?? (mg && sid ? stackPlatesForStructure(mg, sid) : []),
    [platesProp, mg, sid]
  );

  const vertical = useMemo(
    () => (mg && sid ? verticalLinksForStructure(mg, sid) : []),
    [mg, sid]
  );

  const structure = mg?.structures?.find((s) => s.structureId === sid);

  const stack = useMemo(
    () => layoutUnifiedBuildingStack(plates, structure, vertical),
    [plates, structure, vertical]
  );

  const nodeById = useMemo(
    () => new Map((mg?.nodes ?? []).map((n) => [n.sceneId, n])),
    [mg]
  );

  const connectors = useMemo(
    () => (stack ? unifiedStackConnectors(stack, vertical, nodeById) : []),
    [stack, vertical, nodeById]
  );

  const extrusionFaces = useMemo(
    () => (stack && structure ? buildingExtrusionFaces(stack, structure) : []),
    [stack, structure]
  );

  const archStyle = resolveArchitectureStyle(graph);
  const tokens = styleTokens(archStyle, true);

  if (!stack || plates.length === 0) {
    return null;
  }

  const insetX = ROOT_MARGIN + LABEL_GUTTER;
  const insetY = ROOT_MARGIN;
  const floorTransform = (stackY: number) =>
    `translate(${insetX}, ${insetY + stackY * stack.scale}) scale(${stack.scale}) translate(${-stack.vb.x}, ${-stack.vb.y})`;

  return (
    <svg
      viewBox={`0 0 ${stack.rootW} ${stack.rootH}`}
      className="level-stack__svg level-stack__svg--building"
      role="img"
      aria-label="Building cutaway"
    >
      {extrusionFaces.map((d, i) => (
        <path
          key={`extrude-${i}`}
          d={d}
          className="level-stack__extrusion"
          fill="var(--map-structure-fill, rgba(28, 36, 48, 0.7))"
          stroke="var(--border)"
          strokeWidth={0.2}
        />
      ))}

      {stack.floors.map((floor) => {
        const isFocus = floor.level === focusLevel;
        return (
          <g
            key={floor.level}
            data-stack-level={floor.level}
            className={`level-stack-floor${isFocus ? " level-stack-floor--focus" : ""}`}
            transform={floorTransform(floor.stackY)}
          >
            <IsoDiagramPlate
              nodes={floor.nodes}
              edges={floor.edges}
              structure={structure}
              origin={stack.origin}
              tokens={tokens}
              useStructureShell
              dimmed={!isFocus}
              interactive={Boolean(onSelectScene)}
              selectedSceneId={selectedSceneId}
              onSceneClick={onSelectScene}
              idPrefix={`stack-${floor.level}`}
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
