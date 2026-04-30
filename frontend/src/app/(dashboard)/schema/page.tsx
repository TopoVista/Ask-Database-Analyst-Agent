"use client";

import { useEffect, useState } from "react";
import { Database, Layers3, RefreshCcw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { listConnections, getSchema } from "@/lib/api";
import { SchemaTree } from "@/components/schema/SchemaTree";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useChatStore } from "@/stores/chatStore";
import { cn } from "@/lib/utils";

export default function SchemaPage() {
  const { getToken, isLoaded, userId } = useAuth();
  const { activeConnectionId, setActiveConnection } = useChatStore();
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
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
    enabled: isLoaded && Boolean(userId) && Boolean(activeConnectionId),
    retry: false,
  });

  const schema = schemaQuery.data?.schema ?? null;

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <Badge className="border-accent/20 bg-accent/10 text-accent">Schema explorer</Badge>
              <CardTitle className="mt-4 text-3xl">Inspect the tables that shape the agent&apos;s reasoning</CardTitle>
              <CardDescription className="mt-3 text-base text-fg/72">
                Select an active connection, review the discovered tables, and keep the prompt context visible while you ask questions.
              </CardDescription>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <MetricTile label="Connections" value={String(connections.data?.length ?? 0)} icon={Database} />
              <MetricTile label="Tables" value={String(Object.keys(schema?.tables ?? {}).length)} icon={Layers3} />
              <MetricTile label="Refresh" value="Manual" icon={RefreshCcw} />
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.34fr,0.66fr]">
        <Card>
          <CardHeader>
            <CardTitle>Connected sources</CardTitle>
            <CardDescription>Pick the database whose structure you want the agent to reason over.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {connections.data?.map((connection) => (
              <button
                key={connection.id}
                onClick={() => setActiveConnection(connection.id)}
                className={cn(
                  "flex w-full items-center justify-between rounded-[24px] border px-4 py-4 text-left transition-[background-color,border-color,transform]",
                  activeConnectionId === connection.id
                    ? "border-white/16 bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                    : "border-white/10 bg-[rgba(10,16,27,0.9)] hover:border-white/14 hover:bg-white/8"
                )}
              >
                <div>
                  <p className="font-medium text-fg">{connection.name}</p>
                  <p className="mt-1 text-xs text-muted-fg">{connection.database_name}</p>
                </div>
                <Badge className={activeConnectionId === connection.id ? "border-accent/20 bg-accent/10 text-accent" : ""}>
                  {connection.db_type}
                </Badge>
              </button>
            ))}

            {!connections.data?.length ? (
              <div className="rounded-[24px] border border-dashed border-white/12 bg-[rgba(10,16,27,0.7)] px-4 py-8 text-sm text-muted-fg">
                No connections available yet.
              </div>
            ) : null}

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
              <CardContent className="py-10 text-sm text-red-300">
                {schemaQuery.error instanceof Error ? schemaQuery.error.message : "Unable to load schema."}
              </CardContent>
            </Card>
          ) : null}

          {schemaQuery.data?.prompt_string ? (
            <Card>
              <CardHeader>
                <CardTitle>Prompt context</CardTitle>
                <CardDescription>Compressed schema text used by the SQL generation workflow.</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-[24px] border border-white/10 bg-[rgba(9,15,25,0.9)] p-4 font-mono text-[11px] leading-5 text-fg/90">
                  {schemaQuery.data.prompt_string}
                </pre>
              </CardContent>
            </Card>
          ) : null}

          <SchemaTree schema={schema} />
        </div>
      </div>
    </div>
  );
}

function MetricTile({
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
