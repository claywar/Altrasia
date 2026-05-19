import { useCallback, useEffect, useState } from "react";
import { api, type WebToolsAccess } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  embedded?: boolean;
};

type CastMember = Awaited<ReturnType<typeof api.listCharacters>>[number];

const WEB_ACCESS_OPTIONS: { value: WebToolsAccess; label: string; hint: string }[] = [
  { value: "off", label: "Off", hint: "No web tools" },
  {
    value: "ask",
    label: "Ask each time",
    hint: "Requires your approval before each fetch",
  },
  {
    value: "allow",
    label: "Allowed",
    hint: "Pre-authorized; skips approval prompts",
  },
];

export function CastListPanel({ worldId, embedded }: Props) {
  const [cast, setCast] = useState<CastMember[]>([]);
  const [savingId, setSavingId] = useState<string | null>(null);

  const load = useCallback(() => {
    api.listCharacters(worldId).then(setCast).catch(() => setCast([]));
  }, [worldId]);

  useEffect(() => {
    load();
  }, [load]);

  const saveWebAccess = async (characterId: string, webToolsAccess: WebToolsAccess) => {
    setSavingId(characterId);
    try {
      await api.patchCharacter(characterId, { definition: { webToolsAccess } });
      load();
    } finally {
      setSavingId(null);
    }
  };

  const list = (
    <ul className="settings-list settings-list-plain">
      {cast.map((c) => {
        const access = c.definition?.webToolsAccess ?? "off";
        return (
          <li key={c.characterId} className="settings-list-item cast-list-item">
            <div className="settings-list-text">
              <strong>{c.displayName}</strong>
              {c.muted ? " (muted)" : ""}
              {c.disabled ? " (disabled)" : ""}
              <span className="settings-list-meta">{c.characterId.replace("char-", "")}</span>
            </div>
            <label className="cast-web-access">
              <span className="settings-muted">Web tools</span>
              <select
                value={access}
                disabled={savingId === c.characterId}
                onChange={(e) =>
                  saveWebAccess(c.characterId, e.target.value as WebToolsAccess)
                }
                aria-label={`Web tools access for ${c.displayName}`}
              >
                {WEB_ACCESS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value} title={opt.hint}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </li>
        );
      })}
      {cast.length === 0 && (
        <li className="settings-list-item settings-list-empty">No cast yet</li>
      )}
    </ul>
  );

  if (embedded) {
    return (
      <SettingsBlock
        title="Cast"
        description="Per-character web tool access. Allowed skips approval even when the world requires it."
      >
        {list}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Cast</h3>
      <p className="settings-muted">
        {cast.length} character(s). Configure web tools per character below.
      </p>
      {list}
    </section>
  );
}
