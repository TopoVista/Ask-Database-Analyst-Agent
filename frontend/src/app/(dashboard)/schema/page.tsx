"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { listConnections, getSchema } from "@/lib/api";
import { SchemaTree } from "@/components/schema/SchemaTree";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import { cn } from "@/lib/utils";

export default function SchemaPage() {
  const { getToken } = useAuth();
  const { activeConnectionId, setActiveConnection } = useChatStore();
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
  });
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const availableConnections = connections.data ?? [];
    const stillExists = activeConnectionId ? availableConnections.some((connection) => connection.id === activeConnectionId) : false;
    if (!availableConnections.length) {
      if (activeConnectionId) {
        setActiveConnection(null);
      }
      return;
    }
    if (!activeConnectionId || !stillExists) {
      setActiveConnection(availableConnections[0].id);
    }
  }, [connections.data, activeConnectionId, setActiveConnection]);

  const schemaQuery = useQuery({
    queryKey: ["schema", activeConnectionId, refreshKey],
    queryFn: async () => (activeConnectionId ? getSchema(activeConnectionId, await getToken()) : null),
    enabled: Boolean(activeConnectionId),
  });

  const schema = schemaQuery.data?.schema ?? null;

  return (
    <div className="grid gap-6 px-4 py-6 md:px-6 lg:grid-cols-[0.35fr,0.65fr] lg:px-8">
      <Card>
        <CardHeader>
          <CardTitle>Schema explorer</CardTitle>
          <CardDescription>Inspect the table tree to help the agent reason about your database.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {connections.data?.map((connection) => (
            <button
              key={connection.id}
              onClick={() => setActiveConnection(connection.id)}
              className={cn(
                "flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition hover:bg-white/10",
                activeConnectionId === connection.id
                  ? "border-white/70 bg-white/10 shadow-glow"
                  : "border-white/10 bg-white/5"
              )}
            >
              <div>
                <p className="font-medium text-fg">{connection.name}</p>
                <p className="text-xs text-muted-fg">{connection.database_name}</p>
              </div>
              <span className="text-xs uppercase tracking-[0.2em] text-muted-fg">{connection.db_type}</span>
            </button>
          ))}
          <Button variant="secondary" size="sm" onClick={() => setRefreshKey((value) => value + 1)}>
            Refresh schema
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {schemaQuery.isLoading ? (
          <Card>
            <CardContent className="py-10 text-sm text-muted-fg">Loading schema...</CardContent>
          </Card>
        ) : null}
        {schemaQuery.error ? (
          <Card>
            <CardContent className="py-10 text-sm text-red-400">
              {schemaQuery.error instanceof Error ? schemaQuery.error.message : "Unable to load schema."}
            </CardContent>
          </Card>
        ) : null}
        {schemaQuery.data?.prompt_string ? (
          <Card>
            <CardHeader>
              <CardTitle>Prompt context</CardTitle>
              <CardDescription>Compressed schema text used for SQL generation.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-white/10 bg-white/5 p-4 font-mono text-[11px] leading-5 text-fg/90">
                {schemaQuery.data.prompt_string}
              </pre>
            </CardContent>
          </Card>
        ) : null}
        <SchemaTree schema={schema} />
      </div>
    </div>
  );
}
