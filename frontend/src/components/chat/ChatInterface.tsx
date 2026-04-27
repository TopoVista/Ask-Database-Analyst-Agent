"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useStreamingQuery } from "@/hooks/useStreamingQuery";
import { QueryInput } from "./QueryInput";
import { MessageBubble } from "./MessageBubble";
import { ThinkingSteps } from "./ThinkingSteps";
import { ResultsPanel } from "@/components/results/ResultsPanel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const EXAMPLE_QUERIES = [
  "Why did profit drop last month?",
  "Which products have the highest return rate?",
  "What if we increase price by 10%?",
  "Show me anomalies in sales data",
];

export function ChatInterface() {
  const { messages, addMessage, activeConnectionId } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { runQuery, isStreaming, currentSteps, currentResults } = useStreamingQuery();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentSteps, currentResults]);

  const handleSubmit = async (question: string) => {
    if (!activeConnectionId) return;
    addMessage({ role: "user", content: question });
    await runQuery(question, activeConnectionId);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
        {messages.length === 0 ? (
          <div className="flex min-h-[70vh] items-center justify-center">
            <Card className="w-full max-w-4xl overflow-hidden bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03))]">
              <CardHeader>
                <Badge className="mb-3 w-fit border-accent/30 bg-accent/12 text-accent">Decision intelligence</Badge>
                <CardTitle className="text-3xl">Ask the database a business question</CardTitle>
                <CardDescription className="mt-2 max-w-2xl text-base leading-7">
                  Get a multi-step analytical response with SQL generation, result analysis, anomaly detection, and a narrative answer.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_QUERIES.map((query) => (
                    <button
                      key={query}
                      onClick={() => handleSubmit(query)}
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-fg transition hover:bg-white/10"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}

        <div className="mt-5 space-y-5">
          {isStreaming && <ThinkingSteps steps={currentSteps} />}
          {currentResults && <ResultsPanel results={currentResults} />}
        </div>

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-white/10 bg-slate-950/70 px-4 py-4 backdrop-blur-md md:px-6 lg:px-8">
        <QueryInput
          onSubmit={handleSubmit}
          disabled={isStreaming || !activeConnectionId}
          placeholder={!activeConnectionId ? "Connect a database first..." : "Ask a business question..."}
        />
      </div>
    </div>
  );
}

