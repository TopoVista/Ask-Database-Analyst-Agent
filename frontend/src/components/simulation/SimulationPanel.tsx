"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ImpactChart } from "./ImpactChart";

export function SimulationPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>What-if simulation</CardTitle>
        <CardDescription>Use the simulation endpoint to compare baseline and projected outcomes.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ImpactChart data={[{ label: "Baseline", value: 100 }, { label: "Projected", value: 112 }]} />
      </CardContent>
    </Card>
  );
}

