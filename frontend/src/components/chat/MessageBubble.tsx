"use client";

import type { Message } from "@/stores/chatStore";
import { cn } from "@/lib/utils";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[min(42rem,100%)] rounded-2xl border px-4 py-3 shadow-glow",
          isUser
            ? "border-accent/30 bg-accent/12 text-fg"
            : "border-white/10 bg-white/6 text-fg"
        )}
      >
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] text-muted-fg">
          <span>{isUser ? "You" : "Agent"}</span>
          {message.isStreaming ? <span className="text-accent">streaming</span> : null}
          {message.isError ? <span className="text-danger">error</span> : null}
        </div>
        <p className="whitespace-pre-wrap text-sm leading-6">{message.content || (message.isStreaming ? "Thinking..." : "")}</p>
      </div>
    </div>
  );
}

