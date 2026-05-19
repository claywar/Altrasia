import type { SceneGraph3D } from "./buildSceneGraph";

type Props = {
  bounds: SceneGraph3D["bounds"];
  siteCenter: [number, number, number];
};

export function SiteGround({ bounds, siteCenter }: Props) {
  const [minX, , minZ] = bounds.min;
  const [maxX, , maxZ] = bounds.max;
  const w = Math.max(maxX - minX + 4, 8);
  const d = Math.max(maxZ - minZ + 4, 8);
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[siteCenter[0], -0.02, siteCenter[2]]}>
      <planeGeometry args={[w, d]} />
      <meshStandardMaterial color="#1a2420" roughness={0.95} metalness={0.05} />
    </mesh>
  );
}
