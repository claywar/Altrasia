import { useState } from "react";
import {
  hideSocialBanterInTranscript,
  setHideSocialBanterInTranscript,
  setShowAmbientInTranscript,
  showAmbientInTranscript,
} from "../../lib/parse";
import { notifyBanterFilterChanged } from "../../features/transcript/BanterTranscriptToggle";

type Props = {
  onChanged?: () => void;
};

export function AmbientDisplaySection({ onChanged }: Props) {
  const [ambientEnabled, setAmbientEnabled] = useState(showAmbientInTranscript);
  const [hideBanter, setHideBanter] = useState(hideSocialBanterInTranscript);

  return (
    <>
      <label className="settings-list-row">
        <span className="settings-list-text">Show ambient lines in transcript</span>
        <input
          type="checkbox"
          checked={ambientEnabled}
          onChange={(e) => {
            const next = e.target.checked;
            setAmbientEnabled(next);
            setShowAmbientInTranscript(next);
            onChanged?.();
          }}
          aria-label="Show ambient lines in transcript"
        />
      </label>
      <label className="settings-list-row">
        <span className="settings-list-text">Hide sidebar banter in transcript</span>
        <input
          type="checkbox"
          checked={hideBanter}
          onChange={(e) => {
            const next = e.target.checked;
            setHideBanter(next);
            setHideSocialBanterInTranscript(next);
            notifyBanterFilterChanged();
            onChanged?.();
          }}
          aria-label="Hide sidebar banter in transcript"
        />
      </label>
    </>
  );
}
