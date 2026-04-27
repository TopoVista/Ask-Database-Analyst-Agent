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
        <CardContent className="py-8 text-sm text-muted-fg">No chart data available.</CardContent>
      </Card>
    );
  }

  const chartData = getChartData(rows);
  const numericKeys = inferNumericKeys(rows);
  const categoricalKey = Object.keys(rows[0] ?? {}).find((key) => !numericKeys.includes(key));

  if (!numericKeys.length) {
    return (
      <Card>
        <CardContent className="py-8 text-sm text-muted-fg">The result set does not contain numeric fields for a chart.</CardContent>
      </Card>
    );
  }

  const metricKey = numericKeys[0];

  return (
    <Card>
      <CardContent className="h-[320px] p-4">
        <ResponsiveContainer width="100%" height="100%">
          {chartData.length > 1 ? (
            <LineChart data={chartData}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey={categoricalKey ?? metricKey} tick={{ fill: "#a7b0bf", fontSize: 12 }} />
              <YAxis tick={{ fill: "#a7b0bf", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#08101f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} />
              <Line type="monotone" dataKey={metricKey} stroke="#f5b942" strokeWidth={2.5} dot={false} />
            </LineChart>
          ) : (
            <BarChart data={chartData}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
              <XAxis dataKey={categoricalKey ?? metricKey} tick={{ fill: "#a7b0bf", fontSize: 12 }} />
              <YAxis tick={{ fill: "#a7b0bf", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#08101f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} />
              <Bar dataKey={metricKey} fill="#4cc9f0" radius={[8, 8, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

