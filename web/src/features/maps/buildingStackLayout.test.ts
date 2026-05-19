import { describe, expect, it } from "vitest";
import { layoutUnifiedBuildingStack, planToUnifiedStack } from "./buildingStackLayout";
import { stackPlatesForStructure, verticalLinksForStructure } from "./floorLevels";
import type { MapGraph, MapNode } from "./types";

const hall: MapNode = {
  sceneId: "hall",
  locationName: "Hall",
  isActive: true,
  layout: { x: 49, y: 45 },
  planPosition: { x: 49, y: 45 },
  presentCount: 1,
  structureId: "manor",
  levelIndex: 0,
  mapSize: { w: 13, h: 9 },
};

const kitchen: MapNode = {
  sceneId: "kitchen",
  locationName: "Kitchen",
  isActive: false,
  layout: { x: 49, y: 30 },
  planPosition: { x: 49, y: 30 },
  presentCount: 0,
  structureId: "manor",
  levelIndex: 0,
  mapSize: { w: 11, h: 7 },
};

const gallery: MapNode = {
  sceneId: "gallery",
  locationName: "Upper Gallery",
  isActive: false,
  layout: { x: 49, y: 45 },
  planPosition: { x: 49, y: 45 },
  presentCount: 0,
  structureId: "manor",
  levelIndex: 1,
  mapSize: { w: 14, h: 6 },
};

const cellar: MapNode = {
  sceneId: "cellar",
  locationName: "Cellar",
  isActive: false,
  layout: { x: 49, y: 45 },
  planPosition: { x: 49, y: 45 },
  presentCount: 0,
  structureId: "manor",
  levelIndex: -1,
  mapSize: { w: 10, h: 8 },
};

const graph: MapGraph = {
  activeSceneId: "hall",
  nodes: [hall, kitchen, gallery, cellar],
  structures: [
    {
      structureId: "manor",
      displayName: "Manor House",
      kind: "building",
      boundary: {
        vertices: [
          { x: 28, y: 22 },
          { x: 66, y: 22 },
          { x: 66, y: 35 },
          { x: 58, y: 35 },
          { x: 58, y: 58 },
          { x: 28, y: 58 },
        ],
      },
    },
  ],
  edges: [
    {
      exitId: "stairs-up",
      sourceSceneId: "hall",
      targetSceneId: "gallery",
      label: "Stairs up",
      kind: "stairs",
    },
    {
      exitId: "ladder-down",
      sourceSceneId: "hall",
      targetSceneId: "cellar",
      label: "Ladder down",
      kind: "ladder",
    },
  ],
};

describe("buildingStackLayout", () => {
  it("aligns the same plan point vertically across floors", () => {
    const plates = stackPlatesForStructure(graph, "manor");
    const vertical = verticalLinksForStructure(graph, "manor");
    const structure = graph.structures![0];
    const layout = layoutUnifiedBuildingStack(plates, structure, vertical)!;

    expect(layout.floors).toHaveLength(3);
    expect(layout.shellPath).toBeTruthy();

    const ground = layout.floors.find((f) => f.level === 0)!;
    const upper = layout.floors.find((f) => f.level === 1)!;
    const groundHall = planToUnifiedStack(layout, 49, 45, ground.stackY);
    const upperHall = planToUnifiedStack(layout, 49, 45, upper.stackY);

    expect(groundHall.x).toBeCloseTo(upperHall.x, 1);
    expect(upperHall.y).toBeLessThan(groundHall.y);
  });
});
