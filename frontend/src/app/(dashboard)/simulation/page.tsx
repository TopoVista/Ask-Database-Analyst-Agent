"use client";

import { useState } from "react";
import { FlaskConical, Loader2, Play } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { listConnections } from "@/lib/api";
import { API_URL } from "@/lib/constants";
import { consumeEventStream } from "@/lib/streaming";
import { useChatStore } from "@/stores/chatStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SimulationPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const { activeConnectionId } = useChatStore();
  const [question, setQuestion] = useState("What if we increase price by 10%?");
  const [paramText, setParamText] = useState('{"price_change_pct": 10}');
  const [streaming, setStreaming] = useState(false);
  const [events, setEvents] = useState<Array<{ type: string; data: unknown }>>([]);
  const [error, setError] = useState<string | null>(null);

  const connectionsQuery = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });

  const connections = connectionsQuery.data ?? [];
  const activeConnection = connections.find((c) => c.id === activeConnectionId);

  const runSimulation = async () => {
    if (!activeConnectionId) return;
    setStreaming(true);
    setError(null);
    setEvents([]);
    try {
      const token = await getToken();
      let parameters: Record<string, unknown> = {};
      if (paramText.trim()) {
        try { parameters = JSON.parse(paramText); } catch {
          setError("Invalid JSON parameters");
          setStreaming(false);
          return;
        }
      }
      const response = await fetch(`${API_URL}/api/v1/simulate/what-if`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ question, parameters, connection_id: activeConnectionId }),
      });
      if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
      await consumeEventStream(response, (event) => setEvents((prev) => [...prev, event]));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader>
          <Badge className="w-fit border-accent/20 bg-accent/10 text-accent">What-If Simulation</Badge>
          <CardTitle className="mt-4 text-3xl">Run scenario analysis</CardTitle>
          <CardDescription className="mt-3 text-base text-fg/72">Ask hypothetical questions and compare outcomes.</CardDescription>
        </CardHeader>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        <SimMetric label="Connection" value={activeConnection?.name ?? "None"} icon={FlaskConical} />
        <SimMetric label="Status" value={streaming ? "Running" : "Ready"} icon={Play} />
        <SimMetric label="Events" value={String(events.length)} icon={FlaskConical} />
      </div>
      <Card>
        <CardHeader><CardTitle>Parameters</CardTitle><CardDescription>Define the scenario</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <span className="text-[10px] uppercase tracking-[0.22em] text-muted-fg">Question</span>
            <Input value={question} onChange={(e) => setQuestion(e.target.value)} />
          </div>
          <div className="space-y-2">
            <span className="text-[10px] uppercase tracking-[0.22em] text-muted-fg">Parameters (JSON)</span>
            <Input value={paramText} onChange={(e) => setParamText(e.target.value)} className="font-mono text-xs" />
          </div>
          <Button onClick={runSimulation} disabled={streaming || !activeConnectionId}>
            {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {streaming ? "Running..." : "Run simulation"}
          </Button>
          {!activeConnectionId && <p className="text-xs text-muted-fg">Connect a database first.</p>}
          {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>}
        </CardContent>
      </Card>
      {events.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Output</CardTitle><CardDescription>Streaming events</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            {events.map((event, idx) => (
              <div key={idx} className="rounded-[20px] border border-white/10 bg-[rgba(9,15,25,0.9)] p-4">
                <div className="mb-2"><Badge className="border-accent/20 bg-accent/10 text-accent">{event.type}</Badge></div>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-fg/90">
                  {typeof event.data === "string" ? event.data : JSON.stringify(event.data, null, 2)}
                </pre>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SimMetric({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
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
