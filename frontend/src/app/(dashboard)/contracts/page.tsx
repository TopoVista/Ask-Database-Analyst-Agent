"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ClipboardCheck, Loader2, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { createMetricContract, evaluateMetricContract, getReplayWorkspace, listMetricContracts, type ContractEvaluation, type MetricContractRead } from "@/lib/api";

const EXAMPLE = JSON.stringify([
  { id: "revenue-is-non-negative", type: "non_negative", table: "source_data", column: "amount_inr" },
  { id: "required-revenue-columns", type: "required_columns", table: "source_data", columns: ["order_id", "amount_inr"] },
], null, 2);

export default function ContractsPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("Revenue data invariant");
  const [definition, setDefinition] = useState(EXAMPLE);
  const [versionId, setVersionId] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const workspaceQuery = useQuery({ queryKey: ["metrictrace", "replay-workspace"], queryFn: async () => getReplayWorkspace(await getToken()), enabled: isLoaded && Boolean(userId), retry: false });
  const contractsQuery = useQuery({ queryKey: ["metrictrace", "contracts", workspaceQuery.data?.workspace_id], queryFn: async () => listMetricContracts(workspaceQuery.data!.workspace_id, await getToken()), enabled: Boolean(workspaceQuery.data?.workspace_id), retry: false });
  const versions = workspaceQuery.data?.options.dataset_versions ?? [];
  const createMutation = useMutation({
    mutationFn: async () => {
      let contracts: Array<Record<string, unknown>>;
      try {
        const parsed: unknown = JSON.parse(definition);
        if (!Array.isArray(parsed) || !parsed.length || parsed.some((item) => !item || typeof item !== "object" || Array.isArray(item))) throw new Error("Definition must be a non-empty JSON array of contract objects.");
        contracts = parsed as Array<Record<string, unknown>>;
      } catch (error) {
        const message = error instanceof Error ? error.message : "The contract JSON is invalid.";
        setParseError(message);
        throw error;
      }
      setParseError(null);
      return createMetricContract({ workspace_id: workspaceQuery.data!.workspace_id, name: name.trim(), contracts }, await getToken());
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["metrictrace", "contracts", workspaceQuery.data?.workspace_id] }),
  });
  const evaluateMutation = useMutation({
    mutationFn: async (contractId: string) => evaluateMetricContract(contractId, { workspace_id: workspaceQuery.data!.workspace_id, dataset_version_id: versionId }, await getToken()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["metrictrace", "contracts", workspaceQuery.data?.workspace_id] }),
  });
  const canCreate = Boolean(name.trim() && definition.trim() && !createMutation.isPending);

  return <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6 lg:px-8">
    <Card className="overflow-hidden"><CardHeader className="border-b border-white/10 bg-[radial-gradient(circle_at_10%_0%,rgba(82,196,168,0.14),transparent_38%)]"><Badge className="w-fit border-success/20 bg-success/10 text-success">Deterministic governance</Badge><CardTitle className="mt-4 text-3xl">Metric Contracts</CardTitle><CardDescription className="mt-3 max-w-3xl text-base text-fg/72">Version declarative data invariants, explicitly run them against an immutable dataset, and retain the observed evidence. Contract execution never evaluates arbitrary expressions.</CardDescription></CardHeader></Card>
    <Card><CardHeader><CardTitle>New contract version</CardTitle><CardDescription>Saving the same name creates the next immutable version. Use the manifest SQL name <span className="font-mono">source_data</span> for imported datasets.</CardDescription></CardHeader><CardContent className="space-y-5"><label className="block space-y-2"><span className="text-xs font-medium text-fg">Contract name</span><input value={name} onChange={(event) => setName(event.target.value)} maxLength={255} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg" /></label><label className="block space-y-2"><span className="text-xs font-medium text-fg">Contract definition (JSON)</span><Textarea value={definition} onChange={(event) => setDefinition(event.target.value)} className="min-h-64 font-mono text-xs leading-6" aria-describedby="contract-definition-help" /></label><p id="contract-definition-help" className="text-xs text-muted-fg">Supported types include non_null, minimum, maximum, non_negative, primary_key_unique, required_columns, schema_type, freshness, referential_integrity, sql_assertion, and cross_metric_reconciliation.</p>{parseError && <Notice tone="error" text={parseError} />}{createMutation.error && <Notice tone="error" text={errorText(createMutation.error, "Contract definition could not be saved.")} />}<Button onClick={() => createMutation.mutate()} disabled={!canCreate} aria-busy={createMutation.isPending}>{createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}{createMutation.isPending ? "Saving version" : "Save immutable version"}</Button></CardContent></Card>
    <Card><CardHeader><CardTitle>Evaluate historical evidence</CardTitle><CardDescription>An evaluation is an explicit state-changing action. It records exactly the selected immutable version and all contract outcomes.</CardDescription></CardHeader><CardContent className="flex flex-col gap-4 sm:flex-row sm:items-end"><label className="min-w-0 flex-1 space-y-2"><span className="text-xs font-medium text-fg">Dataset version</span><select value={versionId} onChange={(event) => setVersionId(event.target.value)} className="h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-sm text-fg"><option value="">Select immutable evidence</option>{versions.map((version) => <option key={version.id} value={version.id}>{version.source_name} · {formatVersion(version.captured_at, version.content_hash)}</option>)}</select></label><p className="max-w-md text-xs leading-5 text-muted-fg">For PostgreSQL captures, contract table names are each selected table’s lower-case SQL name. Unavailable mandatory inputs are recorded, never silently passed.</p></CardContent></Card>
    {contractsQuery.isLoading && <Notice tone="neutral" text="Loading saved contract versions…" />}
    {contractsQuery.error && <Notice tone="error" text={errorText(contractsQuery.error, "Contract history could not be loaded.")} />}
    {evaluateMutation.error && <Notice tone="error" text={errorText(evaluateMutation.error, "Contract evaluation failed.")} />}
    {contractsQuery.data?.contracts.length === 0 && <Notice tone="neutral" text="No contract versions have been saved for this workspace yet." />}
    <section className="space-y-4">{contractsQuery.data?.contracts.map((contract) => <ContractCard key={contract.id} contract={contract} canEvaluate={Boolean(versionId) && !evaluateMutation.isPending} isEvaluating={evaluateMutation.isPending && evaluateMutation.variables === contract.id} onEvaluate={() => evaluateMutation.mutate(contract.id)} />)}</section>
  </div>;
}

function ContractCard({ contract, canEvaluate, isEvaluating, onEvaluate }: { contract: MetricContractRead; canEvaluate: boolean; isEvaluating: boolean; onEvaluate: () => void }) { const latest = contract.latest_evaluation; return <Card><CardHeader><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><CardTitle>{contract.name}</CardTitle><Badge className="border-white/10 bg-white/6 text-fg/80">v{contract.version}</Badge>{latest && <StatusBadge status={latest.status} />}</div><CardDescription className="mt-2 font-mono text-xs">{contract.definition_hash.slice(0, 16)} · {contract.contracts.length} checks</CardDescription></div><Button size="sm" onClick={onEvaluate} disabled={!canEvaluate} aria-busy={isEvaluating}>{isEvaluating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />}{isEvaluating ? "Evaluating" : "Evaluate"}</Button></div></CardHeader><CardContent>{latest ? <EvaluationEvidence evaluation={latest} /> : <p className="text-sm text-muted-fg">No immutable dataset has been evaluated against this version.</p>}</CardContent></Card>; }
function EvaluationEvidence({ evaluation }: { evaluation: ContractEvaluation }) { const outcomes = evaluation.report.report.outcomes; return <div className="space-y-4"><div className="flex flex-wrap gap-3 text-xs text-muted-fg"><span>Dataset <span className="font-mono text-fg">{evaluation.dataset_version_id.slice(0, 12)}</span></span><span>Evidence <span className="font-mono text-fg">{evaluation.input_fingerprint.slice(0, 16)}</span></span><span>{new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(evaluation.created_at))}</span></div><div className="space-y-2">{outcomes.map((outcome) => <div key={outcome.id} className="flex flex-col gap-2 rounded-xl border border-white/10 bg-white/[0.025] p-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-sm font-medium text-fg">{outcome.id} <span className="font-normal text-muted-fg">· {outcome.type}</span></p>{outcome.message && <p className="mt-1 text-xs text-muted-fg">{outcome.message}</p>}</div><StatusBadge status={outcome.status} /></div>)}</div></div>; }
function StatusBadge({ status }: { status: string }) { const pass = status === "PASS"; const error = status === "ERROR" || status === "FAIL"; return <Badge className={pass ? "border-success/20 bg-success/10 text-success" : error ? "border-danger/20 bg-danger/10 text-danger" : "border-white/10 bg-white/6 text-fg/80"}>{status}</Badge>; }
function Notice({ tone, text }: { tone: "error" | "neutral"; text: string }) { return <div role={tone === "error" ? "alert" : "status"} className={tone === "error" ? "flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-100" : "rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3 text-sm text-muted-fg"}>{tone === "error" ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> : null}<span>{text}</span></div>; }
function errorText(error: unknown, fallback: string) { return error instanceof Error ? error.message : fallback; }
function formatVersion(capturedAt: string, hash: string) { return `${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(capturedAt))} · ${hash.slice(0, 12)}`; }
