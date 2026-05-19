import { describe, expect, it } from "vitest";
import {
  buildMergedExits,
  exitKnockAffordance,
  mergeExitWithGraphEdge,
  pendingKnockTargets,
  type ExitRow,
} from "./exitAffordances";

const door: ExitRow = {
  exitId: "e1",
  label: "Kitchen",
  targetSceneId: "kitchen",
  kind: "door",
};

describe("exitKnockAffordance", () => {
  it("hides knock for non-door exits", () => {
    const stairs: ExitRow = {
      exitId: "s1",
      label: "Stairs",
      targetSceneId: "up",
      kind: "stairs",
    };
    expect(exitKnockAffordance(stairs).showKnock).toBe(false);
  });

  it("shows knock for closed door", () => {
    const aff = exitKnockAffordance({ ...door, doorState: "closed" });
    expect(aff.showKnock).toBe(true);
    expect(aff.label).toBe("Knock");
    expect(aff.disabled).toBe(false);
  });

  it("defaults door without doorState to closed", () => {
    expect(exitKnockAffordance(door).showKnock).toBe(true);
  });

  it("shows knock for unlocked door", () => {
    const aff = exitKnockAffordance({ ...door, doorState: "unlocked" });
    expect(aff.showKnock).toBe(true);
    expect(aff.statusChip).toBe("Unlocked");
  });

  it("hides knock for open door with status chip", () => {
    const aff = exitKnockAffordance({ ...door, doorState: "open" });
    expect(aff.showKnock).toBe(false);
    expect(aff.statusChip).toBe("Open");
  });

  it("hides knock for broken door", () => {
    const aff = exitKnockAffordance({ ...door, doorState: "broken" });
    expect(aff.showKnock).toBe(false);
    expect(aff.statusChip).toBe("Broken");
  });

  it("shows disabled Pending when knock already sent", () => {
    const pending = new Set(["kitchen"]);
    const aff = exitKnockAffordance({ ...door, doorState: "closed" }, pending);
    expect(aff.showKnock).toBe(true);
    expect(aff.label).toBe("Pending");
    expect(aff.disabled).toBe(true);
  });
});

describe("mergeExitWithGraphEdge", () => {
  it("fills doorState and kind from graph edge", () => {
    const merged = mergeExitWithGraphEdge(
      { exitId: "e1", label: "Hall", targetSceneId: "hall" },
      [
        {
          exitId: "e1",
          sourceSceneId: "lobby",
          targetSceneId: "hall",
          label: "Hall",
          kind: "door",
          doorState: "closed",
        },
      ],
      "lobby"
    );
    expect(merged.kind).toBe("door");
    expect(merged.doorState).toBe("closed");
  });
});

describe("buildMergedExits", () => {
  it("parses exitsJson and merges graph", () => {
    const json = JSON.stringify([
      { exitId: "e1", label: "Kitchen", targetSceneId: "kitchen", kind: "door" },
    ]);
    const exits = buildMergedExits(json, null, "lobby");
    expect(exits[0].kind).toBe("door");
  });
});

describe("pendingKnockTargets", () => {
  it("collects pending knock targets from active scene", () => {
    const set = pendingKnockTargets(
      [
        {
          sourceSceneId: "lobby",
          targetSceneId: "kitchen",
          kind: "knock",
          status: "pending",
        },
        {
          sourceSceneId: "hall",
          targetSceneId: "kitchen",
          kind: "knock",
          status: "pending",
        },
      ],
      "lobby"
    );
    expect(set.has("kitchen")).toBe(true);
    expect(set.size).toBe(1);
  });
});
