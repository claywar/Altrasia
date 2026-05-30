type Props = {
  worldId: string;
  characterId: string;
  referenceAssetUrl?: string | null;
};

export function ReferenceSheetPanel({ worldId, characterId, referenceAssetUrl }: Props) {
  return (
    <section className="reference-sheet-panel" aria-label="Character reference">
      <h3 className="reference-sheet-panel__title">Reference sheet</h3>
      {referenceAssetUrl ? (
        <img
          className="reference-sheet-panel__img"
          src={referenceAssetUrl}
          alt="Character reference for IP-Adapter consistency"
        />
      ) : (
        <p className="settings-muted">
          No reference image yet. Generate a portrait with an SDXL or FLUX profile that supports
          referenceImage.
        </p>
      )}
    </section>
  );
}
