"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { listConnections } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";
import { useConnectionStore } from "@/stores/connectionStore";
import { cn } from "@/lib/utils";

export function ConnectionSelector() {
  const { getToken, isLoaded, userId } = useAuth();
  const { activeConnectionId, setActiveConnection } = useChatStore();
  const { connections, setConnections, setActiveConnection: setMirrorConnection } = useConnectionStore();

  const { data } = useQuery({
    queryKey: ["connections"],
    queryFn: async () => listConnections(await getToken()),
    enabled: isLoaded && Boolean(userId),
    retry: false,
  });

  useEffect(() => {
    if (data) {
      setConnections(data);
      const stillExists = activeConnectionId ? data.some((connection) => connection.id === activeConnectionId) : false;
      if ((!activeConnectionId || !stillExists) && data[0]) {
        setActiveConnection(data[0].id);
        setMirrorConnection(data[0].id);
      } else if (!data.length) {
        setActiveConnection(null);
        setMirrorConnection(null);
      }
    }
  }, [data, activeConnectionId, setActiveConnection, setConnections, setMirrorConnection]);

  if (!connections.length) {
    return (
      <div className="rounded-2xl border border-white/10 bg-[rgba(11,18,30,0.92)] px-3.5 py-2.5 text-xs text-muted-fg">
        No connections
      </div>
    );
  }

  return (
    <select
      value={activeConnectionId ?? ""}
      onChange={(event) => {
        setActiveConnection(event.target.value);
        setMirrorConnection(event.target.value);
      }}
      className={cn(
        "h-11 min-w-[13rem] rounded-2xl border border-white/10 bg-[rgba(11,18,30,0.92)] px-4 text-sm text-fg outline-none focus:border-accent/60 focus:ring-2 focus:ring-accent/18"
      )}
    >
      {connections.map((connection) => (
        <option key={connection.id} value={connection.id}>
          {connection.name}
        </option>
      ))}
    </select>
  );
}
