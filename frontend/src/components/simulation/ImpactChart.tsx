"use client";

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Card, CardContent } from "@/components/ui/card";

export function ImpactChart({ data }: { data: Array<{ label: string; value: number }> }) {
  return (
    <Card>
      <CardContent className="h-[280px] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
            <XAxis dataKey="label" tick={{ fill: "#a7b0bf", fontSize: 12 }} />
            <YAxis tick={{ fill: "#a7b0bf", fontSize: 12 }} />
            <Tooltip contentStyle={{ background: "#08101f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} />
            <Line type="monotone" dataKey="value" stroke="#4cc9f0" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

