"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { DatabaseSchema } from "@/types/schema";

export function SchemaTree({ schema }: { schema: DatabaseSchema | null }) {
  if (!schema) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-fg">Select a connection to inspect its schema.</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(schema.tables).map(([name, table]) => (
        <Card key={name}>
          <CardHeader>
            <CardTitle>{name}</CardTitle>
            <CardDescription>{table.row_count_estimate ?? 0} estimated rows</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {table.columns.map((column) => (
                <div key={column.name} className="rounded-[22px] border border-white/10 bg-[rgba(9,15,25,0.9)] px-4 py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-fg">{column.name}</span>
                    <span className="font-mono text-xs text-muted-fg">{column.type}</span>
                  </div>
                  <div className="mt-2 text-xs text-muted-fg">{column.nullable ? "nullable" : "required"}</div>
                </div>
              ))}
            </div>
            {table.sample_rows?.length ? (
              <details className="rounded-[22px] border border-white/10 bg-[rgba(9,15,25,0.9)] p-4">
                <summary className="cursor-pointer text-sm font-medium text-fg">Sample rows</summary>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-fg/90">
                  {JSON.stringify(table.sample_rows, null, 2)}
                </pre>
              </details>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
