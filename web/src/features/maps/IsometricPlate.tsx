import { useMemo } from "react";
import {
  isoBoundsFromCorners,
  isoFootprintCorners,
  isoPointsToPath,
  isoWallTop,
  planToIso,
} from "./isoProjection";
import { nodeFootprint } from "./layoutGeometry";
import type { MapStyleTokens } from "./mapStyle";
import type { MapNode } from "./types";

type Props = {
  nodes: MapNode[];
  focusLevel: number;
  plateLevel: number;
  vb: { x: number; y: number; w: number; h: number };
  tokens: MapStyleTokens;
  onSceneClick?: (sceneId: string) => void;
};

function truncate(name: string, max = 10): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function IsometricPlate({
  nodes,
  focusLevel,
  plateLevel,
  vb,
  tokens,
  onSceneClick,
}: Props) {
  const origin = useMemo(() => ({ x: vb.x + vb.w / 2, y: vb.y + vb.h / 2 }), [vb]);

    const { floorPath, rooms } = useMemo(() => {
    const allCorners: { x: number; y: number }[] = [];
    const roomShapes: Array<{
      sceneId: string;
      floor: string;
      walls: string;
      label: string;
      labelPt: { x: number; y: number };
      active: boolean;
    }> = [];

    for (const node of nodes) {
      const fp = nodeFootprint(node);
      const base = isoFootprintCorners(fp, origin);
      const top = isoWallTop(base);
      allCorners.push(...base, ...top);
      const floor = isoPointsToPath(base);
      const walls = [
        isoPointsToPath([base[0]!, base[1]!, top[1]!, top[0]!]),
        isoPointsToPath([base[1]!, base[2]!, top[2]!, top[1]!]),
        isoPointsToPath([base[2]!, base[3]!, top[3]!, top[2]!]),
      ].join(" ");
      const center = planToIso(fp.cx, fp.cy, origin);
      roomShapes.push({
        sceneId: node.sceneId,
        floor,
        walls,
        label: truncate(node.locationName).toUpperCase(),
        labelPt: center,
        active: Boolean(node.isActive),
      });
    }

    const pad = 3;
    const b = isoBoundsFromCorners(allCorners);
    const floorPath = isoPointsToPath([
      { x: b.minX - pad, y: b.minY - pad },
      { x: b.maxX + pad, y: b.minY - pad },
      { x: b.maxX + pad, y: b.maxY + pad },
      { x: b.minX - pad, y: b.maxY + pad },
    ]);

    return { floorPath, rooms: roomShapes };
  }, [nodes, origin]);

  const isActivePlate = plateLevel === focusLevel;
  const plateOpacity = isActivePlate ? 1 : 0.42;

  return (
    <g className="iso-plate" opacity={plateOpacity}>
      <defs>
        <pattern
          id={`iso-grid-${plateLevel}`}
          width={2.5}
          height={2.5}
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 2.5 0 L 0 0 0 2.5"
            fill="none"
            stroke="var(--border)"
            strokeWidth={0.08}
            opacity={0.35}
          />
        </pattern>
      </defs>
      <path
        d={floorPath}
        fill={`url(#iso-grid-${plateLevel})`}
        stroke={tokens.envelopeStroke}
        strokeWidth={tokens.envelopeStrokeWidth * 0.8}
        opacity={0.95}
      />
      {rooms.map((room) => (
        <g
          key={room.sceneId}
          className={room.active ? "iso-room iso-room--active" : "iso-room"}
          role={onSceneClick ? "button" : undefined}
          tabIndex={onSceneClick ? 0 : undefined}
          style={{ cursor: onSceneClick ? "pointer" : undefined }}
          onClick={onSceneClick ? () => onSceneClick(room.sceneId) : undefined}
          onKeyDown={
            onSceneClick
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSceneClick(room.sceneId);
                  }
                }
              : undefined
          }
        >
          <path d={room.floor} fill={room.active ? tokens.roomFillActive : tokens.roomFill} opacity={0.85} />
          <path
            d={room.walls}
            fill={tokens.envelopeStroke}
            opacity={0.55}
            stroke={tokens.roomStroke}
            strokeWidth={0.15}
          />
          {room.active && (
            <path
              d={room.floor}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={0.35}
              className="iso-room__active-ring"
            />
          )}
          <text
            x={room.labelPt.x}
            y={room.labelPt.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={1.8}
            className="iso-room__label"
            fill="var(--fg)"
            opacity={0.9}
          >
            {room.label}
          </text>
          {room.active && (
            <circle
              cx={room.labelPt.x + 4}
              cy={room.labelPt.y - 2}
              r={0.9}
              fill="var(--accent)"
              className="iso-room__you-are-here"
            />
          )}
        </g>
      ))}
    </g>
  );
}
