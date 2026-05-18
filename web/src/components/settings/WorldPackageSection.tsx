import { useState } from "react";
import { api } from "../../api/client";
import { SettingsBlock } from "./SettingsBlock";

type Props = {
  worldId: string;
  worldName: string;
  onImported: (world: { worldId: string; name: string; activeSceneId: string }) => void;
  onClose: () => void;
};

export function WorldPackageSection({ worldId, worldName, onImported, onClose }: Props) {
  const [busy, setBusy] = useState(false);

  return (
    <SettingsBlock title="World package" description="Export or import a full world .zip package.">
      <ul className="settings-list settings-list-actions">
        <li className="settings-list-item">
          <span className="settings-list-text">Export</span>
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const blob = await api.exportPackage(worldId);
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `altrasia-${worldName.replace(/\s+/g, "-").toLowerCase()}.zip`;
                a.click();
                URL.revokeObjectURL(url);
              } finally {
                setBusy(false);
              }
            }}
          >
            Download .zip
          </button>
        </li>
        <li className="settings-list-item">
          <span className="settings-list-text">Import</span>
          <label className="settings-file-inline">
            <input
              type="file"
              accept=".zip,application/zip"
              disabled={busy}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setBusy(true);
                try {
                  const w = await api.importPackage(file);
                  onImported(w);
                  onClose();
                } finally {
                  setBusy(false);
                  e.target.value = "";
                }
              }}
            />
          </label>
        </li>
      </ul>
    </SettingsBlock>
  );
}
