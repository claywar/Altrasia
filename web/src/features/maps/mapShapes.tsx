import type { MapStyleTokens } from "./mapStyle";
import { WallRect } from "./wallStrokes";
import type { Footprint } from "./types";

type ShapeProps = {
  fp: Footprint;
  active: boolean;
  dimmed?: boolean;
  label: string;
  tokens: MapStyleTokens;
};

function labelFontSize(fp: Footprint): number {
  const m = Math.min(fp.w, fp.h);
  return Math.min(3, Math.max(2, m * 0.22));
}

function truncate(name: string, maxLen: number): string {
  return name.length > maxLen ? `${name.slice(0, maxLen - 1)}…` : name;
}

export function MapNodeShape({ fp, active, dimmed, label, tokens }: ShapeProps) {
  const fill = active ? tokens.roomFillActive : tokens.roomFill;
  const stroke = active ? "var(--fg)" : tokens.roomStroke;
  const opacity = dimmed ? 0.45 : tokens.roomFillOpacity;
  const scale = active ? 1.02 : 1;
  const fs = labelFontSize(fp);
  const labelInsideCircle = fp.shape === "circle";

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
          fill={tokens.showStructureFill ? fill : active ? tokens.roomFillActive : "none"}
          stroke={stroke}
          strokeWidth={active ? tokens.roomStrokeWidth * 1.4 : tokens.roomStrokeWidth}
        />
        {tokens.doubleWall && (
          <circle
            cx={fp.cx}
            cy={fp.cy}
            r={Math.max(0.5, r - 0.45)}
            fill="none"
            stroke={stroke}
            strokeWidth={tokens.roomStrokeWidth * 0.65}
            opacity={0.75}
          />
        )}
        {labelInsideCircle && (
          <text
            x={fp.cx}
            y={fp.cy + 0.5}
            textAnchor="middle"
            dominantBaseline="middle"
            className="map-node-label"
            fontSize={fs}
            fontFamily={tokens.labelFont}
          >
            {display}
          </text>
        )}
      </g>
    );
  }

  const x = fp.cx - fp.w / 2;
  const y = fp.cy - fp.h / 2;
  const rx = fp.shape === "corridor" ? 1.2 : 2.8;
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
          fill={tokens.corridorFill}
          stroke={stroke}
          strokeWidth={tokens.roomStrokeWidth}
        />
        <text
          x={fp.cx}
          y={fp.cy + 0.5}
          textAnchor="middle"
          dominantBaseline="middle"
          className="map-node-label"
          fontSize={fs * 0.9}
          fontFamily={tokens.labelFont}
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
        stroke={tokens.doubleWall ? "none" : stroke}
        strokeWidth={active ? tokens.roomStrokeWidth * 1.4 : tokens.roomStrokeWidth}
      />
      {tokens.doubleWall && (
        <WallRect
          x={x}
          y={y}
          w={fp.w}
          h={fp.h}
          rx={rx}
          stroke={stroke}
          strokeWidth={tokens.roomStrokeWidth}
          doubleWall
        />
      )}
      <text
        x={fp.cx}
        y={fp.cy + 0.5}
        textAnchor="middle"
        dominantBaseline="middle"
        className="map-node-label"
        fontSize={fs}
        fontFamily={tokens.labelFont}
      >
        {display}
      </text>
    </g>
  );
}

export function CorridorShape({
  x,
  y,
  w,
  h,
  tokens,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  tokens: MapStyleTokens;
}) {
  const cap = Math.min(w, h) * 0.35;
  return (
    <rect
      x={x}
      y={y}
      width={w}
      height={h}
      rx={cap}
      fill={tokens.corridorFill}
      stroke="var(--map-corridor-stroke, var(--border))"
      strokeWidth={0.35}
      className="map-corridor"
    />
  );
}
