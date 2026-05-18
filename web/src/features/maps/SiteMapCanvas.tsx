import { useCallback, useRef, useState } from "react";
import type { SpatialGraph } from "../../api/client";
import { MapRenderer } from "./MapRenderer";
import { structureEnvelope } from "./layoutGeometry";
import type { MapNode } from "./types";

type Props = {
  graph: SpatialGraph | null;
  onClose: () => void;
  onEnhanceLayout?: () => void;
};

const VB = 100;

export function SiteMapCanvas({ graph, onClose, onEnhanceLayout }: Props) {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fitWorld = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  const fitActiveStructure = useCallback(() => {
    if (!graph) return;
    const active = graph.nodes.find((n) => n.isActive);
    const sid = active?.structureId;
    if (!sid) {
      fitWorld();
      return;
    }
    const st = graph.structures?.find((s) => s.structureId === sid);
    const env = structureEnvelope(sid, graph.nodes as MapNode[], st?.boundary);
    if (!env) {
      fitWorld();
      return;
    }
    const w = env.maxX - env.minX;
    const h = env.maxY - env.minY;
    const cx = (env.minX + env.maxX) / 2;
    const cy = (env.minY + env.maxY) / 2;
    const scale = Math.min(VB / Math.max(w, 20), VB / Math.max(h, 20)) * 0.85;
    setZoom(scale);
    setPan({ x: VB / 2 - cx * scale, y: VB / 2 - cy * scale });
  }, [graph, fitWorld]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(4, Math.max(0.5, z * delta)));
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    dragRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const scale = rect.width / VB;
    const dx = (e.clientX - dragRef.current.x) / scale;
    const dy = (e.clientY - dragRef.current.y) / scale;
    setPan({ x: dragRef.current.panX + dx, y: dragRef.current.panY + dy });
  };

  const onPointerUp = () => {
    dragRef.current = null;
  };

  const viewportRect = {
    x: -pan.x / zoom + (VB - VB / zoom) / 2,
    y: -pan.y / zoom + (VB - VB / zoom) / 2,
    w: VB / zoom,
    h: VB / zoom,
  };

  return (
    <div
      className="map-overlay map-canvas map-canvas--site"
      role="dialog"
      aria-label="World map canvas"
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <header className="map-overlay-header">
        <h2>World map</h2>
        <nav className="map-mode-tabs" aria-label="Map view mode">
          <span className="map-mode-tabs__active">Site</span>
          <span className="map-mode-tabs__disabled" title="Coming soon">
            Structure
          </span>
          <span className="map-mode-tabs__disabled" title="Coming soon">
            Floor
          </span>
          <span className="map-mode-tabs__disabled" title="Coming soon">
            Stack
          </span>
        </nav>
        <div className="map-overlay-actions">
          <button type="button" onClick={fitWorld}>
            Fit world
          </button>
          <button type="button" onClick={fitActiveStructure}>
            Fit structure
          </button>
          {onEnhanceLayout && (
            <button type="button" onClick={onEnhanceLayout}>
              Enhance layout
            </button>
          )}
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>
      </header>
      <div className="map-canvas-body map-canvas-body--site">
        <div
          ref={containerRef}
          className="site-map-viewport"
          onWheel={onWheel}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        >
          <div
            className="site-map-transform"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "center center",
            }}
          >
            <MapRenderer
              graph={graph}
              showCompass
              showSiteUnderlay
              showScaleBar
              className="site-map-main"
              viewFit="full"
            />
          </div>
        </div>
        <aside className="map-pip" aria-label="Mini-map inset">
          <MapRenderer
            graph={graph}
            viewportRect={viewportRect}
            className="map-pip-inner"
            viewFit="neighborhood"
            showZones={false}
          />
        </aside>
        {graph?.structures && graph.structures.length > 0 && (
          <aside className="map-canvas-structures">
            <h3>Structures</h3>
            <ul>
              {graph.structures.map((s) => (
                <li key={s.structureId}>
                  {s.displayName}
                  {s.containsActiveScene ? " (active)" : ""}
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>
    </div>
  );
}
