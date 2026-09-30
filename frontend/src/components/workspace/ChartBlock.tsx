"use client";

import { useId, useMemo, useState } from "react";

import Icon from "@/components/ui/Icon";
import { cx } from "@/lib/cx";
import type { Chart } from "@/lib/types";

/**
 * Dependency-free SVG chart renderer.
 *
 * Charts arrive as validated data from the backend (see `app/rag/charts.py`),
 * and a markdown table is converted client-side when the model ignored the
 * chart instruction. Nothing here parses model output, and no value is injected
 * into markup, so a hostile document cannot produce script.
 */

const PALETTE = [
  "var(--color-brand-500)",
  "var(--color-accent-500)",
  "var(--color-brand-400)",
  "var(--color-accent-400)",
  "var(--color-brand-600)",
  "var(--color-accent-600)",
];

type Props = {
  chart: Chart;
  className?: string;
};

const W = 560;
const HEIGHT = 240;
const PAD = { top: 12, right: 12, bottom: 34, left: 44 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = HEIGHT - PAD.top - PAD.bottom;

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const scaled = value / magnitude;
  const step = scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10;
  return step * magnitude;
}

function formatValue(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export default function ChartBlock({ chart, className }: Props) {
  const [hidden, setHidden] = useState(false);
  const gradientId = useId();
  const { data, type } = chart;

  const stats = useMemo(() => {
    const values = data.map((point) => point.value);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    const total = values.reduce((sum, value) => sum + value, 0);
    return { min, max, total, peak: max === min ? Math.abs(max) || 1 : max };
  }, [data]);

  const top = niceMax(stats.peak);
  const scaleY = (value: number) =>
    PAD.top + PLOT_H - ((value - stats.min) / (top - stats.min || 1)) * PLOT_H;

  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((fraction) => ({
    y: PAD.top + PLOT_H * (1 - fraction),
    label: formatValue(top * fraction),
  }));

  if (hidden) {
    return (
      <button
        type="button"
        onClick={() => setHidden(false)}
        className="text-xs text-muted-foreground hover:text-foreground"
      >
        Show chart
      </button>
    );
  }

  return (
    <figure
      className={cx(
        "card mt-3 overflow-hidden p-4 text-left",
        className,
      )}
    >
      <figcaption className="mb-3 flex items-center gap-2">
        <Icon name="activity" className="size-3.5 text-brand-600" />
        <span className="text-xs font-semibold">
          {chart.title || "Chart"}
        </span>
        <span className="chip ml-auto py-0.5 text-[0.625rem]">
          {data.length} {data.length === 1 ? "point" : "points"}
        </span>
        <button
          type="button"
          onClick={() => setHidden(true)}
          className="text-muted-foreground transition-colors hover:text-foreground"
          aria-label="Hide chart"
        >
          <Icon name="close" className="size-3.5" />
        </button>
      </figcaption>

      {type === "pie" ? (
        <PieChart data={data} total={stats.total} />
      ) : type === "line" ? (
        <LineChart
          data={data}
          scaleY={scaleY}
          gridLines={gridLines}
          gradientId={gradientId}
        />
      ) : (
        <BarChart
          data={data}
          type={type}
          scaleY={scaleY}
          top={top}
          gridLines={gridLines}
          width={W}
          height={HEIGHT}
        />
      )}

      <table className="sr-only">
        <caption>{chart.title || "Chart data"}</caption>
        <tbody>
          {data.map((point) => (
            <tr key={point.label}>
              <th scope="row">{point.label}</th>
              <td>{point.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

// ---------------------------------------------------------------------------
function BarChart({
  data,
  type,
  scaleY,
  top,
  gridLines,
  width,
  height,
}: {
  data: Chart["data"];
  type: "bar" | "hbar";
  scaleY: (value: number) => number;
  /** Upper bound of the value axis, used to scale horizontal bars. */
  top: number;
  gridLines: { y: number; label: string }[];
  width: number;
  height: number;
}) {
  if (type === "hbar") {
    const rowH = 26;
    const h = Math.max(data.length * rowH + 16, 80);
    const max = top;
    return (
      <svg
        viewBox={`0 0 ${width} ${h}`}
        className="w-full"
        role="img"
        aria-label="Bar chart"
      >
        {data.map((point, index) => {
          const y = 8 + index * rowH;
          const w = Math.max((point.value / (max || 1)) * (width - 150), 2);
          return (
            <g key={`${point.label}-${index}`}>
              <text
                x={0}
                y={y + 15}
                className="fill-muted-foreground text-[11px]"
              >
                {point.label.length > 18
                  ? `${point.label.slice(0, 17)}…`
                  : point.label}
              </text>
              <rect
                x={110}
                y={y + 4}
                width={w}
                height={rowH - 12}
                rx={4}
                fill={PALETTE[index % PALETTE.length]}
              />
              <text
                x={116 + w}
                y={y + 15}
                className="fill-foreground text-[11px] font-semibold"
              >
                {formatValue(point.value)}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }

  const slot = PLOT_W / data.length;
  const barW = Math.min(slot * 0.62, 54);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Bar chart">
      {gridLines.map((line) => (
        <g key={line.y}>
          <line
            x1={PAD.left}
            x2={width - PAD.right}
            y1={line.y}
            y2={line.y}
            className="stroke-line"
            strokeDasharray="3 3"
          />
          <text
            x={PAD.left - 8}
            y={line.y + 4}
            textAnchor="end"
            className="fill-muted-foreground text-[10px]"
          >
            {line.label}
          </text>
        </g>
      ))}
      {data.map((point, index) => {
        const x = PAD.left + slot * index + (slot - barW) / 2;
        const y = scaleY(point.value);
        return (
          <g key={`${point.label}-${index}`}>
            <rect
              x={x}
              y={Math.min(y, scaleY(0))}
              width={barW}
              height={Math.max(Math.abs(scaleY(0) - y), 2)}
              rx={4}
              fill={PALETTE[index % PALETTE.length]}
            >
              <title>{`${point.label}: ${formatValue(point.value)}`}</title>
            </rect>
            <text
              x={x + barW / 2}
              y={height - 12}
              textAnchor="middle"
              className="fill-muted-foreground text-[10px]"
            >
              {point.label.length > 10
                ? `${point.label.slice(0, 9)}…`
                : point.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
function LineChart({
  data,
  scaleY,
  gridLines,
  gradientId,
}: {
  data: Chart["data"];
  scaleY: (value: number) => number;
  gridLines: { y: number; label: string }[];
  gradientId: string;
}) {
  const step = data.length > 1 ? PLOT_W / (data.length - 1) : 0;
  const points = data.map((point, index) => ({
    ...point,
    x: PAD.left + step * index,
    y: scaleY(point.value),
  }));
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${PAD.left},${scaleY(0)} ${line} ${points.at(-1)?.x ?? PAD.left},${scaleY(0)}`;

  return (
    <svg
      viewBox={`0 0 ${W} ${HEIGHT}`}
      className="w-full"
      role="img"
      aria-label="Line chart"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-brand-500)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--color-brand-500)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {gridLines.map((line) => (
        <g key={line.y}>
          <line
            x1={PAD.left}
            x2={W - PAD.right}
            y1={line.y}
            y2={line.y}
            className="stroke-line"
            strokeDasharray="3 3"
          />
          <text
            x={PAD.left - 8}
            y={line.y + 4}
            textAnchor="end"
            className="fill-muted-foreground text-[10px]"
          >
            {line.label}
          </text>
        </g>
      ))}
      <polygon points={area} fill={`url(#${gradientId})`} />
      <polyline
        points={line}
        fill="none"
        stroke="var(--color-brand-500)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.map((point, index) => (
        <g key={`${point.label}-${index}`}>
          <circle cx={point.x} cy={point.y} r={3.5} className="fill-card stroke-brand-500" strokeWidth={2}>
            <title>{`${point.label}: ${formatValue(point.value)}`}</title>
          </circle>
          <text
            x={point.x}
            y={HEIGHT - 12}
            textAnchor="middle"
            className="fill-muted-foreground text-[10px]"
          >
            {point.label.length > 10 ? `${point.label.slice(0, 9)}…` : point.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ---------------------------------------------------------------------------
function PieChart({
  data,
  total,
}: {
  data: Chart["data"];
  total: number;
}) {
  const size = 220;
  const radius = 88;
  const centre = size / 2;
  const magnitude = Math.abs(total) || 1;

  // Slices are laid out from 12 o'clock, accumulating the angle per point.
  const slices = data.map((point, index) => {
    const start = -Math.PI / 2 + (data.slice(0, index).reduce(
      (sum, earlier) => sum + (Math.abs(earlier.value) / magnitude) * Math.PI * 2,
      0,
    ));
    const end = start + (Math.abs(point.value) / magnitude) * Math.PI * 2;
    const large = end - start > Math.PI ? 1 : 0;
    const path = [
      `M ${centre} ${centre}`,
      `L ${centre + radius * Math.cos(start)} ${centre + radius * Math.sin(start)}`,
      `A ${radius} ${radius} 0 ${large} 1 ${centre + radius * Math.cos(end)} ${centre + radius * Math.sin(end)}`,
      "Z",
    ].join(" ");
    return { path, point, index };
  });

  return (
    <div className="flex flex-wrap items-center justify-center gap-6">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="size-52 shrink-0"
        role="img"
        aria-label="Pie chart"
      >
        {slices.map((slice) => (
          <path
            key={`${slice.point.label}-${slice.index}`}
            d={slice.path}
            fill={PALETTE[slice.index % PALETTE.length]}
            stroke="var(--color-card)"
            strokeWidth={1.5}
          >
            <title>{`${slice.point.label}: ${formatValue(slice.point.value)}`}</title>
          </path>
        ))}
      </svg>
      <ul className="space-y-1.5 text-xs">
        {data.map((point, index) => (
          <li key={`${point.label}-${index}`} className="flex items-center gap-2">
            <span
              className="size-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: PALETTE[index % PALETTE.length] }}
            />
            <span className="text-muted-foreground">{point.label}</span>
            <span className="ml-auto font-semibold tabular-nums">
              {formatValue(point.value)}
            </span>
            <span className="w-10 text-right text-muted-foreground tabular-nums">
              {Math.round((Math.abs(point.value) / magnitude) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
