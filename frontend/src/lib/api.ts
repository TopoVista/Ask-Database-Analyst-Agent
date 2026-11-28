import { API_URL } from "@/lib/constants";
import type { ConnectionCreate, ConnectionRead, QueryHistoryRead, SessionRead, SchemaResponse } from "@/types/api";

async function readJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text.trim()) {
    throw new Error("Server returned an empty response.");
  }

  try {
    return JSON.parse(text) as T;
  } catch (error) {
    console.error("INVALID JSON RESPONSE:", text);
    throw new Error("Invalid response from server.");
  }
}

async function apiFetch<T>(path: string, token?: string | null, init: RequestInit = {}): Promise<T> {
  try {
    const url = `${API_URL}${path}`;
    console.log("CALLING:", url);
    const headers = new Headers(init.headers);

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const shouldSendJsonContentType = init.body !== undefined && !(init.body instanceof FormData) && !headers.has("Content-Type");
    if (shouldSendJsonContentType) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
    });

    console.log("STATUS:", response.status);

    if (!response.ok) {
      const text = await response.text();
      console.error("ERROR RESPONSE:", text);
      try {
        const parsed = JSON.parse(text);
        const message =
          typeof parsed?.detail === "string"
            ? parsed.detail
            : typeof parsed?.message === "string"
              ? parsed.message
              : text;
        throw new Error(message || `Request failed: ${response.status}`);
      } catch {
        throw new Error(text || `Request failed: ${response.status}`);
      }
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return await readJsonResponse<T>(response);
  } catch (err) {
    console.error("FETCH FAILED:", err);
    throw err;
  }
}

export async function createConnection(payload: ConnectionCreate, token?: string | null) {
  return apiFetch<ConnectionRead>("/api/v1/connections", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function testConnection(connectionId: string, token?: string | null) {
  return apiFetch<{ success: boolean; message: string }>(`/api/v1/connections/${connectionId}/test`, token, {
    method: "POST",
  });
}

export async function deleteConnection(connectionId: string, token?: string | null) {
  return apiFetch<void>(`/api/v1/connections/${connectionId}`, token, {
    method: "DELETE",
  });
}

export async function getSchema(connectionId: string, token?: string | null) {
  return apiFetch<SchemaResponse>(`/api/v1/schema/${connectionId}`, token);
}

export async function listConnections(token?: string | null) {
  return apiFetch<ConnectionRead[]>("/api/v1/connections", token);
}

export async function listSessions(token?: string | null) {
  return apiFetch<SessionRead[]>("/api/v1/sessions", token);
}

export async function getSession(sessionId: string, token?: string | null) {
  return apiFetch<{ session: SessionRead; history: QueryHistoryRead[] }>(`/api/v1/sessions/${sessionId}`, token);
}

// --- Specialists ---

export interface SpecialistInfo {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  supported_data_types: string[];
  tools: string[];
  available: boolean;
  direct_invocation: boolean;
  skills: string[];
  skill_inputs?: Record<string, SpecialistInput[]>;
}

export interface SpecialistInput {
  name: string;
  kind: "text" | "number" | "boolean" | "list" | "rows" | "object";
  required: boolean;
  default: unknown;
}

export async function listSpecialists(token?: string | null) {
  return apiFetch<{ specialists: SpecialistInfo[]; count: number }>("/api/v1/specialists", token);
}

// --- Evaluation ---

export interface AuditFinding {
  severity: string;
  category: string;
  message: string;
  details: string;
}

export interface SecurityAuditResult {
  passed: boolean;
  findings: AuditFinding[];
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export async function runSecurityAudit(token?: string | null) {
  return apiFetch<SecurityAuditResult>("/api/v1/evaluation/security-audit", token);
}

// --- Datasets ---

export interface DatasetRead {
  id: string;
  name: string;
  filename: string;
  source_type: string;
  row_count: number | null;
  column_count: number | null;
  created_at: string;
  descriptor: Record<string, unknown> | null;
}

export interface DatasetListResponse {
  datasets: DatasetRead[];
  total: number;
}

export interface TablePreviewResponse {
  dataset_id: string;
  table_name: string;
  columns: string[];
  rows_preview: Record<string, unknown>[];
}

export async function listDatasets(token?: string | null) {
  return apiFetch<DatasetListResponse>("/api/v1/datasets", token);
}

export async function uploadDataset(file: File, token?: string | null) {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<DatasetRead>("/api/v1/datasets", token, {
    method: "POST",
    body: formData,
  });
}

export async function getDataset(datasetId: string, token?: string | null) {
  return apiFetch<DatasetRead>(`/api/v1/datasets/${datasetId}`, token);
}

export async function profileDataset(datasetId: string, token?: string | null) {
  return apiFetch<DatasetRead>(`/api/v1/datasets/${datasetId}/profile`, token, {
    method: "POST",
  });
}

export async function previewDataset(datasetId: string, token?: string | null, limit = 20) {
  return apiFetch<TablePreviewResponse>(
    `/api/v1/datasets/${datasetId}/preview?limit=${limit}`,
    token
  );
}

export async function deleteDataset(datasetId: string, token?: string | null) {
  return apiFetch<void>(`/api/v1/datasets/${datasetId}`, token, {
    method: "DELETE",
  });
}

// --- Simulation ---

export interface SimulationRequest {
  question: string;
  parameters: Record<string, string | number | boolean>;
}

// --- Specialists ---

export async function invokeSpecialist(
  specialistId: string,
  skill: string,
  params: Record<string, unknown>,
  token?: string | null
) {
  return apiFetch<{ specialist_id: string; skill: string; result: unknown }>(
    `/api/v1/specialists/${specialistId}/invoke`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ skill, params }),
    }
  );
}

// --- Evaluation Benchmarks ---

export interface BenchmarkResult {
  benchmark_id: string;
  mode?: string;
  total_cases: number;
  passed: number;
  failed: number;
  accuracy: number;
  total_time_ms: number;
  cases: Record<string, unknown>[];
}

export async function runNLQBenchmark(token?: string | null) {
  return apiFetch<BenchmarkResult>("/api/v1/evaluation/benchmarks/nlq_to_sql/run", token, {
    method: "POST",
  });
}

export async function runEDABenchmark(token?: string | null) {
  return apiFetch<BenchmarkResult>("/api/v1/evaluation/benchmarks/eda_correctness/run", token, {
    method: "POST",
  });
}

export async function runNLPBenchmark(token?: string | null) {
  return apiFetch<BenchmarkResult>("/api/v1/evaluation/benchmarks/nlp_sentiment/run", token, {
    method: "POST",
  });
}

export interface MetricTraceReplayCell {
  label: string;
  result_inr: string | null;
  status: "completed" | "failed" | "running";
  error: string | null;
}

export interface MetricTraceDemoResult {
  workspace_id: string;
  replay_id: string;
  status: string;
  headline: string;
  inputs: Record<string, string>;
  cells: MetricTraceReplayCell[];
  attribution: {
    data_effect: string;
    definition_effect: string;
    interaction_effect: string;
    data_contribution?: string;
    definition_contribution?: string;
    total_change: string;
    reconciles: boolean;
  } | null;
}

export async function runMetricTraceDemo(token?: string | null) {
  return apiFetch<MetricTraceDemoResult>("/api/v1/metrictrace/demo", token, { method: "POST" });
}

export interface ReplayOptions {
  dataset_versions: Array<{ id: string; source_id: string; source_name: string; captured_at: string; content_hash: string }>;
  metric_definitions: Array<{ id: string; metric_id: string; metric_name: string; version: string; sql_hash: string }>;
}

export interface ReplayWorkspace {
  workspace_id: string;
  options: ReplayOptions;
}

export async function getReplayWorkspace(token?: string | null) {
  return apiFetch<ReplayWorkspace>("/api/v1/metrictrace/replay-workspace", token);
}

export async function getReplayOptions(workspaceId: string, token?: string | null) {
  return apiFetch<ReplayOptions>(`/api/v1/metrictrace/replay-options?workspace_id=${encodeURIComponent(workspaceId)}`, token);
}

export interface ReplayStatus {
  replay_id: string;
  status: string;
  attribution: MetricTraceDemoResult["attribution"];
  cells: Array<Omit<MetricTraceReplayCell, "status"> & { id: string; status: string; duration_ms: number; job_id: string | null; retryable: boolean }>;
}

export async function submitReplay(
  input: { workspace_id: string; old_version_id: string; new_version_id: string; old_definition_id: string; new_definition_id: string },
  token?: string | null,
) {
  return apiFetch<{ replay_id: string; status: string }>("/api/v1/metrictrace/replays", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getReplay(replayId: string, token?: string | null) {
  return apiFetch<ReplayStatus>(`/api/v1/metrictrace/replays/${encodeURIComponent(replayId)}`, token);
}

export async function cancelReplay(replayId: string, token?: string | null) {
  return apiFetch<{ replay_id: string; status: string }>(`/api/v1/metrictrace/replays/${encodeURIComponent(replayId)}`, token, {
    method: "DELETE",
  });
}

export interface PostgresDiscoveredTable {
  schema: string;
  table: string;
  primary_key: string[];
  columns: Array<{ column_name: string; data_type: string; is_nullable: string }>;
  capture_supported: boolean;
  unsupported_reason: string | null;
}

export interface MetricSourceRead {
  id: string;
  name: string;
  source_type: string;
  connection_id: string | null;
  capture_status: string;
  tables: Array<{ schema: string; table: string }>;
  schedule_seconds: number | null;
  version_count: number;
  latest_version_id: string | null;
  latest_captured_at: string | null;
}

export async function discoverPostgresTables(input: { workspace_id: string; connection_id: string }, token?: string | null) {
  return apiFetch<{ tables: PostgresDiscoveredTable[] }>("/api/v1/metrictrace/sources/postgresql/discover", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function listMetricSources(workspaceId: string, token?: string | null) {
  return apiFetch<{ sources: MetricSourceRead[] }>(`/api/v1/metrictrace/sources?workspace_id=${encodeURIComponent(workspaceId)}`, token);
}

export async function createPostgresSource(input: {
  workspace_id: string;
  connection_id: string;
  name: string;
  tables: Array<{ schema: string; table: string }>;
  schedule_seconds?: number;
}, token?: string | null) {
  return apiFetch<{ source_id: string; status: string; source_type: string }>("/api/v1/metrictrace/sources/postgresql", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function capturePostgresSource(sourceId: string, workspaceId: string, token?: string | null) {
  return apiFetch<{ job_id: string; status: string; source_id: string }>(`/api/v1/metrictrace/sources/${encodeURIComponent(sourceId)}/captures?workspace_id=${encodeURIComponent(workspaceId)}`, token, {
    method: "POST",
  });
}

export async function getPostgresCapture(sourceId: string, jobId: string, workspaceId: string, token?: string | null) {
  return apiFetch<{ job_id: string; source_id: string; status: string; error: { category: string; message: string } | null; result: { dataset_version_id?: string; row_count?: number } | null }>(`/api/v1/metrictrace/sources/${encodeURIComponent(sourceId)}/captures/${encodeURIComponent(jobId)}?workspace_id=${encodeURIComponent(workspaceId)}`, token);
}

export interface DatasetDiffResult {
  old_version_id: string;
  new_version_id: string;
  old_table: { schema: string; table: string } | null;
  new_table: { schema: string; table: string } | null;
  comparison: {
    fingerprint: string;
    schema_changes: Array<{ kind: string; column: string; old_type?: string; new_type?: string }>;
    key_validation: Record<string, { duplicate_key_groups: number; null_key_rows: number }> | null;
    summary: { mode: string; comparable: boolean; reason?: string; inserted?: number; deleted?: number; modified?: number; unchanged?: number };
    records: Array<{ kind: string; key: Record<string, unknown>; changed_columns: string[]; old: Record<string, unknown>; new: Record<string, unknown> }>;
  };
}

export async function compareDatasetVersions(input: {
  workspace_id: string;
  old_version_id: string;
  new_version_id: string;
  key_columns: string[];
  old_table?: { schema: string; table: string };
  new_table?: { schema: string; table: string };
  limit?: number;
  offset?: number;
}, token?: string | null) {
  return apiFetch<DatasetDiffResult>("/api/v1/metrictrace/dataset-diff", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface SqlRegressionResult {
  dataset_version_id: string;
  table: { schema: string; table: string } | null;
  regression: {
    status: "PASS" | "FAIL";
    baseline: { value: string; duration_ms: number; normalized_sql: string };
    candidate: { value: string; duration_ms: number; normalized_sql: string };
    difference: { absolute: string; percent: string | null };
    gates: Array<{ type: string; limit: string; actual: string | null; status: "PASS" | "FAIL" | "ERROR"; message?: string }>;
    static_sql_changed: boolean;
    fingerprint: string;
  };
}

export async function checkSqlRegression(input: {
  workspace_id: string;
  dataset_version_id: string;
  baseline_sql: string;
  candidate_sql: string;
  table?: { schema: string; table: string };
  max_absolute_difference?: string;
  max_percent_difference?: string;
  parameters?: Record<string, string | number | boolean | null>;
}, token?: string | null) {
  return apiFetch<SqlRegressionResult>("/api/v1/metrictrace/sql-regression", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface JoinAuditResult {
  dataset_version_id: string;
  tables: Array<{ schema: string; table: string; sql_name: string }>;
  audit: {
    supported: boolean;
    joins: Array<{ join_index: number; join_type: string; left: { table: string; columns: string[]; profile: { rows: number; distinct_non_null_keys: number; duplicate_key_groups: number; null_key_rows: number } }; right: { table: string; columns: string[]; profile: { rows: number; distinct_non_null_keys: number; duplicate_key_groups: number; null_key_rows: number } }; joined_rows: number; unmatched_left_rows: number; unmatched_right_rows: number; potential_aggregate_amplification: boolean; interpretation: string }>;
    uncertainty: Array<{ join_index: number; reason: string }>;
    aggregations: string[];
  };
}

export async function auditSqlJoins(input: { workspace_id: string; dataset_version_id: string; sql: string }, token?: string | null) {
  return apiFetch<JoinAuditResult>("/api/v1/metrictrace/join-audit", token, { method: "POST", body: JSON.stringify(input) });
}

export interface MetricContractRead {
  id: string;
  name: string;
  version: number;
  definition_hash: string;
  contracts: Array<Record<string, unknown>>;
  created_at: string;
  latest_evaluation: ContractEvaluation | null;
}

export interface ContractEvaluation {
  id: string;
  status: "PASS" | "FAIL" | "ERROR";
  dataset_version_id: string;
  input_fingerprint: string;
  report: {
    dataset_content_hash: string;
    tables: Array<{ schema: string; table: string; sql_name: string }>;
    report: {
      summary: Record<string, number | boolean>;
      outcomes: Array<{ id: string; type: string; severity: string; status: "PASS" | "FAIL" | "ERROR" | "NOT_EVALUATED"; message: string; evidence: Record<string, unknown> }>;
    };
  };
  created_at: string;
}

export async function listMetricContracts(workspaceId: string, token?: string | null) {
  return apiFetch<{ contracts: MetricContractRead[] }>(`/api/v1/metrictrace/contracts?workspace_id=${encodeURIComponent(workspaceId)}`, token);
}

export async function createMetricContract(input: { workspace_id: string; name: string; contracts: Array<Record<string, unknown>> }, token?: string | null) {
  return apiFetch<{ contract: MetricContractRead }>("/api/v1/metrictrace/contracts", token, { method: "POST", body: JSON.stringify(input) });
}

export async function evaluateMetricContract(contractId: string, input: { workspace_id: string; dataset_version_id: string }, token?: string | null) {
  return apiFetch<{ contract: MetricContractRead; evaluation: ContractEvaluation }>(`/api/v1/metrictrace/contracts/${encodeURIComponent(contractId)}/evaluations`, token, { method: "POST", body: JSON.stringify(input) });
}

export interface ShadowExecutionResult {
  id: string;
  status: "PASS" | "FAIL";
  policy_id: string;
  input_fingerprint: string;
  report: {
    dataset_content_hash: string;
    policy_hash: string;
    regression: SqlRegressionResult["regression"];
    required_contract: { id: string; definition_hash: string; report: ContractEvaluation["report"]["report"] } | null;
  };
}

export async function createRegressionPolicy(input: {
  workspace_id: string;
  name: string;
  max_absolute_difference?: string;
  max_percent_difference?: string;
  required_contract_id?: string;
}, token?: string | null) {
  return apiFetch<{ policy_id: string; version: number; definition_hash: string }>("/api/v1/metrictrace/regression-policies", token, { method: "POST", body: JSON.stringify(input) });
}

export async function executeShadowRun(input: {
  workspace_id: string;
  policy_id: string;
  baseline_definition_id: string;
  candidate_definition_id: string;
  dataset_version_id: string;
  table?: { schema: string; table: string };
}, token?: string | null) {
  return apiFetch<ShadowExecutionResult>("/api/v1/metrictrace/shadow-executions", token, { method: "POST", body: JSON.stringify(input) });
}

export async function promoteMetricDefinition(definitionId: string, input: { workspace_id: string; shadow_execution_id: string }, token?: string | null) {
  return apiFetch<{ promotion_id: string; candidate_definition_id: string; previous_definition_id: string | null; evidence_fingerprint: string }>(`/api/v1/metrictrace/metric-definitions/${encodeURIComponent(definitionId)}/promotions`, token, { method: "POST", body: JSON.stringify(input) });
}

export interface DecisionReceiptResult {
  id: string;
  replay_id: string;
  integrity_sha256: string;
  created_at: string;
  verification: { valid: boolean; integrity_valid: boolean; reconciliation_valid: boolean; missing_fields: string[]; note: string };
  receipt: { scope: string; replay_id: string; created_at: string; attribution: { total_change: string; reconciles: boolean }; cells: Record<string, { result: string; duration_ms: number; execution_fingerprint: string; definition: { id: string; sql_hash: string }; dataset: { id: string; content_hash: string } }>; contract_outcomes: Array<{ contract_id: string; definition_hash: string; dataset_version_id: string; status: string; outcomes: Array<{ id: string; status: string }> }>; limitations: string[] };
}

export async function createDecisionReceipt(replayId: string, token?: string | null) {
  return apiFetch<DecisionReceiptResult>(`/api/v1/metrictrace/replays/${encodeURIComponent(replayId)}/decision-receipt`, token, { method: "POST" });
}

export async function getDecisionReceipt(receiptId: string, token?: string | null) {
  return apiFetch<DecisionReceiptResult>(`/api/v1/metrictrace/decision-receipts/${encodeURIComponent(receiptId)}`, token);
}
