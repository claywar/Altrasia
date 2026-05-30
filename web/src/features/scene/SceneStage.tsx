import { useMemo } from "react";
import type { Message, Scene, SpatialGraph } from "../../api/client";
import { Button } from "../../ui/Button";
import { Chip } from "../../ui/Chip";
import { MiniMap3D } from "../map3d/MiniMap3D";
import { compassFromActive } from "../maps/mapNavigation";
import {
  parsePresent,
  sceneFixtureChips,
  sceneHasSocialIdleMessages,
  sceneStructureHints,
  structureLabel,
  structureTint,
} from "../../lib/parse";
import { BanterTranscriptToggle } from "../transcript/BanterTranscriptToggle";

type PresencePerson = {
  characterId: string;
  displayName: string;
  inventorySummary?: string;
};

type Props = {
  scene: Scene | null;
  graph?: SpatialGraph | null;
  messages?: Message[];
  rosterAtLocation: PresencePerson[];
  spatialOpen: boolean;
  onToggleSpatial: () => void;
  onMapOpen?: () => void;
};

function displayNameForId(id: string, roster: PresencePerson[]): string {
  if (id === "__persona__") return "You";
  const found = roster.find((p) => p.characterId === id);
  if (found) return found.displayName;
  return id.replace(/^char-/, "").replace(/.*-char-/, "");
}

export function SceneStage({
  scene,
  graph,
  messages = [],
  rosterAtLocation,
  spatialOpen,
  onToggleSpatial,
  onMapOpen,
}: Props) {
  if (!scene) return null;

  const hasBanter = useMemo(() => sceneHasSocialIdleMessages(messages), [messages]);

  const { structureId, fixtures: hintFixtures } = sceneStructureHints(scene.layoutHintsJson);
  const fixtureChips = useMemo(() => {
    const fromJson = sceneFixtureChips(scene.fixturesJson);
    return fromJson.length ? fromJson : hintFixtures ?? [];
  }, [scene.fixturesJson, hintFixtures]);
  const presentIds = parsePresent(scene.presentJson);
  const tintHue = structureTint(structureId ?? undefined);
  const structure = graph?.structures?.find((s) => s.structureId === structureId);
  const compass = graph ? compassFromActive(graph) : null;

  return (
    <header
      className="scene-stage scene-header"
      data-testid="scene-stage"
      style={{ "--scene-tint-hue": tintHue } as React.CSSProperties}
    >
      <div className="scene-stage__inner">
        <div className="scene-stage__top">
          {structureId && (
            <p className="scene-stage__breadcrumb">
              {structure?.displayName ?? structureLabel(structureId)} › {scene.locationName}
            </p>
          )}
          <div className="scene-stage__title-row">
            <h2 className="scene-stage__title">{scene.locationName}</h2>
            {compass && (
              <span className="scene-stage__compass" title="Nearest exit bearing">
                {compass}
              </span>
            )}
            {onMapOpen && graph && (
              <button
                type="button"
                className="scene-stage__map-chip"
                onClick={onMapOpen}
                aria-label="Open world map"
                title="World map (M)"
              >
                <MiniMap3D graph={graph} className="scene-stage__map-chip-inner" />
              </button>
            )}
            <Button
              className="scene-stage__spatial-toggle"
              variant="ghost"
              size="sm"
              onClick={onToggleSpatial}
              aria-expanded={spatialOpen}
              aria-controls="spatial-drawer"
            >
              {spatialOpen ? "Hide spatial" : "Spatial"}
            </Button>
          </div>
        </div>
        {scene.locationDescription && (
          <p className="scene-stage__description">{scene.locationDescription}</p>
        )}
        {fixtureChips.length > 0 && (
          <div className="scene-stage__fixtures" aria-label="Fixtures">
            {fixtureChips.map((f) => (
              <span key={f} className="scene-stage__fixture">
                {f}
              </span>
            ))}
          </div>
        )}
        <div className="scene-stage__presence" aria-label="Present">
          {presentIds.length === 0 ? (
            <span className="scene-stage__presence-empty">No one visible</span>
          ) : (
            presentIds.map((id) => {
              const name = displayNameForId(id, rosterAtLocation);
              const person = rosterAtLocation.find((p) => p.characterId === id);
              const inv = person?.inventorySummary;
              return (
                <div key={id} className="scene-stage__presence-person">
                  <Chip
                    label={name}
                    initials={id === "__persona__" ? "You".slice(0, 2) : name.slice(0, 2)}
                    hint={inv ? `Possessions: ${inv}` : undefined}
                  />
                  {inv && id !== "__persona__" && (
                    <span className="scene-stage__presence-inventory">{inv}</span>
                  )}
                </div>
              );
            })
          )}
        </div>
        {hasBanter && (
          <div className="scene-stage__banter" data-testid="scene-stage-banter">
            <span className="scene-stage__banter-label">Sidebar banter</span>
            <span className="scene-stage__banter-hint">Shown in chronicle below</span>
            <BanterTranscriptToggle visible />
          </div>
        )}
      </div>
    </header>
  );
}
