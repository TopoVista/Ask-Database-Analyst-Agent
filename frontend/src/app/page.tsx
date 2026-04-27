import Link from "next/link";
import { ArrowRight, Database, BrainCircuit, Sparkles, ShieldCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const FEATURE_CARDS = [
  {
    title: "Explain the why",
    description: "Turn a business question into a rooted narrative with SQL, analysis, and recommendations.",
    icon: BrainCircuit,
  },
  {
    title: "Schema-aware reasoning",
    description: "The agent reads your schema first, then generates targeted queries instead of blind guesses.",
    icon: Database,
  },
  {
    title: "Safety-first execution",
    description: "SELECT-only query execution, rate limiting, and credential encryption keep the system controlled.",
    icon: ShieldCheck,
  },
];

export default function LandingPage() {
  return (
    <main className="relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 lg:px-8">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge className="border-accent/30 bg-accent/12 text-accent">Decision Intelligence</Badge>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/sign-in"
              className="inline-flex h-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-fg transition hover:bg-white/10"
            >
              Sign in
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex h-10 items-center justify-center rounded-xl bg-accent px-4 text-sm font-medium text-accent-fg shadow-glow transition hover:brightness-110"
            >
              Open dashboard
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </header>

        <section className="relative grid min-h-[calc(100vh-6rem)] items-center lg:grid-cols-[1.2fr,0.8fr]">
          <div className="max-w-3xl py-16 lg:py-0">
            <Badge className="mb-5 border-white/10 bg-white/6 text-fg">Autonomous analytics for business teams</Badge>
            <h1 className="text-5xl font-semibold tracking-tight text-fg md:text-7xl">
              Ask your data a question.
              <span className="block text-white/60">Get the why, not just the what.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-fg/72">
              A reasoning agent that decomposes your question, executes SQL safely, detects anomalies, and writes a business narrative you can act on.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className="inline-flex h-12 items-center justify-center rounded-xl bg-accent px-5 text-base font-medium text-accent-fg shadow-glow transition hover:brightness-110"
              >
                Launch analysis
                <Sparkles className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/sign-up"
                className="inline-flex h-12 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-5 text-base font-medium text-fg transition hover:bg-white/10"
              >
                Create account
              </Link>
            </div>
          </div>

          <div className="grid gap-4">
            {FEATURE_CARDS.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card key={feature.title} className="bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.04))]">
                  <CardContent className="flex items-start gap-4 p-5">
                    <div className="rounded-2xl border border-white/10 bg-white/8 p-3">
                      <Icon className="h-5 w-5 text-accent" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-fg">{feature.title}</h2>
                      <p className="mt-2 text-sm leading-6 text-fg/70">{feature.description}</p>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
