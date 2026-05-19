import { describe, expect, it } from "vitest";
import { rosterByScene, sortWorldRailGroups, type PlaceGroup } from "./rosterByScene";

describe("rosterByScene", () => {
  it("merges atLocation and elsewhere by sceneId", () => {
    const { byScene, unplaced } = rosterByScene({
      atLocation: [
        { characterId: "a", displayName: "Ada", sceneId: "s1" },
      ],
      elsewhere: [
        { characterId: "b", displayName: "Ben", sceneId: "s2", locationName: "Hall" },
      ],
      unplaced: [{ characterId: "c", displayName: "Cy" }],
    });
    expect(byScene.get("s1")?.map((p) => p.displayName)).toEqual(["Ada"]);
    expect(byScene.get("s2")?.map((p) => p.displayName)).toEqual(["Ben"]);
    expect(unplaced.map((p) => p.displayName)).toEqual(["Cy"]);
  });
});

describe("sortWorldRailGroups", () => {
  const groups: PlaceGroup[] = [
    {
      key: "b1",
      title: "House",
      levels: [
        {
          key: "b1-0",
          title: "Ground",
          rows: [
            { scene: { sceneId: "hall", locationName: "Hall" }, actionLabel: "Go" },
            { scene: { sceneId: "kitchen", locationName: "Kitchen" }, actionLabel: null },
          ],
        },
      ],
    },
  ];

  it("hoists active scene and removes duplicate from tree", () => {
    const { activeRow, groupsWithoutActive } = sortWorldRailGroups(groups, "kitchen");
    expect(activeRow?.scene.sceneId).toBe("kitchen");
    const remaining = groupsWithoutActive[0]?.levels[0]?.rows ?? [];
    expect(remaining.map((r) => r.scene.sceneId)).toEqual(["hall"]);
  });

  it("flat mode returns flatRest without active scene", () => {
    const flat: PlaceGroup[] = [
      {
        key: "x",
        title: "X",
        levels: [
          {
            key: "x-0",
            title: "L",
            rows: [
              { scene: { sceneId: "a", locationName: "A" }, actionLabel: null },
              { scene: { sceneId: "b", locationName: "B" }, actionLabel: "Go" },
            ],
          },
        ],
      },
    ];
    const { activeRow, flatRest, groupsWithoutActive } = sortWorldRailGroups(flat, "a", true);
    expect(activeRow?.scene.sceneId).toBe("a");
    expect(flatRest.map((r) => r.scene.sceneId)).toEqual(["b"]);
    expect(groupsWithoutActive).toEqual([]);
  });
});
