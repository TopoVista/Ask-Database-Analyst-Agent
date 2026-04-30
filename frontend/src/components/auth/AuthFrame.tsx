import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";

export function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,24,37,0.94),rgba(9,14,23,0.96))] shadow-glow lg:grid-cols-[0.95fr,1.05fr]">
        <div className="hidden border-r border-white/10 bg-[linear-gradient(180deg,rgba(26,36,55,0.98),rgba(12,18,29,0.96))] p-8 lg:flex lg:flex-col lg:justify-between">
          <div>
            <Badge className="border-accent/20 bg-accent/10 text-accent">Decision Intelligence</Badge>
            <h1 className="mt-5 text-[34px] font-semibold leading-[1.02] text-fg">Trace the logic behind every answer.</h1>
            <p className="mt-4 text-sm leading-7 text-fg/72">
              Connect your data source, inspect the schema, and run analytical workflows that show their steps instead of hiding them.
            </p>
          </div>

          <div className="space-y-3">
            <AuthPoint title="Schema-first reasoning" description="The agent understands structure before writing SQL." />
            <AuthPoint title="Operational visibility" description="Results, SQL, and narrative stay in one workspace." />
            <AuthPoint title="Deliberate surfaces" description="Clear state, less chrome, tighter hierarchy." />
          </div>
        </div>

        <div className="bg-[rgba(8,13,22,0.9)] p-3 md:p-5">{children}</div>
      </div>
    </div>
  );
}

function AuthPoint({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
      <p className="text-sm font-medium text-fg">{title}</p>
      <p className="mt-1 text-sm leading-6 text-fg/66">{description}</p>
    </div>
  );
}
