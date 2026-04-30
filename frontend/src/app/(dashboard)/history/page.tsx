"use client";

import { useEffect, useState } from "react";
import { Clock3, FolderClock, ScrollText } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { getSession, listSessions } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export default function HistoryPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => listSessions(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });
  const details = useQuery({
    queryKey: ["session", selected],
    queryFn: async () => (selected ? getSession(selected, await getToken()) : null),
    enabled: isLoaded && Boolean(userId) && Boolean(selected),
    retry: false,
  });

  useEffect(() => {
    if (!selected && sessions.data?.[0]?.id) {
      setSelected(sessions.data[0].id);
    }
  }, [selected, sessions.data]);

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <Badge className="border-accent/20 bg-accent/10 text-accent">Session history</Badge>
              <CardTitle className="mt-4 text-3xl">Review previous analytical threads without losing context</CardTitle>
              <CardDescription className="mt-3 text-base text-fg/72">
                Revisit question chains, inspect the generated insight trail, and keep the history view as structured as the live workspace.
              </CardDescription>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <HistoryMetric label="Sessions" value={String(sessions.data?.length ?? 0)} icon={FolderClock} />
              <HistoryMetric label="Focus" value={selected ? "Selected" : "None"} icon={ScrollText} />
              <HistoryMetric label="Timeline" value="Ordered" icon={Clock3} />
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.8fr,1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Query sessions</CardTitle>
            <CardDescription>Each session groups a chain of related questions and answers.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {sessions.isLoading ? <p className="text-sm text-muted-fg">Loading sessions...</p> : null}
            {sessions.error ? <p className="text-sm text-red-400">Unable to load session history.</p> : null}
            {sessions.data?.length ? (
              sessions.data.map((session) => (
                <button
                  key={session.id}
                  onClick={() => setSelected(session.id)}
                  className={`flex w-full items-center justify-between rounded-[24px] border px-4 py-4 text-left transition hover:border-white/14 hover:bg-white/8 ${
                    selected === session.id
                      ? "border-white/16 bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                      : "border-white/10 bg-[rgba(10,16,27,0.9)]"
                  }`}
                >
                  <div>
                    <p className="font-medium text-fg">{session.title ?? "Untitled session"}</p>
                    <p className="mt-1 text-xs text-muted-fg">{formatDate(session.created_at)}</p>
                  </div>
                  <Badge>{session.query_count ?? 0} queries</Badge>
                </button>
              ))
            ) : (
              <div className="rounded-[24px] border border-dashed border-white/12 bg-[rgba(10,16,27,0.7)] px-4 py-10 text-sm text-muted-fg">
                No history yet.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session detail</CardTitle>
            <CardDescription>{selected ? "Inspect the raw question and insight trail." : "Pick a session to inspect its output."}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {details.isLoading && selected ? <p className="text-sm text-muted-fg">Loading session detail...</p> : null}
            {details.error ? <p className="text-sm text-red-400">Unable to load session detail.</p> : null}
            {details.data?.history?.length ? (
              details.data.history.map((item) => (
                <div key={item.id} className="rounded-[24px] border border-white/10 bg-[rgba(10,16,27,0.9)] p-4">
                  <p className="mb-2 text-[10px] uppercase tracking-[0.2em] text-muted-fg">{formatDate(item.created_at)}</p>
                  <p className="text-sm font-medium text-fg">{item.user_question}</p>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-fg/80">{item.final_insight ?? item.error ?? "Pending"}</p>
                </div>
              ))
            ) : selected ? (
              <p className="text-sm text-muted-fg">This session exists, but no query history has been recorded for it yet.</p>
            ) : (
              <p className="text-sm text-muted-fg">No session selected.</p>
            )}
            <Button variant="secondary" size="sm" onClick={() => setSelected(null)}>
              Clear
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HistoryMetric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
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
