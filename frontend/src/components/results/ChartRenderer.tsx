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
} from "recharts";
import { AlertTriangle, BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

function getChartData(rows: Record<string, unknown>[]) {
  if (!rows.length) return [];
  return rows.map((row) => ({ ...row }));
}

function inferNumericKeys(rows: Record<string, unknown>[]) {
  const first = rows[0] ?? {};
  return Object.keys(first).filter((key) => typeof first[key] === "number");
}

export function ChartRenderer({ rows }: { rows: Record<string, unknown>[] }) {
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

  if (!numericKeys.length) {
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

  const metricKey = numericKeys[0];
  const isSingleMetric = rows.length === 1 && numericKeys.length === 1 && Object.keys(rows[0] ?? {}).length <= 2;

  if (isSingleMetric) {
    const value = rows[0]?.[metricKey];
    return (
      <Card>
        <CardContent className="flex h-[320px] flex-col justify-center gap-3 p-6">
          <p className="text-[11px] uppercase tracking-[0.24em] text-muted-fg">Headline metric</p>
          <p className="text-5xl font-semibold tracking-tight text-fg">
            {typeof value === "number" ? value.toLocaleString() : String(value ?? "-")}
          </p>
          <p className="max-w-sm text-sm leading-6 text-muted-fg">
            A single-row result is clearer as a metric card than as a chart.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="h-[320px] p-4">
        <ResponsiveContainer width="100%" height="100%">
          {chartData.length > 1 ? (
            <LineChart data={chartData}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey={categoricalKey ?? metricKey} tick={{ fill: "#9aa6ba", fontSize: 12 }} />
              <YAxis tick={{ fill: "#9aa6ba", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#0a1322", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16 }} />
              <Line type="monotone" dataKey={metricKey} stroke="#fcba49" strokeWidth={2.5} dot={false} />
            </LineChart>
          ) : (
            <BarChart data={chartData}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey={categoricalKey ?? metricKey} tick={{ fill: "#9aa6ba", fontSize: 12 }} />
              <YAxis tick={{ fill: "#9aa6ba", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#0a1322", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16 }} />
              <Bar dataKey={metricKey} fill="#65b7ff" radius={[8, 8, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
