import { useCallback, useEffect, useState } from "react";
import { api, type CastCharacter, type CharacterInventory } from "../api/client";
import { SettingsBlock } from "./settings/SettingsBlock";

type Props = {
  worldId: string;
  activeSceneId?: string;
  embedded?: boolean;
  onChanged?: () => void;
};

function emptyInventory(): CharacterInventory {
  return { worn: [], held: [], containers: [] };
}

function SlotList({
  title,
  items,
  onRemove,
}: {
  title: string;
  items: { itemId: string; label: string }[];
  onRemove: (itemId: string) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="inventory-slot">
        <strong>{title}</strong>
        <p className="settings-muted">(empty)</p>
      </div>
    );
  }
  return (
    <div className="inventory-slot">
      <strong>{title}</strong>
      <ul className="settings-list settings-list-plain">
        {items.map((item) => (
          <li key={item.itemId} className="settings-list-item">
            <span>{item.label}</span>
            <button type="button" className="settings-link-btn" onClick={() => onRemove(item.itemId)}>
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function InventoryPanel({ worldId, activeSceneId, embedded, onChanged }: Props) {
  const [cast, setCast] = useState<CastCharacter[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [inventory, setInventory] = useState<CharacterInventory>(emptyInventory());
  const [saving, setSaving] = useState(false);
  const [newLabel, setNewLabel] = useState("");
  const [newSlot, setNewSlot] = useState<"held" | "worn">("held");
  const [presets, setPresets] = useState<Record<string, { displayName: string }>>({});
  const [presetId, setPresetId] = useState("");

  const loadCast = useCallback(() => {
    api.listCharacters(worldId).then(setCast).catch(() => setCast([]));
  }, [worldId]);

  const loadPresets = useCallback(() => {
    api
      .getOutfitPresets(worldId)
      .then((r) => setPresets(r.outfitPresets ?? {}))
      .catch(() => setPresets({}));
  }, [worldId]);

  useEffect(() => {
    loadCast();
    loadPresets();
  }, [loadCast, loadPresets]);

  useEffect(() => {
    if (!selectedId && cast.length) {
      setSelectedId(cast[0].characterId);
    }
  }, [cast, selectedId]);

  useEffect(() => {
    if (!selectedId) {
      setInventory(emptyInventory());
      return;
    }
    const fromCast = cast.find((c) => c.characterId === selectedId)?.inventory;
    if (fromCast) {
      setInventory(fromCast);
      return;
    }
    api
      .fetchCharacterInventory(worldId, selectedId)
      .then((r) => setInventory(r.inventory))
      .catch(() => setInventory(emptyInventory()));
  }, [worldId, selectedId, cast]);

  const save = async (next: CharacterInventory) => {
    if (!selectedId) return;
    setSaving(true);
    try {
      await api.patchCharacterInventory(worldId, selectedId, next);
      setInventory(next);
      onChanged?.();
      loadCast();
    } finally {
      setSaving(false);
    }
  };

  const removeItem = (itemId: string) => {
    const next = structuredClone(inventory);
    for (const slot of ["worn", "held"] as const) {
      next[slot] = next[slot].filter((i) => i.itemId !== itemId);
    }
    next.containers = next.containers
      .map((c) => ({
        ...c,
        contents: (c.contents ?? []).filter((i) => i.itemId !== itemId),
      }))
      .filter((c) => c.itemId !== itemId);
    void save(next);
  };

  const addItem = () => {
    const label = newLabel.trim();
    if (!label) return;
    const next = structuredClone(inventory);
    const item = {
      itemId: `item-${Date.now()}`,
      label,
      ...(newSlot === "worn" ? { wearable: true } : {}),
    };
    next[newSlot].push(item);
    setNewLabel("");
    void save(next);
  };

  const body = (
    <>
      <label className="settings-field">
        <span className="settings-field-label">Character</span>
        <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
          {cast.map((c) => (
            <option key={c.characterId} value={c.characterId}>
              {c.displayName}
            </option>
          ))}
        </select>
      </label>
      {Object.keys(presets).length > 0 && selectedId && (
        <div className="inventory-outfit-apply">
          <label className="settings-field">
            <span className="settings-field-label">Outfit preset</span>
            <select value={presetId} onChange={(e) => setPresetId(e.target.value)}>
              <option value="">—</option>
              {Object.entries(presets).map(([id, p]) => (
                <option key={id} value={id}>
                  {p.displayName ?? id}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={saving || !presetId}
            onClick={async () => {
              if (!presetId) return;
              setSaving(true);
              try {
                const out = await api.applyOutfitPreset(worldId, selectedId, presetId);
                setInventory(out.inventory);
                onChanged?.();
                loadCast();
              } finally {
                setSaving(false);
              }
            }}
          >
            Apply preset
          </button>
        </div>
      )}
      <SlotList title="Worn" items={inventory.worn} onRemove={removeItem} />
      <SlotList title="Held" items={inventory.held} onRemove={removeItem} />
      {inventory.containers.map((c) => (
        <SlotList
          key={c.itemId}
          title={`Container: ${c.label}`}
          items={c.contents ?? []}
          onRemove={removeItem}
        />
      ))}
      <div className="inventory-add">
        <input
          type="text"
          placeholder="New item label"
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          aria-label="New item label"
        />
        <select value={newSlot} onChange={(e) => setNewSlot(e.target.value as "held" | "worn")}>
          <option value="held">Held</option>
          <option value="worn">Worn</option>
        </select>
        <button type="button" disabled={saving || !newLabel.trim()} onClick={addItem}>
          Add item
        </button>
      </div>
      {activeSceneId && (
        <p className="settings-muted">
          Inventory is world-scoped and follows characters across scenes (LP-2).
        </p>
      )}
    </>
  );

  if (embedded) {
    return (
      <SettingsBlock title="Character inventory" description="Worn, held, and container items.">
        {body}
      </SettingsBlock>
    );
  }

  return (
    <section className="settings-section">
      <h3>Character inventory</h3>
      {body}
    </section>
  );
}
