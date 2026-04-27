export interface ConnectionCreate {
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  ssl_mode: string;
}

export interface ConnectionRead {
  id: string;
  user_id: string;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  ssl_mode: string;
  is_active: boolean;
  last_tested_at?: string | null;
  created_at: string;
}

export interface QueryHistoryRead {
  id: string;
  session_id: string;
  user_id: string;
  user_question: string;
  intent_type?: string | null;
  task_plan?: Record<string, unknown> | null;
  generated_queries?: Array<Record<string, unknown>> | null;
  analysis_result?: Record<string, unknown> | null;
  hypotheses?: Array<Record<string, unknown>> | null;
  final_insight?: string | null;
  anomalies_detected?: Array<Record<string, unknown>> | null;
  execution_time_ms?: number | null;
  total_tokens_used?: number | null;
  error?: string | null;
  created_at: string;
}

export interface SessionRead {
  id: string;
  user_id: string;
  connection_id: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
  query_count?: number | null;
}

export interface SchemaResponse {
  schema: SchemaDocument;
  cached: boolean;
  prompt_string: string;
}

export interface SchemaDocument {
  tables: Record<string, TableSchema>;
}

export interface TableSchema {
  columns: Array<{
    name: string;
    type: string;
    nullable: boolean;
    default?: string | null;
  }>;
  primary_keys?: string[];
  foreign_keys?: Array<{
    column: string;
    references: string;
  }>;
  indexes?: string[];
  row_count_estimate?: number;
  sample_rows?: Array<Record<string, unknown>>;
}

