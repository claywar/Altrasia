import { useEffect, useState } from "react";
import { api, type EvidenceRecord } from "../api/client";

type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  onClose: () => void;
};

export function MemoryInspector({ worldId, characterId, displayName, onClose }: Props) {
  const [mind, setMind] = useState<Array<{ locusKey: string; value: string }>>([]);
  const [diary, setDiary] = useState<Array<{ text: string; createdAt: string }>>([]);
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.characterMind(worldId, characterId),
      api.characterDiary(worldId, characterId),
      api.characterEvidence(worldId, characterId),
    ])
      .then(([m, d, ev]) => {
        setMind(m);
        setDiary(d);
        setEvidence(ev);
      })
      .finally(() => setLoading(false));
  }, [worldId, characterId]);

  const evidenceFor = (key: string) => evidence.filter((e) => e.locusKey === key);

  return (
    <div className="memory-inspector" role="dialog" aria-label={`Memory — ${displayName}`}>
      <header className="memory-inspector-header">
        <h2>Memory — {displayName}</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </header>
      {loading ? (
        <p className="memory-muted">Loading…</p>
      ) : (
        <div className="memory-inspector-body">
          <section>
            <h3>Mind loci</h3>
            {mind.length === 0 && <p className="memory-muted">No mind loci.</p>}
            <ul className="memory-list">
              {mind.map((row) => {
                const ev = evidenceFor(row.locusKey);
                return (
                  <li key={row.locusKey}>
                    <strong>{row.locusKey}</strong>
                    {ev.length > 0 && (
                      <button
                        type="button"
                        className="memory-evidence-toggle"
                        onClick={() =>
                          setExpanded(expanded === row.locusKey ? null : row.locusKey)
                        }
                      >
                        {ev.length} source{ev.length === 1 ? "" : "s"}
                      </button>
                    )}
                    <p>{row.value}</p>
                    {expanded === row.locusKey && ev.length > 0 && (
                      <ul className="memory-evidence-list">
                        {ev.map((e) => (
                          <li key={e.evidenceId}>
                            <span className="memory-evidence-kind">{e.sourceKind}</span>
                            <span className="memory-muted"> {e.sourceRef}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
          <section>
            <h3>Diary (witnessed)</h3>
            {diary.length === 0 && <p className="memory-muted">No diary segments.</p>}
            <ul className="memory-list">
              {diary.slice(-12).map((row, i) => (
                <li key={`${row.createdAt}-${i}`}>
                  <p>{row.text}</p>
                  <time className="memory-muted">{row.createdAt}</time>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
