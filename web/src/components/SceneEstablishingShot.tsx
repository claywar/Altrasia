type Props = {
  worldId: string;
  sceneId: string;
  assetUrl?: string | null;
  caption?: string | null;
};

export function SceneEstablishingShot({ worldId, sceneId, assetUrl, caption }: Props) {
  if (!assetUrl) {
    return (
      <div className="scene-establishing scene-establishing--placeholder" aria-hidden>
        <span className="scene-establishing__label">Scene</span>
      </div>
    );
  }

  return (
    <figure className="scene-establishing">
      <img src={assetUrl} alt={caption ?? `Establishing shot for scene ${sceneId}`} />
      {caption ? <figcaption className="scene-establishing__caption">{caption}</figcaption> : null}
    </figure>
  );
}
