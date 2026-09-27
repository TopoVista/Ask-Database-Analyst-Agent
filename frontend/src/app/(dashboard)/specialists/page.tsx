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

const humanize = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const splitList = (value: string, numeric = false) => value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean).map((item) => numeric ? Number(item) : item).filter((item) => !numeric || Number.isFinite(item));
const parseRows = (value: string) => {
  const [header = "", ...lines] = value.trim().split(/\r?\n/).filter(Boolean);
  const columns = header.split(",").map((item) => item.trim()).filter(Boolean);
  const rows = lines.map((line) => Object.fromEntries(columns.map((column, index) => {
    const raw = line.split(",")[index]?.trim() ?? "";
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
  const inputs = selected?.skill_inputs?.[skill] ?? [];

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

  return <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
    <Card><CardHeader className="border-b border-white/10"><div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between"><div className="max-w-2xl"><Badge className="border-accent/20 bg-accent/10 text-accent">Specialist Agents</Badge><CardTitle className="mt-4 text-3xl">Specialist workbench</CardTitle><CardDescription className="mt-3 text-base text-fg/72">Choose an analytical skill, fill in its guided inputs, and inspect the result without writing JSON.</CardDescription></div><div className="grid gap-3 sm:grid-cols-3"><Metric label="Total" value={String(specialists.length)} icon={Brain}/><Metric label="Selected" value={selected?.name ?? "None"} icon={Wrench}/><Metric label="Status" value={invoking ? "Running" : "Ready"} icon={Play}/></div></div></CardHeader></Card>
    <div className="grid gap-6 xl:grid-cols-[0.4fr,0.6fr]"><SpecialistList specialists={specialists} selectedId={selectedId} loading={query.isLoading} error={query.error instanceof Error ? query.error.message : null} onSelect={setSelectedId}/><Card><CardHeader><CardTitle>{selected?.name ?? "Specialist details"}</CardTitle><CardDescription>{selected?.description ?? "Select a specialist to view its skills."}</CardDescription></CardHeader><CardContent className="space-y-5">{selected ? <><div className="flex flex-wrap gap-2">{selected.capabilities.map((item) => <Badge key={item} className="border-white/10 bg-white/6 text-fg/80">{item}</Badge>)}</div>{selected.direct_invocation && selected.skills.length ? <><div className="flex flex-wrap gap-2">{selected.skills.map((item) => <Button key={item} variant={skill === item ? "secondary" : "outline"} size="sm" onClick={() => { setSkill(item); setValues({}); setResult(null); }}>{humanize(item)}</Button>)}</div><SkillForm inputs={inputs} values={values} onChange={(name, value) => setValues((current) => ({ ...current, [name]: value }))}/><Button onClick={invoke} disabled={invoking || !selected.available || inputs.some((input) => input.required && !values[input.name])}>{invoking ? <Loader2 className="h-4 w-4 animate-spin"/> : <Play className="h-4 w-4"/>}Run {humanize(skill)}</Button></> : <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-muted-fg">This specialist runs automatically as part of the analysis workflow.</p>}{error && <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}{result !== null && (isDashboard(result) ? <DashboardView dashboard={result}/> : <Result value={result}/>)}</> : <Empty>Select a specialist.</Empty>}</CardContent></Card></div>
  </div>;
}

function SkillForm({ inputs, values, onChange }: { inputs: SpecialistInput[]; values: Values; onChange: (name: string, value: string) => void }) {
  if (!inputs.length) return null;
  return <div className="grid gap-4 md:grid-cols-2">{inputs.map((input) => {
    const value = values[input.name] ?? (input.default == null ? "" : String(input.default));
    const csv = input.kind === "rows";
    const list = input.kind === "list";
    if (input.kind === "object") return <p key={input.name} className="md:col-span-2 text-xs text-muted-fg">{humanize(input.name)} is optional and is produced by the preceding specialist result.</p>;
    return <label key={input.name} className={csv || input.name === "text" || list ? "space-y-2 md:col-span-2" : "space-y-2"}><span className="text-xs font-medium text-fg">{humanize(input.name)}{input.required ? " *" : ""}</span>{input.kind === "boolean" ? <select value={value || "false"} onChange={(event) => onChange(input.name, event.target.value)} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg"><option value="false">No</option><option value="true">Yes</option></select> : csv || input.name === "text" || list ? <Textarea value={value} onChange={(event) => onChange(input.name, event.target.value)} placeholder={csv ? "region,revenue\nNorth,420\nSouth,280" : list ? "One value per line or comma-separated" : `Enter ${humanize(input.name).toLowerCase()}`} /> : <Input type={input.kind === "number" ? "number" : "text"} value={value} onChange={(event) => onChange(input.name, event.target.value)} />}{csv && <span className="block text-xs text-muted-fg">Paste CSV: the first row is column names. This becomes the data table for the specialist.</span>}</label>;
  })}</div>;
}

function SpecialistList({ specialists, selectedId, loading, error, onSelect }: { specialists: SpecialistInfo[]; selectedId: string | null; loading: boolean; error: string | null; onSelect: (id: string) => void }) { return <Card><CardHeader><CardTitle>Available specialists</CardTitle><CardDescription>Select a specialist</CardDescription></CardHeader><CardContent className="space-y-3">{loading ? <p className="text-sm text-muted-fg">Loading...</p> : error ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-400">Could not load specialists: {error}</p> : specialists.map((item) => <button key={item.id} onClick={() => onSelect(item.id)} className={`w-full rounded-2xl border p-4 text-left transition ${selectedId === item.id ? "border-white/20 bg-white/10" : "border-white/10 bg-white/[0.025] hover:bg-white/5"}`}><div className="flex items-center justify-between gap-2"><p className="font-medium text-fg">{item.name}</p><Badge className={item.available ? "border-success/40 bg-success/10 text-success" : "border-white/10 bg-white/6 text-fg/60"}>{item.available ? "Ready" : "Offline"}</Badge></div><p className="mt-1 text-xs text-muted-fg line-clamp-2">{item.description}</p></button>)}</CardContent></Card>; }
function Metric({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) { return <div className="rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3"><div className="flex items-center gap-2"><Icon className="h-4 w-4 text-accent"/><span className="text-[10px] uppercase tracking-[0.2em] text-muted-fg">{label}</span></div><p className="mt-2 text-sm font-semibold text-fg">{value}</p></div>; }
function Result({ value }: { value: unknown }) { return <pre className="overflow-x-auto rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] p-4 text-xs leading-5 text-fg/90">{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>; }
function Empty({ children }: { children: React.ReactNode }) { return <div className="rounded-2xl border border-dashed border-white/12 px-4 py-10 text-center text-sm text-muted-fg">{children}</div>; }
