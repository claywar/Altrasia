import { useState } from "react";
import { api, type LayoutDraft } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  onCommitted?: () => void;
  embedded?: boolean;
};

export function MapDraftPanel({ worldId, onCommitted, embedded }: Props) {
  const [brief, setBrief] = useState("");
  const [draft, setDraft] = useState<LayoutDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const body = (
    <>
      <textarea
        className="char-draft-brief"
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        placeholder="e.g. Hall left, kitchen right, courtyard below…"
        rows={3}
      />
      <div className="settings-inline-actions">
        <button
          type="button"
          disabled={busy || !brief.trim()}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              const d = await api.createLayoutDraft(worldId, {
                brief: brief.trim(),
                scope: "mini",
              });
              setDraft(d);
            } catch (e) {
              setError(e instanceof Error ? e.message : "Draft failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          Generate draft
        </button>
        {draft?.status === "ready" && (
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                await api.commitLayoutDraft(worldId, draft.layoutDraftId);
                setDraft(null);
                setBrief("");
                onCommitted?.();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Commit failed");
              } finally {
                setBusy(false);
              }
            }}
          >
            Commit layout
          </button>
        )}
      </div>
      {error && <p className="settings-error">{error}</p>}
      {draft?.proposed?.nodes && draft.proposed.nodes.length > 0 && (
        <svg className="map-draft-svg" viewBox="0 0 100 100" role="img" aria-label="Draft layout preview">
          {draft.proposed.nodes.map((n) => {
            const x = n.mapPosition?.x ?? 50;
            const y = n.mapPosition?.y ?? 50;
            return (
              <g key={n.sceneId}>
                <rect
                  x={x - 6}
                  y={y - 4}
                  width={12}
                  height={8}
                  rx={1}
                  fill="var(--accent)"
                  opacity={0.85}
                />
                <title>{n.sceneId}</title>
              </g>
            );
          })}
        </svg>
      )}
      {draft && (
        <pre className="map-draft-preview">
          {JSON.stringify(draft.proposed?.nodes ?? [], null, 2)}
        </pre>
      )}
    </>
  );

  if (embedded) {
    return (
      <SettingsBlock
        title="Map layout"
        description="Propose mini-map positions via LLM; commit applies scene positions."
      >
        {body}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Map layout (MapDraft)</h3>
      <p className="settings-muted">
        Propose mini-map positions via LLM; commit applies non-conflicting scene positions.
      </p>
      {body}
    </section>
  );
}
