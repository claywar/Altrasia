import { GpuQueueStrip } from "../components/GpuQueueStrip";
import { WorldActivityLog } from "../components/WorldActivityLog";
import type { Message, QueueSnapshot } from "../api/client";
import { Button } from "../ui/Button";

type Props = {
  worldName: string;
  worldPaused: boolean;
  queue: QueueSnapshot;
  ambientActivity: Message[];
  ambientCharName: (characterId: string | null) => string;
  currentJobId: string | null;
  onPauseToggle: () => void;
  onMap: () => void;
  onObserver: () => void;
  onSettings: () => void;
  onCancelJob?: () => void;
  onToggleRightRail?: () => void;
  rightRailOpen?: boolean;
};

export function TopBar({
  worldName,
  worldPaused,
  queue,
  ambientActivity,
  ambientCharName,
  currentJobId,
  onPauseToggle,
  onMap,
  onObserver,
  onSettings,
  onCancelJob,
  onToggleRightRail,
  rightRailOpen,
}: Props) {
  return (
    <header className="top-bar" data-testid="top-bar">
      <div className="top-bar__brand">
        <span className="top-bar__dot" aria-hidden title="Connected" />
        <h1>Altrasia — {worldName}</h1>
      </div>
      <WorldActivityLog entries={ambientActivity} charName={ambientCharName} />
      <GpuQueueStrip
        busy={queue.busy}
        depth={queue.depth}
        estimatedWaitMs={queue.estimatedWaitMs}
        currentJob={queue.currentJob ?? undefined}
        leaseKind={queue.gpu?.currentLease?.kind}
        onCancel={currentJobId ? onCancelJob : undefined}
      />
      <nav className="top-bar__actions" aria-label="World controls">
        <Button
          variant={worldPaused ? "primary" : "ghost"}
          size="sm"
          onClick={onPauseToggle}
          title={worldPaused ? "Resume world activity" : "Pause world activity"}
        >
          {worldPaused ? "Resume" : "Pause"}
        </Button>
        <Button variant="ghost" size="sm" onClick={onMap}>
          Map
        </Button>
        <Button variant="ghost" size="sm" onClick={onObserver}>
          Observer
        </Button>
        <Button variant="ghost" size="sm" onClick={onSettings}>
          Settings
        </Button>
        {onToggleRightRail && (
          <Button
            variant="ghost"
            size="sm"
            className="top-bar__rail-toggle"
            onClick={onToggleRightRail}
            aria-expanded={rightRailOpen}
          >
            Places
          </Button>
        )}
        {worldPaused && <span className="paused-badge">Paused</span>}
      </nav>
    </header>
  );
}
