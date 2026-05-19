import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type NavigationRoute, type SpatialGraph } from "../../api/client";
import { FocusTrap } from "../../ui/FocusTrap";
import {
  activeLevel,
  activeStructureId,
  type MapViewMode,
} from "../maps/floorLevels";
import { mapViewCapabilities } from "../maps/mapNavigation";
import type { MapGraph } from "../maps/types";
import { buildSceneGraph3D, type SceneGraphViewFilter } from "./buildSceneGraph";
import { EdgeTubes } from "./EdgeTubes";
import { MapEnhanceDrawer } from "./MapEnhanceDrawer";
import { MapFloatingHud } from "./MapFloatingHud";
import { MapFloorPlanSlide } from "./MapFloorPlanSlide";
import { MapSelectionChip } from "./MapSelectionChip";
import { MapTravelRail } from "./MapTravelRail";
import { ReferencePointMarkers } from "./ReferencePointMarkers";
import { RoomVolume } from "./RoomVolume";
import { SiteGround } from "./SiteGround";
import { StairConnectors } from "./StairConnectors";
import { StructureShell } from "./StructureShell";
import { WorldScene } from "./WorldScene";

type Props = {
  graph: SpatialGraph | null;
  worldId: string;
  layoutDesignMode?: boolean;
  onClose: () => void;
  onSwitchScene?: (sceneId: string) => void;
  onTravel?: (targetSceneId: string) => void;
  onWalkRoute?: (targetSceneId: string) => void | Promise<void>;
  onKnock?: (targetSceneId: string) => void;
  highlightedExitId?: string | null;
  onExitHover?: (exitId: string | null) => void;
  onGraphRefresh?: () => void;
};

export type MapViewScope = "site" | "building";

function viewFilterForScope(mg: MapGraph, scope: MapViewScope): SceneGraphViewFilter {
  if (scope === "site") {
    return { context: "site" };
  }
  const structId = activeStructureId(mg);
  return {
    context: "floor",
    structureId: structId ?? undefined,
    level: activeLevel(mg),
  };
}

export function SpatialCanvasPlay({
  graph,
  worldId,
  layoutDesignMode = true,
  onClose,
  onSwitchScene,
  onTravel,
  onWalkRoute,
  onKnock,
  onGraphRefresh,
}: Props) {
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [route, setRoute] = useState<NavigationRoute | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [floorPlanOpen, setFloorPlanOpen] = useState(false);
  const [enhanceOpen, setEnhanceOpen] = useState(false);
  const [previewGraph, setPreviewGraph] = useState<SpatialGraph | null>(null);
  const [viewScope, setViewScope] = useState<MapViewScope>("site");

  const displayGraph = previewGraph ?? graph;
  const activeId = displayGraph?.activeSceneId ?? null;

  const viewFilter = useMemo(() => {
    if (!displayGraph || floorPlanOpen) return undefined;
    return viewFilterForScope(displayGraph as MapGraph, viewScope);
  }, [displayGraph, floorPlanOpen, viewScope]);

  const sceneData = useMemo(
    () => (displayGraph && !floorPlanOpen ? buildSceneGraph3D(displayGraph, route, viewFilter) : null),
    [displayGraph, route, viewFilter, floorPlanOpen]
  );

  const caps = useMemo(() => mapViewCapabilities(displayGraph), [displayGraph]);

  const layoutIncomplete =
    !!displayGraph &&
    (displayGraph.layoutStatus === "missing" ||
      displayGraph.layoutStatus === "partial" ||
      displayGraph.layout3dStatus === "derived");

  const showEnhance = layoutDesignMode && layoutIncomplete;

  const handleTravel = useCallback(
    (sceneId: string) => {
      if (onTravel) onTravel(sceneId);
      else onSwitchScene?.(sceneId);
      setSelectedSceneId(null);
    },
    [onTravel, onSwitchScene]
  );

  const handleTravelReachable = useCallback(
    (sceneId: string) => {
      const mg = displayGraph as MapGraph | null;
      if (!mg) return;
      const adjacent =
        mg.activeSceneId !== sceneId &&
        mg.edges.some(
          (e) =>
            (e.sourceSceneId === mg.activeSceneId && e.targetSceneId === sceneId) ||
            (e.targetSceneId === mg.activeSceneId && e.sourceSceneId === sceneId)
        );
      if (adjacent) handleTravel(sceneId);
      else if (onWalkRoute) onWalkRoute(sceneId);
      else handleTravel(sceneId);
    },
    [displayGraph, handleTravel, onWalkRoute]
  );

  const focusBuilding = useCallback((structureId: string) => {
    setViewScope("building");
    const mg = displayGraph as MapGraph;
    const room = mg.nodes.find((n) => n.structureId === structureId);
    if (room) setSelectedSceneId(room.sceneId);
  }, [displayGraph]);

  const handlePatchPosition = useCallback(
    async (sceneId: string, x: number, y: number) => {
      try {
        await api.patchLayoutSafe(worldId, {
          nodes: [{ sceneId, mapPosition: { x, y } }],
        });
        onGraphRefresh?.();
      } catch {
        /* ignore */
      }
    },
    [worldId, onGraphRefresh]
  );

  useEffect(() => {
    if (!displayGraph || !selectedSceneId || !activeId || selectedSceneId === activeId) {
      setRoute(null);
      return;
    }
    let cancelled = false;
    setRouteLoading(true);
    api
      .navigationRoute(worldId, activeId, selectedSceneId)
      .then((r) => {
        if (!cancelled) setRoute(r);
      })
      .catch(() => {
        if (!cancelled) setRoute(null);
      })
      .finally(() => {
        if (!cancelled) setRouteLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [displayGraph, worldId, activeId, selectedSceneId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (enhanceOpen) setEnhanceOpen(false);
        else if (floorPlanOpen) setFloorPlanOpen(false);
        else if (viewScope !== "site") setViewScope("site");
        else onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, enhanceOpen, floorPlanOpen, viewScope]);

  if (!graph || !displayGraph) {
    return (
      <div className="spatial-canvas-scrim">
        <div className="spatial-canvas-play spatial-canvas-play--empty">
          <p>Map data unavailable.</p>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    );
  }

  const mg = displayGraph as MapGraph;
  const previewLevel = activeLevel(mg);
  const cameraContext: MapViewMode = viewScope === "site" ? "site" : "floor";

  return (
    <FocusTrap active>
      <div className="spatial-canvas-scrim" data-testid="spatial-canvas-play">
        <div className={`spatial-canvas-play${floorPlanOpen ? " spatial-canvas-play--floor" : ""}`}>
          <MapFloatingHud
            graph={displayGraph}
            cameraContext={cameraContext}
            previewLevel={previewLevel}
            caps={caps}
            layoutIncomplete={layoutIncomplete}
            showEnhance={showEnhance}
            floorPlanOpen={floorPlanOpen}
            viewScope={viewScope}
            onLevelChange={() => {}}
            onToggleFloorPlan={() => setFloorPlanOpen((v) => !v)}
            onSeeAll={() => setViewScope("site")}
            onEnhance={() => setEnhanceOpen(true)}
            onClose={onClose}
          />

          <div className="spatial-canvas-play__main">
            {floorPlanOpen ? (
              <MapFloorPlanSlide
                graph={displayGraph}
                viewMode={viewScope}
                selectedSceneId={selectedSceneId}
                onSelectScene={setSelectedSceneId}
                onPatchPosition={layoutDesignMode ? handlePatchPosition : undefined}
              />
            ) : (
              <div className="spatial-canvas-play__canvas">
                <WorldScene
                  className="spatial-canvas-play__world"
                  fitMargin={viewScope === "site" ? 1.45 : 1.15}
                >
                  {sceneData && (
                    <>
                      <SiteGround bounds={sceneData.bounds} siteCenter={sceneData.siteCenter} />
                      <StructureShell
                        structures={sceneData.structures}
                        siteOverview={viewScope === "site"}
                        onStructureClick={focusBuilding}
                        onStructureDoubleClick={focusBuilding}
                      />
                      <RoomVolume
                        rooms={sceneData.rooms}
                        selectedSceneId={selectedSceneId}
                        onSelect={setSelectedSceneId}
                        hiddenWalls={sceneData.hiddenWalls}
                      />
                      <StairConnectors
                        edges={sceneData.edges}
                        onVerticalClick={(targetSceneId) => {
                          if (targetSceneId) setSelectedSceneId(targetSceneId);
                        }}
                      />
                      <EdgeTubes edges={sceneData.edges} />
                      <ReferencePointMarkers
                        markers={sceneData.references}
                        onSelect={(sceneId) => sceneId && setSelectedSceneId(sceneId)}
                      />
                    </>
                  )}
                </WorldScene>
              </div>
            )}

            {!floorPlanOpen && (
              <MapTravelRail
                graph={displayGraph}
                selectedSceneId={selectedSceneId}
                onSelectScene={setSelectedSceneId}
                onTravel={handleTravelReachable}
                onKnock={onKnock}
              />
            )}
          </div>

          <MapSelectionChip
            graph={displayGraph}
            selectedSceneId={selectedSceneId}
            route={route}
            routeLoading={routeLoading}
            onTravel={handleTravel}
            onWalkRoute={onWalkRoute}
            onKnock={onKnock}
            onClear={() => setSelectedSceneId(null)}
          />
        </div>

        <MapEnhanceDrawer
          open={enhanceOpen}
          worldId={worldId}
          graph={graph}
          onClose={() => {
            setEnhanceOpen(false);
            setPreviewGraph(null);
          }}
          onCommitted={onGraphRefresh}
          onPreviewChange={setPreviewGraph}
        />
      </div>
    </FocusTrap>
  );
}
