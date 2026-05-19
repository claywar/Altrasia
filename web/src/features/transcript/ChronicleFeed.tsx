import { useMemo, useSyncExternalStore } from "react";
import type { Message } from "../../api/client";
import {
  chronicleMessages,
  hideSocialBanterInTranscript,
  parseScope,
  sceneHasSocialIdleMessages,
} from "../../lib/parse";
import { BanterTranscriptToggle } from "./BanterTranscriptToggle";
import { ChronicleEntry } from "./ChronicleEntry";

type Props = {
  messages: Message[];
  worldId: string;
};

function subscribeBanterFilter(cb: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (
      e.key === "altrasia.hideSocialBanterInTranscript" ||
      e.key === "altrasia.showSocialIdleInTranscript"
    ) {
      cb();
    }
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener("altrasia-banter-filter", cb);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("altrasia-banter-filter", cb);
  };
}

function speakerLabel(m: Message): string {
  if (m.role === "user") return "You";
  if (m.role === "system") return "Scene";
  const id = m.characterId ?? "";
  return id.replace(/^.*-char-/, "").replace(/^char-/, "") || "NPC";
}

export function ChronicleFeed({ messages, worldId }: Props) {
  const hideBanter = useSyncExternalStore(
    subscribeBanterFilter,
    hideSocialBanterInTranscript,
    () => false
  );

  const hasBanter = useMemo(() => sceneHasSocialIdleMessages(messages), [messages]);

  const visible = useMemo(() => chronicleMessages(messages), [messages, hideBanter]);

  return (
    <div className="chronicle-feed" data-testid="chronicle-feed">
      {hasBanter && (
        <div className="chronicle-feed__toolbar">
          <span className="chronicle-feed__toolbar-label">Sidebar banter</span>
          <BanterTranscriptToggle visible />
        </div>
      )}
      {visible.length === 0 && (
        <p className="chronicle-feed__empty">The scene is quiet. Speak as persona to begin.</p>
      )}
      {visible.map((m) => {
        const sc = parseScope(m.metaJson);
        const perceived = m.perceivedByPersona !== false;
        return (
          <ChronicleEntry
            key={m.messageId}
            message={m}
            scope={sc}
            speakerLabel={speakerLabel(m)}
            perceived={perceived}
            worldId={worldId}
          />
        );
      })}
    </div>
  );
}
