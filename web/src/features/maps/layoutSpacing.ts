import { footprintBounds, nodeFootprint } from "./layoutGeometry";
import type { MapNode } from "./types";

export type Bbox = { minX: number; minY: number; maxX: number; maxY: number };

export function footprintBox(node: MapNode, pad = 1.5): Bbox {
  return footprintBounds(nodeFootprint(node), pad);
}

export function boxesOverlap(a: Bbox, b: Bbox, gap = 1.25): boolean {
  return !(
    a.maxX + gap <= b.minX ||
    b.maxX + gap <= a.minX ||
    a.maxY + gap <= b.minY ||
    b.maxY + gap <= a.minY
  );
}

/** Minimum gap between same-structure room footprints. */
export function assertNoOverlaps(nodes: MapNode[], minGap = 1.25): string[] {
  const errors: string[] = [];
  const boxes = nodes.map((n) => ({ id: n.sceneId, box: footprintBox(n, 1.5) }));
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      if (boxesOverlap(boxes[i].box, boxes[j].box, minGap)) {
        errors.push(`${boxes[i].id} overlaps ${boxes[j].id}`);
      }
    }
  }
  return errors;
}
