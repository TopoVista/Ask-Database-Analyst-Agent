"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { listSessions, getSession } from "@/lib/api";

export function useQueryHistory() {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: ["sessions"],
    queryFn: async () => listSessions(await getToken()),
  });
}

export function useSessionDetails(sessionId: string | null) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: async () => {
      if (!sessionId) return null;
      return getSession(sessionId, await getToken());
    },
    enabled: Boolean(sessionId),
  });
}

