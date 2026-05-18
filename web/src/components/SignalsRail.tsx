import { api } from "../api/client";
import { RailSection } from "../ui/RailSection";

export type Signal = {
  signalId: string;
  kind: string;
  sourceSceneId: string;
  targetSceneId: string;
  status?: string;
};

type CastRef = { characterId: string; displayName: string };

type Props = {
  worldId: string;
  activeSceneId: string;
  signals: Signal[];
  castAtActive: CastRef[];
  sceneLabel: (sceneId: string) => string;
  onChanged: () => void;
};

export function SignalsRail({
  worldId,
  activeSceneId,
  signals,
  castAtActive,
  sceneLabel,
  onChanged,
}: Props) {
  const pending = signals.filter((s) => s.status !== "dismissed");

  return (
    <RailSection title="Signals" testId="signals-rail">
      <ul className="rail-list signals-list">
        {pending.length === 0 && <li className="signals-empty">The house is quiet</li>}
        {pending.map((s) => {
          const forHere = s.targetSceneId === activeSceneId;
          const answerCast =
            castAtActive.find((c) => c.characterId !== "__persona__") ?? castAtActive[0];
          return (
            <li key={s.signalId} className="signal-row">
              <span className="signal-summary">
                {s.kind}: {sceneLabel(s.sourceSceneId)} → {sceneLabel(s.targetSceneId)}
                {forHere ? " · here" : ""}
              </span>
              <div className="people-actions">
                {forHere && answerCast && s.kind === "knock" && (
                  <button
                    type="button"
                    className="people-secondary"
                    onClick={async () => {
                      await api.answerSignal(worldId, s.signalId, {
                        characterId: answerCast.characterId,
                        targetSceneId: activeSceneId,
                      });
                      onChanged();
                    }}
                  >
                    Answer ({answerCast.displayName})
                  </button>
                )}
                <button
                  type="button"
                  className="people-memory"
                  onClick={async () => {
                    await api.dismissSignal(worldId, s.signalId);
                    onChanged();
                  }}
                >
                  Dismiss
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </RailSection>
  );
}
