import type { SpatialGraph } from "../api/client";

type Props = { graph: SpatialGraph | null };

export function MiniMap({ graph }: Props) {
  if (!graph) return <div className="minimap">No map</div>;

  const nodes = graph.nodes;
  const edges = graph.edges;

  return (
    <div className="minimap">
      <svg viewBox="0 0 100 100" role="img" aria-label="Spatial mini-map">
        {edges.map((e) => {
          const a = nodes.find((n) => n.sceneId === e.sourceSceneId);
          const b = nodes.find((n) => n.sceneId === e.targetSceneId);
          if (!a?.layout || !b?.layout) return null;
          return (
            <line
              key={e.exitId}
              x1={a.layout.x}
              y1={a.layout.y}
              x2={b.layout.x}
              y2={b.layout.y}
              stroke="var(--border)"
              strokeWidth={0.8}
            />
          );
        })}
        {nodes.map((n) => (
          <g key={n.sceneId}>
            <rect
              x={n.layout.x - 6}
              y={n.layout.y - 4}
              width={12}
              height={8}
              rx={1}
              fill={n.isActive ? "var(--accent)" : "var(--surface-2)"}
              stroke={n.isActive ? "var(--fg)" : "var(--border)"}
              strokeWidth={0.5}
            />
            <title>{n.locationName}</title>
          </g>
        ))}
      </svg>
    </div>
  );
}
