import { useEffect, useState } from "react";
import { api } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  embedded?: boolean;
};

export function CastListPanel({ worldId, embedded }: Props) {
  const [cast, setCast] = useState<Awaited<ReturnType<typeof api.listCharacters>>>([]);

  useEffect(() => {
    api.listCharacters(worldId).then(setCast).catch(() => setCast([]));
  }, [worldId]);

  const list = (
    <ul className="settings-list settings-list-plain">
      {cast.map((c) => (
        <li key={c.characterId} className="settings-list-item">
          <span className="settings-list-text">
            {c.displayName}
            {c.muted ? " (muted)" : ""}
            {c.disabled ? " (disabled)" : ""}
          </span>
          <span className="settings-list-meta">{c.characterId.replace("char-", "")}</span>
        </li>
      ))}
      {cast.length === 0 && (
        <li className="settings-list-item settings-list-empty">No cast yet</li>
      )}
    </ul>
  );

  if (embedded) {
    return (
      <SettingsBlock title="Cast" description={`${cast.length} character(s) in this world.`}>
        {list}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Cast</h3>
      <p className="settings-muted">{cast.length} character(s) in this world.</p>
      <ul className="scene-geo-list">
        {cast.map((c) => (
          <li key={c.characterId} className="scene-geo-row">
            <span>
              {c.displayName}
              {c.muted ? " (muted)" : ""}
              {c.disabled ? " (disabled)" : ""}
            </span>
            <span className="settings-muted" style={{ fontSize: 11 }}>
              {c.characterId.replace("char-", "")}
            </span>
          </li>
        ))}
        {cast.length === 0 && <li style={{ color: "var(--muted)" }}>No cast yet</li>}
      </ul>
    </section>
  );
}
