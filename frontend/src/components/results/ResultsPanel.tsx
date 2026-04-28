"use client";

import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
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
  const rowLabel = `${first.rowCount ?? first.rows.length} ${first.rowCount === 1 || first.rows.length === 1 ? "row" : "rows"} returned`;

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
                <ResultStatus result={first} fallbackLabel={rowLabel} />
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
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-muted-fg">
              <ResultStatus
                result={result}
                fallbackLabel={`${result.rowCount ?? result.rows.length} ${result.rowCount === 1 || result.rows.length === 1 ? "row" : "rows"} returned`}
              />
            </div>
            {result.rows.length ? <DataTable rows={result.rows} columns={result.columns} /> : null}
          </CardContent>
        </Card>
      ))}

      <InsightCard
        title="What this means"
        summary="The SQL and table below let you inspect the exact data behind the agent's answer."
      />
    </div>
  );
}

function ResultStatus({ result, fallbackLabel }: { result: QueryResult; fallbackLabel: string }) {
  if (!result.success) {
    return (
      <div className="flex items-start gap-2 text-red-300">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-medium text-red-200">This query step failed</p>
          <p className="mt-1 text-sm text-red-300/90">{sanitizeError(result.error)}</p>
        </div>
      </div>
    );
  }

  if (!result.rows.length) {
    return (
      <div className="flex items-start gap-2">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-fg" />
        <div>
          <p className="font-medium text-fg">No rows returned</p>
          <p className="mt-1 text-sm text-muted-fg">The SQL ran successfully, but no matching data was returned for this step.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
      <span>{fallbackLabel}</span>
    </div>
  );
}

function sanitizeError(error: string | null | undefined) {
  if (!error) return "The database query did not complete successfully.";
  const compact = error.replace(/\s+/g, " ").trim();
  const lowered = compact.toLowerCase();

  if (lowered.includes("does not exist")) {
    return "The generated SQL referenced a table or column that does not exist in this schema.";
  }
  if (lowered.includes("syntax error")) {
    return "The generated SQL had a syntax problem and could not be executed.";
  }
  if (lowered.includes("permission denied")) {
    return "The connected database user does not have permission to run this query.";
  }

  return compact.length > 220 ? `${compact.slice(0, 217)}...` : compact;
}
