export interface AgentStep {
  step: string;
  message: string;
  timestamp: number;
}

export interface ChartSpec {
  chart_type: "metric" | "line" | "bar" | "scatter" | "pie" | "table";
  x: string | null;
  y: string | null;
  title: string;
  rationale: string;
}

export interface QueryResult {
  taskId: string;
  taskDescription: string;
  sql: string;
  rows: Record<string, unknown>[];
  columns: string[];
  success: boolean;
  rowCount?: number;
  error?: string | null;
  chartSpec?: ChartSpec | null;
}

export interface InsightMetadata {
  intent?: unknown;
  analysis?: unknown;
  queryResults?: QueryResult[];
  executionTimeMs?: number;
}

