import { useEffect, useState } from "react";
import { api } from "../api/client";

type Props = {
  worldId: string;
};

export function CastListPanel({ worldId }: Props) {
  const [cast, setCast] = useState<Awaited<ReturnType<typeof api.listCharacters>>>([]);

  useEffect(() => {
    api.listCharacters(worldId).then(setCast).catch(() => setCast([]));
  }, [worldId]);

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
