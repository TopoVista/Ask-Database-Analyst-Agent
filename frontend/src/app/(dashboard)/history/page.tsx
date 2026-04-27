"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { getSession, listSessions } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export default function HistoryPage() {
  const { getToken } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => listSessions(await getToken()),
  });
  const details = useQuery({
    queryKey: ["session", selected],
    queryFn: async () => (selected ? getSession(selected, await getToken()) : null),
    enabled: Boolean(selected),
  });

  useEffect(() => {
    if (!selected && sessions.data?.[0]?.id) {
      setSelected(sessions.data[0].id);
    }
  }, [selected, sessions.data]);

  return (
    <div className="grid gap-6 px-4 py-6 md:px-6 lg:grid-cols-[0.8fr,1.2fr] lg:px-8">
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
                className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition hover:bg-white/10 ${
                  selected === session.id ? "border-white/70 bg-white/10" : "border-white/10 bg-white/5"
                }`}
              >
                <div>
                  <p className="font-medium text-fg">{session.title ?? "Untitled session"}</p>
                  <p className="text-xs text-muted-fg">{formatDate(session.created_at)}</p>
                </div>
                <Badge>{session.query_count ?? 0} queries</Badge>
              </button>
            ))
          ) : (
            <p className="text-sm text-muted-fg">No history yet.</p>
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
              <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="mb-2 text-xs uppercase tracking-[0.2em] text-muted-fg">{formatDate(item.created_at)}</p>
                <p className="text-sm font-medium text-fg">{item.user_question}</p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-fg/80">{item.final_insight ?? item.error ?? "Pending"}</p>
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
  );
}
