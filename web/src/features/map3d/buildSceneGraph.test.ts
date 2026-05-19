import { describe, expect, it } from "vitest";
import type { SpatialGraph } from "../../api/client";
import { buildSceneGraph3D } from "./buildSceneGraph";

describe("buildSceneGraph3D", () => {
  it("derives 3D positions from layout when position3d missing", () => {
    const graph: SpatialGraph = {
      activeSceneId: "a",
      nodes: [
        {
          sceneId: "a",
          locationName: "Hall",
          isActive: true,
          layout: { x: 50, y: 50 },
          presentCount: 0,
          mapLevel: 1,
        },
      ],
      edges: [],
    };
    const sg = buildSceneGraph3D(graph, null);
    expect(sg.rooms[0].position[1]).toBeGreaterThan(2.5);
    expect(sg.structures.length).toBeGreaterThanOrEqual(0);
  });
});
