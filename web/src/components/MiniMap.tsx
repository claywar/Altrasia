import type { SpatialGraph } from "../api/client";

type Props = { graph: SpatialGraph | null };

function anchorPoint(
  x: number,
  y: number,
  anchor: string | undefined,
  w: number,
  h: number
): { cx: number; cy: number } {
  const ax = anchor?.[0]?.toUpperCase() ?? "C";
  const ay = anchor?.[1]?.toUpperCase() ?? "C";
  let cx = x;
  let cy = y;
  if (ax === "W") cx = x - w / 2;
  if (ax === "E") cx = x + w / 2;
  if (ay === "N") cy = y - h / 2;
  if (ay === "S") cy = y + h / 2;
  return { cx, cy };
}

export function MiniMap({ graph }: Props) {
  if (!graph) return <div className="minimap">No map</div>;

  const nodes = graph.nodes;
  const edges = graph.edges;
  const byStructure = new Map<string, typeof nodes>();
  for (const n of nodes) {
    const sid = (n as { structureId?: string }).structureId ?? "_none";
    if (!byStructure.has(sid)) byStructure.set(sid, []);
    byStructure.get(sid)!.push(n);
  }

  return (
    <div className="minimap">
      <svg viewBox="0 0 100 100" role="img" aria-label="Spatial mini-map">
        {Array.from(byStructure.entries()).map(([sid, group]) => {
          if (sid === "_none" || group.length < 2) return null;
          const xs = group.map((n) => n.layout?.x ?? 0);
          const ys = group.map((n) => n.layout?.y ?? 0);
          const pad = 4;
          const minX = Math.min(...xs) - pad;
          const maxX = Math.max(...xs) + pad;
          const minY = Math.min(...ys) - pad;
          const maxY = Math.max(...ys) + pad;
          return (
            <rect
              key={`env-${sid}`}
              x={minX}
              y={minY}
              width={maxX - minX}
              height={maxY - minY}
              fill="none"
              stroke="var(--border)"
              strokeDasharray="2 1"
              strokeWidth={0.6}
              rx={1}
            />
          );
        })}
        {edges.map((e) => {
          const a = nodes.find((n) => n.sceneId === e.sourceSceneId);
          const b = nodes.find((n) => n.sceneId === e.targetSceneId);
          if (!a?.layout || !b?.layout) return null;
          const ax = a.layout.x;
          const ay = a.layout.y;
          const bx = b.layout.x;
          const by = b.layout.y;
          const anchor = (e as { exitAnchor?: string }).exitAnchor;
          const start = anchorPoint(ax, ay, anchor, 12, 8);
          return (
            <line
              key={e.exitId}
              x1={start.cx}
              y1={start.cy}
              x2={bx}
              y2={by}
              stroke="var(--border)"
              strokeWidth={0.8}
            />
          );
        })}
        {nodes.map((n) => {
          const shape = (n as { mapShape?: string }).mapShape;
          const x = n.layout?.x ?? 0;
          const y = n.layout?.y ?? 0;
          const active = n.isActive;
          if (shape === "circle") {
            return (
              <circle
                key={n.sceneId}
                cx={x}
                cy={y}
                r={5}
                fill={active ? "var(--accent)" : "var(--surface-2)"}
                stroke={active ? "var(--fg)" : "var(--border)"}
                strokeWidth={0.5}
              >
                <title>{n.locationName}</title>
              </circle>
            );
          }
          return (
            <g key={n.sceneId}>
              <rect
                x={x - 6}
                y={y - 4}
                width={12}
                height={8}
                rx={1}
                fill={active ? "var(--accent)" : "var(--surface-2)"}
                stroke={active ? "var(--fg)" : "var(--border)"}
                strokeWidth={0.5}
              />
              <title>{n.locationName}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
