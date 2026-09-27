"use client";

import type { DashboardResult } from "@/types/agent";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartRenderer } from "./ChartRenderer";

export function DashboardView({ dashboard }: { dashboard: DashboardResult }) {
  if (!dashboard.panels.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{dashboard.title}</CardTitle>
        <CardDescription>{dashboard.panel_count} evidence-backed panels assembled from this analysis.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5 xl:grid-cols-2">
        {dashboard.panels.map((panel) => (
          <section key={panel.id} className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.025] p-4">
            <ChartRenderer rows={panel.preview_rows} chartSpec={panel.chart_spec ?? null} />
            <div>
              <h3 className="text-sm font-medium text-fg">{panel.title}</h3>
              <p className="mt-1 text-sm leading-6 text-muted-fg">{panel.narrative}</p>
            </div>
          </section>
        ))}
      </CardContent>
    </Card>
  );
}
