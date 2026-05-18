import type { MapViewMode } from "./floorLevels";
import type { MapViewCapabilities } from "./mapNavigation";
import { viewModeDescription } from "./mapNavigation";

type Props = {
  viewMode: MapViewMode;
  caps: MapViewCapabilities;
  onSwitchView?: (mode: MapViewMode) => void;
};

/** Labels on the overview (PiP) inset so view modes are discoverable. */
export function MapPipChrome({ viewMode, caps, onSwitchView }: Props) {
  const desc = viewModeDescription(viewMode, caps);
  const suggestStack = caps.recommendedModes.includes("stack") && viewMode === "site";

  return (
    <div className="map-pip-chrome" aria-label="Overview map legend">
      <span className="map-pip-chrome__view">{desc.title}</span>
      <span className="map-pip-chrome__sub">{desc.subtitle}</span>
      {suggestStack && onSwitchView && (
        <button
          type="button"
          className="map-pip-chrome__link"
          onClick={() => onSwitchView("stack")}
        >
          See all floors
        </button>
      )}
    </div>
  );
}
