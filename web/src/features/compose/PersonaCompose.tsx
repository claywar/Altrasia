import { Button } from "../../ui/Button";

const SCOPES = [
  { value: "public", label: "Public" },
  { value: "whisper", label: "Whisper" },
  { value: "dm", label: "DM" },
] as const;

type PersonOption = { characterId: string; displayName: string };

type Props = {
  text: string;
  scope: string;
  loading: boolean;
  phoneChannelId: string | null;
  whisperTarget: string;
  people: PersonOption[];
  onTextChange: (v: string) => void;
  onScopeChange: (v: string) => void;
  onWhisperTargetChange: (v: string) => void;
  onSend: () => void;
};

export function PersonaCompose({
  text,
  scope,
  loading,
  phoneChannelId,
  whisperTarget,
  people,
  onTextChange,
  onScopeChange,
  onWhisperTargetChange,
  onSend,
}: Props) {
  const scopes = phoneChannelId ? [...SCOPES, { value: "phone", label: "Phone" }] : SCOPES;
  const needsTarget = scope === "whisper" || scope === "dm";

  return (
    <footer className="persona-compose" data-testid="persona-compose">
      <div className="persona-compose__scopes">
        <div className="ui-segmented" role="group" aria-label="Message scope">
          {scopes.map((s) => (
            <button
              key={s.value}
              type="button"
              className={`ui-segmented__btn${scope === s.value ? " ui-segmented__btn--active" : ""}`}
              onClick={() => onScopeChange(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
        {needsTarget && (
          <select
            className="persona-compose__target"
            value={whisperTarget}
            onChange={(e) => onWhisperTargetChange(e.target.value)}
            aria-label="Whisper target"
          >
            <option value="">Select character…</option>
            {people.map((p) => (
              <option key={p.characterId} value={p.characterId}>
                {p.displayName}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="persona-compose__row">
        <textarea
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          placeholder="Speak as persona…"
          title="Enter to send, Shift+Enter for newline"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
        />
        <Button variant="primary" onClick={onSend} disabled={loading || !text.trim()}>
          Send
        </Button>
      </div>
    </footer>
  );
}
