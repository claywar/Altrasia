import { FocusTrap } from "../../ui/FocusTrap";
import type { SpatialGraph } from "../../api/client";
import { MapEnhancePanel } from "./MapEnhancePanel";

type Props = {
  open: boolean;
  worldId: string;
  graph: SpatialGraph | null;
  onClose: () => void;
  onCommitted?: () => void;
  onPreviewChange?: (preview: SpatialGraph | null) => void;
};

export function MapEnhanceDrawer({
  open,
  worldId,
  graph,
  onClose,
  onCommitted,
  onPreviewChange,
}: Props) {
  if (!open) return null;

  return (
    <FocusTrap active>
      <div className="map-enhance-drawer-scrim" onClick={onClose} role="presentation">
        <aside
          className="map-enhance-drawer"
          data-testid="map-enhance-drawer"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-label="Enhance map"
        >
          <header className="map-enhance-drawer__head">
            <h3>Enhance map</h3>
            <button type="button" onClick={onClose} aria-label="Close">
              ×
            </button>
          </header>
          <MapEnhancePanel
            worldId={worldId}
            graph={graph}
            onCommitted={() => {
              onCommitted?.();
              onClose();
            }}
            onPreviewChange={onPreviewChange}
          />
        </aside>
      </div>
    </FocusTrap>
  );
}
