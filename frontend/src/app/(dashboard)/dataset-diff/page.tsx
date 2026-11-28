"use client";

import { useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Database, GitCompareArrows, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { compareDatasetVersions, getReplayWorkspace, listMetricSources, type DatasetDiffResult } from "@/lib/api";

export default function DatasetDiffPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const [sourceId, setSourceId] = useState("");
  const [oldVersionId, setOldVersionId] = useState("");
  const [newVersionId, setNewVersionId] = useState("");
  const [tableKey, setTableKey] = useState("");
  const [keys, setKeys] = useState("");
  const workspaceQuery = useQuery({
    queryKey: ["metrictrace", "replay-workspace"],
    queryFn: async () => getReplayWorkspace(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });
  const sourcesQuery = useQuery({
    queryKey: ["metrictrace", "sources", workspaceQuery.data?.workspace_id],
    queryFn: async () => listMetricSources(workspaceQuery.data!.workspace_id, await getToken()),
    enabled: Boolean(workspaceQuery.data?.workspace_id),
    retry: false,
  });
  const versions = useMemo(() => workspaceQuery.data?.options.dataset_versions.filter((version) => version.source_id === sourceId) ?? [], [workspaceQuery.data, sourceId]);
  const selectedSource = sourcesQuery.data?.sources.find((source) => source.id === sourceId);
  const selectedTable = selectedSource?.tables.find((table) => `${table.schema}.${table.table}` === tableKey) ?? (selectedSource?.tables.length === 1 ? selectedSource.tables[0] : undefined);
  const keyColumns = keys.split(",").map((key) => key.trim()).filter(Boolean);
  const compareMutation = useMutation({
    mutationFn: async () => compareDatasetVersions({
      workspace_id: workspaceQuery.data!.workspace_id,
      old_version_id: oldVersionId,
      new_version_id: newVersionId,
      key_columns: keyColumns,
      ...(selectedTable ? { old_table: selectedTable, new_table: selectedTable } : {}),
    }, await getToken()),
  });
  const needsTable = Boolean(selectedSource?.tables.length && selectedSource.tables.length > 1);
  const canCompare = Boolean(sourceId && oldVersionId && newVersionId && oldVersionId !== newVersionId && (!needsTable || selectedTable) && !compareMutation.isPending);

  function selectSource(value: string) {
    setSourceId(value);
    setOldVersionId("");
    setNewVersionId("");
    setTableKey("");
    compareMutation.reset();
  }

  return <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
    <Card className="overflow-hidden"><CardHeader className="border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(252,186,73,0.14),transparent_38%)]"><Badge className="w-fit border-accent/20 bg-accent/10 text-accent">Deterministic comparison</Badge><CardTitle className="mt-4 text-3xl">Dataset Diff</CardTitle><CardDescription className="mt-3 max-w-3xl text-base text-fg/72">Compare exactly two immutable versions with the shared DuckDB engine. Stable keys produce inserted, deleted, modified, and unchanged counts; keyless comparison remains explicitly multiset-only.</CardDescription></CardHeader></Card>
    <Card><CardHeader><CardTitle>Choose historical versions</CardTitle><CardDescription>Versions are read from workspace-owned snapshot metadata. The browser never supplies a file path.</CardDescription></CardHeader><CardContent className="space-y-5"><div className="grid gap-5 lg:grid-cols-2"><SelectField label="Data source" value={sourceId} onChange={selectSource} placeholder="Select an authorized source">{uniqueSources(workspaceQuery.data?.options.dataset_versions ?? []).map((source) => <option key={source.source_id} value={source.source_id}>{source.source_name}</option>)}</SelectField><TextField label="Stable key columns (optional)" value={keys} onChange={setKeys} placeholder="order_id, line_id" /><SelectField label="Older dataset version" value={oldVersionId} onChange={setOldVersionId} placeholder="Select a version" disabled={!sourceId}>{versions.map((version) => <option key={version.id} value={version.id}>{formatVersion(version.captured_at, version.content_hash)}</option>)}</SelectField><SelectField label="Newer dataset version" value={newVersionId} onChange={setNewVersionId} placeholder="Select a version" disabled={!sourceId}>{versions.map((version) => <option key={version.id} value={version.id}>{formatVersion(version.captured_at, version.content_hash)}</option>)}</SelectField>{selectedSource?.tables.length ? <SelectField label={needsTable ? "Captured table" : "Captured table (automatic)"} value={tableKey || (needsTable ? "" : `${selectedSource.tables[0].schema}.${selectedSource.tables[0].table}`)} onChange={setTableKey} placeholder="Select a table" disabled={!needsTable}>{selectedSource.tables.map((table) => <option key={`${table.schema}.${table.table}`} value={`${table.schema}.${table.table}`}>{table.schema}.{table.table}</option>)}</SelectField> : null}</div><div className="flex flex-col gap-3 border-t border-white/10 pt-5 sm:flex-row sm:items-center sm:justify-between"><p className="max-w-xl text-xs leading-5 text-muted-fg">Rows with duplicate or null stable keys are reported as non-comparable; MetricTrace will not fabricate row-level matches.</p><Button onClick={() => compareMutation.mutate()} disabled={!canCompare} aria-busy={compareMutation.isPending}>{compareMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitCompareArrows className="h-4 w-4" />}{compareMutation.isPending ? "Comparing versions" : "Compare versions"}</Button></div></CardContent></Card>
    {compareMutation.error && <ErrorNotice text={compareMutation.error instanceof Error ? compareMutation.error.message : "Dataset comparison failed."} />}
    {compareMutation.data && <DiffResult result={compareMutation.data} />}
    {!workspaceQuery.isLoading && !workspaceQuery.data?.options.dataset_versions.length && <Card><CardContent className="py-14 text-center"><Database className="mx-auto h-8 w-8 text-accent" /><h2 className="mt-4 text-lg font-semibold">No historical versions available</h2><p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-fg">Register a Data Source and complete at least two captures before running a historical comparison.</p></CardContent></Card>}
  </div>;
}

function DiffResult({ result }: { result: DatasetDiffResult }) {
  const { comparison } = result;
  const summary = comparison.summary;
  return <section className="space-y-6"><div className="flex flex-wrap items-center gap-3"><Badge className={summary.comparable ? "border-success/20 bg-success/10 text-success" : "border-danger/20 bg-danger/10 text-danger"}>{summary.comparable ? "Comparable" : "Not comparable"}</Badge><p className="text-sm text-muted-fg">Evidence fingerprint <span className="font-mono text-fg">{comparison.fingerprint.slice(0, 16)}</span></p></div>{summary.comparable ? <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Count label="Inserted" value={summary.inserted} /><Count label="Deleted" value={summary.deleted} /><Count label="Modified" value={summary.modified} /><Count label="Unchanged" value={summary.unchanged} /></div> : <ErrorNotice text={summary.reason ?? "The comparison is not available for these versions."} />}<div className="grid gap-6 lg:grid-cols-2"><Card><CardHeader><CardTitle>Schema changes</CardTitle><CardDescription>Column changes are evaluated before matching records.</CardDescription></CardHeader><CardContent>{comparison.schema_changes.length ? <ul className="space-y-2 text-sm">{comparison.schema_changes.map((change) => <li key={`${change.kind}-${change.column}`} className="rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2"><span className="font-medium text-fg">{change.column}</span><span className="ml-2 text-muted-fg">{change.kind.replaceAll("_", " ")}</span></li>)}</ul> : <p className="text-sm text-muted-fg">No schema differences detected.</p>}</CardContent></Card><Card><CardHeader><CardTitle>Changed records</CardTitle><CardDescription>Bounded evidence rows, never a complete unbounded export.</CardDescription></CardHeader><CardContent>{comparison.records.length ? <div className="space-y-3">{comparison.records.map((record, index) => <div key={`${record.kind}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.025] p-3"><div className="flex flex-wrap items-center gap-2"><Badge className="border-white/10 bg-white/6 text-fg/80">{record.kind}</Badge><code className="text-xs text-fg/85">{JSON.stringify(record.key)}</code></div>{record.changed_columns.length ? <p className="mt-2 text-xs text-muted-fg">Changed columns: {record.changed_columns.join(", ")}</p> : null}</div>)}</div> : <p className="text-sm text-muted-fg">No changed-record evidence is available for this comparison mode.</p>}</CardContent></Card></div></section>;
}

function SelectField({ label, value, onChange, placeholder, disabled, children }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; disabled?: boolean; children: React.ReactNode }) { return <label className="space-y-2"><span className="text-xs font-medium text-fg">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg disabled:cursor-not-allowed disabled:opacity-50"><option value="">{placeholder}</option>{children}</select></label>; }
function TextField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="space-y-2"><span className="text-xs font-medium text-fg">{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg placeholder:text-muted-fg" /></label>; }
function Count({ label, value }: { label: string; value: number | undefined }) { return <Card><CardContent className="py-4"><p className="text-[10px] uppercase tracking-[0.16em] text-muted-fg">{label}</p><p className="mt-2 font-mono text-2xl font-semibold text-fg">{value ?? "—"}</p></CardContent></Card>; }
function ErrorNotice({ text }: { text: string }) { return <div role="alert" className="flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-100"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{text}</span></div>; }
function uniqueSources(versions: Array<{ source_id: string; source_name: string }>) { return Array.from(new Map(versions.map((version) => [version.source_id, version])).values()); }
function formatVersion(capturedAt: string, hash: string) { return `${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(capturedAt))} · ${hash.slice(0, 12)}`; }
