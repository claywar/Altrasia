import { useCallback, useRef, useState } from "react";
import { nodeFootprint, structureEnvelope } from "./layoutGeometry";
import type { MapNode } from "./types";
import type { SpatialGraph } from "../../api/client";

const VB = 100;
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
/** Pan state is screen pixels (matches CSS translate on site-map-transform). */
const KEY_PAN_PX = 24;

export type MapViewportState = {
  pan: { x: number; y: number };
  zoom: number;
  cursorMap: { x: number; y: number } | null;
};

export function useMapViewport(graph: SpatialGraph | null) {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [cursorMap, setCursorMap] = useState<{ x: number; y: number } | null>(null);
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const pinchRef = useRef<{ dist: number; zoom: number } | null>(null);

  const fitWorld = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  /** Fit entire site — all rooms and structure envelopes with generous padding. */
  const fitSite = useCallback(() => {
    if (!graph?.nodes.length) {
      fitWorld();
      return;
    }
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const n of graph.nodes) {
      const fp = nodeFootprint(n as MapNode);
      minX = Math.min(minX, fp.cx - fp.w / 2);
      minY = Math.min(minY, fp.cy - fp.h / 2);
      maxX = Math.max(maxX, fp.cx + fp.w / 2);
      maxY = Math.max(maxY, fp.cy + fp.h / 2);
    }
    for (const st of graph.structures ?? []) {
      const env = structureEnvelope(st.structureId, graph.nodes as MapNode[], st.boundary);
      if (!env) continue;
      minX = Math.min(minX, env.minX);
      minY = Math.min(minY, env.minY);
      maxX = Math.max(maxX, env.maxX);
      maxY = Math.max(maxY, env.maxY);
    }
    if (!Number.isFinite(minX)) {
      fitWorld();
      return;
    }
    const w = Math.max(maxX - minX, 24);
    const h = Math.max(maxY - minY, 24);
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const scale = Math.min(VB / w, VB / h) * 0.72;
    setZoom(scale);
    setPan({ x: VB / 2 - cx * scale, y: VB / 2 - cy * scale });
  }, [graph, fitWorld]);

  const fitStructure = useCallback(
    (structureId: string) => {
      if (!graph) return;
      const st = graph.structures?.find((s) => s.structureId === structureId);
      const env = structureEnvelope(structureId, graph.nodes as MapNode[], st?.boundary);
      if (!env) {
        fitWorld();
        return;
      }
      const w = env.maxX - env.minX;
      const h = env.maxY - env.minY;
      const cx = (env.minX + env.maxX) / 2;
      const cy = (env.minY + env.maxY) / 2;
      const scale = Math.min(VB / Math.max(w, 20), VB / Math.max(h, 20)) * 0.48;
      setZoom(scale);
      setPan({ x: VB / 2 - cx * scale, y: VB / 2 - cy * scale });
    },
    [graph, fitWorld]
  );

  const fitActiveStructure = useCallback(() => {
    const active = graph?.nodes.find((n) => n.isActive);
    if (active?.structureId) fitStructure(active.structureId);
    else fitWorld();
  }, [graph, fitStructure, fitWorld]);

  const fitScene = useCallback(
    (sceneId: string) => {
      const node = graph?.nodes.find((n) => n.sceneId === sceneId);
      if (!node?.layout) {
        fitWorld();
        return;
      }
      const scale = 2.2;
      setZoom(scale);
      setPan({
        x: VB / 2 - node.layout.x * scale,
        y: VB / 2 - node.layout.y * scale,
      });
    },
    [graph, fitWorld]
  );

  const zoomBy = useCallback((factor: number) => {
    setZoom((z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z * factor)));
  }, []);

  const zoomIn = useCallback(() => zoomBy(1.15), [zoomBy]);
  const zoomOut = useCallback(() => zoomBy(1 / 1.15), [zoomBy]);

  const onWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        zoomBy(e.deltaY > 0 ? 0.9 : 1.1);
        return;
      }
      zoomBy(e.deltaY > 0 ? 0.92 : 1.08);
    },
    [zoomBy]
  );

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return;
      if ((e.target as HTMLElement).closest(".map-viewport-guide")) return;
      dragRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    },
    [pan]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent, container: HTMLDivElement | null) => {
      if (dragRef.current) {
        const dx = e.clientX - dragRef.current.x;
        const dy = e.clientY - dragRef.current.y;
        setPan({ x: dragRef.current.panX + dx, y: dragRef.current.panY + dy });
      }
      if (container) {
        const rect = container.getBoundingClientRect();
        const scale = rect.width / VB;
        const mx = (e.clientX - rect.left) / scale;
        const my = (e.clientY - rect.top) / scale;
        const mapX = (mx - pan.x) / zoom + (VB - VB / zoom) / 2;
        const mapY = (my - pan.y) / zoom + (VB - VB / zoom) / 2;
        if (mapX >= 0 && mapX <= VB && mapY >= 0 && mapY <= VB) {
          setCursorMap({ x: Math.round(mapX), y: Math.round(mapY) });
        } else {
          setCursorMap(null);
        }
      }
    },
    [pan, zoom]
  );

  const onPointerUp = useCallback(() => {
    dragRef.current = null;
    pinchRef.current = null;
  }, []);

  const onTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 2) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        pinchRef.current = { dist: Math.hypot(dx, dy), zoom };
      }
    },
    [zoom]
  );

  const onTouchMove = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 2 && pinchRef.current) {
      e.preventDefault();
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      const ratio = dist / pinchRef.current.dist;
      setZoom(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, pinchRef.current.zoom * ratio)));
    }
  }, []);

  const panByKeys = useCallback((dx: number, dy: number) => {
    setPan((p) => ({
      x: p.x + dx * KEY_PAN_PX,
      y: p.y + dy * KEY_PAN_PX,
    }));
  }, []);

  const viewportRect = {
    x: -pan.x / zoom + (VB - VB / zoom) / 2,
    y: -pan.y / zoom + (VB - VB / zoom) / 2,
    w: VB / zoom,
    h: VB / zoom,
  };

  return {
    pan,
    zoom,
    cursorMap,
    viewportRect,
    zoomPercent: Math.round(zoom * 100),
    fitWorld,
    fitSite,
    fitStructure,
    fitActiveStructure,
    fitScene,
    zoomIn,
    zoomOut,
    onWheel,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onTouchStart,
    onTouchMove,
    panByKeys,
    VB,
  };
}
