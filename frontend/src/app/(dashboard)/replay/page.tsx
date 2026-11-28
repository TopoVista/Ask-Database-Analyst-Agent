"use client";

import { useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, CheckCircle2, CircleDashed, Database, Loader2, RefreshCw, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cancelReplay, getReplay, getReplayWorkspace, submitReplay, type ReplayOptions, type ReplayStatus } from "@/lib/api";

const cellLabels: Record<string, string> = {
  old_data_old_definition: "Original data · original definition",
  old_data_new_definition: "Original data · proposed definition",
  new_data_old_definition: "Corrected data · original definition",
  new_data_new_definition: "Corrected data · proposed definition",
};
const terminalReplayStates = new Set(["completed", "failed", "cancelled"]);

function formatMoney(value: string | null | undefined) {
  if (value === null || value === undefined) return "Unavailable";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
}

function isTerminal(status: string | undefined) { return terminalReplayStates.has(status ?? ""); }

export default function ReplayPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const replayId = searchParams.get("replay");
  const [sourceId, setSourceId] = useState("");
  const [oldVersionId, setOldVersionId] = useState("");
  const [newVersionId, setNewVersionId] = useState("");
  const [metricId, setMetricId] = useState("");
  const [oldDefinitionId, setOldDefinitionId] = useState("");
  const [newDefinitionId, setNewDefinitionId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const workspaceQuery = useQuery({
    queryKey: ["metrictrace", "replay-workspace"],
    queryFn: async () => getReplayWorkspace(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });
  const replayQuery = useQuery({
    queryKey: ["metrictrace", "replay", replayId],
    queryFn: async () => getReplay(replayId!, await getToken()),
    enabled: Boolean(replayId) && isLoaded && Boolean(userId),
    retry: 1,
    refetchInterval: (query) => (isTerminal(query.state.data?.status) ? false : 1_500),
    refetchIntervalInBackground: true,
  });
  const submitMutation = useMutation({
    mutationFn: async () => submitReplay({ workspace_id: workspaceQuery.data!.workspace_id, old_version_id: oldVersionId, new_version_id: newVersionId, old_definition_id: oldDefinitionId, new_definition_id: newDefinitionId }, await getToken()),
    onSuccess: (replay) => { setFormError(null); router.replace(`/replay?replay=${encodeURIComponent(replay.replay_id)}`); },
    onError: (error) => setFormError(error instanceof Error ? error.message : "Replay could not be started."),
  });
  const cancelMutation = useMutation({
    mutationFn: async () => cancelReplay(replayId!, await getToken()),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["metrictrace", "replay", replayId] }); },
  });
  const options = workspaceQuery.data?.options;
  const compatibilityError = useMemo(() => replayCompatibilityError(options, sourceId, oldVersionId, newVersionId, metricId, oldDefinitionId, newDefinitionId), [options, sourceId, oldVersionId, newVersionId, metricId, oldDefinitionId, newDefinitionId]);
  const replay = replayQuery.data;

  function selectSource(value: string) { setSourceId(value); setOldVersionId(""); setNewVersionId(""); setFormError(null); }
  function selectMetric(value: string) { setMetricId(value); setOldDefinitionId(""); setNewDefinitionId(""); setFormError(null); }
  function startReplay() {
    if (compatibilityError) { setFormError(compatibilityError); return; }
    submitMutation.mutate();
  }

  return <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
    <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
      <Card className="overflow-hidden"><CardHeader className="border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(252,186,73,0.14),transparent_38%)]"><Badge className="w-fit border-accent/20 bg-accent/10 text-accent">Deterministic replay</Badge><CardTitle className="mt-4 text-3xl">Why did a historical metric move?</CardTitle><CardDescription className="mt-3 max-w-2xl text-base text-fg/72">Execute every combination of two immutable dataset versions and two metric definitions. Replay state remains on the server, so this URL can be reopened safely.</CardDescription></CardHeader><CardContent className="grid gap-3 pt-6 sm:grid-cols-3"><ReplayMetric label="Workspace" value={workspaceQuery.data ? "Authorized" : workspaceQuery.isLoading ? "Loading" : "Unavailable"} /><ReplayMetric label="Execution" value={replay?.status ?? "Not started"} /><ReplayMetric label="Evidence cells" value={replay ? `${replay.cells.filter((cell) => cell.status === "completed").length}/4 complete` : "Four required"} /></CardContent></Card>
      <Card><CardHeader><CardTitle>Replay guarantee</CardTitle><CardDescription>Values never come from an LLM.</CardDescription></CardHeader><CardContent className="space-y-4 text-sm text-fg/76"><Guarantee text="Only workspace-authorized, immutable versions can be selected." /><Guarantee text="A failed or cancelled cell is never represented as zero." /><Guarantee text="Attribution appears only after all four cells succeed." /></CardContent></Card>
    </section>
    <ReplayInputPanel options={options} isLoading={workspaceQuery.isLoading} error={workspaceQuery.error instanceof Error ? workspaceQuery.error.message : null} sourceId={sourceId} oldVersionId={oldVersionId} newVersionId={newVersionId} metricId={metricId} oldDefinitionId={oldDefinitionId} newDefinitionId={newDefinitionId} formError={formError} compatibilityError={compatibilityError} pending={submitMutation.isPending} canSubmit={Boolean(workspaceQuery.data && !compatibilityError && !submitMutation.isPending)} onRetry={() => workspaceQuery.refetch()} onSourceChange={selectSource} onOldVersionChange={setOldVersionId} onNewVersionChange={setNewVersionId} onMetricChange={selectMetric} onOldDefinitionChange={setOldDefinitionId} onNewDefinitionChange={setNewDefinitionId} onSubmit={startReplay} />
    {replayQuery.error && replayId && <InlineError text={`The replay is still stored, but its latest status could not be loaded: ${replayQuery.error instanceof Error ? replayQuery.error.message : "network error"}`} action={<Button variant="outline" size="sm" onClick={() => replayQuery.refetch()}><RefreshCw className="h-3.5 w-3.5" />Retry status</Button>} />}
    {replayId && replayQuery.isLoading && <ReplayLoadingState />}
    {replay && <ReplayResult replay={replay} cancelling={cancelMutation.isPending} cancelError={cancelMutation.error instanceof Error ? cancelMutation.error.message : null} onCancel={() => cancelMutation.mutate()} onNewReplay={() => router.replace("/replay")} />}
  </div>;
}

function ReplayInputPanel(props: { options: ReplayOptions | undefined; isLoading: boolean; error: string | null; sourceId: string; oldVersionId: string; newVersionId: string; metricId: string; oldDefinitionId: string; newDefinitionId: string; formError: string | null; compatibilityError: string | null; pending: boolean; canSubmit: boolean; onRetry: () => void; onSourceChange: (value: string) => void; onOldVersionChange: (value: string) => void; onNewVersionChange: (value: string) => void; onMetricChange: (value: string) => void; onOldDefinitionChange: (value: string) => void; onNewDefinitionChange: (value: string) => void; onSubmit: () => void }) {
  if (props.isLoading) return <ReplayLoadingState />;
  if (props.error) return <InlineError text={`Replay inputs could not be loaded: ${props.error}`} action={<Button variant="outline" size="sm" onClick={props.onRetry}><RefreshCw className="h-3.5 w-3.5" />Retry</Button>} />;
  if (!props.options) return null;
  if (!props.options.dataset_versions.length || !props.options.metric_definitions.length) return <Card><CardContent className="py-14 text-center"><Database className="mx-auto h-8 w-8 text-accent" /><h2 className="mt-4 text-lg font-semibold">Replay inputs are not available yet</h2><p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-fg">Capture at least two ready versions from one data source and create two versions of one metric definition. Nothing has been inferred or filled with sample values.</p></CardContent></Card>;
  const sources = uniqueBy(props.options.dataset_versions, (version) => version.source_id);
  const versions = props.options.dataset_versions.filter((version) => version.source_id === props.sourceId);
  const metrics = uniqueBy(props.options.metric_definitions, (definition) => definition.metric_id);
  const definitions = props.options.metric_definitions.filter((definition) => definition.metric_id === props.metricId);
  return <Card><CardHeader className="border-b border-white/10"><Badge className="w-fit border-white/10 bg-white/6 text-fg/80">Replay inputs</Badge><CardTitle className="mt-4">Select exact historical evidence</CardTitle><CardDescription className="mt-2">Versions must originate from the same data source; definitions must belong to the same metric.</CardDescription></CardHeader><CardContent className="space-y-6 pt-6"><div className="grid gap-5 lg:grid-cols-2"><InputSelect id="replay-source" label="Data source" value={props.sourceId} onChange={props.onSourceChange} placeholder="Select an authorized source">{sources.map((source) => <option key={source.source_id} value={source.source_id}>{source.source_name}</option>)}</InputSelect><InputSelect id="replay-metric" label="Metric" value={props.metricId} onChange={props.onMetricChange} placeholder="Select a metric">{metrics.map((metric) => <option key={metric.metric_id} value={metric.metric_id}>{metric.metric_name}</option>)}</InputSelect><InputSelect id="replay-old-version" label="Original dataset version" value={props.oldVersionId} onChange={props.onOldVersionChange} placeholder="Select an older version" disabled={!props.sourceId}>{versions.map((version) => <option key={version.id} value={version.id}>{formatVersion(version.captured_at, version.content_hash)}</option>)}</InputSelect><InputSelect id="replay-new-version" label="Corrected dataset version" value={props.newVersionId} onChange={props.onNewVersionChange} placeholder="Select a newer version" disabled={!props.sourceId}>{versions.map((version) => <option key={version.id} value={version.id}>{formatVersion(version.captured_at, version.content_hash)}</option>)}</InputSelect><InputSelect id="replay-old-definition" label="Original metric definition" value={props.oldDefinitionId} onChange={props.onOldDefinitionChange} placeholder="Select a definition" disabled={!props.metricId}>{definitions.map((definition) => <option key={definition.id} value={definition.id}>Version {definition.version} · {definition.sql_hash.slice(0, 12)}</option>)}</InputSelect><InputSelect id="replay-new-definition" label="Proposed metric definition" value={props.newDefinitionId} onChange={props.onNewDefinitionChange} placeholder="Select a definition" disabled={!props.metricId}>{definitions.map((definition) => <option key={definition.id} value={definition.id}>Version {definition.version} · {definition.sql_hash.slice(0, 12)}</option>)}</InputSelect></div>{props.compatibilityError && <InlineError text={props.compatibilityError} />}{props.formError && <InlineError text={props.formError} />}<div className="flex flex-col gap-3 border-t border-white/10 pt-5 sm:flex-row sm:items-center sm:justify-between"><p className="max-w-xl text-xs leading-5 text-muted-fg">Submitting records the identifiers above as the authoritative inputs. The result is shareable through its replay URL.</p><Button onClick={props.onSubmit} disabled={!props.canSubmit} aria-busy={props.pending}>{props.pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CircleDashed className="h-4 w-4" />}{props.pending ? "Queuing replay" : "Run four-way replay"}</Button></div></CardContent></Card>;
}

function ReplayResult({ replay, cancelling, cancelError, onCancel, onNewReplay }: { replay: ReplayStatus; cancelling: boolean; cancelError: string | null; onCancel: () => void; onNewReplay: () => void }) {
  const cells = Object.fromEntries(replay.cells.map((cell) => [cell.label, cell]));
  const complete = replay.cells.filter((cell) => cell.status === "completed").length;
  const attributionReady = complete === 4 && replay.status === "completed" && replay.attribution !== null;
  const mayCancel = !isTerminal(replay.status);
  return <section className="space-y-6" aria-live="polite"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><StatusBadge status={replay.status} /><p className="text-sm text-fg/80">{complete} of 4 exact executions have completed.</p></div><div className="flex gap-2">{mayCancel && <Button variant="outline" size="sm" onClick={onCancel} disabled={cancelling}>{cancelling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}{cancelling ? "Cancelling" : "Cancel replay"}</Button>}<Button variant="outline" size="sm" onClick={onNewReplay}>New replay</Button></div></div>{cancelError && <InlineError text={`Cancellation could not be confirmed: ${cancelError}`} />}{replay.status === "failed" && <InlineError text="Replay execution failed. Inspect the affected cell below; no attribution has been calculated." />}{replay.status === "cancelled" && <InlineError text="Replay was cancelled before a complete evidence set was published. No attribution has been calculated." />}<section className="grid gap-6 lg:grid-cols-2"><Card><CardHeader><CardTitle>Four-way replay</CardTitle><CardDescription>Data versions are rows; metric definitions are columns.</CardDescription></CardHeader><CardContent><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="text-xs uppercase tracking-[0.16em] text-muted-fg"><tr><th className="px-3 py-3">Input pair</th><th className="px-3 py-3">Result</th><th className="px-3 py-3">State</th></tr></thead><tbody className="divide-y divide-white/10">{Object.keys(cellLabels).map((key) => { const cell = cells[key]; return <tr key={key}><td className="px-3 py-4 text-fg/82">{cellLabels[key]}</td><td className="px-3 py-4 font-mono text-fg">{formatMoney(cell?.result_inr)}</td><td className="px-3 py-4"><StatusBadge status={cell?.status ?? "missing"} />{cell?.retryable && <p className="mt-1 text-xs text-accent">Retry scheduled after a transient worker failure.</p>}{cell?.duration_ms > 0 && <p className="mt-1 text-xs text-muted-fg">{cell.duration_ms} ms</p>}{cell?.error && <p className="mt-1 max-w-48 text-xs text-danger">{cell.error}</p>}</td></tr>; })}</tbody></table></div></CardContent></Card><Card><CardHeader><CardTitle>Change attribution</CardTitle><CardDescription>Three-part decomposition with symmetric Shapley allocation.</CardDescription></CardHeader><CardContent>{attributionReady ? <div className="space-y-3"><Attribution label="Data effect" value={replay.attribution?.data_effect} /><Attribution label="Definition effect" value={replay.attribution?.definition_effect} /><Attribution label="Interaction effect" value={replay.attribution?.interaction_effect} /><div className="my-4 border-t border-white/10" /><Attribution label="Total change" value={replay.attribution?.total_change} strong /><div className="mt-5 rounded-xl border border-white/10 bg-white/[0.025] p-3"><p className="text-[10px] uppercase tracking-[0.16em] text-muted-fg">Shapley allocation</p><div className="mt-2 grid grid-cols-2 gap-3"><Attribution label="Data" value={replay.attribution?.data_contribution} /><Attribution label="Definition" value={replay.attribution?.definition_contribution} /></div></div><div className="mt-5 flex items-center gap-2 text-xs text-muted-fg"><CheckCircle2 className="h-4 w-4 text-success" />Effects reconcile exactly to the total change.</div></div> : <div className="flex min-h-52 flex-col items-center justify-center text-center"><CircleDashed className="h-7 w-7 text-accent" /><p className="mt-3 text-sm font-medium text-fg">Attribution is pending complete evidence</p><p className="mt-1 max-w-sm text-sm leading-6 text-muted-fg">MetricTrace waits for all four successful cells. Failed, cancelled, and unavailable results cannot be attributed.</p></div>}</CardContent></Card></section></section>;
}

function replayCompatibilityError(options: ReplayOptions | undefined, sourceId: string, oldVersionId: string, newVersionId: string, metricId: string, oldDefinitionId: string, newDefinitionId: string) {
  if (!options) return "Replay inputs are still loading.";
  if (!sourceId || !metricId || !oldVersionId || !newVersionId || !oldDefinitionId || !newDefinitionId) return "Select one data source, two dataset versions, one metric, and two definition versions.";
  if (oldVersionId === newVersionId) return "Select two different dataset versions.";
  if (oldDefinitionId === newDefinitionId) return "Select two different metric definition versions.";
  const versions = options.dataset_versions.filter((version) => version.id === oldVersionId || version.id === newVersionId);
  if (versions.length !== 2 || versions.some((version) => version.source_id !== sourceId)) return "Both dataset versions must be authorized versions of the selected data source.";
  const definitions = options.metric_definitions.filter((definition) => definition.id === oldDefinitionId || definition.id === newDefinitionId);
  if (definitions.length !== 2 || definitions.some((definition) => definition.metric_id !== metricId)) return "Both definitions must be authorized versions of the selected metric.";
  return null;
}

function uniqueBy<T>(items: T[], key: (item: T) => string) { return Array.from(new Map(items.map((item) => [key(item), item])).values()); }
function formatVersion(capturedAt: string, contentHash: string) { return `${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(capturedAt))} · ${contentHash.slice(0, 12)}`; }
function InputSelect({ id, label, value, onChange, placeholder, disabled, children }: { id: string; label: string; value: string; onChange: (value: string) => void; placeholder: string; disabled?: boolean; children: React.ReactNode }) { return <label className="space-y-2" htmlFor={id}><span className="text-xs font-medium text-fg">{label}</span><select id={id} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg outline-none transition focus:border-accent/60 focus:ring-2 focus:ring-accent/18 disabled:cursor-not-allowed disabled:opacity-50"><option value="">{placeholder}</option>{children}</select></label>; }
function StatusBadge({ status }: { status: string }) { const completed = status === "completed"; const failed = status === "failed" || status === "cancelled" || status === "missing"; return <Badge className={completed ? "border-success/20 bg-success/10 text-success" : failed ? "border-danger/20 bg-danger/10 text-danger" : "border-accent/20 bg-accent/10 text-accent"}>{status}</Badge>; }
function ReplayMetric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3"><p className="text-[10px] uppercase tracking-[0.16em] text-muted-fg">{label}</p><p className="mt-2 truncate text-sm font-medium text-fg">{value}</p></div>; }
function Guarantee({ text }: { text: string }) { return <div className="flex gap-3"><CheckCircle2 className="h-4 w-4 shrink-0 text-success" /><span>{text}</span></div>; }
function InlineError({ text, action }: { text: string; action?: React.ReactNode }) { return <div role="alert" className="flex flex-col gap-3 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-100 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-start gap-3"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{text}</span></div>{action}</div>; }
function ReplayLoadingState() { return <Card aria-busy="true"><CardContent className="flex min-h-36 items-center justify-center gap-3 text-sm text-muted-fg"><Loader2 className="h-5 w-5 animate-spin text-accent" />Loading authoritative replay state…</CardContent></Card>; }
function Attribution({ label, value, strong = false }: { label: string; value?: string; strong?: boolean }) { return <div className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3"><span className={strong ? "font-semibold text-fg" : "text-fg/76"}>{label}</span><span className={strong ? "font-mono font-semibold text-accent" : "font-mono text-fg"}>{formatMoney(value)}</span></div>; }
