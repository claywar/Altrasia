import { useState } from "react";
import { api, type ObserverDigest as Digest } from "../api/client";

type Props = {
  digest: Digest | null;
  worldId?: string;
  onRefresh?: () => void | Promise<void>;
};

export function ObserverDigest({ digest, worldId, onRefresh }: Props) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!digest) {
    return <p className="observer-digest-loading">Loading digest…</p>;
  }

  const wid = worldId ?? digest.worldId;

  return (
    <aside className="observer-digest" aria-label="World digest">
      <p className="observer-digest-summary">{digest.summary}</p>
      {digest.paused && <p className="observer-digest-paused">World paused</p>}
      {error && <p className="observer-digest-error">{error}</p>}
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
        <h3>Commissions</h3>
        {(digest.commissions?.length ?? 0) === 0 ? (
          <p className="muted">None open</p>
        ) : (
          <ul className="observer-commission-list">
            {digest.commissions!.map((c) => (
              <li key={c.commissionId} className="observer-commission-item">
                <div>
                  {c.assigneeCharacterId.replace("char-", "")}
                  <span className={`commission-status status-${c.status}`}>{c.status}</span>
                  <span className="muted"> @ {c.targetSceneId.replace("scene-", "")}</span>
                </div>
                {c.brief && <p className="observer-commission-brief">{c.brief}</p>}
                {wid && c.status === "queued" && (
                  <button
                    type="button"
                    className="people-secondary observer-commission-start"
                    disabled={busyId === c.commissionId}
                    onClick={async () => {
                      setBusyId(c.commissionId);
                      setError(null);
                      try {
                        await api.startCommission(wid, c.commissionId);
                        await onRefresh?.();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Start failed");
                      } finally {
                        setBusyId(null);
                      }
                    }}
                  >
                    Start work
                  </button>
                )}
                {c.status === "blocked" && (
                  <span className="muted observer-commission-hint">Summon assignee to scene</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h3>Debates</h3>
        {(digest.debates?.length ?? 0) === 0 ? (
          <p className="muted">None active</p>
        ) : (
          <ul>
            {digest.debates!.map((d) => (
              <li key={d.sceneId}>
                {d.locationName || d.sceneId} · phase {d.phase}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h3>Approvals</h3>
        {(digest.pendingApprovals?.length ?? 0) === 0 ? (
          <p className="muted">None pending</p>
        ) : (
          <ul>
            {digest.pendingApprovals!.map((a) => (
              <li key={a.approvalId}>
                {a.toolName}
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
