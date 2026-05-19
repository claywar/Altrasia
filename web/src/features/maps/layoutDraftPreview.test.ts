import { describe, expect, it } from "vitest";
import { ensurePlanPositions, mergeDraftToGraph } from "./layoutDraftMerge";
import type { SpatialGraph } from "../../api/client";

const baseGraph: SpatialGraph = {
  activeSceneId: "scene-lobby",
  nodes: [
    {
      sceneId: "scene-lobby",
      locationName: "Lobby",
      isActive: true,
      layout: { x: 40, y: 50 },
      presentCount: 1,
      structureId: "hq",
    },
    {
      sceneId: "scene-conference-room",
      locationName: "Conference Room",
      isActive: false,
      layout: { x: 60, y: 40 },
      presentCount: 0,
      structureId: "hq",
    },
  ],
  edges: [],
  structures: [
    {
      structureId: "hq",
      displayName: "Vertex Labs HQ",
      boundary: { shape: "rect", x: 20, y: 20, w: 60, h: 60 },
    },
  ],
};

describe("layoutDraftMerge", () => {
  it("merges draft node positions over base graph", () => {
    const merged = mergeDraftToGraph(
      {
        nodes: [
          { sceneId: "scene-lobby", mapPosition: { x: 10, y: 20 } },
          { sceneId: "scene-conference-room", mapPosition: { x: 80, y: 30 } },
        ],
      },
      baseGraph
    );
    expect(merged?.nodes).toHaveLength(2);
    expect(merged?.nodes.find((n) => n.sceneId === "scene-lobby")?.layout).toEqual({
      x: 10,
      y: 20,
    });
  });

  it("ensurePlanPositions copies layout to planPosition", () => {
    const merged = mergeDraftToGraph(
      { nodes: [{ sceneId: "scene-lobby", mapPosition: { x: 33, y: 44 } }] },
      baseGraph
    );
    const withPlan = ensurePlanPositions(merged!);
    const lobby = withPlan.nodes.find((n) => n.sceneId === "scene-lobby");
    expect(lobby?.planPosition).toEqual({ x: 33, y: 44 });
  });

  it("merges worldMap from site draft", () => {
    const merged = mergeDraftToGraph(
      {
        worldMap: {
          structurePlacements: [
            { structureId: "hq", origin: { x: 48, y: 38 } },
          ],
        },
        nodes: [],
      },
      baseGraph
    );
    expect(merged?.worldMap?.structurePlacements).toHaveLength(1);
  });
});
