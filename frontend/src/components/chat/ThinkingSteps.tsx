"use client";

import { BarChart2, Brain, CheckCircle, Database, Lightbulb, Loader2 } from "lucide-react";
import type { AgentStep } from "@/types/agent";

const STEP_ICONS: Record<string, React.ReactNode> = {
  schema_inspection: <Database className="h-3.5 w-3.5" />,
  intent_classification: <Brain className="h-3.5 w-3.5" />,
  task_planning: <Brain className="h-3.5 w-3.5" />,
  sql_generation: <Database className="h-3.5 w-3.5" />,
  sql_correction: <Database className="h-3.5 w-3.5 text-warning" />,
  result_analysis: <BarChart2 className="h-3.5 w-3.5" />,
  hypothesis_generation: <Lightbulb className="h-3.5 w-3.5" />,
  insight_generation: <Lightbulb className="h-3.5 w-3.5" />,
};

export function ThinkingSteps({ steps }: { steps: AgentStep[] }) {
  if (!steps.length) return null;

  return (
    <div className="max-w-3xl rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,24,38,0.96),rgba(10,15,26,0.98))] p-5 shadow-glow">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-muted-fg">Agent reasoning</p>
          <p className="mt-1 text-sm text-fg/72">Each step is streamed as the system decomposes and answers the prompt.</p>
        </div>
        <Loader2 className="h-4 w-4 animate-spin text-accent" />
      </div>
      <div className="space-y-2">
        {steps.map((step, index) => (
          <div
            key={`${step.step}-${index}`}
            className="flex items-center gap-3 rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-sm"
          >
            <span className="text-muted-fg">{STEP_ICONS[step.step] ?? <Loader2 className="h-3.5 w-3.5 animate-spin" />}</span>
            <span className="text-fg/90">{step.message}</span>
            {index < steps.length - 1 ? (
              <CheckCircle className="ml-auto h-3.5 w-3.5 text-success" />
            ) : (
              <Loader2 className="ml-auto h-3.5 w-3.5 animate-spin text-accent" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
