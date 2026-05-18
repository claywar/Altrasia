import { Badge } from "./Badge";

const SCOPE_LABELS: Record<string, string> = {
  public: "Public",
  whisper: "Whisper",
  dm: "DM",
  narrator: "Narrator",
  phone: "Phone",
};

type Props = {
  scope: string;
};

export function ScopeBadge({ scope }: Props) {
  const key = scope.toLowerCase();
  const label = SCOPE_LABELS[key] ?? scope;
  return <Badge className={`ui-badge--${key}`}>{label}</Badge>;
}
