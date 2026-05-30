import { useState } from "react";
import { ModalShell } from "../ui/ModalShell";
import { MemoryInspectorPanel, type MemoryInspectorSection } from "./MemoryInspectorPanel";

type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  onClose: () => void;
};

type Tab = MemoryInspectorSection;

export function MemoryInspector({ worldId, characterId, displayName, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("memory");

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
        <MemoryInspectorPanel worldId={worldId} characterId={characterId} section={tab} />
      </div>
    </ModalShell>
  );
}
