import { describe, expect, it } from "vitest";
import {
  isVerticalEdge,
  levelsForStructure,
  personaOffSitePlan,
  prepareGraphForView,
  SITE_DISPLAY_LEVEL,
  stackPlatesForStructure,
} from "./floorLevels";
import type { MapGraph, MapNode } from "./types";

const manorGround: MapNode = {
  sceneId: "hall",
  locationName: "Hall",
  isActive: true,
  layout: { x: 50, y: 50 },
  presentCount: 1,
  structureId: "manor",
  levelIndex: 0,
  mapZone: "Ground floor",
};

const manorUpper: MapNode = {
  sceneId: "gallery",
  locationName: "Upper Gallery",
  isActive: false,
  layout: { x: 50, y: 50 },
  presentCount: 0,
  structureId: "manor",
  levelIndex: 1,
  levelLabel: "Upper gallery",
};

const courtyard: MapNode = {
  sceneId: "yard",
  locationName: "Courtyard",
  isActive: false,
  layout: { x: 20, y: 80 },
  presentCount: 0,
  structureId: "bailey",
};

const graph: MapGraph = {
  activeSceneId: "hall",
  nodes: [manorGround, manorUpper, courtyard],
  edges: [
    {
      exitId: "stairs",
      sourceSceneId: "hall",
      targetSceneId: "gallery",
      label: "Stairs up",
      kind: "stairs",
    },
    {
      exitId: "path",
      sourceSceneId: "hall",
      targetSceneId: "yard",
      label: "To yard",
      crossesStructure: true,
    },
  ],
  structures: [
    { structureId: "manor", displayName: "Manor", containsActiveScene: true },
    { structureId: "bailey", displayName: "Bailey" },
  ],
};

describe("floorLevels", () => {
  it("site view always shows ground floor only", () => {
    const upperActive: MapGraph = {
      ...graph,
      activeSceneId: "gallery",
      nodes: [
        { ...manorGround, isActive: false },
        { ...manorUpper, isActive: true },
        courtyard,
      ],
    };
    const { graph: view, offPlanActive } = prepareGraphForView(upperActive, "site");
    expect(view.nodes.map((n) => n.sceneId)).toEqual(["hall", "yard"]);
    expect(offPlanActive?.sceneId).toBe("gallery");
    expect(personaOffSitePlan(upperActive)).toBe(true);
  });

  it("site view does not add ghost footprints", () => {
    const prep = prepareGraphForView(graph, "site");
    expect(prep.graph.nodes.some((n) => n.ghost)).toBe(false);
    expect(prep.focusLevel).toBe(SITE_DISPLAY_LEVEL);
  });

  it("structure view adds ghost footprints for other floors", () => {
    const prep = prepareGraphForView(graph, "structure", { selectedLevel: 0 });
    expect(prep.graph.nodes.some((n) => n.ghost && n.sceneId === "gallery")).toBe(true);
    expect(prep.graph.nodes.some((n) => !n.ghost && n.sceneId === "hall")).toBe(true);
  });

  it("floor view isolates selected level", () => {
    const { graph: view } = prepareGraphForView(graph, "floor", { selectedLevel: 1 });
    expect(view.nodes.map((n) => n.sceneId)).toEqual(["gallery"]);
  });

  it("detects vertical edges", () => {
    expect(isVerticalEdge({ ...graph.edges[0], kind: "stairs" })).toBe(true);
    expect(levelsForStructure(graph.nodes, "manor")).toEqual([0, 1]);
    expect(stackPlatesForStructure(graph, "manor")).toHaveLength(2);
  });
});

describe("manor three-level stack", () => {
  const cellar: MapNode = {
    sceneId: "cellar",
    locationName: "Cellar",
    isActive: false,
    layout: { x: 49, y: 45 },
    presentCount: 0,
    structureId: "manor",
    levelIndex: -1,
  };

  const manorGraph: MapGraph = {
    ...graph,
    nodes: [...graph.nodes, cellar],
    edges: [
      ...graph.edges,
      {
        exitId: "ladder",
        sourceSceneId: "hall",
        targetSceneId: "cellar",
        label: "Ladder down",
        kind: "ladder",
      },
    ],
  };

  it("builds three stack plates for manor", () => {
    expect(levelsForStructure(manorGraph.nodes, "manor")).toEqual([-1, 0, 1]);
    expect(stackPlatesForStructure(manorGraph, "manor")).toHaveLength(3);
  });
});
