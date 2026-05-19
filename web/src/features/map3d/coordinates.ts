/** Single plan 0–100 → WebGL XZ scale for map3d (display only). */
export const PLAN_SCALE = 0.14;

export const FLOOR_HEIGHT = 2.75;

/** Plan center (0–100) to world XZ; Y comes from level or position3d. */
export function planToWorldXz(x: number, y: number): [number, number] {
  return [(x - 50) * PLAN_SCALE, (y - 50) * PLAN_SCALE];
}

export function worldYFromLevel(level: number): number {
  return level * FLOOR_HEIGHT;
}

/** Map API position3d (backend COORD_SCALE) to display XZ when present. */
export function position3dToWorldXz(p: { x: number; y: number; z?: number }): [number, number] {
  const displayScale = PLAN_SCALE / 0.02;
  return [p.x * displayScale, p.y * displayScale];
}

export function referencePointToWorld(p: { x: number; y: number; z: number }): [number, number, number] {
  const [wx, wz] = position3dToWorldXz({ x: p.x, y: p.y });
  return [wx, worldYFromLevel(p.z / 3) || p.z * FLOOR_HEIGHT, wz];
}
