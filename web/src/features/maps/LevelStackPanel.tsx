import { useCallback, useEffect, useMemo, useRef } from "react";
import type { SpatialGraph } from "../../api/client";
import {
  activeLevel,
  activeStructureId,
  levelLabelFor,
  levelsForStructure,
  stackPlatesForStructure,
  verticalLinksForStructure,
} from "./floorLevels";
import { LevelStackLegend } from "./LevelStackLegend";
import { LevelStackView } from "./LevelStackView";
import { DIAGRAM_PROFILES } from "./diagramProfiles";
import {
  layoutStackPlates,
  levelSelectorBadge,
  levelSelectorIcon,
  plateDescription,
} from "./stackGeometry";
import type { MapGraph } from "./types";

type Props = {
  graph: SpatialGraph | null;
  structureId?: string;
  focusLevel: number;
  onFocusLevel: (level: number) => void;
  selectedSceneId?: string | null;
  onSelectScene?: (sceneId: string) => void;
  onTravelVertical?: (exitId: string) => void;
};

function toMapGraph(graph: SpatialGraph): MapGraph {
  return graph as MapGraph;
}

function LevelIcon({ kind }: { kind: "ladder" | "stairs" | "floor" }) {
  if (kind === "ladder") {
    return (
      <svg viewBox="0 0 16 16" width={18} height={18} aria-hidden>
        <path d="M4 2v12M12 2v12M4 5h8M4 8h8M4 11h8" stroke="currentColor" fill="none" strokeWidth={1.2} />
      </svg>
    );
  }
  if (kind === "stairs") {
    return (
      <svg viewBox="0 0 16 16" width={18} height={18} aria-hidden>
        <path d="M3 13h4V9h4V5h4V2" stroke="currentColor" fill="none" strokeWidth={1.2} />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 16 16" width={18} height={18} aria-hidden>
      <rect x={3} y={5} width={10} height={8} stroke="currentColor" fill="none" strokeWidth={1.2} />
      <path d="M3 8h10" stroke="currentColor" strokeWidth={0.8} />
    </svg>
  );
}

export function LevelStackPanel({
  graph,
  structureId,
  focusLevel,
  onFocusLevel,
  selectedSceneId = null,
  onSelectScene,
  onTravelVertical,
}: Props) {
  const diagramRef = useRef<HTMLDivElement>(null);
  const mg = graph ? toMapGraph(graph) : null;
  const sid = structureId ?? (mg ? activeStructureId(mg) : undefined);
  const personaLevel = mg ? activeLevel(mg) : 0;

  const plates = useMemo(
    () => (mg && sid ? stackPlatesForStructure(mg, sid) : []),
    [mg, sid]
  );
  const vertical = useMemo(
    () => (mg && sid ? verticalLinksForStructure(mg, sid) : []),
    [mg, sid]
  );
  const levels = useMemo(
    () => (mg && sid ? levelsForStructure(mg.nodes, sid) : []),
    [mg, sid]
  );
  const orderedLevels = useMemo(() => [...levels].sort((a, b) => b - a), [levels]);

  const stackLayout = useMemo(
    () =>
      plates.length
        ? layoutStackPlates(plates, vertical, DIAGRAM_PROFILES.stack.projection)
        : null,
    [plates, vertical]
  );

  const st = mg?.structures?.find((s) => s.structureId === sid);
  const displayName = st?.displayName ?? sid ?? "Structure";

  const scrollToLevel = useCallback(
    (level: number) => {
      const el = diagramRef.current?.querySelector(`[data-stack-level="${level}"]`);
      el?.scrollIntoView({ block: "center", behavior: "smooth" });
    },
    []
  );

  const handleLevelClick = useCallback(
    (level: number) => {
      onFocusLevel(level);
      scrollToLevel(level);
    },
    [onFocusLevel, scrollToLevel]
  );

  useEffect(() => {
    if (focusLevel != null) scrollToLevel(focusLevel);
  }, [focusLevel, scrollToLevel]);

  if (!mg || !sid || plates.length === 0) {
    return <div className="level-stack level-stack--empty">No multi-level structure selected.</div>;
  }

  return (
    <div className="level-stack-panel" role="region" aria-label={`Level stack: ${displayName}`}>
      <header className="level-stack-panel__header">
        <h3>Level stack · {displayName}</h3>
        <p className="level-stack-panel__note">Levels are schematic. Not to scale.</p>
      </header>

      <div className="level-stack-panel__body">
        <aside className="level-stack-panel__left" aria-label="Level selector">
          <h4>Levels</h4>
          <ul className="level-stack-selector">
            {orderedLevels.map((lvl) => {
              const icon = levelSelectorIcon(lvl);
              const active = focusLevel === lvl;
              const personaHere = personaLevel === lvl;
              return (
                <li key={lvl}>
                  <button
                    type="button"
                    className={
                      active ? "level-stack-selector__btn level-stack-selector__btn--active" : "level-stack-selector__btn"
                    }
                    onClick={() => handleLevelClick(lvl)}
                    aria-pressed={active}
                  >
                    <span className="level-stack-selector__icon">
                      <LevelIcon kind={icon} />
                    </span>
                    <span className="level-stack-selector__text">
                      <span className="level-stack-selector__badge">{levelSelectorBadge(lvl)}</span>
                      <span className="level-stack-selector__name">
                        {levelLabelFor(mg.nodes, sid, lvl)}
                      </span>
                    </span>
                    {personaHere && (
                      <span className="level-stack-selector__dot" title="You are here" aria-hidden />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
          <LevelStackLegend />
        </aside>

        <div className="level-stack-panel__diagram" ref={diagramRef}>
          <LevelStackView
            graph={graph}
            structureId={sid}
            focusLevel={focusLevel}
            stackLayout={stackLayout}
            plates={plates}
            vertical={vertical}
            selectedSceneId={selectedSceneId}
            onSelectScene={onSelectScene}
            onTravelVertical={onTravelVertical}
          />
        </div>

        <aside className="level-stack-panel__right" aria-label="Level descriptions">
          {stackLayout?.layouts.map((layout) => {
            const active = focusLevel === layout.level;
            const levelTitle =
              layout.level > 0
                ? `Level +${layout.level}`
                : layout.level === 0
                  ? "Level 0"
                  : `Level ${layout.level}`;
            return (
              <div
                key={layout.level}
                className={
                  active
                    ? "level-stack-annotation level-stack-annotation--active"
                    : "level-stack-annotation"
                }
              >
                <p className="level-stack-annotation__level">{levelTitle}</p>
                <p className="level-stack-annotation__title">{layout.label.toUpperCase()}</p>
                <p className="level-stack-annotation__desc">{plateDescription(layout.nodes)}</p>
              </div>
            );
          })}
        </aside>
      </div>
    </div>
  );
}
