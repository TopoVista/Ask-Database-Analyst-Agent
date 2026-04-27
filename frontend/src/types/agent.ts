export interface AgentStep {
  step: string;
  message: string;
  timestamp: number;
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
}

export interface InsightMetadata {
  intent?: unknown;
  analysis?: unknown;
  queryResults?: QueryResult[];
  executionTimeMs?: number;
}

