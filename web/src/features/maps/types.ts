import type { SpatialGraph } from "../../api/client";

export type MapNode = SpatialGraph["nodes"][number] & {
  mapZone?: string;
  mapSize?: { w?: number; h?: number };
  mapLevel?: number;
  levelLabel?: string;
  dimmed?: boolean;
  ghost?: boolean;
};

export type MapEdge = SpatialGraph["edges"][number] & {
  direction?: string;
  doorState?: string;
  kind?: string;
  crossesStructure?: boolean;
};

export type MapStructure = NonNullable<SpatialGraph["structures"]>[number] & {
  boundary?: {
    shape?: string;
    vertices?: Array<{ x: number; y: number }>;
    x?: number;
    y?: number;
    w?: number;
    h?: number;
    cx?: number;
    cy?: number;
    r?: number;
    cornerRadius?: number;
  } | null;
};

export type MapGraph = Omit<SpatialGraph, "nodes" | "edges" | "structures"> & {
  nodes: MapNode[];
  edges: MapEdge[];
  structures?: MapStructure[];
  siteLayoutApplied?: boolean;
};

export type Footprint = {
  cx: number;
  cy: number;
  w: number;
  h: number;
  shape: string;
  sceneId?: string;
};

export type Point = { x: number; y: number };

export type CorridorSegment = {
  id: string;
  cx: number;
  cy: number;
  x: number;
  y: number;
  w: number;
  h: number;
  start: Point;
  end: Point;
};
