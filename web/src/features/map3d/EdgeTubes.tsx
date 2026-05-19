import { Line } from "@react-three/drei";
import type { EdgeSegment } from "./buildSceneGraph";

type Props = {
  edges: EdgeSegment[];
};

function PathEdge({ edge }: { edge: EdgeSegment }) {
  const color = edge.onRoute ? "#fbbf24" : edge.vertical ? "#94a3b8" : "#64748b";
  const width = edge.onRoute ? 3 : edge.vertical ? 2 : 1.5;
  const dashed = edge.vertical && !edge.onRoute;

  return (
    <Line
      points={[edge.from, edge.to]}
      color={color}
      lineWidth={width}
      dashed={dashed}
      dashScale={dashed ? 2 : 1}
    />
  );
}

export function EdgeTubes({ edges }: Props) {
  return (
    <group>
      {edges.map((e, i) => (
        <PathEdge key={e.exitId ?? `e-${i}`} edge={e} />
      ))}
    </group>
  );
}
