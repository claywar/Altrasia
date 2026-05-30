import { useCallback, useEffect, useState } from "react";
import {
  api,
  type EvidenceRecord,
  type MemoryLink,
  type PersonaProposal,
  type ReflectionRun,
} from "../api/client";
import { ModalShell } from "../ui/ModalShell";
import { FormSection } from "../ui/FormSection";

type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  onClose: () => void;
};

type Tab = "memory" | "reflection";

export function MemoryInspector({ worldId, characterId, displayName, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("memory");
  const [mind, setMind] = useState<Array<{ locusKey: string; value: string }>>([]);
  const [diary, setDiary] = useState<Array<{ text: string; createdAt: string }>>([]);
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [links, setLinks] = useState<MemoryLink[]>([]);
  const [runs, setRuns] = useState<ReflectionRun[]>([]);
  const [proposals, setProposals] = useState<PersonaProposal[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reflecting, setReflecting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setActionError(null);
    Promise.all([
      api.characterMind(worldId, characterId),
      api.characterDiary(worldId, characterId),
      api.characterEvidence(worldId, characterId),
      api.characterMemoryLinks(worldId, characterId),
      api.characterReflectionRuns(characterId),
      api.characterPersonaProposals(worldId, characterId),
    ])
      .then(([m, d, ev, lk, rn, pr]) => {
        setMind(m);
        setDiary(d);
        setEvidence(ev);
        setLinks(lk);
        setRuns(rn);
        setProposals(pr);
      })
      .finally(() => setLoading(false));
  }, [worldId, characterId]);

  useEffect(() => {
    load();
  }, [load]);

  const evidenceFor = (key: string) => evidence.filter((e) => e.locusKey === key);

  const handleReflect = async () => {
    setReflecting(true);
    setActionError(null);
    try {
      const result = await api.reflectCharacter(characterId, worldId);
      if (result.status === "failed") {
        setActionError(result.error ?? "Reflection failed");
      }
      load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Reflection failed");
    } finally {
      setReflecting(false);
    }
  };

  const handleProposal = async (proposalId: string, approve: boolean) => {
    setActionError(null);
    try {
      if (approve) {
        await api.approvePersonaProposal(proposalId);
      } else {
        await api.rejectPersonaProposal(proposalId);
      }
      load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed");
    }
  };

  const pendingProposals = proposals.filter((p) => p.status === "pending");

  return (
    <ModalShell
      title={`Memory — ${displayName}`}
      side="right"
      onClose={onClose}
      testId="memory-inspector"
    >
      <div className="memory-inspector-body">
        <div className="memory-inspector-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "memory"}
            className={tab === "memory" ? "memory-tab active" : "memory-tab"}
            onClick={() => setTab("memory")}
          >
            Memory
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "reflection"}
            className={tab === "reflection" ? "memory-tab active" : "memory-tab"}
            onClick={() => setTab("reflection")}
          >
            Reflection
          </button>
        </div>

        {actionError && <p className="memory-error">{actionError}</p>}

        {loading ? (
          <p className="memory-muted">Loading…</p>
        ) : tab === "memory" ? (
          <>
            <FormSection title="Mind loci">
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
            </FormSection>
            <FormSection title="Diary (witnessed)">
              {diary.length === 0 && <p className="memory-muted">No diary segments.</p>}
              <ul className="memory-list">
                {diary.slice(-12).map((row, i) => (
                  <li key={`${row.createdAt}-${i}`}>
                    <p>{row.text}</p>
                    <time className="memory-muted">{row.createdAt}</time>
                  </li>
                ))}
              </ul>
            </FormSection>
          </>
        ) : (
          <>
            <FormSection title="Reflection">
              <button
                type="button"
                className="memory-reflect-btn"
                disabled={reflecting}
                onClick={handleReflect}
              >
                {reflecting ? "Reflecting…" : "Run reflection now"}
              </button>
              <p className="memory-muted">
                Consolidates recent diary into beliefs, lessons, and memory links. Nightly runs
                when reflection is enabled in world policy.
              </p>
            </FormSection>

            <FormSection title="Persona proposals">
              {pendingProposals.length === 0 && (
                <p className="memory-muted">No pending persona proposals.</p>
              )}
              <ul className="memory-list">
                {pendingProposals.map((p) => (
                  <li key={p.proposalId}>
                    <strong>{p.field}</strong>
                    <p className="memory-muted">{p.rationale}</p>
                    <p>{p.proposedValue}</p>
                    <div className="memory-proposal-actions">
                      <button
                        type="button"
                        onClick={() => handleProposal(p.proposalId, true)}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleProposal(p.proposalId, false)}
                      >
                        Reject
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </FormSection>

            <FormSection title="Memory graph">
              {links.length === 0 && <p className="memory-muted">No memory links yet.</p>}
              <ul className="memory-list memory-graph-list">
                {links.map((link) => (
                  <li key={link.linkId}>
                    <span className="memory-graph-edge">
                      {link.fromKind}:{link.fromRef.slice(0, 8)}…
                    </span>
                    <span className="memory-graph-relation"> — {link.relation} → </span>
                    <span className="memory-graph-edge">
                      {link.toKind}:{link.toRef.slice(0, 8)}…
                    </span>
                    {link.summary && <p>{link.summary}</p>}
                  </li>
                ))}
              </ul>
            </FormSection>

            <FormSection title="Reflection runs">
              {runs.length === 0 && <p className="memory-muted">No reflection runs yet.</p>}
              <ul className="memory-list">
                {runs.map((run) => (
                  <li key={run.runId}>
                    <strong>{run.status}</strong>
                    <span className="memory-muted">
                      {" "}
                      · {run.trigger} · {run.startedAt}
                    </span>
                    {run.outputLinkCount != null && run.outputLinkCount > 0 && (
                      <span className="memory-muted"> · {run.outputLinkCount} links</span>
                    )}
                    {run.errorText && <p className="memory-error">{run.errorText}</p>}
                  </li>
                ))}
              </ul>
            </FormSection>
          </>
        )}
      </div>
    </ModalShell>
  );
}
