import type { EdgeSegment } from "./buildSceneGraph";

type Props = {
  edges: EdgeSegment[];
  onVerticalClick?: (targetSceneId: string) => void;
};

/** Simple stair ramp for vertical links between floors. */
export function StairConnectors({ edges, onVerticalClick }: Props) {
  const vertical = edges.filter((e) => e.vertical);
  return (
    <group>
      {vertical.map((e, i) => {
        const [x0, y0, z0] = e.from;
        const [, y1] = e.to;
        const lowY = Math.min(y0, y1);
        const highY = Math.max(y0, y1);
        const rise = highY - lowY;
        const mid: [number, number, number] = [x0, lowY + rise / 2, z0];
        const color = e.onRoute ? "#fbbf24" : "#94a3b8";
        return (
          <group
            key={e.exitId ?? `stair-${i}`}
            position={mid}
            onClick={(ev) => {
              ev.stopPropagation();
              if (e.targetSceneId) onVerticalClick?.(e.targetSceneId);
            }}
          >
            <mesh rotation={[0, 0, Math.atan2(rise, 1.2)]} position={[0.3, 0, 0]}>
              <boxGeometry args={[1.4, 0.12, 0.7]} />
              <meshStandardMaterial color={color} roughness={0.7} />
            </mesh>
            {[0, 1, 2, 3].map((step) => (
              <mesh
                key={step}
                position={[(step * 0.28) - 0.2, (step * rise) / 4 - rise / 2, 0]}
              >
                <boxGeometry args={[0.55, 0.1, 0.65]} />
                <meshStandardMaterial color={shade(color, 0.85)} roughness={0.8} />
              </mesh>
            ))}
          </group>
        );
      })}
    </group>
  );
}

function shade(color: string, factor: number) {
  if (color.startsWith("#")) {
    const n = parseInt(color.slice(1), 16);
    const r = ((n >> 16) & 255) * factor;
    const g = ((n >> 8) & 255) * factor;
    const b = (n & 255) * factor;
    return `rgb(${r},${g},${b})`;
  }
  return color;
}
