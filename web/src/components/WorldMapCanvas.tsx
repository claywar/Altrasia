import { SiteMapCanvas } from "../features/maps/SiteMapCanvas";
import type { SpatialGraph } from "../api/client";

type Props = {
  graph: SpatialGraph | null;
  onClose: () => void;
  onEnhanceLayout?: () => void;
};

/** Site-scale world map (Phase 6a) — schematic pan/zoom with PiP mini-map. */
export function WorldMapCanvas({ graph, onClose, onEnhanceLayout }: Props) {
  return <SiteMapCanvas graph={graph} onClose={onClose} onEnhanceLayout={onEnhanceLayout} />;
}
