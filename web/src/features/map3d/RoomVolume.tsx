import { Text } from "@react-three/drei";
import type { ThreeEvent } from "@react-three/fiber";
import type { RoomMesh } from "./buildSceneGraph";
import { FLOOR_SLAB, WALL_THICK, structureColor } from "./buildSceneGraph";

type Props = {
  rooms: RoomMesh[];
  selectedSceneId: string | null;
  onSelect: (sceneId: string) => void;
  /** Only label active/selected rooms (reduces clutter on minimap). */
  labelActiveOnly?: boolean;
  /** Per-room walls to omit: N | S | E | W */
  hiddenWalls?: Record<string, Set<string>>;
};

function wallMaterial(color: string, active: boolean, selected: boolean, dimmed?: boolean) {
  return (
    <meshStandardMaterial
      color={active ? "#6ee7a0" : selected ? "#93c5fd" : color}
      emissive={active ? "#14532d" : selected ? "#1e3a5f" : "#000000"}
      emissiveIntensity={active ? 0.2 : selected ? 0.12 : 0}
      roughness={0.82}
      metalness={0.05}
      transparent={dimmed}
      opacity={dimmed ? 0.32 : 1}
    />
  );
}

function RectRoom({
  room,
  selected,
  onSelect,
  hiddenWalls,
  showLabel,
}: {
  room: RoomMesh;
  selected: boolean;
  onSelect: () => void;
  hiddenWalls?: Set<string>;
  showLabel: boolean;
}) {
  const [w, wallH, d] = room.size;
  const base = structureColor(room.structureId);
  const floorColor = room.isOutdoor ? "#3d5c44" : activeTint(room, "#8b7355");
  const active = room.isActive;
  const dimmed = room.dimmed;

  const click = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect();
  };

  const halfW = w / 2;
  const halfD = d / 2;
  const wallY = FLOOR_SLAB + wallH / 2;

  return (
    <group position={room.position} onClick={click}>
      {/* Floor slab */}
      <mesh position={[0, FLOOR_SLAB / 2, 0]}>
        <boxGeometry args={[w * 0.96, FLOOR_SLAB, d * 0.96]} />
        <meshStandardMaterial
          color={floorColor}
          roughness={0.9}
          emissive={active ? "#14532d" : "#000000"}
          emissiveIntensity={active ? 0.15 : 0}
          transparent={dimmed}
          opacity={dimmed ? 0.35 : 1}
        />
      </mesh>
      {/* Walls — omit shared interior faces when hiddenWalls set */}
      {!hiddenWalls?.has("N") && (
        <mesh position={[0, wallY, -halfD]}>
          <boxGeometry args={[w, wallH, WALL_THICK]} />
          {wallMaterial(shade(base, 1.08), active, selected, dimmed)}
        </mesh>
      )}
      {!hiddenWalls?.has("S") && (
        <mesh position={[0, wallY, halfD]}>
          <boxGeometry args={[w, wallH, WALL_THICK]} />
          {wallMaterial(shade(base, 0.92), active, selected, dimmed)}
        </mesh>
      )}
      {!hiddenWalls?.has("W") && (
        <mesh position={[-halfW, wallY, 0]}>
          <boxGeometry args={[WALL_THICK, wallH, d]} />
          {wallMaterial(shade(base, 0.96), active, selected, dimmed)}
        </mesh>
      )}
      {!hiddenWalls?.has("E") && (
        <mesh position={[halfW, wallY, 0]}>
          <boxGeometry args={[WALL_THICK, wallH, d]} />
          {wallMaterial(shade(base, 0.88), active, selected, dimmed)}
        </mesh>
      )}
      {/* Interior fill hint (visible through top) */}
      <mesh position={[0, wallY, 0]}>
        <boxGeometry args={[w * 0.88, wallH * 0.95, d * 0.88]} />
        <meshStandardMaterial
          color={active ? "#4ade80" : shade(base, 0.75)}
          transparent
          opacity={active ? 0.25 : 0.12}
          depthWrite={false}
        />
      </mesh>
      {showLabel && <Label room={room} y={wallH + 0.35} />}
    </group>
  );
}

function CylinderRoom({
  room,
  selected,
  onSelect,
  showLabel,
}: {
  room: RoomMesh;
  selected: boolean;
  onSelect: () => void;
  showLabel: boolean;
}) {
  const [diam, wallH] = [room.size[0], room.size[1]];
  const r = diam / 2;
  const base = structureColor(room.structureId);
  const active = room.isActive;

  return (
    <group
      position={room.position}
      onClick={(e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        onSelect();
      }}
    >
      <mesh position={[0, FLOOR_SLAB / 2, 0]}>
        <cylinderGeometry args={[r * 0.95, r * 0.95, FLOOR_SLAB, 24]} />
        <meshStandardMaterial color="#6b7280" roughness={0.85} />
      </mesh>
      <mesh position={[0, FLOOR_SLAB + wallH / 2, 0]}>
        <cylinderGeometry args={[r, r, wallH, 24, 1, true]} />
        {wallMaterial(shade(base, 1), active, selected, room.dimmed)}
      </mesh>
      {showLabel && <Label room={room} y={wallH + 0.4} />}
    </group>
  );
}

function Label({ room, y }: { room: RoomMesh; y: number }) {
  return (
    <>
      <Text
        position={[0, y, 0]}
        fontSize={0.26}
        color={room.isActive ? "#ecfdf5" : "#e2e8f0"}
        anchorX="center"
        anchorY="bottom"
        outlineWidth={0.03}
        outlineColor="#0a0e12"
      >
        {room.locationName}
      </Text>
      {room.levelIndex !== 0 && room.levelLabel && (
        <Text position={[0, y + 0.22, 0]} fontSize={0.16} color="#94a3b8" anchorX="center">
          {room.levelLabel}
        </Text>
      )}
    </>
  );
}

function activeTint(room: RoomMesh, fallback: string) {
  if (room.isActive) return "#4ade80";
  return fallback;
}

function shade(hex: string, factor: number) {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.min(255, ((n >> 16) & 255) * factor);
  const g = Math.min(255, ((n >> 8) & 255) * factor);
  const b = Math.min(255, (n & 255) * factor);
  return `rgb(${r | 0},${g | 0},${b | 0})`;
}

export function RoomVolume({
  rooms,
  selectedSceneId,
  onSelect,
  labelActiveOnly = false,
  hiddenWalls,
}: Props) {
  return (
    <group>
      {rooms.map((room) => {
        const selected = room.sceneId === selectedSceneId;
        const showLabel =
          !labelActiveOnly || room.isActive || selected;
        const walls = hiddenWalls?.[room.sceneId];
        return room.shape === "circle" ? (
          <CylinderRoom
            key={room.sceneId}
            room={room}
            selected={selected}
            onSelect={() => onSelect(room.sceneId)}
            showLabel={showLabel}
          />
        ) : (
          <RectRoom
            key={room.sceneId}
            room={room}
            selected={selected}
            onSelect={() => onSelect(room.sceneId)}
            hiddenWalls={walls}
            showLabel={showLabel}
          />
        );
      })}
    </group>
  );
}
