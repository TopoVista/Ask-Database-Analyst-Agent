"use client";

import type { Message } from "@/stores/chatStore";
import { cn } from "@/lib/utils";
import { RichTextMessage } from "./RichTextMessage";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "w-full border px-5 py-4 shadow-glow",
          isUser
            ? "max-w-[min(40rem,100%)] rounded-[28px_28px_12px_28px] border-accent/24 bg-[linear-gradient(180deg,rgba(58,45,14,0.7),rgba(34,27,11,0.86))]"
            : "max-w-[min(52rem,100%)] rounded-[28px_28px_28px_12px] border-white/10 bg-[linear-gradient(180deg,rgba(16,24,38,0.96),rgba(10,15,26,0.98))]"
        )}
      >
        <div className="mb-3 flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] text-muted-fg">
          <span>{isUser ? "Question" : "Analysis agent"}</span>
          {message.isStreaming ? <span className="text-accent">streaming</span> : null}
          {message.isError ? <span className="text-danger">error</span> : null}
        </div>
        {isUser || message.isError ? (
          <p className="whitespace-pre-wrap text-sm leading-7 text-fg/92">{message.content || (message.isStreaming ? "Thinking..." : "")}</p>
        ) : (
          <RichTextMessage text={message.content || (message.isStreaming ? "Thinking..." : "")} />
        )}
      </div>
    </div>
  );
}
