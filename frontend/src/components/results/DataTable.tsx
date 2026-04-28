"use client";

import { Card, CardContent } from "@/components/ui/card";

export function DataTable({
  rows,
  columns,
}: {
  rows: Record<string, unknown>[];
  columns: string[];
}) {
  if (!rows.length) {
    return (
      <Card>
        <CardContent className="py-8 text-sm text-muted-fg">No rows returned.</CardContent>
      </Card>
    );
  }

  const headers = columns.length ? columns : Object.keys(rows[0] ?? {});

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-white/5 text-left text-[11px] uppercase tracking-[0.2em] text-muted-fg">
            <tr>
              {headers.map((column) => (
                <th key={column} className="px-4 py-3 font-medium">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {rows.map((row, index) => (
              <tr key={index} className="hover:bg-white/5">
                {headers.map((column) => (
                  <td key={column} className="max-w-[16rem] px-4 py-3 text-fg/90">
                    {formatCell(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
