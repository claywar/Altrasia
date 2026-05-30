type Props = {
  worldId: string;
  characterId: string;
  displayName: string;
  portraitUrl?: string | null;
  className?: string;
};

export function CharacterPortrait({
  worldId,
  characterId,
  displayName,
  portraitUrl,
  className = "cast-row__avatar",
}: Props) {
  const initials = displayName.slice(0, 2).toUpperCase();
  const src = portraitUrl ?? null;

  if (src) {
    return (
      <img
        className={`${className} character-portrait`}
        src={src}
        alt=""
        aria-hidden
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
    );
  }

  return (
    <span className={className} aria-hidden>
      {initials}
    </span>
  );
}
