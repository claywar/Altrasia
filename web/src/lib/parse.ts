import type { Message } from "../api/client";

export const AMBIENT_ACTIVITY_LIMIT = 15;
export const SHOW_AMBIENT_IN_TRANSCRIPT_KEY = "altrasia.showAmbientInTranscript";
/** @deprecated use HIDE_SOCIAL_BANTER_IN_TRANSCRIPT_KEY — legacy opt-in key */
export const SHOW_SOCIAL_IDLE_IN_TRANSCRIPT_KEY = "altrasia.showSocialIdleInTranscript";
/** When "1", banter is hidden from the scene chronicle (default: show banter). */
export const HIDE_SOCIAL_BANTER_IN_TRANSCRIPT_KEY = "altrasia.hideSocialBanterInTranscript";

export function messageGenerationTrigger(m: Message): string | null {
  if (m.generationTrigger) return m.generationTrigger;
  try {
    const meta = JSON.parse(m.metaJson || "{}") as {
      orchestration?: { trigger?: string };
    };
    return meta.orchestration?.trigger ?? null;
  } catch {
    return null;
  }
}

export function parseOrchestration(m: Message): {
  trigger?: string;
  socialIdle?: boolean;
  banterSessionId?: string;
  participants?: string[];
} {
  try {
    const meta = JSON.parse(m.metaJson || "{}") as {
      orchestration?: {
        trigger?: string;
        socialIdle?: boolean;
        banterSessionId?: string;
        participants?: string[];
      };
    };
    return meta.orchestration ?? {};
  } catch {
    return {};
  }
}

export function isSocialIdleMessage(m: Message): boolean {
  if (parseOrchestration(m).socialIdle === true) return true;
  const t = messageGenerationTrigger(m);
  return t === "banter_turn" || t === "idle_continue";
}

export function isAmbientMessage(m: Message): boolean {
  const t = messageGenerationTrigger(m);
  return t === "idle_timer" || isSocialIdleMessage(m);
}

/** Messages shown in the scene chronicle (respects ambient transcript toggle). */
export function chronicleMessages(msgs: Message[]): Message[] {
  if (showAmbientInTranscript()) return msgs;
  return msgs.filter((m) => {
    if (isAmbientMessage(m) && !isSocialIdleMessage(m)) return false;
    if (isSocialIdleMessage(m) && hideSocialBanterInTranscript()) return false;
    return true;
  });
}

export function sceneHasSocialIdleMessages(msgs: Message[]): boolean {
  return msgs.some(isSocialIdleMessage);
}

export function showAmbientInTranscript(): boolean {
  try {
    return sessionStorage.getItem(SHOW_AMBIENT_IN_TRANSCRIPT_KEY) === "1";
  } catch {
    return false;
  }
}

export function setShowAmbientInTranscript(enabled: boolean): void {
  try {
    sessionStorage.setItem(SHOW_AMBIENT_IN_TRANSCRIPT_KEY, enabled ? "1" : "0");
  } catch {
    /* ignore */
  }
}

export function hideSocialBanterInTranscript(): boolean {
  try {
    const hide = sessionStorage.getItem(HIDE_SOCIAL_BANTER_IN_TRANSCRIPT_KEY);
    if (hide === "1") return true;
    if (hide === "0") return false;
    const legacy = sessionStorage.getItem(SHOW_SOCIAL_IDLE_IN_TRANSCRIPT_KEY);
    if (legacy === "0") return true;
    if (legacy === "1") return false;
    return false;
  } catch {
    return false;
  }
}

export function setHideSocialBanterInTranscript(hide: boolean): void {
  try {
    sessionStorage.setItem(HIDE_SOCIAL_BANTER_IN_TRANSCRIPT_KEY, hide ? "1" : "0");
    sessionStorage.removeItem(SHOW_SOCIAL_IDLE_IN_TRANSCRIPT_KEY);
  } catch {
    /* ignore */
  }
}

/** @deprecated use hideSocialBanterInTranscript */
export function showSocialIdleInTranscript(): boolean {
  return !hideSocialBanterInTranscript();
}

/** @deprecated use setHideSocialBanterInTranscript */
export function setShowSocialIdleInTranscript(enabled: boolean): void {
  setHideSocialBanterInTranscript(!enabled);
}

export function splitSceneMessages(msgs: Message[]): {
  dialogueMessages: Message[];
  ambientActivity: Message[];
} {
  const ambient = msgs.filter(isAmbientMessage);
  const dialogue = chronicleMessages(msgs);
  return {
    dialogueMessages: dialogue,
    ambientActivity: ambient.slice(-AMBIENT_ACTIVITY_LIMIT),
  };
}

export type ToolCallRecord = {
  name: string;
  arguments: Record<string, unknown>;
  result: string;
};

export function parseToolCallsFromRationale(
  selectionRationaleJson?: string | null
): ToolCallRecord[] {
  if (!selectionRationaleJson) return [];
  try {
    const parsed = JSON.parse(selectionRationaleJson) as {
      toolCalls?: ToolCallRecord[];
    };
    return Array.isArray(parsed.toolCalls) ? parsed.toolCalls : [];
  } catch {
    return [];
  }
}

export function parseScope(metaJson: string): string {
  try {
    return JSON.parse(metaJson).communication?.scope ?? "public";
  } catch {
    return "public";
  }
}

export function parseGenerationError(metaJson: string): string | null {
  try {
    const err = JSON.parse(metaJson || "{}").generationError;
    return typeof err === "string" && err.trim() ? err.trim() : null;
  } catch {
    return null;
  }
}

export function parsePresent(raw: string): string[] {
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function structureLabel(structureId: string): string {
  return structureId.replace(/^struct-/, "").replace(/-/g, " ");
}

export function sceneStructureHints(layoutHintsJson?: string | null): {
  structureId?: string;
  fixtures?: string[];
} {
  if (!layoutHintsJson) return {};
  try {
    const hints = JSON.parse(layoutHintsJson);
    return {
      structureId: hints.structureId as string | undefined,
      fixtures: Array.isArray(hints.fixtures) ? hints.fixtures : undefined,
    };
  } catch {
    return {};
  }
}

export function structureTint(structureId?: string | null): string {
  if (!structureId) return "220";
  let hash = 0;
  for (let i = 0; i < structureId.length; i++) {
    hash = (hash * 31 + structureId.charCodeAt(i)) | 0;
  }
  return String(200 + (Math.abs(hash) % 40));
}
