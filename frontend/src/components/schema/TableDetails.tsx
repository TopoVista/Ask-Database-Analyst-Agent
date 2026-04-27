"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { TableSchema } from "@/types/schema";

export function TableDetails({ name, table }: { name: string; table: TableSchema }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{name}</CardTitle>
        <CardDescription>{table.row_count_estimate ?? 0} estimated rows</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          {table.columns.map((column) => (
            <div key={column.name} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm">
              <span className="font-medium text-fg">{column.name}</span>
              <span className="font-mono text-xs text-muted-fg">{column.type}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

