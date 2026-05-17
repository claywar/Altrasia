import { useState } from "react";
import { api, type CharacterDraft } from "../api/client";

type Props = {
  worldId: string;
  onCharacterAdded: () => void;
};

export function CharacterDraftPanel({ worldId, onCharacterAdded }: Props) {
  const [brief, setBrief] = useState("");
  const [draft, setDraft] = useState<CharacterDraft | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateDraft = async () => {
    if (!brief.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.createCharacterDraft(brief.trim());
      setDraft(d);
      setDisplayName("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Draft failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    if (!draft || draft.status !== "ready") return;
    setBusy(true);
    setError(null);
    try {
      await api.approveCharacter({
        draftId: draft.draftId,
        worldId,
        displayName: displayName.trim() || undefined,
        definitionJson: draft.definitionJson ?? undefined,
      });
      setBrief("");
      setDraft(null);
      onCharacterAdded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const discard = async () => {
    if (!draft) return;
    setBusy(true);
    try {
      await api.discardCharacterDraft(draft.draftId);
      setDraft(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="settings-section">
      <h3>Create character (AI draft)</h3>
      <p className="settings-muted">
        Describe a new cast member in natural language. Review the draft before adding to this
        world.
      </p>
      <textarea
        className="char-draft-brief"
        rows={3}
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
        placeholder="e.g. A retired sea captain, gruff but fair…"
        disabled={busy}
      />
      <div className="settings-actions">
        <button type="button" disabled={busy || !brief.trim()} onClick={generateDraft}>
          {busy && !draft ? "Drafting…" : "Generate draft"}
        </button>
        {draft && (
          <>
            <button type="button" disabled={busy} onClick={approve}>
              Approve & add to world
            </button>
            <button type="button" disabled={busy} onClick={discard}>
              Discard
            </button>
          </>
        )}
      </div>
      {error && <p className="settings-error">{error}</p>}
      {draft?.definitionJson && (
        <div className="char-draft-preview">
          <label className="settings-row">
            Display name
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Optional"
            />
          </label>
          <p>
            <strong>Persona:</strong> {draft.definitionJson.persona}
          </p>
          <p>
            <strong>Instructions:</strong> {draft.definitionJson.instructions}
          </p>
        </div>
      )}
    </section>
  );
}
