"use client";

import { useState } from "react";
import { BarChart3, Loader2, Play, ShieldCheck } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { runEDABenchmark, runNLQBenchmark, runNLPBenchmark, type BenchmarkResult } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type BenchmarkKey = "nlq" | "eda" | "nlp";

export default function EvaluationPage() {
  const { getToken } = useAuth();
  const [results, setResults] = useState<Partial<Record<BenchmarkKey, BenchmarkResult>>>({});
  const [running, setRunning] = useState<BenchmarkKey | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runBenchmark = async (key: BenchmarkKey) => {
    setRunning(key);
    setError(null);
    try {
      const token = await getToken();
      let result: BenchmarkResult;
      if (key === "nlq") result = await runNLQBenchmark(token);
      else if (key === "eda") result = await runEDABenchmark(token);
      else result = await runNLPBenchmark(token);
      setResults((prev) => ({ ...prev, [key]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Benchmark failed");
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <Badge className="border-accent/20 bg-accent/10 text-accent">Evaluation & Benchmarks</Badge>
              <CardTitle className="mt-4 text-3xl">Run accuracy benchmarks</CardTitle>
              <CardDescription className="mt-3 text-base text-fg/72">
                Evaluate NLQ-to-SQL, EDA trend detection, and NLP sentiment accuracy.
              </CardDescription>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <EvalMetric label="Benchmarks" value="3" icon={BarChart3} />
              <EvalMetric label="Last run" value={running ?? "Idle"} icon={Play} />
              <EvalMetric label="Security" value="Audit" icon={ShieldCheck} />
            </div>
          </div>
        </CardHeader>
      </Card>
      <div className="grid gap-6 md:grid-cols-3">
        <BenchmarkCard title="NLQ-to-SQL" description="Natural language to SQL accuracy" result={results.nlq} isRunning={running === "nlq"} onRun={() => runBenchmark("nlq")} />
        <BenchmarkCard title="EDA Correctness" description="Trend and anomaly detection" result={results.eda} isRunning={running === "eda"} onRun={() => runBenchmark("eda")} />
        <BenchmarkCard title="NLP Sentiment" description="Sentiment classification accuracy" result={results.nlp} isRunning={running === "nlp"} onRun={() => runBenchmark("nlp")} />
      </div>
      {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>}
    </div>
  );
}

function EvalMetric({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-[rgba(10,16,27,0.9)] px-4 py-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-accent" />
        <p className="text-[10px] uppercase tracking-[0.22em] text-muted-fg">{label}</p>
      </div>
      <p className="mt-3 text-lg font-semibold text-fg">{value}</p>
    </div>
  );
}

function BenchmarkCard({ title, description, result, isRunning, onRun }: {
  title: string; description: string; result?: BenchmarkResult; isRunning: boolean; onRun: () => void;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <Button variant="outline" size="sm" onClick={onRun} disabled={isRunning}>
          {isRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
          {isRunning ? "Running..." : "Run benchmark"}
        </Button>
        {result && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-fg">Accuracy</span>
              <span className="text-sm font-medium text-fg">{(result.accuracy * 100).toFixed(1)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-fg">Passed</span>
              <Badge className="border-success/40 bg-success/10 text-success">{result.passed}/{result.total_cases}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-fg">Failed</span>
              <Badge className="border-danger/40 bg-danger/10 text-danger">{result.failed}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-fg">Time</span>
              <span className="text-xs text-fg/70">{result.total_time_ms}ms</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
