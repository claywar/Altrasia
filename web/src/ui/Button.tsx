import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "ghost" | "danger";
type Size = "md" | "sm" | "icon";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
};

export function Button({
  variant = "ghost",
  size = "md",
  className = "",
  children,
  ...rest
}: Props) {
  const classes = [
    "ui-btn",
    `ui-btn--${variant}`,
    size === "sm" ? "ui-btn--sm" : "",
    size === "icon" ? "ui-btn--icon" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button type="button" className={classes} {...rest}>
      {children}
    </button>
  );
}
