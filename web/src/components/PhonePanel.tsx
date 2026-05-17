import { useEffect, useState } from "react";
import { api, type PhoneChannel } from "../api/client";

type RosterEntry = {
  characterId: string;
  displayName: string;
  sceneId?: string;
  presentSceneId?: string;
  locationName?: string | null;
};

type Props = {
  worldId: string;
  activeSceneId: string;
  atLocation: RosterEntry[];
  elsewhere: RosterEntry[];
  onChannelChange: () => void;
};

export function PhonePanel({
  worldId,
  activeSceneId,
  atLocation,
  elsewhere,
  onChannelChange,
}: Props) {
  const [channels, setChannels] = useState<PhoneChannel[]>([]);
  const [remoteChar, setRemoteChar] = useState("");

  const refresh = () => api.listChannels(worldId).then(setChannels);

  useEffect(() => {
    refresh();
  }, [worldId]);

  const active = channels[0];
  const myEndpoint = active?.endpoints?.find((e) => e.sceneId === activeSceneId);
  const localChar =
    atLocation.find((p) => p.characterId !== "__persona__")?.characterId ??
    "char-alice";

  return (
    <div className="rail-section">
      <h3>Phone</h3>
      {!active ? (
        <div className="phone-start">
          <select value={remoteChar} onChange={(e) => setRemoteChar(e.target.value)}>
            <option value="">Call character elsewhere…</option>
            {elsewhere.map((p) => (
              <option key={p.characterId} value={p.characterId}>
                {p.displayName} ({p.locationName ?? p.presentSceneId})
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!remoteChar}
            onClick={async () => {
              const remote = elsewhere.find((p) => p.characterId === remoteChar);
              const remoteScene = remote?.presentSceneId ?? remote?.sceneId;
              if (!remoteScene) return;
              await api.createPhoneChannel(worldId, {
                sceneIdA: activeSceneId,
                characterIdA: localChar,
                sceneIdB: remoteScene,
                characterIdB: remoteChar,
              });
              await refresh();
              onChannelChange();
            }}
          >
            Start call
          </button>
        </div>
      ) : (
        <div className="phone-active">
          <p className="settings-muted">
            Active · {myEndpoint?.speakerphone ? "Speakerphone" : "Handset"}
          </p>
          <button
            type="button"
            onClick={async () => {
              await api.setSpeakerphone(
                worldId,
                active.channelId,
                activeSceneId,
                !myEndpoint?.speakerphone
              );
              await refresh();
              onChannelChange();
            }}
          >
            Toggle speakerphone (here)
          </button>
          <button
            type="button"
            onClick={async () => {
              await api.endPhoneChannel(worldId, active.channelId);
              await refresh();
              onChannelChange();
            }}
          >
            End call
          </button>
        </div>
      )}
    </div>
  );
}
