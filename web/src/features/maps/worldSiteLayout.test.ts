import { describe, expect, it } from "vitest";
import { readPlanPosition } from "./diagramModel";
import { applySiteLayout, structureCentroid } from "./worldSiteLayout";
import type { MapGraph, MapNode } from "./types";

const hqNodes: MapNode[] = [
  {
    sceneId: "scene-lobby",
    locationName: "Lobby",
    isActive: true,
    layout: { x: 50, y: 48 },
    presentCount: 1,
    structureId: "hq",
    levelIndex: 0,
  },
  {
    sceneId: "scene-conference-room",
    locationName: "Conference Room",
    isActive: false,
    layout: { x: 68, y: 52 },
    presentCount: 0,
    structureId: "hq",
    levelIndex: 0,
  },
];

const graph: MapGraph = {
  activeSceneId: "scene-lobby",
  nodes: hqNodes,
  edges: [],
  structures: [
    {
      structureId: "hq",
      displayName: "Vertex Labs HQ",
      boundary: {
        shape: "polygon",
        vertices: [
          { x: 22, y: 20 },
          { x: 78, y: 20 },
          { x: 78, y: 62 },
          { x: 22, y: 62 },
        ],
      },
    },
  ],
  worldMap: {
    structurePlacements: [{ structureId: "hq", origin: { x: 48, y: 40 } }],
  },
};

describe("worldSiteLayout", () => {
  it("computes structure centroid from boundary", () => {
    const c = structureCentroid(graph.structures![0]!.boundary, hqNodes);
    expect(c.x).toBeCloseTo(50, 0);
    expect(c.y).toBeCloseTo(41, 0);
  });

  it("moves scenes so structure centroid aligns to placement origin", () => {
    const out = applySiteLayout(graph);
    const lobby = out.nodes.find((n) => n.sceneId === "scene-lobby")!;
    const centroid = structureCentroid(
      out.structures![0]!.boundary,
      out.nodes.filter((n) => n.structureId === "hq")
    );
    expect(centroid.x).toBeCloseTo(48, 0.5);
    expect(centroid.y).toBeCloseTo(40, 0.5);
    expect(readPlanPosition(lobby).x).toBeGreaterThan(40);
  });

  it("no-ops without placements", () => {
    const g = { ...graph, worldMap: undefined };
    expect(applySiteLayout(g)).toBe(g);
  });
});
