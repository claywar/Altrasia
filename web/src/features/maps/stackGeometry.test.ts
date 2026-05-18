import { describe, expect, it } from "vitest";
import {
  computeStackAnchorX,
  connectorLabel,
  layoutStackPlates,
  stackConnectors,
  stackPlatesDescending,
  verticalAnchorSceneIds,
} from "./stackGeometry";
import { stackPlatesForStructure, verticalLinksForStructure } from "./floorLevels";
import type { MapEdge, MapGraph, MapNode } from "./types";

const hall: MapNode = {
  sceneId: "hall",
  locationName: "Hall",
  isActive: true,
  layout: { x: 49, y: 45 },
  planPosition: { x: 49, y: 45 },
  presentCount: 1,
  structureId: "manor",
  levelIndex: 0,
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
};

const graph: MapGraph = {
  activeSceneId: "hall",
  nodes: [hall, kitchen, gallery, cellar],
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

describe("stackGeometry", () => {
  it("orders plates high to low", () => {
    const plates = stackPlatesForStructure(graph, "manor");
    const ordered = stackPlatesDescending(plates);
    expect(ordered.map((p) => p.level)).toEqual([1, 0, -1]);
  });

  it("lays out three plates with connectors between levels", () => {
    const plates = stackPlatesForStructure(graph, "manor");
    const vertical = verticalLinksForStructure(graph, "manor");
    expect(vertical).toHaveLength(2);
    const layout = layoutStackPlates(plates, vertical, "iso");
    expect(layout.layouts).toHaveLength(3);
    expect(layout.layouts[0]!.level).toBe(1);
    expect(layout.layouts[2]!.level).toBe(-1);

    const nodeById = new Map(graph.nodes.map((n) => [n.sceneId, n]));
    const connectors = stackConnectors(layout.layouts, vertical, nodeById, "iso");
    expect(connectors).toHaveLength(2);
    expect(connectors[0]!.y2).toBeLessThan(connectors[0]!.y1);
    expect(layout.layouts[0]!.scale).toBeGreaterThan(0);
    expect(layout.layouts[0]!.scaledW).toBe(58);
    expect(connectorLabel(vertical[0] as MapEdge, 0, 1)).toBe("STAIRS UP");
    expect(connectorLabel(vertical[1] as MapEdge, 0, -1)).toBe("LADDER DOWN");
  });

  it("aligns vertical anchor scenes on shared stack X", () => {
    const vertical = verticalLinksForStructure(graph, "manor");
    const anchorIds = verticalAnchorSceneIds(vertical);
    const anchorX = computeStackAnchorX(graph.nodes, anchorIds);
    expect(anchorX).toBe(49);
  });
});
