type CompassProps = { x?: number; y?: number; size?: number };

/** Compass inset; default top-right of 0–100 canvas — pass viewBox-relative coords when fitted. */
export function MapCompass({ x = 88, y = 8, size = 5 }: CompassProps) {
  return (
    <g className="map-compass" transform={`translate(${x}, ${y})`} aria-hidden>
      <text x={0} y={-size * 0.3} textAnchor="middle" fontSize={2.2} className="map-compass__n">
        N
      </text>
      <line x1={0} y1={0} x2={0} y2={-size} stroke="var(--muted)" strokeWidth={0.4} />
      <polygon
        points={`0,${-size} ${-size * 0.35},${-size * 0.35} ${size * 0.35},${-size * 0.35}`}
        fill="var(--muted)"
      />
    </g>
  );
}

type HeaderProps = {
  structureName?: string;
  sceneName?: string;
  mapZone?: string;
};

export function MapPanelHeader({ structureName, sceneName, mapZone }: HeaderProps) {
  const parts = [structureName, mapZone, sceneName].filter(Boolean);
  if (parts.length === 0) return null;
  return (
    <div className="map-panel-header">
      <span className="map-panel-header__title">{parts.join(" › ")}</span>
    </div>
  );
}
