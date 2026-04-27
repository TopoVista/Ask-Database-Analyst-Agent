"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { listConnections } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import { useConnectionStore } from "@/stores/connectionStore";
import { cn } from "@/lib/utils";

export function ConnectionSelector() {
  const { getToken } = useAuth();
  const { activeConnectionId, setActiveConnection } = useChatStore();
  const { connections, setConnections, setActiveConnection: setMirrorConnection } = useConnectionStore();

  const { data } = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
  });

  useEffect(() => {
    if (data) {
      setConnections(data);
      if (!activeConnectionId && data[0]) {
        setActiveConnection(data[0].id);
        setMirrorConnection(data[0].id);
      }
    }
  }, [data, activeConnectionId, setActiveConnection, setConnections, setMirrorConnection]);

  if (!connections.length) {
    return <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-muted-fg">No connections</div>;
  }

  return (
    <select
      value={activeConnectionId ?? ""}
      onChange={(event) => {
        setActiveConnection(event.target.value);
        setMirrorConnection(event.target.value);
      }}
      className={cn("h-10 rounded-xl border border-white/10 bg-slate-950/80 px-3 text-sm text-fg outline-none")}
    >
      {connections.map((connection) => (
        <option key={connection.id} value={connection.id}>
          {connection.name}
        </option>
      ))}
    </select>
  );
}
