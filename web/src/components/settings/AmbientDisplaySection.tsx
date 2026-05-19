import { useState } from "react";
import {
  setShowAmbientInTranscript,
  showAmbientInTranscript,
} from "../../lib/parse";

type Props = {
  onChanged?: () => void;
};

export function AmbientDisplaySection({ onChanged }: Props) {
  const [enabled, setEnabled] = useState(showAmbientInTranscript);

  return (
    <label className="settings-list-row">
      <span className="settings-list-text">Show ambient lines in transcript</span>
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => {
          const next = e.target.checked;
          setEnabled(next);
          setShowAmbientInTranscript(next);
          onChanged?.();
        }}
        aria-label="Show ambient lines in transcript"
      />
    </label>
  );
}
