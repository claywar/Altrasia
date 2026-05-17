import { useEffect, useState } from "react";
import { api } from "../api/client";

type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  onClose: () => void;
};

export function MemoryInspector({ worldId, characterId, displayName, onClose }: Props) {
  const [mind, setMind] = useState<Array<{ locusKey: string; value: string }>>([]);
  const [diary, setDiary] = useState<Array<{ text: string; createdAt: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.characterMind(worldId, characterId), api.characterDiary(worldId, characterId)])
      .then(([m, d]) => {
        setMind(m);
        setDiary(d);
      })
      .finally(() => setLoading(false));
  }, [worldId, characterId]);

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
              {mind.map((row) => (
                <li key={row.locusKey}>
                  <strong>{row.locusKey}</strong>
                  <p>{row.value}</p>
                </li>
              ))}
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
