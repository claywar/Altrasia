import { useCallback, useEffect, useMemo, useRef } from "react";
import type { SpatialGraph } from "../../api/client";
import {
  activeLevel,
  activeStructureId,
  levelLabelFor,
  levelsForStructure,
  stackPlatesForStructure,
} from "./floorLevels";
import { LevelStackLegend } from "./LevelStackLegend";
import { LevelStackView } from "./LevelStackView";
import { levelSelectorBadge } from "./stackGeometry";
import type { MapGraph } from "./types";

type Props = {
  graph: SpatialGraph | null;
  structureId?: string;
  focusLevel: number;
  onFocusLevel: (level: number) => void;
  selectedSceneId?: string | null;
  onSelectScene?: (sceneId: string) => void;
  onTravelScene?: (sceneId: string) => void;
  onTravelVertical?: (exitId: string) => void;
};

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

export function LevelStackPanel({
  graph,
  structureId,
  focusLevel,
  onFocusLevel,
  selectedSceneId = null,
  onSelectScene,
  onTravelScene,
  onTravelVertical,
}: Props) {
  const diagramRef = useRef<HTMLDivElement>(null);
  const mg = graph ? toMapGraph(graph) : null;
  const sid = structureId ?? (mg ? activeStructureId(mg) : undefined);
  const personaLevel = mg ? activeLevel(mg) : 0;
  const activeSceneId = graph?.activeSceneId ?? "";

  const plates = useMemo(
    () => (mg && sid ? stackPlatesForStructure(mg, sid) : []),
    [mg, sid]
  );
  const levels = useMemo(
    () => (mg && sid ? levelsForStructure(mg.nodes, sid) : []),
    [mg, sid]
  );
  const orderedLevels = useMemo(() => [...levels].sort((a, b) => b - a), [levels]);

  const st = mg?.structures?.find((s) => s.structureId === sid);
  const displayName = st?.displayName ?? sid ?? "Structure";

  const scrollToLevel = useCallback((level: number) => {
    const el = diagramRef.current?.querySelector(`[data-stack-level="${level}"]`);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, []);

  const handleLevelClick = useCallback(
    (level: number) => {
      onFocusLevel(level);
      scrollToLevel(level);
    },
    [onFocusLevel, scrollToLevel]
  );

  const handleRoomClick = useCallback(
    (sceneId: string) => {
      onSelectScene?.(sceneId);
      if (sceneId !== activeSceneId && onTravelScene) {
        onTravelScene(sceneId);
      }
    },
    [onSelectScene, onTravelScene, activeSceneId]
  );

  useEffect(() => {
    if (focusLevel != null) scrollToLevel(focusLevel);
  }, [focusLevel, scrollToLevel]);

  if (!mg || !sid || plates.length === 0) {
    return <div className="level-stack level-stack--empty">No multi-level structure selected.</div>;
  }

  return (
    <div className="level-stack-panel level-stack-panel--holistic" role="region" aria-label={`${displayName} building`}>
      <header className="level-stack-panel__header">
        <h3>{displayName}</h3>
        <p className="level-stack-panel__note">
          Cutaway of the whole building — same footprint on every floor. Click a room to go there.
        </p>
      </header>

      <nav className="level-stack-panel__levels" aria-label="Floors">
        {orderedLevels.map((lvl) => {
          const active = focusLevel === lvl;
          const personaHere = personaLevel === lvl;
          return (
            <button
              key={lvl}
              type="button"
              className={
                active
                  ? "level-stack-chip level-stack-chip--active"
                  : "level-stack-chip"
              }
              onClick={() => handleLevelClick(lvl)}
              aria-pressed={active}
            >
              <span className="level-stack-chip__badge">{levelSelectorBadge(lvl)}</span>
              <span className="level-stack-chip__name">
                {levelLabelFor(mg.nodes, sid, lvl)}
              </span>
              {personaHere && (
                <span className="level-stack-chip__dot" title="You are here" aria-hidden />
              )}
            </button>
          );
        })}
      </nav>

      <div className="level-stack-panel__diagram" ref={diagramRef}>
        <LevelStackView
          graph={graph}
          structureId={sid}
          focusLevel={focusLevel}
          plates={plates}
          selectedSceneId={selectedSceneId}
          onSelectScene={handleRoomClick}
          onTravelVertical={onTravelVertical}
        />
      </div>

      <footer className="level-stack-panel__footer">
        <LevelStackLegend compact />
      </footer>
    </div>
  );
}
