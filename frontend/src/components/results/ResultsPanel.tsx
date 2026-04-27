"use client";

import type { QueryResult } from "@/types/agent";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { DataTable } from "./DataTable";
import { ChartRenderer } from "./ChartRenderer";
import { InsightCard } from "./InsightCard";
import { AnomalyBadge } from "./AnomalyBadge";

export function ResultsPanel({ results }: { results: QueryResult[] }) {
  if (!results.length) return null;
  const first = results.find((result) => result.success && result.rows.length > 0) ?? results[0];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Query Results
            <AnomalyBadge severity={first.success ? "low" : "medium"} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-[1.4fr,1fr]">
            <ChartRenderer rows={first.rows} />
            <div className="space-y-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="mb-2 text-[10px] uppercase tracking-[0.25em] text-muted-fg">SQL</p>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-fg/90">
                  {first.sql}
                </pre>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-muted-fg">
                {first.success ? `${first.rowCount ?? first.rows.length} rows returned.` : first.error ?? "No result"}
              </div>
            </div>
          </div>
          <Separator />
          <DataTable rows={first.rows} columns={first.columns} />
        </CardContent>
      </Card>

      {results.slice(1).map((result) => (
        <Card key={result.taskId}>
          <CardHeader>
            <CardTitle className="text-sm">{result.taskDescription}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-fg/90">
                {result.sql}
              </pre>
            </div>
            <DataTable rows={result.rows} columns={result.columns} />
          </CardContent>
        </Card>
      ))}

      <InsightCard
        title="What this means"
        summary="The dashboard surfaces the raw result set so the analyst can inspect the underlying data shape while the agent composes the narrative answer."
      />
    </div>
  );
}

