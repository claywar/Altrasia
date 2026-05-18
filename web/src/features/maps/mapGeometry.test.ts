import { describe, expect, it } from "vitest";
import { computeViewBox } from "./computeViewBox";
import { routeEdge } from "./edgeRouting";
import { edgeEndpoints, nodeFootprint } from "./layoutGeometry";
import type { MapGraph, MapNode } from "./types";

const hall: MapNode = {
  sceneId: "hall",
  locationName: "Hall",
  isActive: true,
  layout: { x: 50, y: 50 },
  presentCount: 1,
  mapShape: "rect",
  mapSize: { w: 12, h: 8 },
};

const kitchen: MapNode = {
  sceneId: "kitchen",
  locationName: "Kitchen",
  isActive: false,
  layout: { x: 50, y: 30 },
  presentCount: 0,
  mapShape: "rect",
  mapSize: { w: 12, h: 8 },
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
