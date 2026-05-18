import type { MapViewMode } from "./floorLevels";
import { mapViewCapabilities, viewModeDescription, type MapViewCapabilities } from "./mapNavigation";
import type { SpatialGraph } from "../../api/client";

const MODES: { id: MapViewMode; key: string }[] = [
  { id: "site", key: "1" },
  { id: "structure", key: "2" },
  { id: "floor", key: "3" },
  { id: "stack", key: "4" },
];

type Props = {
  graph: SpatialGraph | null;
  viewMode: MapViewMode;
  onViewModeChange: (mode: MapViewMode) => void;
  caps?: MapViewCapabilities;
};

export function MapViewModeSelector({ graph, viewMode, onViewModeChange, caps: capsProp }: Props) {
  const caps = capsProp ?? mapViewCapabilities(graph);
  const activeDesc = viewModeDescription(viewMode, caps);

  return (
    <div className="map-view-mode-selector">
      <nav className="map-view-mode-selector__tabs" aria-label="Map view mode">
        {MODES.map((m) => {
          const desc = viewModeDescription(m.id, caps);
          const recommended = caps.recommendedModes.includes(m.id);
          const isActive = viewMode === m.id;
          return (
            <button
              key={m.id}
              type="button"
              className={`map-view-mode-tab${isActive ? " map-view-mode-tab--active" : ""}${recommended && !isActive ? " map-view-mode-tab--suggested" : ""}`}
              aria-current={isActive ? "page" : undefined}
              aria-describedby={`map-view-desc-${m.id}`}
              title={`${desc.title}: ${desc.subtitle} (press ${m.key})`}
              onClick={() => onViewModeChange(m.id)}
            >
              <span className="map-view-mode-tab__label">{desc.title}</span>
              <span className="map-view-mode-tab__sub" id={`map-view-desc-${m.id}`}>
                {desc.subtitle}
              </span>
              {recommended && !isActive && (
                <span className="map-view-mode-tab__badge" aria-hidden>
                  {m.id === "stack" && caps.hasMultipleFloors
                    ? `${caps.floorCount}↑`
                    : "↑"}
                </span>
              )}
            </button>
          );
        })}
      </nav>
      {caps.personaOffSitePlan && viewMode === "site" && (
        <p className="map-view-mode-selector__nudge" role="status">
          You are on <strong>{caps.personaLevelLabel ?? "another floor"}</strong> — Site view
          only shows ground level. Try{" "}
          <button type="button" onClick={() => onViewModeChange("stack")}>
            Stack
          </button>{" "}
          or{" "}
          <button type="button" onClick={() => onViewModeChange("floor")}>
            Floor
          </button>{" "}
          to see your room.
        </p>
      )}
      {caps.hasMultipleFloors && viewMode === "site" && !caps.personaOffSitePlan && (
        <p className="map-view-mode-selector__nudge map-view-mode-selector__nudge--muted">
          This building has {caps.floorCount} floors ({caps.floorLabels.join(", ")}). Use{" "}
          <button type="button" onClick={() => onViewModeChange("stack")}>
            Stack
          </button>{" "}
          to compare levels.
        </p>
      )}
      {!caps.personaOffSitePlan && viewMode !== "site" && (
        <p className="map-view-mode-selector__current" aria-live="polite">
          Viewing: <strong>{activeDesc.title}</strong> — {activeDesc.subtitle}
        </p>
      )}
    </div>
  );
}
