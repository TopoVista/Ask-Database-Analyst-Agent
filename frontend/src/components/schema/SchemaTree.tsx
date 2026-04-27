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
          <CardContent className="space-y-3">
            <div className="grid gap-2 md:grid-cols-2">
              {table.columns.map((column) => (
                <div key={column.name} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-fg">{column.name}</span>
                    <span className="font-mono text-xs text-muted-fg">{column.type}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-fg">{column.nullable ? "nullable" : "required"}</div>
                </div>
              ))}
            </div>
            {table.sample_rows?.length ? (
              <details className="rounded-xl border border-white/10 bg-white/5 p-3">
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

