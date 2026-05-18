import { describe, expect, it } from "vitest";
import { computeCorridors, findCorridorForEdge } from "./corridorGeometry";
import { computeViewBox } from "./computeViewBox";
import { routeEdge } from "./edgeRouting";
import { edgeEndpoints, nodeFootprint } from "./layoutGeometry";
import { structureLabels, labelsOverlap } from "./labelLayout";
import { assertNoOverlaps } from "./layoutSpacing";
import type { MapGraph, MapNode } from "./types";

const demoManorRooms: MapNode[] = [
  {
    sceneId: "scene-hall",
    locationName: "Hall",
    isActive: true,
    layout: { x: 49, y: 45 },
    presentCount: 1,
    mapShape: "rect",
    mapSize: { w: 13, h: 9 },
    structureId: "manor",
  },
  {
    sceneId: "scene-kitchen",
    locationName: "Kitchen",
    isActive: false,
    layout: { x: 49, y: 30 },
    presentCount: 0,
    mapShape: "rect",
    mapSize: { w: 11, h: 7 },
    structureId: "manor",
  },
  {
    sceneId: "scene-pantry",
    locationName: "Pantry",
    isActive: false,
    layout: { x: 36, y: 27 },
    presentCount: 0,
    mapShape: "rect",
    mapSize: { w: 6, h: 5 },
    structureId: "manor",
  },
];

const hall: MapNode = {
  sceneId: "hall",
  locationName: "Hall",
  isActive: true,
  layout: { x: 52, y: 45 },
  presentCount: 1,
  mapShape: "rect",
  mapSize: { w: 12, h: 8 },
  structureId: "manor",
};

const kitchen: MapNode = {
  sceneId: "kitchen",
  locationName: "Kitchen",
  isActive: false,
  layout: { x: 46, y: 31 },
  presentCount: 0,
  mapShape: "rect",
  mapSize: { w: 12, h: 8 },
  structureId: "manor",
};

describe("edgeEndpoints", () => {
  it("terminates on footprint rims without stretching", () => {
    const { start, end } = edgeEndpoints(hall, kitchen, {
      exitId: "e1",
      sourceSceneId: "hall",
      targetSceneId: "kitchen",
      label: "door",
      travelSteps: 2,
      direction: "N",
      exitAnchor: "N",
    });
    expect(start.y).toBeLessThan(hall.layout!.y);
    expect(end.y).toBeGreaterThan(kitchen.layout!.y);
    expect(end.y).toBeCloseTo(kitchen.layout!.y + 4, 0);
  });
});

describe("computeCorridors", () => {
  it("creates corridor for interior hall-kitchen connection", () => {
    const edges = [
      {
        exitId: "e1",
        sourceSceneId: "hall",
        targetSceneId: "kitchen",
        label: "door",
        crossesStructure: false,
      },
    ];
    const corridors = computeCorridors([hall, kitchen], edges);
    expect(corridors.length).toBe(1);
    const { start, end } = edgeEndpoints(hall, kitchen, edges[0]);
    expect(findCorridorForEdge(corridors, start, end)).not.toBeNull();
  });
});

describe("routeEdge", () => {
  it("routes around obstacle footprint", () => {
    const start = { x: 50, y: 46 };
    const end = { x: 50, y: 34 };
    const obstacle = nodeFootprint({
      sceneId: "mid",
      locationName: "Mid",
      isActive: false,
      layout: { x: 50, y: 40 },
      presentCount: 0,
    });
    const routed = routeEdge(start, end, [obstacle]);
    expect(routed.pathD.length).toBeGreaterThan(10);
    expect(routed.points.length).toBeGreaterThanOrEqual(2);
  });

  it("uses bezier for cross-structure outdoor paths", () => {
    const routed = routeEdge(
      { x: 58, y: 45 },
      { x: 24, y: 78 },
      [],
      0,
      { crossesStructure: true }
    );
    expect(routed.outdoor).toBe(true);
    expect(routed.pathD).toMatch(/^M .+ (Q|C) .+/);
  });

  it("routes interior through corridor when provided", () => {
    const edges = [
      {
        exitId: "e1",
        sourceSceneId: "hall",
        targetSceneId: "kitchen",
        label: "door",
        crossesStructure: false,
      },
    ];
    const corridors = computeCorridors([hall, kitchen], edges);
    const { start, end } = edgeEndpoints(hall, kitchen, edges[0]);
    const routed = routeEdge(start, end, [], 0, {
      corridors,
      interiorOnly: true,
    });
    expect(routed.points.length).toBeGreaterThanOrEqual(3);
  });
});

describe("computeViewBox", () => {
  it("fits neighborhood around active scene", () => {
    const graph: MapGraph = {
      activeSceneId: "hall",
      nodes: [hall, kitchen],
      edges: [
        {
          exitId: "e1",
          sourceSceneId: "hall",
          targetSceneId: "kitchen",
          label: "door",
        },
      ],
    };
    const vb = computeViewBox(graph, "neighborhood");
    expect(vb.w).toBeLessThan(80);
    expect(vb.x).toBeLessThan(45);
  });
});

describe("layoutSpacing", () => {
  it("demo manor rooms do not overlap", () => {
    const overlaps = assertNoOverlaps(demoManorRooms, 1.5);
    expect(overlaps).toEqual([]);
  });
});

describe("labelLayout", () => {
  it("places structure titles without overlapping each other", () => {
    const graph: MapGraph = {
      activeSceneId: "hall",
      nodes: [hall, kitchen],
      structures: [
        {
          structureId: "manor",
          displayName: "Manor House",
          kind: "building",
          containsActiveScene: true,
        },
        {
          structureId: "keep",
          displayName: "Round Keep",
          kind: "building",
          boundary: { shape: "rect", x: 70, y: 40, w: 20, h: 20 },
        },
      ],
      edges: [],
    };
    const labels = structureLabels(graph.structures!, graph.nodes);
    expect(labels.length).toBe(2);
    if (labels.length === 2) {
      expect(labelsOverlap(labels[0], labels[1], 3)).toBe(false);
    }
  });
});
