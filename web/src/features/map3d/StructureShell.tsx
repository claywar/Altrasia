import { useMemo } from "react";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import type { StructurePad } from "./buildSceneGraph";
import {
  FLOOR_HEIGHT,
  FLOOR_SLAB,
  WALL_HEIGHT,
  WALL_THICK,
  structureColor,
} from "./buildSceneGraph";

type Props = {
  structures: StructurePad[];
  /** Site overview: show all building names and emphasize envelopes. */
  siteOverview?: boolean;
  /** Hide floating structure titles (e.g. when rooms are labeled). */
  hideLabels?: boolean;
  onStructureClick?: (structureId: string) => void;
  onStructureDoubleClick?: (structureId: string) => void;
};

function footprintShape(footprint: Array<[number, number]>) {
  if (footprint.length < 3) return null;
  const shape = new THREE.Shape();
  shape.moveTo(footprint[0][0], footprint[0][1]);
  for (let i = 1; i < footprint.length; i++) {
    shape.lineTo(footprint[i][0], footprint[i][1]);
  }
  shape.closePath();
  return shape;
}

function PerimeterWalls({
  footprint,
  yBase,
  height,
  color,
}: {
  footprint: Array<[number, number]>;
  yBase: number;
  height: number;
  color: string;
}) {
  const segments = useMemo(() => {
    const out: Array<{ mid: [number, number, number]; len: number; rotY: number }> = [];
    for (let i = 0; i < footprint.length; i++) {
      const p0 = footprint[i];
      const p1 = footprint[(i + 1) % footprint.length];
      const dx = p1[0] - p0[0];
      const dz = p1[1] - p0[1];
      const len = Math.hypot(dx, dz);
      if (len < 0.05) continue;
      out.push({
        mid: [(p0[0] + p1[0]) / 2, yBase + height / 2, (p0[1] + p1[1]) / 2],
        len,
        rotY: Math.atan2(dx, dz),
      });
    }
    return out;
  }, [footprint, yBase, height]);

  return (
    <>
      {segments.map((seg, i) => (
        <mesh key={i} position={seg.mid} rotation={[0, seg.rotY, 0]}>
          <boxGeometry args={[WALL_THICK, height, seg.len]} />
          <meshStandardMaterial color={color} roughness={0.88} metalness={0.04} />
        </mesh>
      ))}
    </>
  );
}

function StructureBuilding({
  st,
  siteOverview,
  hideLabels,
  onClick,
  onDoubleClick,
}: {
  st: StructurePad;
  siteOverview?: boolean;
  hideLabels?: boolean;
  onClick?: (structureId: string) => void;
  onDoubleClick?: (structureId: string) => void;
}) {
  const shape = useMemo(() => footprintShape(st.footprint), [st.footprint]);
  const color = structureColor(st.structureId);
  const shellHeight = st.isOutdoor ? 0.9 : WALL_HEIGHT + 0.15;
  const roofY = FLOOR_HEIGHT * st.maxLevel + shellHeight;

  if (!shape) return null;

  const showLabel = siteOverview || (!hideLabels && !st.containsActive);
  const foundationLift = siteOverview ? 0.06 : 0.02;

  return (
    <group
      onClick={(e) => {
        e.stopPropagation();
        onClick?.(st.structureId);
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        onDoubleClick?.(st.structureId);
      }}
    >
      {/* Foundation */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[st.center[0], foundationLift, st.center[2]]}>
        <shapeGeometry args={[shape]} />
        <meshStandardMaterial
          color={shade(color, st.containsActive && !siteOverview ? 0.62 : 0.55)}
          roughness={0.95}
          emissive={st.containsActive && siteOverview ? color : "#000000"}
          emissiveIntensity={st.containsActive && siteOverview ? 0.12 : 0}
        />
      </mesh>

      {/* Outer shell walls along footprint (exterior envelope) */}
      <PerimeterWalls
        footprint={st.footprint}
        yBase={FLOOR_SLAB}
        height={shellHeight}
        color={shade(color, st.containsActive ? 1.15 : 1.05)}
      />

      {/* Roof cap on buildings (not open courtyards) */}
      {!st.isOutdoor && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[st.center[0], roofY, st.center[2]]}>
          <shapeGeometry args={[shape]} />
          <meshStandardMaterial
            color={shade(color, 0.72)}
            roughness={0.9}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {showLabel && (
        <Text
          position={[st.center[0], roofY + (st.isOutdoor ? 0.2 : 0.55), st.center[2]]}
          fontSize={siteOverview ? 0.62 : 0.48}
          color={st.containsActive ? "#d4e4f8" : "#9fb0c4"}
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.035}
          outlineColor="#0a0e12"
        >
          {st.displayName}
        </Text>
      )}
    </group>
  );
}

function shade(hex: string, factor: number) {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.min(255, ((n >> 16) & 255) * factor);
  const g = Math.min(255, ((n >> 8) & 255) * factor);
  const b = Math.min(255, (n & 255) * factor);
  return `rgb(${r | 0},${g | 0},${b | 0})`;
}

export function StructureShell({
  structures,
  siteOverview,
  hideLabels,
  onStructureClick,
  onStructureDoubleClick,
}: Props) {
  return (
    <group>
      {structures.map((st) => (
        <StructureBuilding
          key={st.structureId}
          st={st}
          siteOverview={siteOverview}
          hideLabels={hideLabels}
          onClick={onStructureClick}
          onDoubleClick={onStructureDoubleClick}
        />
      ))}
    </group>
  );
}
