type Props = {
  locationName: string;
  destinationCount: number;
  onDismiss: () => void;
};

function stopPan(e: React.MouseEvent | React.PointerEvent) {
  e.stopPropagation();
}

/** Coach overlay on the map viewport — explains primary actions. */
export function MapViewportGuide({ locationName, destinationCount, onDismiss }: Props) {
  return (
    <div
      className="map-viewport-guide"
      role="dialog"
      aria-labelledby="map-viewport-guide-title"
      onPointerDown={stopPan}
      onClick={(e) => {
        if (e.target === e.currentTarget) onDismiss();
      }}
    >
      <div className="map-viewport-guide__card" onPointerDown={stopPan} onClick={stopPan}>
        <p className="map-viewport-guide__lead" id="map-viewport-guide-title">
          You are in <strong>{locationName}</strong>
        </p>
        {destinationCount > 0 ? (
          <p className="map-viewport-guide__text">
            Use the <strong>Go somewhere</strong> panel on the right to travel, or click a
            connected room or path on the map.
          </p>
        ) : (
          <p className="map-viewport-guide__text">
            Explore other buildings on the map, or switch scenes from the Places list.
          </p>
        )}
        <ul className="map-viewport-guide__steps">
          <li>Drag the map to pan · scroll or +/− to zoom</li>
          <li>Click a room to see details and travel options</li>
          <li>Press <kbd>Esc</kbd> to dismiss this hint · <kbd>M</kbd> to close the map</li>
        </ul>
        <button
          type="button"
          className="map-viewport-guide__dismiss"
          data-testid="map-guide-dismiss"
          onPointerDown={stopPan}
          onClick={(e) => {
            stopPan(e);
            onDismiss();
          }}
        >
          Got it
        </button>
      </div>
    </div>
  );
}
