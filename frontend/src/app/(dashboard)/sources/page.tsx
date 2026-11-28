"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Database, Loader2, Play, RefreshCw, Table2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  capturePostgresSource,
  createPostgresSource,
  discoverPostgresTables,
  getPostgresCapture,
  getReplayWorkspace,
  listConnections,
  listMetricSources,
  type MetricSourceRead,
  type PostgresDiscoveredTable,
} from "@/lib/api";

const terminalCaptureStates = new Set(["SUCCEEDED", "FAILED", "CANCELLED"]);

export default function SourcesPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const queryClient = useQueryClient();
  const [connectionId, setConnectionId] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [scheduleSeconds, setScheduleSeconds] = useState("");
  const [tables, setTables] = useState<PostgresDiscoveredTable[]>([]);
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [captureTask, setCaptureTask] = useState<{ sourceId: string; jobId: string } | null>(null);

  const workspaceQuery = useQuery({
    queryKey: ["metrictrace", "replay-workspace"],
    queryFn: async () => getReplayWorkspace(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });
  const connectionsQuery = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });
  const sourcesQuery = useQuery({
    queryKey: ["metrictrace", "sources", workspaceQuery.data?.workspace_id],
    queryFn: async () => listMetricSources(workspaceQuery.data!.workspace_id, await getToken()),
    enabled: Boolean(workspaceQuery.data?.workspace_id),
    retry: false,
  });
  const captureQuery = useQuery({
    queryKey: ["metrictrace", "capture", captureTask?.jobId],
    queryFn: async () => getPostgresCapture(captureTask!.sourceId, captureTask!.jobId, workspaceQuery.data!.workspace_id, await getToken()),
    enabled: Boolean(captureTask && workspaceQuery.data?.workspace_id),
    refetchInterval: (query) => terminalCaptureStates.has(query.state.data?.status ?? "") ? false : 1_500,
    refetchIntervalInBackground: true,
    retry: 1,
  });

  const postgresConnections = useMemo(
    () => (connectionsQuery.data ?? []).filter((connection) => ["postgres", "postgresql"].includes(connection.db_type.toLowerCase())),
    [connectionsQuery.data],
  );
  const discoverMutation = useMutation({
    mutationFn: async () => discoverPostgresTables({ workspace_id: workspaceQuery.data!.workspace_id, connection_id: connectionId }, await getToken()),
    onSuccess: (result) => {
      setTables(result.tables);
      setSelectedTables(result.tables.filter((table) => table.capture_supported).map(tableKey));
      setNotice(result.tables.length ? "Select the tables to capture. Unsupported tables cannot be selected." : "No readable user tables were found.");
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : "Catalog discovery failed."),
  });
  const createMutation = useMutation({
    mutationFn: async () => createPostgresSource({
      workspace_id: workspaceQuery.data!.workspace_id,
      connection_id: connectionId,
      name: sourceName.trim(),
      tables: tables.filter((table) => selectedTables.includes(tableKey(table))).map(({ schema, table }) => ({ schema, table })),
      ...(scheduleSeconds ? { schedule_seconds: Number(scheduleSeconds) } : {}),
    }, await getToken()),
    onSuccess: async () => {
      setNotice("Data source registered. Start a capture when you are ready to create immutable history.");
      setTables([]);
      setSelectedTables([]);
      setSourceName("");
      setScheduleSeconds("");
      await queryClient.invalidateQueries({ queryKey: ["metrictrace", "sources"] });
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : "Data source could not be registered."),
  });
  const captureMutation = useMutation({
    mutationFn: async (source: MetricSourceRead) => capturePostgresSource(source.id, workspaceQuery.data!.workspace_id, await getToken()),
    onSuccess: async (capture) => {
      setCaptureTask({ sourceId: capture.source_id, jobId: capture.job_id });
      setNotice("Capture queued. This page will continue to show its durable status.");
      await queryClient.invalidateQueries({ queryKey: ["metrictrace", "sources"] });
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : "Capture could not be queued."),
  });

  const captureStatus = captureQuery.data;
  const terminalCaptureStatus = terminalCaptureStates.has(captureStatus?.status ?? "") ? captureStatus?.status : null;
  useEffect(() => {
    if (terminalCaptureStatus) {
      queryClient.invalidateQueries({ queryKey: ["metrictrace", "sources"] }).catch(() => undefined);
      queryClient.invalidateQueries({ queryKey: ["metrictrace", "replay-workspace"] }).catch(() => undefined);
    }
  }, [queryClient, terminalCaptureStatus]);
  const canDiscover = Boolean(connectionId && workspaceQuery.data && !discoverMutation.isPending);
  const canRegister = Boolean(sourceName.trim() && selectedTables.length && !createMutation.isPending);

  return <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
    <Card className="overflow-hidden"><CardHeader className="border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(252,186,73,0.14),transparent_38%)]"><Badge className="w-fit border-accent/20 bg-accent/10 text-accent">Immutable source history</Badge><CardTitle className="mt-4 text-3xl">Data sources</CardTitle><CardDescription className="mt-3 max-w-3xl text-base text-fg/72">Discover tables through a saved, authorized PostgreSQL connection, select only capture-compatible objects, and publish a bounded repeatable-read snapshot through the durable worker queue.</CardDescription></CardHeader><CardContent className="grid gap-3 pt-6 sm:grid-cols-3"><Metric label="Sources" value={String(sourcesQuery.data?.sources.length ?? 0)} /><Metric label="Connections" value={String(postgresConnections.length)} /><Metric label="Workspace" value={workspaceQuery.data ? "Authorized" : "Loading"} /></CardContent></Card>
    {notice && <Notice message={notice} />}
    {captureTask && <CaptureProgress status={captureStatus} error={captureQuery.error instanceof Error ? captureQuery.error.message : null} onRetry={() => captureQuery.refetch()} />}
    <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <Card><CardHeader><CardTitle>Register a PostgreSQL source</CardTitle><CardDescription>Credentials remain in the encrypted connection record; they are never copied into a source or job payload.</CardDescription></CardHeader><CardContent className="space-y-5"><label className="block space-y-2"><span className="text-xs font-medium text-fg">Saved PostgreSQL connection</span><select value={connectionId} onChange={(event) => { setConnectionId(event.target.value); setTables([]); setSelectedTables([]); }} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg"><option value="">Select a connection</option>{postgresConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} · {connection.host}</option>)}</select></label><Button variant="secondary" onClick={() => discoverMutation.mutate()} disabled={!canDiscover}>{discoverMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Table2 className="h-4 w-4" />}{discoverMutation.isPending ? "Discovering tables" : "Discover tables"}</Button>{tables.length > 0 && <><div className="grid gap-4 md:grid-cols-2"><TextInput label="Source name" value={sourceName} onChange={setSourceName} placeholder="Production orders" /><TextInput label="Schedule seconds (optional)" value={scheduleSeconds} onChange={setScheduleSeconds} placeholder="300 or greater" type="number" /></div><TablePicker tables={tables} selected={selectedTables} onChange={setSelectedTables} /><Button onClick={() => createMutation.mutate()} disabled={!canRegister}>{createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}{createMutation.isPending ? "Registering source" : "Register source"}</Button></>}</CardContent></Card>
      <SourceList sources={sourcesQuery.data?.sources ?? []} loading={sourcesQuery.isLoading} onCapture={(source) => captureMutation.mutate(source)} capturing={captureMutation.isPending} />
    </div>
  </div>;
}

function CaptureProgress({ status, error, onRetry }: { status: { status: string; error: { message: string } | null; result: { dataset_version_id?: string; row_count?: number } | null } | undefined; error: string | null; onRetry: () => void }) {
  const failed = status?.status === "FAILED";
  return <Card><CardContent className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-start gap-3"><RefreshCw className={`mt-0.5 h-5 w-5 ${terminalCaptureStates.has(status?.status ?? "") ? "text-muted-fg" : "animate-spin text-accent"}`} /><div><p className="text-sm font-medium text-fg">Capture {status?.status?.toLowerCase() ?? "status loading"}</p><p className="mt-1 text-xs text-muted-fg">{status?.result?.dataset_version_id ? `Published dataset version ${status.result.dataset_version_id}` : status?.error?.message ?? error ?? "The worker state is authoritative and survives navigation."}</p></div></div>{failed && <Button variant="outline" size="sm" onClick={onRetry}>Refresh status</Button>}</CardContent></Card>;
}

function SourceList({ sources, loading, onCapture, capturing }: { sources: MetricSourceRead[]; loading: boolean; onCapture: (source: MetricSourceRead) => void; capturing: boolean }) {
  return <Card><CardHeader><CardTitle>Registered sources</CardTitle><CardDescription>Only ready, immutable versions are made available to Replay Lab.</CardDescription></CardHeader><CardContent className="space-y-3">{loading ? <p className="text-sm text-muted-fg">Loading sources…</p> : sources.length ? sources.map((source) => <div key={source.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-4"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><p className="font-medium text-fg">{source.name}</p><Badge className="border-white/10 bg-white/6 text-fg/80">{source.source_type}</Badge><Badge className={source.capture_status === "ready" ? "border-success/20 bg-success/10 text-success" : "border-accent/20 bg-accent/10 text-accent"}>{source.capture_status}</Badge></div><p className="mt-2 text-xs text-muted-fg">{source.tables.length} table{source.tables.length === 1 ? "" : "s"} · {source.version_count} immutable version{source.version_count === 1 ? "" : "s"}</p>{source.latest_captured_at && <p className="mt-1 text-xs text-muted-fg">Latest: {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(source.latest_captured_at))}</p>}</div>{source.source_type === "postgresql" && <Button variant="outline" size="sm" disabled={capturing || source.capture_status === "capturing" || source.capture_status === "queued"} onClick={() => onCapture(source)}><Play className="h-3.5 w-3.5" />Capture now</Button>}</div></div>) : <div className="rounded-2xl border border-dashed border-white/12 px-4 py-12 text-center text-sm text-muted-fg"><Database className="mx-auto mb-3 h-7 w-7 text-accent" />No registered source yet.</div>}</CardContent></Card>;
}

function TablePicker({ tables, selected, onChange }: { tables: PostgresDiscoveredTable[]; selected: string[]; onChange: (next: string[]) => void }) {
  return <div className="space-y-3"><div><p className="text-sm font-medium text-fg">Selectable tables</p><p className="mt-1 text-xs text-muted-fg">Unsupported types are shown for review but cannot be captured.</p></div><div className="max-h-80 space-y-2 overflow-y-auto rounded-2xl border border-white/10 p-3">{tables.map((table) => { const key = tableKey(table); const checked = selected.includes(key); return <label key={key} className={`flex gap-3 rounded-xl border p-3 ${table.capture_supported ? "cursor-pointer border-white/10 bg-white/[0.025]" : "border-danger/20 bg-danger/5 opacity-70"}`}><input type="checkbox" checked={checked} disabled={!table.capture_supported} onChange={() => onChange(checked ? selected.filter((item) => item !== key) : [...selected, key])} className="mt-1 h-4 w-4 accent-accent" /><span className="min-w-0"><span className="block font-mono text-sm text-fg">{table.schema}.{table.table}</span><span className="mt-1 block text-xs text-muted-fg">{table.capture_supported ? `${table.columns.length} columns${table.primary_key.length ? ` · primary key: ${table.primary_key.join(", ")}` : ""}` : table.unsupported_reason}</span></span></label>; })}</div></div>;
}

function TextInput({ label, value, onChange, placeholder, type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; type?: string }) { return <label className="space-y-2"><span className="text-xs font-medium text-fg">{label}</span><input type={type} min={type === "number" ? 300 : undefined} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg placeholder:text-muted-fg" /></label>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3"><p className="text-[10px] uppercase tracking-[0.16em] text-muted-fg">{label}</p><p className="mt-2 truncate text-sm font-medium text-fg">{value}</p></div>; }
function Notice({ message }: { message: string }) { const failed = /failed|could not|unsupported/i.test(message); return <div role="status" className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${failed ? "border-danger/30 bg-danger/10 text-red-100" : "border-success/20 bg-success/10 text-success"}`}><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{message}</span></div>; }
function tableKey(table: Pick<PostgresDiscoveredTable, "schema" | "table">) { return `${table.schema}.${table.table}`; }
