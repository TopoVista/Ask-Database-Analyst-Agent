"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createConnection, listConnections, testConnection } from "@/lib/api";
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
  ssl_mode: "prefer",
};

export default function ConnectionsPage() {
  const [form, setForm] = useState<ConnectionCreate>(INITIAL_FORM);
  const [status, setStatus] = useState<string | null>(null);
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const { setActiveConnection } = useConnectionStore();
  const { setActiveConnection: setChatConnection } = useChatStore();

  const tokenQuery = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
  });

  const submit = async () => {
    setStatus(null);
    const token = await getToken();
    const created = await createConnection(form, token);
    setStatus(`Created ${created.name}`);
    setForm(INITIAL_FORM);
    await queryClient.invalidateQueries({ queryKey: ["connections"] });
    setActiveConnection(created.id);
    setChatConnection(created.id);
  };

  return (
    <div className="grid gap-6 px-4 py-6 md:px-6 lg:grid-cols-[0.95fr,1.05fr] lg:px-8">
      <Card>
        <CardHeader>
          <CardTitle>Connect a database</CardTitle>
          <CardDescription>Store credentials securely and reuse the connection across queries.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
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
          <div className="grid grid-cols-2 gap-3">
            <GridInput
              label="Port"
              type="number"
              value={String(form.port)}
              onChange={(port) => setForm((prev) => ({ ...prev, port: Number(port) || 5432 }))}
            />
            <GridInput
              label="SSL mode"
              value={form.ssl_mode}
              onChange={(ssl_mode) => setForm((prev) => ({ ...prev, ssl_mode }))}
            />
          </div>
          <Button onClick={submit} disabled={!form.name || !form.host || !form.database_name || !form.username || !form.password}>
            Save connection
          </Button>
          {status ? <p className="text-sm text-success">{status}</p> : null}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Saved connections</CardTitle>
            <CardDescription>Switch the active connection from here or the dashboard header.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {tokenQuery.data?.length ? (
              tokenQuery.data.map((connection) => (
                <div
                  key={connection.id}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3"
                >
                  <div>
                    <p className="font-medium text-fg">{connection.name}</p>
                    <p className="text-xs text-muted-fg">
                      {connection.host}:{connection.port} | {connection.database_name}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={connection.is_active ? "border-success/30 bg-success/10 text-success" : ""}>
                      {connection.db_type}
                    </Badge>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={async () => {
                        const token = await getToken();
                        const result = await testConnection(connection.id, token);
                        setStatus(result.message);
                      }}
                    >
                      Test
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-fg">No connections yet.</p>
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
    <label className="block space-y-1.5">
      <span className="text-xs uppercase tracking-[0.2em] text-muted-fg">{label}</span>
      <Input type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

