import { create } from "zustand";
import type { ConnectionRead } from "@/types/api";

interface ConnectionStore {
  activeConnectionId: string | null;
  connections: ConnectionRead[];
  setActiveConnection: (id: string | null) => void;
  setConnections: (connections: ConnectionRead[]) => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  activeConnectionId: null,
  connections: [],
  setActiveConnection: (id) => set({ activeConnectionId: id }),
  setConnections: (connections) => set({ connections }),
}));

