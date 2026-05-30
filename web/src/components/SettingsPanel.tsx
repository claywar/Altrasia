import { useEffect, useState } from "react";
import { api, type OperatorSettings, type Scene } from "../api/client";
import { CharacterDraftPanel } from "./CharacterDraftPanel";
import { SceneGeographyPanel } from "./SceneGeographyPanel";
import { CastListPanel } from "./CastListPanel";
import { CommissionsPanel } from "./CommissionsPanel";
import { WorldPolicyPanel } from "./WorldPolicyPanel";
import { BriefingPanel } from "./BriefingPanel";
import { InventoryPanel } from "./InventoryPanel";
import { SceneFixturesPanel } from "./SceneFixturesPanel";
import { SceneSharedStashPanel } from "./SceneSharedStashPanel";
import { SettingsShell } from "./settings/SettingsShell";
import { SettingsCategoryPane } from "./settings/SettingsCategoryPane";
import type { SettingsCategoryId } from "./settings/settingsNav";
import { WorldPackageSection } from "./settings/WorldPackageSection";
import { DemoResetSection } from "./settings/DemoResetSection";
import { WorldStatusSection } from "./settings/WorldStatusSection";
import { AmbientDisplaySection } from "./settings/AmbientDisplaySection";
import { IdleSocialPolicySection } from "./settings/IdleSocialPolicySection";
import { ReflectionPolicySection } from "./settings/ReflectionPolicySection";
import { ServerPluginsSection } from "./settings/ServerPluginsSection";
import { ServerInferenceSection } from "./settings/ServerInferenceSection";
import { ServerHeartbeatSection } from "./settings/ServerHeartbeatSection";
import { ImageGenerationSettingsSection } from "./settings/ImageGenerationSettingsSection";
import { WorldImagePolicySection } from "./settings/WorldImagePolicySection";
import { SettingsScenesEmpty } from "./settings/SettingsScenesEmpty";
import { OperationsDebateHint } from "./settings/OperationsDebateHint";
import { SettingsGroup } from "./settings/SettingsGroup";

type Props = {
  worldId: string;
  worldName: string;
  worldPaused: boolean;
  isDemoWorld?: boolean;
  onClose: () => void;
  onWorldImported: (world: { worldId: string; name: string; activeSceneId: string }) => void;
  onDemoReset?: () => void | Promise<void>;
  onCastChanged?: () => void;
  scenes?: Scene[];
  onScenesChanged?: () => void;
  activeSceneId?: string;
  onAmbientTranscriptChange?: () => void;
};

export function SettingsPanel({
  worldId,
  worldName,
  worldPaused,
  isDemoWorld = false,
  onClose,
  onWorldImported,
  onDemoReset,
  onCastChanged,
  scenes = [],
  onScenesChanged,
  activeSceneId = "",
  onAmbientTranscriptChange,
}: Props) {
  const [settings, setSettings] = useState<OperatorSettings | null>(null);
  const [activeCategory, setActiveCategory] = useState<SettingsCategoryId>("world");
  const hasScenes = scenes.length > 0;

  useEffect(() => {
    api.operatorSettings().then(setSettings);
  }, []);

  const renderCategory = () => {
    switch (activeCategory) {
      case "world":
        return (
          <SettingsCategoryPane categoryId="world">
            <SettingsGroup>
              <WorldStatusSection worldPaused={worldPaused} />
              {isDemoWorld && onDemoReset && (
                <DemoResetSection worldId={worldId} onReset={onDemoReset} />
              )}
              <AmbientDisplaySection onChanged={onAmbientTranscriptChange} />
              <IdleSocialPolicySection worldId={worldId} />
              <ReflectionPolicySection worldId={worldId} />
              <WorldImagePolicySection worldId={worldId} />
              <WorldPolicyPanel worldId={worldId} embedded />
              <WorldPackageSection
                worldId={worldId}
                worldName={worldName}
                onImported={onWorldImported}
                onClose={onClose}
              />
              {hasScenes && activeSceneId && (
                <BriefingPanel
                  worldId={worldId}
                  scenes={scenes}
                  activeSceneId={activeSceneId}
                  embedded
                />
              )}
            </SettingsGroup>
          </SettingsCategoryPane>
        );
      case "architect":
        return (
          <SettingsCategoryPane categoryId="architect">
            {!hasScenes ? (
              <SettingsScenesEmpty />
            ) : (
              <SettingsGroup>
                <SceneFixturesPanel
                  worldId={worldId}
                  scenes={scenes}
                  activeSceneId={activeSceneId}
                  embedded
                  onChanged={() => onScenesChanged?.()}
                />
                <SceneSharedStashPanel
                  worldId={worldId}
                  scenes={scenes}
                  activeSceneId={activeSceneId}
                  embedded
                  onChanged={() => onScenesChanged?.()}
                />
                <SceneGeographyPanel
                  worldId={worldId}
                  scenes={scenes}
                  onChanged={() => onScenesChanged?.()}
                  embedded
                />
                <p className="settings-muted">
                  Map layout is edited in the world map. Press <kbd>M</kbd> and choose{" "}
                  <strong>Enhance map</strong>.
                </p>
              </SettingsGroup>
            )}
          </SettingsCategoryPane>
        );
      case "cast":
        return (
          <SettingsCategoryPane categoryId="cast">
            <SettingsGroup>
              <CastListPanel worldId={worldId} embedded />
              <InventoryPanel
                worldId={worldId}
                activeSceneId={activeSceneId}
                embedded
                onChanged={() => onCastChanged?.()}
              />
              <CharacterDraftPanel
                worldId={worldId}
                onCharacterAdded={() => onCastChanged?.()}
                embedded
              />
            </SettingsGroup>
          </SettingsCategoryPane>
        );
      case "operations":
        return (
          <SettingsCategoryPane categoryId="operations">
            {!hasScenes ? (
              <SettingsScenesEmpty />
            ) : (
              <SettingsGroup>
                <OperationsDebateHint />
                <CommissionsPanel worldId={worldId} scenes={scenes} embedded />
              </SettingsGroup>
            )}
          </SettingsCategoryPane>
        );
      case "media":
        return (
          <SettingsCategoryPane categoryId="media">
            {settings ? (
              <SettingsGroup>
                <ImageGenerationSettingsSection settings={settings} onUpdated={setSettings} />
              </SettingsGroup>
            ) : (
              <p className="settings-muted settings-loading">Loading media settings…</p>
            )}
          </SettingsCategoryPane>
        );
      case "server":
        return (
          <SettingsCategoryPane categoryId="server">
            {settings ? (
              <SettingsGroup>
                <ServerInferenceSection settings={settings} onUpdated={setSettings} />
                <ServerHeartbeatSection settings={settings} onUpdated={setSettings} />
                <ServerPluginsSection settings={settings} onUpdated={setSettings} />
              </SettingsGroup>
            ) : (
              <p className="settings-muted settings-loading">Loading server settings…</p>
            )}
          </SettingsCategoryPane>
        );
      default:
        return null;
    }
  };

  return (
    <SettingsShell
      worldName={worldName}
      activeCategory={activeCategory}
      onCategoryChange={setActiveCategory}
      onClose={onClose}
    >
      {renderCategory()}
    </SettingsShell>
  );
}
