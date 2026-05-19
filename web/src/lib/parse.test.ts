import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import type { Message } from "../api/client";
import {
  hideSocialBanterInTranscript,
  isAmbientMessage,
  isSocialIdleMessage,
  parseToolCallsFromRationale,
  setHideSocialBanterInTranscript,
  setShowAmbientInTranscript,
  splitSceneMessages,
} from "./parse";

function msg(overrides: Partial<Message> = {}): Message {
  return {
    messageId: "m1",
    role: "assistant",
    characterId: "char-jordan-reyes",
    outputText: "Ambient.",
    streamStatus: "final",
    metaJson: "{}",
    generationTrigger: "idle_timer",
    idleSource: "tab_visible",
    ...overrides,
  };
}

describe("parseToolCallsFromRationale", () => {
  it("returns toolCalls array from rationale JSON", () => {
    const calls = parseToolCallsFromRationale(
      JSON.stringify({
        pick: "reactive",
        toolCalls: [{ name: "memory_search", arguments: { q: "x" }, result: "hit" }],
      })
    );
    expect(calls).toHaveLength(1);
    expect(calls[0].name).toBe("memory_search");
  });
});

describe("isAmbientMessage", () => {
  it("matches idle_timer trigger", () => {
    expect(isAmbientMessage(msg())).toBe(true);
    expect(isAmbientMessage(msg({ generationTrigger: "reactive" }))).toBe(false);
  });

  it("matches orchestration.trigger in metaJson when generationTrigger absent", () => {
    expect(
      isAmbientMessage(
        msg({
          generationTrigger: undefined,
          metaJson: JSON.stringify({
            communication: { scope: "public" },
            orchestration: { trigger: "idle_timer", idleSource: "tab_visible" },
          }),
        })
      )
    ).toBe(true);
  });
});

describe("splitSceneMessages", () => {
  const storage = new Map<string, string>();

  beforeEach(() => {
    storage.clear();
    vi.stubGlobal("sessionStorage", {
      getItem: (k: string) => storage.get(k) ?? null,
      setItem: (k: string, v: string) => {
        storage.set(k, v);
      },
      removeItem: (k: string) => {
        storage.delete(k);
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("excludes idle from dialogue by default", () => {
    const idle = msg({ messageId: "idle-1" });
    const reactive = msg({
      messageId: "r1",
      generationTrigger: "reactive",
      outputText: "Hello.",
    });
    const { dialogueMessages, ambientActivity } = splitSceneMessages([idle, reactive]);
    expect(dialogueMessages).toHaveLength(1);
    expect(dialogueMessages[0].messageId).toBe("r1");
    expect(ambientActivity).toHaveLength(1);
    expect(ambientActivity[0].messageId).toBe("idle-1");
  });

  it("includes idle in dialogue when opt-in enabled", () => {
    setShowAmbientInTranscript(true);
    const idle = msg();
    const { dialogueMessages, ambientActivity } = splitSceneMessages([idle]);
    expect(dialogueMessages).toHaveLength(1);
    expect(ambientActivity).toHaveLength(1);
  });

  it("includes social banter in dialogue by default", () => {
    setHideSocialBanterInTranscript(false);
    const banter = msg({
      messageId: "b1",
      generationTrigger: "banter_turn",
      metaJson: JSON.stringify({
        orchestration: { trigger: "banter_turn", socialIdle: true },
      }),
    });
    expect(isSocialIdleMessage(banter)).toBe(true);
    expect(isAmbientMessage(banter)).toBe(true);
    const { dialogueMessages } = splitSceneMessages([banter]);
    expect(dialogueMessages).toHaveLength(1);
  });

  it("excludes social banter when hide toggle on", () => {
    setHideSocialBanterInTranscript(true);
    const banter = msg({
      messageId: "b2",
      generationTrigger: "banter_turn",
      metaJson: JSON.stringify({
        orchestration: { trigger: "banter_turn", socialIdle: true },
      }),
    });
    const { dialogueMessages } = splitSceneMessages([banter]);
    expect(dialogueMessages).toHaveLength(0);
    expect(hideSocialBanterInTranscript()).toBe(true);
    setHideSocialBanterInTranscript(false);
  });
});
