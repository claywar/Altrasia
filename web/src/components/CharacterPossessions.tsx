import { useEffect, useState } from "react";
import { api, type CharacterInventory } from "../api/client";

type Props = {
  worldId: string;
  characterId: string;
  /** Inline summary from roster when full inventory not loaded yet */
  summaryHint?: string;
};

function slotLabels(items: { label: string }[]): string {
  if (!items.length) return "(none)";
  return items.map((i) => i.label).join(", ");
}

export function CharacterPossessions({ worldId, characterId, summaryHint }: Props) {
  const [inventory, setInventory] = useState<CharacterInventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .fetchCharacterInventory(worldId, characterId)
      .then((r) => {
        if (!cancelled) setInventory(r.inventory);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load inventory");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [worldId, characterId]);

  if (loading) {
    return <p className="character-possessions character-possessions--loading">Loading…</p>;
  }
  if (error || !inventory) {
    return summaryHint ? (
      <p className="character-possessions character-possessions--summary">{summaryHint}</p>
    ) : (
      <p className="character-possessions character-possessions--empty">{error ?? "No data"}</p>
    );
  }

  const hasAnything =
    inventory.worn.length > 0 ||
    inventory.held.length > 0 ||
    inventory.containers.some((c) => (c.contents?.length ?? 0) > 0);

  return (
    <div className="character-possessions">
      <dl className="character-possessions__list">
        <div>
          <dt>Worn</dt>
          <dd>{slotLabels(inventory.worn)}</dd>
        </div>
        <div>
          <dt>Held</dt>
          <dd>{slotLabels(inventory.held)}</dd>
        </div>
        {inventory.containers.map((c) => (
          <div key={c.itemId}>
            <dt>{c.label}</dt>
            <dd>{slotLabels(c.contents ?? [])}</dd>
          </div>
        ))}
      </dl>
      {!hasAnything && <p className="character-possessions--empty">Nothing carried or worn.</p>}
    </div>
  );
}
