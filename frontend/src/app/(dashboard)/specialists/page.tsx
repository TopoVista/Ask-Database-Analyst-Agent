"use client";

import { useState } from "react";
import { Brain, Loader2, Play, Wrench } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { invokeSpecialist, listSpecialists, type SpecialistInfo } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SpecialistsPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [skillParams, setSkillParams] = useState<string>("");
  const [invokeResult, setInvokeResult] = useState<unknown>(null);
  const [invoking, setInvoking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const specialistsQuery = useQuery({
    queryKey: ["specialists"],
    queryFn: async () => listSpecialists(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });

  const specialists = specialistsQuery.data?.specialists ?? [];
  const selected = specialists.find((s) => s.id === selectedId) ?? null;

  const handleInvoke = async (skill: string) => {
    if (!selectedId) return;
    setInvoking(true);
    setError(null);
    setInvokeResult(null);
    try {
      const token = await getToken();
      let params: Record<string, unknown> = {};
      if (skillParams.trim()) {
        try { params = JSON.parse(skillParams); } catch {
          setError("Invalid JSON parameters");
          setInvoking(false);
          return;
        }
      }
      const result = await invokeSpecialist(selectedId, skill, params, token);
      setInvokeResult(result.result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invocation failed");
    } finally {
      setInvoking(false);
    }
  };

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <Badge className="border-accent/20 bg-accent/10 text-accent">Specialist Agents</Badge>
              <CardTitle className="mt-4 text-3xl">Browse and invoke specialized agents</CardTitle>
              <CardDescription className="mt-3 text-base text-fg/72">
                Each specialist handles a narrow task. Select one and invoke its skills directly.
              </CardDescription>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <SpecMetric label="Total" value={String(specialists.length)} icon={Brain} />
              <SpecMetric label="Selected" value={selected ? selected.name : "None"} icon={Wrench} />
              <SpecMetric label="Status" value={invoking ? "Running" : "Ready"} icon={Play} />
            </div>
          </div>
        </CardHeader>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[0.4fr,0.6fr]">
        <SpecialistList
          specialists={specialists}
          isLoading={specialistsQuery.isLoading}
          selectedId={selectedId}
          onSelect={(id) => { setSelectedId(id); setInvokeResult(null); setError(null); }}
        />
        <SpecialistDetail
          selected={selected}
          skillParams={skillParams}
          onParamsChange={setSkillParams}
          onInvoke={handleInvoke}
          invoking={invoking}
          error={error}
          result={invokeResult}
        />
      </div>
    </div>
  );
}

function SpecMetric({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
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

function SpecialistList({ specialists, isLoading, selectedId, onSelect }: {
  specialists: SpecialistInfo[]; isLoading: boolean; selectedId: string | null; onSelect: (id: string) => void;
}) {
  return (
    <Card>
      <CardHeader><CardTitle>Available Specialists</CardTitle><CardDescription>Select a specialist</CardDescription></CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <p className="text-sm text-muted-fg">Loading...</p>
        ) : specialists.length ? (
          specialists.map((spec) => (
            <button key={spec.id} onClick={() => onSelect(spec.id)}
              className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${selectedId === spec.id ? "border-white/16 bg-white/10" : "border-white/10 bg-[rgba(10,16,27,0.9)] hover:border-white/14 hover:bg-white/8"}`}
            >
              <div className="flex items-center justify-between">
                <p className="font-medium text-fg">{spec.name}</p>
                <Badge className={spec.available ? "border-success/40 bg-success/10 text-success" : "border-white/10 bg-white/6 text-fg/60"}>
                  {spec.available ? "Ready" : "Offline"}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-fg line-clamp-2">{spec.description}</p>
            </button>
          ))
        ) : (
          <div className="rounded-[24px] border border-dashed border-white/12 bg-[rgba(10,16,27,0.7)] px-4 py-10 text-center text-sm text-muted-fg">No specialists available.</div>
        )}
      </CardContent>
    </Card>
  );
}

function SpecialistDetail({ selected, skillParams, onParamsChange, onInvoke, invoking, error, result }: {
  selected: SpecialistInfo | null; skillParams: string; onParamsChange: (v: string) => void;
  onInvoke: (skill: string) => void; invoking: boolean; error: string | null; result: unknown;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{selected ? selected.name : "Specialist Details"}</CardTitle>
        <CardDescription>{selected ? selected.description : "Select a specialist to view its skills"}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {selected ? (
          <>
            <div className="flex flex-wrap gap-2">
              {selected.capabilities.map((cap) => (<Badge key={cap} className="border-white/10 bg-white/6 text-fg/80">{cap}</Badge>))}
            </div>
            <div className="space-y-3">
              <p className="text-[10px] uppercase tracking-[0.2em] text-muted-fg">Invoke a skill</p>
              <Input value={skillParams} onChange={(e) => onParamsChange(e.target.value)} placeholder='{"text": "sample"}' className="font-mono text-xs" />
              <div className="flex flex-wrap gap-2">
                {selected.capabilities.map((cap) => (
                  <Button key={cap} variant="outline" size="sm" onClick={() => onInvoke(cap)} disabled={invoking || !selected.available}>
                    {invoking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}{cap}
                  </Button>
                ))}
              </div>
            </div>
            {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</div>}
            {result !== null && (
              <div className="rounded-[20px] border border-white/10 bg-[rgba(9,15,25,0.9)] p-4">
                <p className="mb-2 text-[10px] uppercase tracking-[0.2em] text-muted-fg">Result</p>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-fg/90">
                  {typeof result === "string" ? result : JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </>
        ) : (
          <div className="rounded-[24px] border border-dashed border-white/12 bg-[rgba(10,16,27,0.7)] px-4 py-10 text-center text-sm text-muted-fg">Select a specialist.</div>
        )}
      </CardContent>
    </Card>
  );
}
