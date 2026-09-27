"use client";

import { useEffect, useState } from "react";
import { Brain, Loader2, Play, Wrench } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { invokeSpecialist, listSpecialists, type SpecialistInfo, type SpecialistInput } from "@/lib/api";
import type { DashboardResult } from "@/types/agent";
import { DashboardView } from "@/components/results/DashboardView";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type Values = Record<string, string>;
const field = (name: string, kind: SpecialistInput["kind"], required = true, defaultValue: unknown = null): SpecialistInput => ({ name, kind, required, default: defaultValue });
const FALLBACK_INPUTS: Record<string, SpecialistInput[]> = {
  assemble_dashboard: [field("query_results", "rows"), field("dashboard_title", "text", false, "Analysis Dashboard")],
  generate_narrative: [field("rows", "rows"), field("columns", "list"), field("title", "text", false)],
  suggest_layout: [field("panels", "rows")],
  detect_anomalies: [field("data", "rows"), field("columns", "list")],
  isolation_forest_detect: [field("data", "rows"), field("columns", "list")],
  zscore_detect: [field("data", "rows"), field("column", "text"), field("threshold", "number", false, 2)],
  iqr_detect: [field("data", "rows"), field("column", "text")],
  train_model: [field("data", "rows"), field("target", "text"), field("features", "list"), field("task", "text", false, "regression")],
  predict: [field("data", "rows")],
  moving_average: [field("values", "list"), field("window", "number", false, 3)],
  exponential_smoothing: [field("values", "list"), field("alpha", "number", false, 0.3)],
  trend: [field("values", "list")], seasonality: [field("values", "list"), field("period", "number", false)],
  change_points: [field("values", "list"), field("threshold", "number", false, 2)], forecast: [field("values", "list"), field("horizon", "number", false, 5)],
  decompose: [field("values", "list")], full_analysis: [field("values", "list"), field("column_name", "text", false)],
  tokenize: [field("text", "text")], sentiment: [field("text", "text")], entities: [field("text", "text")],
  keywords: [field("text", "text"), field("top_k", "number", false, 10)], summarize: [field("text", "text"), field("max_sentences", "number", false, 3)],
  analyze_column: [field("values", "list"), field("column_name", "text", false)],
  detect_confounders: [field("variables", "list"), field("treatment", "text"), field("outcome", "text")],
  generate_dag: [field("variables", "list"), field("treatment", "text"), field("outcome", "text")],
  estimate_causal_effect: [field("data", "rows"), field("treatment", "text"), field("outcome", "text"), field("confounders", "list")],
};

const humanize = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const splitList = (value: string, numeric = false) => value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean).map((item) => numeric ? Number(item) : item).filter((item) => !numeric || Number.isFinite(item));
const splitCsvLine = (line: string) => {
  const cells: string[] = []; let cell = ""; let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"' && line[index + 1] === '"' && quoted) { cell += char; index += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { cells.push(cell.trim()); cell = ""; }
    else cell += char;
  }
  return [...cells, cell.trim()];
};
const parseRows = (value: string) => {
  const [header = "", ...lines] = value.trim().split(/\r?\n/).filter(Boolean);
  const columns = splitCsvLine(header).filter(Boolean);
  const rows = lines.map((line) => Object.fromEntries(columns.map((column, index) => {
    const raw = splitCsvLine(line)[index] ?? "";
    const numeric = Number(raw);
    return [column, raw !== "" && Number.isFinite(numeric) ? numeric : raw];
  }))).filter((row) => Object.keys(row).length);
  return { columns, rows };
};

function valuesToParams(inputs: SpecialistInput[], values: Values) {
  const params: Record<string, unknown> = {};
  for (const input of inputs) {
    const value = values[input.name] ?? "";
    if (!value && !input.required) continue;
    if (input.kind === "number") params[input.name] = Number(value);
    else if (input.kind === "boolean") params[input.name] = value === "true";
    else if (input.kind === "list") params[input.name] = splitList(value, input.name === "values");
    else if (input.kind === "rows") {
      const { columns, rows } = parseRows(value);
      if (input.name === "query_results") {
        params[input.name] = [{ success: true, task_id: "manual", task_description: "Manual dataset analysis", columns, rows, row_count: rows.length }];
      } else {
        params[input.name] = rows;
        if (inputs.some((candidate) => candidate.name === "columns") && !values.columns) params.columns = columns;
      }
    } else if (input.kind !== "object") params[input.name] = value;
  }
  return params;
}

function isDashboard(value: unknown): value is DashboardResult {
  return Boolean(value && typeof value === "object" && Array.isArray((value as DashboardResult).panels));
}

export default function SpecialistsPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skill, setSkill] = useState("");
  const [values, setValues] = useState<Values>({});
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [invoking, setInvoking] = useState(false);
  const query = useQuery({ queryKey: ["specialists"], queryFn: async () => listSpecialists(await getToken()), enabled: isLoaded && Boolean(userId), retry: 1 });
  const specialists = query.data?.specialists ?? [];
  const selected = specialists.find((item) => item.id === selectedId) ?? null;
  const inputs = selected?.skill_inputs?.[skill] ?? FALLBACK_INPUTS[skill] ?? [];

  useEffect(() => {
    const first = selected?.skills[0] ?? "";
    setSkill(first); setValues({}); setResult(null); setError(null);
  }, [selectedId, selected?.skills]);

  const invoke = async () => {
    if (!selected || !skill) return;
    setInvoking(true); setError(null); setResult(null);
    try { setResult((await invokeSpecialist(selected.id, skill, valuesToParams(inputs, values), await getToken())).result); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Invocation failed"); }
    finally { setInvoking(false); }
  };

  const requiredMissing = inputs.some((input) => input.required && !values[input.name] && input.default == null);
  return <div className="mx-auto max-w-[1440px] space-y-8 px-4 py-7 md:px-6 lg:px-8">
    <Card><CardHeader className="border-b border-white/10 pb-6"><div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between"><div className="max-w-2xl"><Badge className="border-accent/20 bg-accent/10 text-accent">Specialist Agents</Badge><CardTitle className="mt-4 text-3xl">Specialist workbench</CardTitle><CardDescription className="mt-3 text-base text-fg/72">Choose an analytical skill, fill in its guided inputs, and inspect the result without writing JSON.</CardDescription></div><div className="grid gap-3 sm:grid-cols-3"><Metric label="Total" value={String(specialists.length)} icon={Brain}/><Metric label="Selected" value={selected?.name ?? "None"} icon={Wrench}/><Metric label="Status" value={invoking ? "Running" : "Ready"} icon={Play}/></div></div></CardHeader></Card>
    <div className="grid items-start gap-6 xl:grid-cols-[minmax(320px,0.8fr)_minmax(0,1.2fr)]"><SpecialistList specialists={specialists} selectedId={selectedId} loading={query.isLoading} error={query.error instanceof Error ? query.error.message : null} onSelect={setSelectedId}/><Card><CardHeader className="border-b border-white/10 pb-6"><CardTitle>{selected?.name ?? "Specialist details"}</CardTitle><CardDescription className="mt-2">{selected?.description ?? "Select a specialist to view its skills."}</CardDescription></CardHeader><CardContent className="space-y-6 pt-6">{selected ? <><div className="flex flex-wrap gap-2">{selected.capabilities.map((item) => <Badge key={item} className="border-white/10 bg-white/6 text-fg/80">{item}</Badge>)}</div>{selected.direct_invocation && selected.skills.length ? <><div className="space-y-3"><p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-fg">Choose a skill</p><div className="flex flex-wrap gap-2">{selected.skills.map((item) => <Button key={item} variant={skill === item ? "secondary" : "outline"} size="sm" onClick={() => { setSkill(item); setValues({}); setResult(null); }}>{humanize(item)}</Button>)}</div></div><div className="rounded-2xl border border-white/10 bg-white/[0.018] p-5"><div className="mb-5"><p className="text-sm font-semibold text-fg">Input details</p><p className="mt-1 text-sm text-muted-fg">Required fields are marked with an asterisk. Tables use a simple CSV format.</p></div><SkillForm inputs={inputs} values={values} onChange={(name, value) => setValues((current) => ({ ...current, [name]: value }))}/><div className="mt-6 flex items-center gap-3"><Button onClick={invoke} disabled={invoking || !selected.available || requiredMissing}>{invoking ? <Loader2 className="h-4 w-4 animate-spin"/> : <Play className="h-4 w-4"/>}Run {humanize(skill)}</Button>{requiredMissing && <span className="text-xs text-muted-fg">Complete the required fields to run this skill.</span>}</div></div></> : <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-muted-fg">This specialist runs automatically as part of the analysis workflow.</p>}{error && <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}{result !== null && (isDashboard(result) ? <DashboardView dashboard={result}/> : <Result value={result}/>)}</> : <Empty>Select a specialist.</Empty>}</CardContent></Card></div>
  </div>;
}

function SkillForm({ inputs, values, onChange, onUpload: suppliedUpload }: { inputs: SpecialistInput[]; values: Values; onChange: (name: string, value: string) => void; onUpload?: (name: string, file?: File) => void }) {
  if (!inputs.length) return null;
  const onUpload = suppliedUpload ?? (async (name: string, file?: File) => {
    if (!file || file.size > 1024 * 1024) return;
    if (!file.name.toLowerCase().endsWith(".csv") && file.type && file.type !== "text/csv") return;
    onChange(name, (await file.text()).replace(/^\uFEFF/, ""));
  });
  return <div className="grid gap-4 md:grid-cols-2">{inputs.map((input) => {
    const value = values[input.name] ?? (input.default == null ? "" : String(input.default));
    const csv = input.kind === "rows";
    const list = input.kind === "list";
    if (input.kind === "object") return <p key={input.name} className="md:col-span-2 text-xs text-muted-fg">{humanize(input.name)} is optional and is produced by the preceding specialist result.</p>;
    const label = input.name === "query_results" ? "Data rows" : humanize(input.name);
    return <label key={input.name} className={csv || input.name === "text" || list ? "space-y-2 md:col-span-2" : "space-y-2"}><span className="text-xs font-medium text-fg">{label}{input.required ? " *" : ""}</span>{input.kind === "boolean" ? <select value={value || "false"} onChange={(event) => onChange(input.name, event.target.value)} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg"><option value="false">No</option><option value="true">Yes</option></select> : csv || input.name === "text" || list ? <Textarea value={value} onChange={(event) => onChange(input.name, event.target.value)} placeholder={csv ? "region,revenue\nNorth,420\nSouth,280" : list ? "One value per line or comma-separated" : `Enter ${label.toLowerCase()}`} /> : <Input type={input.kind === "number" ? "number" : "text"} value={value} onChange={(event) => onChange(input.name, event.target.value)} />}{csv && <><span className="block text-xs text-muted-fg">Paste CSV: the first row is column names. This becomes the data table for the specialist.</span><span className="flex flex-wrap items-center gap-3"><span className="inline-flex cursor-pointer rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-fg transition hover:-translate-y-0.5 hover:border-accent/50 hover:bg-accent/10">Choose CSV file<input className="sr-only" type="file" accept=".csv,text/csv" onChange={(event) => onUpload(input.name, event.target.files?.[0])}/></span><span className="text-xs text-muted-fg">Read only in your browser; it is not uploaded or stored.</span></span></>}</label>;
  })}</div>;
}

function SpecialistList({ specialists, selectedId, loading, error, onSelect }: { specialists: SpecialistInfo[]; selectedId: string | null; loading: boolean; error: string | null; onSelect: (id: string) => void }) { return <Card><CardHeader className="pb-5"><CardTitle>Available specialists</CardTitle><CardDescription className="mt-1">Select a specialist</CardDescription></CardHeader><CardContent className="max-h-[680px] space-y-3 overflow-y-auto pt-0">{loading ? <p className="text-sm text-muted-fg">Loading...</p> : error ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">Could not load specialists: {error}</p> : specialists.map((item) => <button key={item.id} onClick={() => onSelect(item.id)} className={`w-full rounded-2xl border p-4 text-left transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_24px_rgba(0,0,0,0.16)] ${selectedId === item.id ? "border-white/20 bg-white/10" : "border-white/10 bg-white/[0.025] hover:border-white/20 hover:bg-white/5"}`}><div className="flex items-center justify-between gap-2"><p className="font-medium text-fg">{item.name}</p><Badge className={item.available ? "border-success/40 bg-success/10 text-success" : "border-white/10 bg-white/6 text-fg/60"}>{item.available ? "Ready" : "Offline"}</Badge></div><p className="mt-1 text-xs text-muted-fg line-clamp-2">{item.description}</p></button>)}</CardContent></Card>; }
function Metric({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) { return <div className="rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3 transition duration-200 hover:-translate-y-0.5 hover:border-white/20"><div className="flex items-center gap-2"><Icon className="h-4 w-4 text-accent"/><span className="text-[10px] uppercase tracking-[0.2em] text-muted-fg">{label}</span></div><p className="mt-2 text-sm font-semibold text-fg">{value}</p></div>; }
function Result({ value }: { value: unknown }) { return <pre className="overflow-x-auto rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] p-4 text-xs leading-5 text-fg/90">{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>; }
function Empty({ children }: { children: React.ReactNode }) { return <div className="rounded-2xl border border-dashed border-white/12 px-4 py-10 text-center text-sm text-muted-fg">{children}</div>; }
