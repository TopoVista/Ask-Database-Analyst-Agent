import Link from "next/link";
import { ArrowRight, Database, ShieldCheck, Sparkles, Workflow, SearchCode } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const FEATURE_CARDS = [
  {
    title: "Reason from the schema",
    description: "The agent reads table structure first, then chooses SQL paths with context instead of guesswork.",
    icon: SearchCode,
  },
  {
    title: "Show the analytical chain",
    description: "Every answer carries its query steps, intermediate results, and the narrative built on top of them.",
    icon: Workflow,
  },
  {
    title: "Keep execution controlled",
    description: "Credential handling, guarded query execution, and explicit connection management keep the system deliberate.",
    icon: ShieldCheck,
  },
];

const WORKFLOW_STEPS = [
  "Inspect the active schema and connection context.",
  "Break the question into traceable query tasks.",
  "Run the best-fit SQL and analyze the returned evidence.",
  "Write a business explanation grounded in the output.",
];

export default function LandingPage() {
  return (
    <main className="relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Badge className="border-accent/20 bg-accent/10 text-accent">Decision Intelligence</Badge>
            <p className="text-sm text-muted-fg">Autonomous analytics for operational teams</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/sign-in"
              className="inline-flex h-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-fg transition hover:border-white/14 hover:bg-white/8"
            >
              Sign in
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex h-11 items-center justify-center rounded-2xl border border-accent/60 bg-accent px-4 text-sm font-medium text-accent-fg shadow-[0_12px_30px_rgba(252,186,73,0.16)] transition hover:brightness-[1.03]"
            >
              Open dashboard
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </header>

        <section className="grid min-h-[calc(100vh-8rem)] items-center gap-8 py-14 lg:grid-cols-[1.05fr,0.95fr] lg:py-20">
          <div className="max-w-3xl">
            <Badge className="border-white/10 bg-white/6 text-fg">Schema-aware analytical system</Badge>
            <h1 className="mt-6 text-5xl font-semibold leading-[0.94] text-fg md:text-7xl">
              Ask one business question.
              <span className="mt-3 block text-white/62">See the reasoning, SQL, and decision narrative.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-fg/74">
              Decision Intelligence turns a vague prompt into a structured analytical workflow with schema inspection,
              SQL execution, evidence review, and an answer you can defend.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className="inline-flex h-12 items-center justify-center rounded-2xl border border-accent/60 bg-accent px-5 text-sm font-medium text-accent-fg shadow-[0_12px_30px_rgba(252,186,73,0.16)] transition hover:brightness-[1.03]"
              >
                Launch analysis
                <Sparkles className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/sign-up"
                className="inline-flex h-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 text-sm font-medium text-fg transition hover:border-white/14 hover:bg-white/8"
              >
                Create account
              </Link>
            </div>

            <div className="mt-10 grid gap-3 sm:grid-cols-3">
              <MetricCard label="Workflow" value="4-step" description="Schema to narrative" />
              <MetricCard label="Output" value="Traceable" description="SQL plus explanation" />
              <MetricCard label="Focus" value="Actionable" description="Built for operators" />
            </div>
          </div>

          <div className="space-y-4">
            <Card className="overflow-hidden">
              <CardContent className="p-0">
                <div className="border-b border-white/10 px-6 py-5">
                  <p className="text-[11px] uppercase tracking-[0.26em] text-muted-fg">Analytical loop</p>
                  <h2 className="mt-3 text-2xl font-semibold text-fg">A calmer, more explicit way to work with data</h2>
                  <p className="mt-3 max-w-xl text-sm leading-6 text-fg/72">
                    The interface is built around one primary action per screen, visible system state, and evidence-first outputs.
                  </p>
                </div>
                <div className="space-y-3 p-6">
                  {WORKFLOW_STEPS.map((step, index) => (
                    <div key={step} className="flex items-start gap-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-sm font-semibold text-accent">
                        0{index + 1}
                      </div>
                      <p className="pt-1 text-sm leading-6 text-fg/78">{step}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 sm:grid-cols-3">
              {FEATURE_CARDS.map((feature) => {
                const Icon = feature.icon;
                return (
                  <Card key={feature.title} className="h-full">
                    <CardContent className="flex h-full flex-col gap-4">
                      <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
                        <Icon className="h-5 w-5 text-accent" />
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-fg">{feature.title}</h3>
                        <p className="mt-2 text-sm leading-6 text-fg/70">{feature.description}</p>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function MetricCard({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-[rgba(13,20,32,0.9)] px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <p className="text-[10px] uppercase tracking-[0.24em] text-muted-fg">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-fg">{value}</p>
      <p className="mt-1 text-sm text-fg/62">{description}</p>
    </div>
  );
}
