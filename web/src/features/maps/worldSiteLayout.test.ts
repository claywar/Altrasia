import { describe, expect, it } from "vitest";
import { readPlanPosition } from "./diagramModel";
import { applySiteLayout, structureCentroid } from "./worldSiteLayout";
import type { MapGraph, MapNode } from "./types";

const manorNodes: MapNode[] = [
  {
    sceneId: "scene-hall",
    locationName: "Hall",
    isActive: true,
    layout: { x: 49, y: 45 },
    presentCount: 1,
    structureId: "manor",
    levelIndex: 0,
  },
  {
    sceneId: "scene-kitchen",
    locationName: "Kitchen",
    isActive: false,
    layout: { x: 49, y: 30 },
    presentCount: 0,
    structureId: "manor",
    levelIndex: 0,
  },
];

const graph: MapGraph = {
  activeSceneId: "scene-hall",
  nodes: manorNodes,
  edges: [],
  structures: [
    {
      structureId: "manor",
      displayName: "Manor House",
      boundary: {
        shape: "polygon",
        vertices: [
          { x: 28, y: 22 },
          { x: 66, y: 22 },
          { x: 66, y: 58 },
          { x: 28, y: 58 },
        ],
      },
    },
  ],
  worldMap: {
    structurePlacements: [{ structureId: "manor", origin: { x: 48, y: 38 } }],
  },
};

describe("worldSiteLayout", () => {
  it("computes structure centroid from boundary", () => {
    const c = structureCentroid(graph.structures![0]!.boundary, manorNodes);
    expect(c.x).toBeCloseTo(47, 0);
    expect(c.y).toBeCloseTo(40, 0);
  });

  it("moves scenes so structure centroid aligns to placement origin", () => {
    const out = applySiteLayout(graph);
    const hall = out.nodes.find((n) => n.sceneId === "scene-hall")!;
    const centroid = structureCentroid(
      out.structures![0]!.boundary,
      out.nodes.filter((n) => n.structureId === "manor")
    );
    expect(centroid.x).toBeCloseTo(48, 0.5);
    expect(centroid.y).toBeCloseTo(38, 0.5);
    expect(readPlanPosition(hall).x).toBeGreaterThan(40);
  });

  it("no-ops without placements", () => {
    const g = { ...graph, worldMap: undefined };
    expect(applySiteLayout(g)).toBe(g);
  });
});
