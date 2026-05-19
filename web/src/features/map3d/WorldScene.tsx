import { Bounds, ContactShadows, Grid, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
  compact?: boolean;
  /** Bounds fit margin — higher = wider overview (default 1.15). */
  fitMargin?: number;
};

export function WorldScene({ children, className, compact, fitMargin }: Props) {
  const margin = fitMargin ?? (compact ? 1.35 : 1.15);
  return (
    <Canvas
      className={className}
      camera={{ position: [12, 14, 12], fov: compact ? 52 : 42 }}
      gl={{ antialias: true }}
      style={{ background: "linear-gradient(180deg, #0c1218 0%, #141c24 55%, #0a100e 100%)" }}
    >
      <color attach="background" args={["#0e1419"]} />
      <fog attach="fog" args={["#1a2430", 40, 72]} />
      <ambientLight intensity={0.65} />
      <hemisphereLight args={["#dce8f5", "#2a4035", 0.7]} />
      <directionalLight position={[8, 18, 6]} intensity={1.35} castShadow />
      <directionalLight position={[-6, 10, -8]} intensity={0.5} />
      {!compact && (
        <Grid
          args={[32, 32]}
          cellSize={0.5}
          cellThickness={0.25}
          sectionSize={2}
          sectionThickness={0.6}
          fadeDistance={28}
          position={[0, -0.04, 0]}
          cellColor="#2a3a48"
          sectionColor="#3d5166"
        />
      )}
      <Bounds fit clip observe margin={margin} maxDuration={0.6}>
        <group>{children}</group>
      </Bounds>
      <ContactShadows position={[0, -0.03, 0]} opacity={0.35} scale={24} blur={2.5} far={12} />
      <OrbitControls
        makeDefault
        maxPolarAngle={Math.PI / 2.2}
        minDistance={compact ? 4 : 6}
        maxDistance={compact ? 22 : margin > 1.3 ? 48 : 36}
        enablePan
      />
    </Canvas>
  );
}
