"use client";

import { useState } from "react";
import { CheckCircle2, Database, ShieldCheck, Trash2, Wifi } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createConnection, deleteConnection, listConnections, testConnection } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import { useConnectionStore } from "@/stores/connectionStore";
import type { ConnectionCreate } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const INITIAL_FORM: ConnectionCreate = {
  name: "",
  db_type: "postgresql",
  host: "",
  port: 5432,
  database_name: "",
  username: "",
  password: "",
  ssl_mode: "require",
};

export default function ConnectionsPage() {
  const [form, setForm] = useState<ConnectionCreate>(INITIAL_FORM);
  const [status, setStatus] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isTestingId, setIsTestingId] = useState<string | null>(null);
  const [isDeletingId, setIsDeletingId] = useState<string | null>(null);
  const { getToken, isLoaded, userId } = useAuth();
  const queryClient = useQueryClient();
  const { activeConnectionId, setActiveConnection } = useConnectionStore();
  const { activeConnectionId: chatActiveConnectionId, setActiveConnection: setChatConnection } = useChatStore();

  const tokenQuery = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });

  const submit = async () => {
    setStatus(null);
    setIsSaving(true);
    try {
      if (!isLoaded || !userId) {
        throw new Error("Sign in again to save a connection.");
      }
      const token = await getToken();
      const created = await createConnection(form, token);
      queryClient.setQueryData(
        ["connections"],
        (existing: Array<(typeof created)> | undefined = []) => [created, ...existing.filter((item) => item.id !== created.id)]
      );

      setStatus(`Connection verified and saved for ${created.name}.`);
      setForm(INITIAL_FORM);
      setActiveConnection(created.id);
      setChatConnection(created.id);

      queryClient.invalidateQueries({ queryKey: ["connections"], refetchType: "none" }).catch((error) => {
        console.error("Unable to refresh connections after save:", error);
      });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to save the connection.");
    } finally {
      setIsSaving(false);
    }
  };

  const removeConnection = async (connectionId: string) => {
    setStatus(null);
    setIsDeletingId(connectionId);
    try {
      if (!isLoaded || !userId) {
        throw new Error("Sign in again to manage connections.");
      }
      const token = await getToken();
      await deleteConnection(connectionId, token);
      const remainingConnections = (tokenQuery.data ?? []).filter((connection) => connection.id !== connectionId);
      const nextActiveId = remainingConnections[0]?.id ?? null;
      queryClient.setQueryData(["connections"], remainingConnections);

      if (activeConnectionId === connectionId) {
        setActiveConnection(nextActiveId);
      }
      if (chatActiveConnectionId === connectionId) {
        setChatConnection(nextActiveId);
      }

      setStatus("Connection removed.");
      queryClient.invalidateQueries({ queryKey: ["connections"], refetchType: "none" }).catch((error) => {
        console.error("Unable to refresh connections after delete:", error);
      });
      queryClient.removeQueries({ queryKey: ["schema", connectionId] });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to delete the connection.");
    } finally {
      setIsDeletingId(null);
    }
  };

  const savedCount = tokenQuery.data?.length ?? 0;

  return (
    <div className="space-y-6 px-4 py-6 md:px-6 lg:px-8">
      <Card>
        <CardHeader className="border-b border-white/10">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <Badge className="border-accent/20 bg-accent/10 text-accent">Connection management</Badge>
              <CardTitle className="mt-4 text-3xl">Create deliberate, reusable database access</CardTitle>
              <CardDescription className="mt-3 text-base text-fg/72">
                Save validated database credentials once, switch them across the workspace, and keep the active analytical context visible.
              </CardDescription>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <MetricPill label="Saved" value={String(savedCount)} icon={Database} />
              <MetricPill label="Validation" value="Preflight" icon={ShieldCheck} />
              <MetricPill label="Context" value="Shared" icon={Wifi} />
            </div>
          </div>
        </CardHeader>
      </Card>

      {status ? <StatusNotice message={status} /> : null}

      <div className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle>Connect a database</CardTitle>
            <CardDescription>Store credentials securely and reuse the connection across queries and schema inspection.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <GridInput label="Name" value={form.name} onChange={(name) => setForm((prev) => ({ ...prev, name }))} />
              <GridInput label="Host" value={form.host} onChange={(host) => setForm((prev) => ({ ...prev, host }))} />
              <GridInput
                label="Database"
                value={form.database_name}
                onChange={(database_name) => setForm((prev) => ({ ...prev, database_name }))}
              />
              <GridInput label="Username" value={form.username} onChange={(username) => setForm((prev) => ({ ...prev, username }))} />
              <GridInput
                label="Password"
                value={form.password}
                type="password"
                onChange={(password) => setForm((prev) => ({ ...prev, password }))}
              />
              <GridInput
                label="Port"
                type="number"
                value={String(form.port)}
                onChange={(port) => setForm((prev) => ({ ...prev, port: Number(port) || 5432 }))}
              />
            </div>

            <div className="rounded-[24px] border border-white/10 bg-[rgba(10,16,27,0.9)] p-4">
              <GridInput
                label="SSL mode"
                value={form.ssl_mode}
                onChange={(ssl_mode) => setForm((prev) => ({ ...prev, ssl_mode }))}
              />
              <p className="mt-3 text-sm leading-6 text-fg/68">
                For Neon, use the exact host, database name, username, and database password from the connection string. Keep SSL mode set to
                <span className="font-medium text-fg"> require</span>.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={submit}
                disabled={isSaving || !form.name || !form.host || !form.database_name || !form.username || !form.password}
              >
                {isSaving ? "Verifying..." : "Save connection"}
              </Button>
              <p className="text-sm text-muted-fg">Credentials are validated before the connection is stored.</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Saved connections</CardTitle>
            <CardDescription>Choose the active data source, verify connectivity, or remove credentials you no longer need.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {tokenQuery.data?.length ? (
              tokenQuery.data.map((connection) => (
                <div
                  key={connection.id}
                  className="rounded-[24px] border border-white/10 bg-[rgba(10,16,27,0.9)] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                >
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold text-fg">{connection.name}</p>
                        <Badge className={connection.is_active ? "border-success/20 bg-success/10 text-success" : ""}>
                          {connection.db_type}
                        </Badge>
                        {chatActiveConnectionId === connection.id ? (
                          <Badge className="border-accent/20 bg-accent/10 text-accent">Active</Badge>
                        ) : null}
                      </div>
                      <div className="grid gap-2 text-sm text-fg/70 md:grid-cols-2">
                        <p>{connection.host}</p>
                        <p>{connection.database_name}</p>
                        <p>Port {connection.port}</p>
                        <p>User {connection.username}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={async () => {
                          setIsTestingId(connection.id);
                          try {
                            if (!isLoaded || !userId) {
                              throw new Error("Sign in again to test connections.");
                            }
                            const token = await getToken();
                            const result = await testConnection(connection.id, token);
                            setStatus(result.message);
                          } catch (error) {
                            setStatus(error instanceof Error ? error.message : "Unable to test the connection.");
                          } finally {
                            setIsTestingId(null);
                          }
                        }}
                      >
                        {isTestingId === connection.id ? "Testing..." : "Test"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isDeletingId === connection.id}
                        onClick={() => removeConnection(connection.id)}
                        className="text-red-200 hover:bg-red-500/10 hover:text-red-100"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        {isDeletingId === connection.id ? "Removing..." : "Delete"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-[24px] border border-dashed border-white/12 bg-[rgba(10,16,27,0.7)] px-4 py-10 text-center text-sm text-muted-fg">
                No connections yet. Add one to unlock schema inspection and query analysis.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function GridInput({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-[11px] uppercase tracking-[0.22em] text-muted-fg">{label}</span>
      <Input type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function StatusNotice({ message }: { message: string }) {
  const normalized = message.toLowerCase();
  const isPositive =
    normalized.includes("saved") ||
    normalized.includes("successful") ||
    normalized.includes("verified") ||
    normalized.includes("removed");
  return (
    <div
      className={`rounded-[24px] border px-4 py-4 text-sm ${
        isPositive ? "border-success/20 bg-success/10 text-success" : "border-red-500/20 bg-red-500/10 text-red-200"
      }`}
    >
      <div className="flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4" />
        <span>{message}</span>
      </div>
    </div>
  );
}

function MetricPill({
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
