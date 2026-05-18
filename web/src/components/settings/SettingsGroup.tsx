import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
};

/** Single card wrapping all blocks in a settings category tab. */
export function SettingsGroup({ children }: Props) {
  return <div className="settings-group ui-card">{children}</div>;
}
