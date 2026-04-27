"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { getSchema } from "@/lib/api";

export function useSchemaExplorer(connectionId: string | null) {
  const { getToken } = useAuth();
  return useQuery({
    queryKey: ["schema", connectionId],
    queryFn: async () => {
      if (!connectionId) return null;
      const token = await getToken();
      return getSchema(connectionId, token);
    },
    enabled: Boolean(connectionId),
  });
}

