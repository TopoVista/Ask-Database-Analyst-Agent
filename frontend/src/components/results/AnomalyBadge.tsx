"use client";

import { Badge } from "@/components/ui/badge";

export function AnomalyBadge({ severity }: { severity: string }) {
  const className =
    severity === "high"
      ? "border-danger/40 bg-danger/10 text-danger"
      : severity === "medium"
      ? "border-warning/40 bg-warning/10 text-warning"
      : "border-success/40 bg-success/10 text-success";
  return <Badge className={className}>{severity}</Badge>;
}

