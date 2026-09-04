"use client";

import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
} from "recharts";
import { AlertTriangle, BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { ChartSpec } from "@/types/agent";

function getChartData(rows: Record<string, unknown>[]) {
  if (!rows.length) return [];
  return rows.map((row) => ({ ...row }));
}

function inferNumericKeys(rows: Record<string, unknown>[]) {
  const first = rows[0] ?? {};
  return Object.keys(first).filter((key) => typeof first[key] === "number");
}

const AXIS_TICK = { fill: "#9aa6ba", fontSize: 12 };
const TOOLTIP_STYLE = {
  background: "#0a1322",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 16,
};

function MetricCard({ label, value }: { label: string; value: unknown }) {
  return (
    <CardContent className="flex h-[320px] flex-col justify-center gap-3 p-6">
      <p className="text-[11px] uppercase tracking-[0.24em] text-muted-fg">Headline metric</p>
      <p className="text-5xl font-semibold tracking-tight text-fg">
        {typeof value === "number" ? value.toLocaleString() : String(value ?? "-")}
      </p>
      <p className="max-w-sm text-sm leading-6 text-muted-fg">
        A single-row result is clearer as a metric card than as a chart.
      </p>
      {label ? <p className="text-xs uppercase tracking-widest text-muted-fg">{label}</p> : null}
    </CardContent>
  );
}

function ChartCaption({ spec }: { spec: ChartSpec }) {
  return (
    <div className="flex flex-col gap-1 px-4 pb-2">
      <p className="text-sm font-medium text-fg">{spec.title}</p>
      {spec.rationale ? <p className="text-xs leading-5 text-muted-fg">{spec.rationale}</p> : null}
    </div>
  );
}

export function ChartRenderer({
  rows,
  chartSpec,
}: {
  rows: Record<string, unknown>[];
  chartSpec?: ChartSpec | null;
}) {
  if (!rows.length) {
    return (
      <Card>
        <CardContent className="flex h-[220px] flex-col items-start justify-center gap-3 p-6">
          <BarChart3 className="h-5 w-5 text-muted-fg" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-fg">No chart preview</p>
            <p className="text-sm text-muted-fg">This result did not return rows that can be visualized.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const chartData = getChartData(rows);
  const numericKeys = inferNumericKeys(rows);
  const categoricalKey = Object.keys(rows[0] ?? {}).find((key) => !numericKeys.includes(key));

  if (!numericKeys.length && chartSpec?.chart_type !== "bar") {
    return (
      <Card>
        <CardContent className="flex h-[220px] flex-col items-start justify-center gap-3 p-6">
          <AlertTriangle className="h-5 w-5 text-muted-fg" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-fg">No numeric chart fields</p>
            <p className="text-sm text-muted-fg">The query returned data, but not in a shape suitable for charting.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Fall back to local heuristics when no (or an unusable) spec was provided.
  const spec: ChartSpec = chartSpec ?? {
    chart_type:
      rows.length === 1 && numericKeys.length === 1
        ? "metric"
        : chartData.length > 1
          ? "line"
          : "bar",
    x: categoricalKey ?? null,
    y: numericKeys[0] ?? null,
    title: "Query result",
    rationale: "",
  };

  const metricKey = spec.y && numericKeys.includes(spec.y) ? spec.y : numericKeys[0];
  const xAxisKey = spec.x && spec.x in (rows[0] ?? {}) ? spec.x : (categoricalKey ?? metricKey);

  let chart: React.ReactNode;
  switch (spec.chart_type) {
    case "metric": {
      const value = rows[0]?.[metricKey];
      return (
        <Card>
          <MetricCard label={spec.title} value={value} />
        </Card>
      );
    }
    case "scatter":
      chart = (
        <ScatterChart>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
          <XAxis type="category" dataKey={xAxisKey} tick={AXIS_TICK} />
          <YAxis type="number" dataKey={metricKey} tick={AXIS_TICK} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Scatter data={chartData} fill="#65b7ff" />
        </ScatterChart>
      );
      break;
    case "bar":
    case "pie":
      chart = (
        <BarChart data={chartData}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
          <XAxis dataKey={xAxisKey} tick={AXIS_TICK} />
          <YAxis tick={AXIS_TICK} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey={metricKey} fill="#65b7ff" radius={[8, 8, 0, 0]} />
        </BarChart>
      );
      break;
    case "line":
    default:
      chart = (
        <LineChart data={chartData}>
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
          <XAxis dataKey={xAxisKey} tick={AXIS_TICK} />
          <YAxis tick={AXIS_TICK} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey={metricKey} stroke="#fcba49" strokeWidth={2.5} dot={false} />
        </LineChart>
      );
  }

  return (
    <Card>
      {spec.title || spec.rationale ? <ChartCaption spec={spec} /> : null}
      <CardContent className="h-[320px] p-4 pt-0">
        <ResponsiveContainer width="100%" height="100%">
          {chart}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
