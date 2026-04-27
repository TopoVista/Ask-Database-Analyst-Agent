export interface DatabaseSchema {
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

