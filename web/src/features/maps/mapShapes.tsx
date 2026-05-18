import type { Footprint } from "./types";

type ShapeProps = {
  fp: Footprint;
  active: boolean;
  dimmed?: boolean;
  label: string;
};

function labelFontSize(fp: Footprint): number {
  const m = Math.min(fp.w, fp.h);
  return Math.min(3, Math.max(2, m * 0.22));
}

function truncate(name: string, maxLen: number): string {
  return name.length > maxLen ? `${name.slice(0, maxLen - 1)}…` : name;
}

export function MapNodeShape({ fp, active, dimmed, label }: ShapeProps) {
  const fill = active ? "var(--accent)" : "var(--surface-2)";
  const stroke = active ? "var(--fg)" : "var(--border)";
  const opacity = dimmed ? 0.45 : 1;
  const scale = active ? 1.05 : 1;
  const fs = labelFontSize(fp);

  if (fp.shape === "circle") {
    const r = fp.w / 2;
    const display = truncate(label, 10);
    return (
      <g
        opacity={opacity}
        transform={`translate(${fp.cx}, ${fp.cy}) scale(${scale}) translate(${-fp.cx}, ${-fp.cy})`}
      >
        <circle
          cx={fp.cx}
          cy={fp.cy}
          r={r}
          fill={fill}
          stroke={stroke}
          strokeWidth={active ? 1 : 0.5}
        />
        <text
          x={fp.cx}
          y={fp.cy + r + 2.5}
          textAnchor="middle"
          className="map-node-label"
          fontSize={fs}
        >
          {display}
        </text>
      </g>
    );
  }

  const x = fp.cx - fp.w / 2;
  const y = fp.cy - fp.h / 2;
  const rx = fp.shape === "corridor" ? 0.5 : 1;
  const display = truncate(label, fp.shape === "corridor" ? 8 : 12);

  if (fp.shape === "corridor") {
    return (
      <g
        opacity={opacity}
        transform={`translate(${fp.cx}, ${fp.cy}) scale(${scale}) translate(${-fp.cx}, ${-fp.cy})`}
      >
        <rect
          x={x}
          y={y}
          width={fp.w}
          height={fp.h}
          rx={rx}
          fill={fill}
          stroke={stroke}
          strokeWidth={active ? 1 : 0.5}
        />
        <text
          x={x - 1.5}
          y={fp.cy + 0.5}
          textAnchor="end"
          dominantBaseline="middle"
          className="map-node-label"
          fontSize={fs}
        >
          {display}
        </text>
      </g>
    );
  }

  return (
    <g
      opacity={opacity}
      transform={`translate(${fp.cx}, ${fp.cy}) scale(${scale}) translate(${-fp.cx}, ${-fp.cy})`}
    >
      <rect
        x={x}
        y={y}
        width={fp.w}
        height={fp.h}
        rx={rx}
        fill={fill}
        stroke={stroke}
        strokeWidth={active ? 1 : 0.5}
      />
      <text
        x={fp.cx}
        y={fp.cy + 0.5}
        textAnchor="middle"
        dominantBaseline="middle"
        className="map-node-label"
        fontSize={fs}
      >
        {display}
      </text>
    </g>
  );
}
