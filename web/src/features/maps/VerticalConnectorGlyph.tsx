import type { StackConnector } from "./buildingStackLayout";

type Props = {
  connector: StackConnector;
  onClick?: (exitId: string) => void;
};

const STAIRS_COLOR = "var(--accent, #4a9eff)";
const LADDER_COLOR = "#c9a227";

export function VerticalConnectorGlyph({ connector, onClick }: Props) {
  const { edge, x1, y1, x2, y2, label, kind, direction } = connector;
  const color = kind === "ladder" ? LADDER_COLOR : STAIRS_COLOR;
  const midY = (y1 + y2) / 2;
  const clickable = Boolean(onClick);

  return (
    <g
      className={`level-stack-connector level-stack-connector--${kind}`}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={label}
      style={{ cursor: clickable ? "pointer" : undefined }}
      onClick={clickable ? () => onClick!(edge.exitId) : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick!(edge.exitId);
              }
            }
          : undefined
      }
    >
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={0.55}
        strokeDasharray="1.5 1"
        opacity={0.95}
      />
      <circle
        cx={x1}
        cy={midY}
        r={2.2}
        fill="var(--panel-elevated, #141c28)"
        stroke={color}
        strokeWidth={0.4}
      />
      <text x={x1} y={midY + 0.4} textAnchor="middle" fontSize={1.6} fill={color}>
        {direction === "up" ? "▲" : "▼"}
      </text>
      <text
        x={x1 + 3.5}
        y={midY + 0.5}
        fontSize={2}
        fill={color}
        className="level-stack-connector__label"
      >
        {label}
      </text>
    </g>
  );
}
