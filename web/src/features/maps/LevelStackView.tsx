import { useMemo } from "react";
import type { SpatialGraph } from "../../api/client";
import { computeViewBox } from "./computeViewBox";
import {
  activeLevel,
  activeStructureId,
  stackPlatesForStructure,
  verticalLinksForStructure,
} from "./floorLevels";
import { edgeEndpoints, nodeFootprint } from "./layoutGeometry";
import { levelBadgeShort } from "./labelLayout";
import { MapNodeShape } from "./mapShapes";
import { resolveArchitectureStyle, styleTokens } from "./mapStyle";
import { getEnvelopePath, SmoothEnvelope } from "./SmoothEnvelope";
import type { MapEdge, MapGraph, MapNode } from "./types";

const PLATE_GAP = 14;
const PLATE_PAD = 6;

type Props = {
  graph: SpatialGraph | null;
  structureId?: string;
};

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

function plateViewBox(nodes: MapNode[]) {
  const sub: MapGraph = { activeSceneId: "", nodes, edges: [] };
  const vb = computeViewBox(sub, "full");
  return {
    ...vb,
    x: vb.x - PLATE_PAD,
    y: vb.y - PLATE_PAD,
    w: vb.w + PLATE_PAD * 2,
    h: vb.h + PLATE_PAD * 2,
  };
}

export function LevelStackView({ graph, structureId }: Props) {
  const mg = graph ? toMapGraph(graph) : null;
  const sid = structureId ?? (mg ? activeStructureId(mg) : undefined);
  const archStyle = resolveArchitectureStyle(graph);
  const tokens = styleTokens(archStyle, true);
  const focusLevel = mg ? activeLevel(mg) : 0;

  const plates = useMemo(
    () => (mg && sid ? stackPlatesForStructure(mg, sid) : []),
    [mg, sid]
  );

  const vertical = useMemo(
    () => (mg && sid ? verticalLinksForStructure(mg, sid) : []),
    [mg, sid]
  );

  if (!mg || !sid || plates.length === 0) {
    return <div className="level-stack level-stack--empty">No multi-level structure selected.</div>;
  }

  const st = mg.structures?.find((s) => s.structureId === sid);
  const displayName = st?.displayName ?? sid;

  let yCursor = 0;
  const plateLayouts = plates.map((plate) => {
    const vb = plateViewBox(plate.nodes);
    const layout = { plate, vb, y: yCursor };
    yCursor += vb.h + PLATE_GAP;
    return layout;
  });
  const totalH = yCursor - PLATE_GAP;
  const maxW = Math.max(...plateLayouts.map((p) => p.vb.w), 40);
  const rootVb = `0 0 ${maxW + 8} ${totalH + 8}`;

  const nodeById = new Map(mg.nodes.map((n) => [n.sceneId, n]));

  return (
    <div className="level-stack" role="region" aria-label={`Level stack: ${displayName}`}>
      <header className="level-stack__header">
        <h3>{displayName}</h3>
        <p className="level-stack__note">Levels are schematic. Not to scale.</p>
      </header>
      <svg viewBox={rootVb} className="level-stack__svg" role="img">
        {plateLayouts.map(({ plate, vb, y }) => {
          const isActive = plate.level === focusLevel;
          const env = getEnvelopePath(sid, plate.nodes, st?.boundary);
          const short = levelBadgeShort(plate.label) ?? `L${plate.level}`;
          return (
            <g key={plate.level} transform={`translate(4, ${y + 4})`}>
              <g transform={`translate(${-vb.x}, ${-vb.y})`}>
                {env && (
                  <SmoothEnvelope
                    structureId={sid}
                    nodes={plate.nodes}
                    boundary={st?.boundary}
                    fill={
                      isActive
                        ? tokens.structureFillActive
                        : tokens.structureFillOther
                    }
                    stroke={tokens.envelopeStroke}
                    strokeWidth={tokens.envelopeStrokeWidth}
                    doubleWall={tokens.doubleWall}
                  />
                )}
                {plate.edges.map((e) => {
                  const a = nodeById.get(e.sourceSceneId);
                  const b = nodeById.get(e.targetSceneId);
                  if (!a?.layout || !b?.layout) return null;
                  const { start, end } = edgeEndpoints(a, b, e as MapEdge);
                  return (
                    <line
                      key={e.exitId}
                      x1={start.x}
                      y1={start.y}
                      x2={end.x}
                      y2={end.y}
                      stroke="var(--map-path, var(--border))"
                      strokeWidth={0.5}
                    />
                  );
                })}
                {plate.nodes.map((n) => {
                  const fp = nodeFootprint(n);
                  return (
                    <MapNodeShape
                      key={n.sceneId}
                      fp={fp}
                      active={n.isActive}
                      dimmed={!isActive}
                      label={n.locationName}
                      tokens={tokens}
                    />
                  );
                })}
              </g>
              <text
                x={maxW}
                y={vb.h / 2}
                textAnchor="start"
                fontSize={2.2}
                className="level-stack__plate-label"
              >
                {short} — {plate.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="level-stack__connectors">
        {vertical.map((e) => (
          <li key={e.exitId}>
            <span className={`level-stack__link level-stack__link--${e.kind}`}>
              {e.kind === "ladder" ? "▼" : "▲"}
            </span>
            {e.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
