import { create } from "zustand";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  isError?: boolean;
  metadata?: {
    intent?: unknown;
    analysis?: unknown;
    queryResults?: unknown[];
    executionTimeMs?: number;
  };
  createdAt: string;
}

interface ChatStore {
  messages: Message[];
  activeConnectionId: string | null;
  currentSessionId: string;
  addMessage: (msg: Omit<Message, "id" | "createdAt">) => void;
  updateLastMessage: (content: string, updates?: Partial<Message>) => void;
  setActiveConnection: (id: string | null) => void;
  clearMessages: () => void;
  newSession: () => void;
}

const createId = () => globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2);

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  activeConnectionId: null,
  currentSessionId: createId(),

  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, { ...msg, id: createId(), createdAt: new Date().toISOString() }],
    })),

  updateLastMessage: (content, updates = {}) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, content, ...updates };
      }
      return { messages };
    }),

  setActiveConnection: (id) => set({ activeConnectionId: id }),
  clearMessages: () => set({ messages: [] }),
  newSession: () => set({ messages: [], currentSessionId: createId() }),
}));

