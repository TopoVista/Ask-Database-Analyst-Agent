"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { AlertCircle, CheckCircle2, FlaskConical, Loader2, RotateCcw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { runMetricTraceDemo, type MetricTraceDemoResult } from "@/lib/api";

const cellLabels: Record<string, string> = {
  old_data_old_definition: "Original data · original definition",
  old_data_new_definition: "Original data · proposed definition",
  new_data_old_definition: "Corrected data · original definition",
  new_data_new_definition: "Corrected data · proposed definition",
};

function formatMoney(value: string | null | undefined) {
  if (value === null || value === undefined) return "Unavailable";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
}

export default function ReplayPage() {
  const { getToken } = useAuth();
  const [result, setResult] = useState<MetricTraceDemoResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runDemo() {
    setPending(true);
    setError(null);
    try {
      setResult(await runMetricTraceDemo(await getToken()));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Replay could not be started.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <section className="grid gap-6 xl:grid-cols-[1.35fr,0.65fr]">
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(252,186,73,0.14),transparent_38%)]">
            <Badge className="w-fit border-accent/20 bg-accent/10 text-accent">Deterministic replay</Badge>
            <CardTitle className="mt-4 text-3xl">Why did a historical metric move?</CardTitle>
            <CardDescription className="mt-3 max-w-2xl text-base text-fg/72">Execute all four combinations of historical data and metric logic. Every cell is real DuckDB execution over an immutable Parquet snapshot.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-sm leading-6 text-muted-fg">Run the included no-AI fixture: Monday revenue changes from ₹24 lakh to ₹18 lakh after a late correction. A proposed definition change is evaluated separately.</p>
            <Button onClick={runDemo} disabled={pending} className="shrink-0" aria-busy={pending}>
              {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
              {pending ? "Replaying evidence" : result ? "Run again" : "Run canonical replay"}
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Replay guarantee</CardTitle><CardDescription>Values never come from an LLM.</CardDescription></CardHeader>
          <CardContent className="space-y-4 text-sm text-fg/76">
            <Guarantee text="Published snapshots have a canonical manifest hash." />
            <Guarantee text="Each cell retains its own data and definition IDs." />
            <Guarantee text="A failed cell is reported as failed, never as zero." />
          </CardContent>
        </Card>
      </section>

      {error && <div role="alert" className="flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-100"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div>}
      {!result && !pending && <Card><CardContent className="py-16 text-center"><RotateCcw className="mx-auto h-8 w-8 text-accent" /><h2 className="mt-4 text-lg font-semibold">Replay Lab is ready</h2><p className="mx-auto mt-2 max-w-md text-sm text-muted-fg">Start the deterministic fixture to populate the evidence grid. No provider credentials are required.</p></CardContent></Card>}
      {result && <ReplayResult result={result} />}
    </div>
  );
}

function Guarantee({ text }: { text: string }) {
  return <div className="flex gap-3"><CheckCircle2 className="h-4 w-4 shrink-0 text-success" /><span>{text}</span></div>;
}

function ReplayResult({ result }: { result: MetricTraceDemoResult }) {
  const cells = Object.fromEntries(result.cells.map((cell) => [cell.label, cell]));
  return <>
    <div className="flex items-center gap-3"><Badge className="border-success/20 bg-success/10 text-success">{result.status}</Badge><p className="text-sm text-fg/80">{result.headline}</p></div>
    <section className="grid gap-6 lg:grid-cols-2">
      <Card><CardHeader><CardTitle>Four-way replay</CardTitle><CardDescription>Data versions are the rows; definition versions are the columns.</CardDescription></CardHeader><CardContent><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="text-xs uppercase tracking-[0.16em] text-muted-fg"><tr><th className="px-3 py-3">Input pair</th><th className="px-3 py-3">Result</th><th className="px-3 py-3">State</th></tr></thead><tbody className="divide-y divide-white/10">{Object.keys(cellLabels).map((key) => { const cell = cells[key]; return <tr key={key}><td className="px-3 py-4 text-fg/82">{cellLabels[key]}</td><td className="px-3 py-4 font-mono text-fg">{formatMoney(cell?.result_inr)}</td><td className="px-3 py-4"><Badge className={cell?.status === "completed" ? "border-success/20 bg-success/10 text-success" : "border-danger/20 bg-danger/10 text-danger"}>{cell?.status ?? "missing"}</Badge>{cell?.error && <p className="mt-1 max-w-48 text-xs text-danger">{cell.error}</p>}</td></tr>; })}</tbody></table></div></CardContent></Card>
      <Card><CardHeader><CardTitle>Change attribution</CardTitle><CardDescription>Exact three-part decomposition, plus Shapley allocations that split the interaction fairly.</CardDescription></CardHeader><CardContent className="space-y-3"><Attribution label="Data effect" value={result.attribution?.data_effect} /><Attribution label="Definition effect" value={result.attribution?.definition_effect} /><Attribution label="Interaction effect" value={result.attribution?.interaction_effect} /><div className="my-4 border-t border-white/10" /><Attribution label="Total change" value={result.attribution?.total_change} strong /><div className="mt-5 rounded-xl border border-white/10 bg-white/[0.025] p-3"><p className="text-[10px] uppercase tracking-[0.16em] text-muted-fg">Shapley allocation</p><div className="mt-2 grid grid-cols-2 gap-3"><Attribution label="Data" value={result.attribution?.data_contribution} /><Attribution label="Definition" value={result.attribution?.definition_contribution} /></div></div><div className="mt-5 flex items-center gap-2 text-xs text-muted-fg">{result.attribution?.reconciles ? <CheckCircle2 className="h-4 w-4 text-success" /> : <AlertCircle className="h-4 w-4 text-danger" />}{result.attribution?.reconciles ? "Effects reconcile exactly to the total change." : "Attribution did not reconcile."}</div></CardContent></Card>
    </section>
    <Card><CardHeader><CardTitle>Evidence inputs</CardTitle><CardDescription>Exact immutable identifiers used by this replay.</CardDescription></CardHeader><CardContent className="grid gap-3 md:grid-cols-2">{Object.entries(result.inputs).map(([key, value]) => <div key={key} className="rounded-xl border border-white/10 bg-white/[0.03] p-3"><p className="text-[10px] uppercase tracking-[0.16em] text-muted-fg">{key.replaceAll("_", " ")}</p><p className="mt-2 break-all font-mono text-xs text-fg/85">{value}</p></div>)}</CardContent></Card>
  </>;
}

function Attribution({ label, value, strong = false }: { label: string; value?: string; strong?: boolean }) {
  return <div className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3"><span className={strong ? "font-semibold text-fg" : "text-fg/76"}>{label}</span><span className={strong ? "font-mono font-semibold text-accent" : "font-mono text-fg"}>{formatMoney(value)}</span></div>;
}
