import type { SpatialGraph } from "../../api/client";

export type MapNode = SpatialGraph["nodes"][number] & {
  mapZone?: string;
  mapSize?: { w?: number; h?: number };
  dimmed?: boolean;
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
  } | null;
};

export type MapGraph = Omit<SpatialGraph, "nodes" | "edges" | "structures"> & {
  nodes: MapNode[];
  edges: MapEdge[];
  structures?: MapStructure[];
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
