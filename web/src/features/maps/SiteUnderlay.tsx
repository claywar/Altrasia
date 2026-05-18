import { structureEnvelope } from "./layoutGeometry";
import { envelopeShapeFromBoundary } from "./smoothGeometry";
import { structureCentroid, translateBoundary } from "./worldSiteLayout";
import type { MapStructure, Point } from "./types";

type WorldMapPlacement = {
  structurePlacements?: Array<{
    structureId: string;
    origin: { x: number; y: number };
  }>;
  terrain?: Array<{ kind?: string; vertices?: Point[] }>;
};

type Props = {
  viewBox: { x: number; y: number; w: number; h: number };
  idPrefix?: string;
  worldMap?: WorldMapPlacement | null;
  structures?: MapStructure[];
};

/** Procedural terrain underlay + structure placement footprints at site origins. */
export function SiteUnderlay({ viewBox, idPrefix = "site", worldMap, structures }: Props) {
  const { x, y, w, h } = viewBox;
  const noiseId = `${idPrefix}-noise`;
  const gradId = `${idPrefix}-soil`;
  const siteGlowId = `${idPrefix}-site-glow`;

  const placementById = new Map(
    (worldMap?.structurePlacements ?? []).map((p) => [p.structureId, p.origin])
  );

  return (
    <g className="map-site-underlay" aria-hidden>
      <defs>
        <filter id={noiseId} x="0%" y="0%" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" result="noise" />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.06" />
          </feComponentTransfer>
        </filter>
        <radialGradient id={gradId} cx="48%" cy="42%" r="70%">
          <stop offset="0%" stopColor="hsl(215 16% 16%)" />
          <stop offset="55%" stopColor="hsl(218 18% 11%)" />
          <stop offset="100%" stopColor="hsl(220 20% 7%)" />
        </radialGradient>
        <radialGradient id={siteGlowId} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(210 20% 20% / 0.35)" />
          <stop offset="100%" stopColor="hsl(210 20% 12% / 0)" />
        </radialGradient>
      </defs>
      <rect x={x} y={y} width={w} height={h} fill={`url(#${gradId})`} />
      <ellipse
        cx={x + w * 0.5}
        cy={y + h * 0.48}
        rx={w * 0.42}
        ry={h * 0.38}
        fill={`url(#${siteGlowId})`}
      />
      <rect x={x} y={y} width={w} height={h} filter={`url(#${noiseId})`} opacity={0.55} />

      <path
        d={`M ${x + 22} ${y + 78} C ${x + 32} ${y + 68} ${x + 40} ${y + 58} ${x + 48} ${y + 52} S ${x + 62} ${y + 48} ${x + 72} ${y + 50}`}
        fill="none"
        stroke="var(--map-trail, hsl(38 18% 30% / 0.35))"
        strokeWidth={1.2}
        strokeLinecap="round"
      />
      <path
        d={`M ${x + 48} ${y + 52} C ${x + 54} ${y + 50} ${x + 58} ${y + 52} ${x + 64} ${y + 54}`}
        fill="none"
        stroke="var(--map-trail, hsl(38 18% 30% / 0.28))"
        strokeWidth={0.9}
        strokeLinecap="round"
      />

      <ellipse cx={x + 10} cy={y + h * 0.88} rx={5} ry={3.5} fill="hsl(135 12% 14% / 0.55)" />
      <ellipse cx={x + 14} cy={y + h * 0.86} rx={3.5} ry={2.5} fill="hsl(135 14% 16% / 0.45)" />
      <ellipse cx={x + w * 0.9} cy={y + h * 0.82} rx={4} ry={3} fill="hsl(135 12% 14% / 0.5)" />
      <ellipse cx={x + w * 0.86} cy={y + h * 0.78} rx={3} ry={2.2} fill="hsl(135 14% 16% / 0.4)" />

      {worldMap?.terrain?.map((region, i) =>
        region.vertices && region.vertices.length >= 3 ? (
          <polygon
            key={`terrain-${i}`}
            points={region.vertices.map((v) => `${v.x},${v.y}`).join(" ")}
            fill="hsl(135 10% 12% / 0.25)"
            stroke="none"
          />
        ) : null
      )}

      {(structures ?? []).map((st) => {
        const origin = placementById.get(st.structureId);
        if (!origin || !st.boundary) return null;
        const centroid = structureCentroid(st.boundary, []);
        const dx = origin.x - centroid.x;
        const dy = origin.y - centroid.y;
        const atSite = translateBoundary(st.boundary, dx, dy);
        const raw = structureEnvelope(st.structureId, [], atSite);
        if (!raw) return null;
        const shape = envelopeShapeFromBoundary(atSite, raw);
        if (!shape?.pathD) return null;
        return (
          <path
            key={`placement-${st.structureId}`}
            d={shape.pathD}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={0.35}
            opacity={0.2}
            strokeDasharray="1.5 1"
            className="map-site-placement-footprint"
          />
        );
      })}

      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        fill="hsl(220 22% 4% / 0.2)"
        style={{ pointerEvents: "none" }}
      />
    </g>
  );
}
