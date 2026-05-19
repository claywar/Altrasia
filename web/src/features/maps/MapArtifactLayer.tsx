import type { SceneMapArtifact } from "../../api/client";

type Props = {
  artifact: SceneMapArtifact;
  onTravel?: (targetSceneId: string) => void;
};

/** Floor-plan walls, fixtures, and exit hotspots from mapArtifact (MAP-1). */
export function MapArtifactLayer({ artifact, onTravel }: Props) {
  const walls = artifact.walls ?? [];
  const fixtures = artifact.fixtures ?? [];
  const exits = artifact.exits ?? [];

  return (
    <g className="map-artifact-layer" aria-hidden={false}>
      {walls.map((w, i) => (
        <line
          key={`wall-${i}`}
          x1={w.x1}
          y1={w.y1}
          x2={w.x2}
          y2={w.y2}
          className="map-artifact-wall"
          stroke="currentColor"
          strokeWidth={0.35}
        />
      ))}
      {fixtures.map((f) => (
        <g key={f.id} className="map-artifact-fixture">
          <circle cx={f.x} cy={f.y} r={1.2} className="map-artifact-fixture__dot" />
          <text x={f.x} y={f.y - 2} className="map-artifact-fixture__label" textAnchor="middle">
            {f.label}
          </text>
        </g>
      ))}
      {exits.map((ex) => (
        <g key={ex.exitId}>
          <circle
            cx={ex.x}
            cy={ex.y}
            r={1.4}
            className="map-artifact-exit"
            role={onTravel ? "button" : undefined}
            tabIndex={onTravel ? 0 : undefined}
            onClick={() => onTravel?.(ex.targetSceneId)}
            onKeyDown={(e) => {
              if (onTravel && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                onTravel(ex.targetSceneId);
              }
            }}
          />
          <text x={ex.x} y={ex.y + 3.5} className="map-artifact-exit__label" textAnchor="middle">
            {ex.label ?? "Exit"}
          </text>
        </g>
      ))}
    </g>
  );
}
