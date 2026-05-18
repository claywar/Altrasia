import {
  DEFAULT_MAP_LAYERS,
  MAP_LAYER_LABELS,
  type MapLayerKey,
  type MapLayerVisibility,
} from "./mapLayers";

type Props = {
  layers: MapLayerVisibility;
  onChange: (layers: MapLayerVisibility) => void;
  architectureStyle?: string;
  onArchitectureStyle?: (style: "diagram" | "blueprint" | "minimal") => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
};

const STYLE_OPTIONS: Array<{ id: "diagram" | "blueprint" | "minimal"; label: string }> = [
  { id: "diagram", label: "Diagram" },
  { id: "blueprint", label: "Blueprint" },
  { id: "minimal", label: "Minimal" },
];

export function MapLayersPanel({
  layers,
  onChange,
  architectureStyle,
  onArchitectureStyle,
  collapsed,
  onToggleCollapsed,
}: Props) {
  const toggle = (key: MapLayerKey) => {
    onChange({ ...layers, [key]: !layers[key] });
  };

  if (collapsed) {
    return (
      <aside className="map-console-layers map-console-layers--collapsed" aria-label="Map layers">
        <button
          type="button"
          className="map-console-layers__expand"
          onClick={onToggleCollapsed}
          title="Show layers"
        >
          Layers
        </button>
      </aside>
    );
  }

  return (
    <aside className="map-console-layers" aria-label="Map layers">
      <div className="map-console-layers__head">
        <h3>Layers</h3>
        {onToggleCollapsed && (
          <button type="button" className="map-console-layers__collapse" onClick={onToggleCollapsed}>
            Hide
          </button>
        )}
      </div>
      <ul className="map-console-layers__list">
        {(Object.keys(DEFAULT_MAP_LAYERS) as MapLayerKey[]).map((key) => (
          <li key={key}>
            <label className="map-console-layers__row">
              <input
                type="checkbox"
                checked={layers[key]}
                onChange={() => toggle(key)}
              />
              <span>{MAP_LAYER_LABELS[key]}</span>
            </label>
          </li>
        ))}
      </ul>
      {onArchitectureStyle && (
        <div className="map-console-layers__style">
          <h4>Style</h4>
          <div className="map-console-layers__style-btns">
            {STYLE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={
                  architectureStyle === opt.id
                    ? "map-console-layers__style-active"
                    : undefined
                }
                onClick={() => onArchitectureStyle(opt.id)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
