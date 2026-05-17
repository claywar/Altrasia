import type { ObserverDigest as Digest } from "../api/client";

type Props = {
  digest: Digest | null;
};

export function ObserverDigest({ digest }: Props) {
  if (!digest) {
    return <p className="observer-digest-loading">Loading digest…</p>;
  }

  return (
    <aside className="observer-digest" aria-label="World digest">
      <p className="observer-digest-summary">{digest.summary}</p>
      {digest.paused && <p className="observer-digest-paused">World paused</p>}
      <section>
        <h3>Scenes</h3>
        <ul>
          {digest.scenes.map((s) => (
            <li key={s.sceneId} className={s.sceneId === digest.activeSceneId ? "active" : ""}>
              {s.locationName || s.sceneId}
              <span className="muted"> ({s.presentCount} present)</span>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>Pending signals</h3>
        {digest.pendingSignals.length === 0 ? (
          <p className="muted">None</p>
        ) : (
          <ul>
            {digest.pendingSignals.map((sig) => (
              <li key={sig.signalId}>
                {sig.kind}: {sig.sourceSceneId} → {sig.targetSceneId}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h3>Phone channels</h3>
        {digest.activeChannels.length === 0 ? (
          <p className="muted">None active</p>
        ) : (
          <ul>
            {digest.activeChannels.map((ch) => (
              <li key={ch.channelId}>
                {ch.participants.join(", ")}
                {ch.endpoints.some((e) => e.speakerphone) ? " · speakerphone" : ""}
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
