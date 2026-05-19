import type { ThreeEvent } from "@react-three/fiber";
import type { ReferenceMarker } from "./buildSceneGraph";

type Props = {
  markers: ReferenceMarker[];
  onSelect: (sceneId: string | undefined, id: string) => void;
};

export function ReferencePointMarkers({ markers, onSelect }: Props) {
  return (
    <group>
      {markers.map((m) => (
        <mesh
          key={m.id}
          position={m.position}
          onClick={(e: ThreeEvent<MouseEvent>) => {
            e.stopPropagation();
            onSelect(m.sceneId, m.id);
          }}
        >
          <sphereGeometry args={[0.25, 12, 12]} />
          <meshStandardMaterial color="#f472b6" emissive="#831843" emissiveIntensity={0.4} />
        </mesh>
      ))}
    </group>
  );
}
