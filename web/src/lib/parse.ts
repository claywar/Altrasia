import type { Message } from "../api/client";

export const AMBIENT_ACTIVITY_LIMIT = 15;
export const SHOW_AMBIENT_IN_TRANSCRIPT_KEY = "altrasia.showAmbientInTranscript";

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

export function isAmbientMessage(m: Message): boolean {
  return messageGenerationTrigger(m) === "idle_timer";
}

/** Messages shown in the scene chronicle (respects ambient transcript toggle). */
export function chronicleMessages(msgs: Message[]): Message[] {
  if (showAmbientInTranscript()) return msgs;
  return msgs.filter((m) => !isAmbientMessage(m));
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
