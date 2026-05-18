/** Layer visibility toggles for MapRenderer / MapConsole. */
export type MapLayerVisibility = {
  structures: boolean;
  labels: boolean;
  zones: boolean;
  edges: boolean;
  compass: boolean;
  scaleBar: boolean;
  underlay: boolean;
  zoneBands: boolean;
  fog: boolean;
};

export const DEFAULT_MAP_LAYERS: MapLayerVisibility = {
  structures: true,
  labels: true,
  zones: true,
  edges: true,
  compass: true,
  scaleBar: true,
  underlay: true,
  zoneBands: true,
  fog: false,
};

export type MapLayerKey = keyof MapLayerVisibility;

export const MAP_LAYER_LABELS: Record<MapLayerKey, string> = {
  structures: "Structures",
  labels: "Labels",
  zones: "Zones",
  edges: "Paths",
  compass: "Compass",
  scaleBar: "Scale",
  underlay: "Terrain",
  zoneBands: "Floor bands",
  fog: "Focus nearby",
};
