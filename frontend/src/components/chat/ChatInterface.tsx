"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Database, ScrollText, Sparkles } from "lucide-react";
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

const PROMISE_POINTS = [
  {
    title: "Schema-aware planning",
    description: "The workflow starts with table context, not blind SQL generation.",
    icon: Database,
  },
  {
    title: "Traceable outputs",
    description: "Each answer keeps the reasoning chain, query steps, and returned evidence visible.",
    icon: ScrollText,
  },
  {
    title: "Operator-friendly narrative",
    description: "Results are translated into a business explanation you can actually act on.",
    icon: Sparkles,
  },
];

export function ChatInterface() {
  const { messages, addMessage, activeConnectionId } = useChatStore();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const { runQuery, isStreaming, currentSteps, currentResults } = useStreamingQuery();

  useEffect(() => {
    if (!autoScrollEnabled || !shouldStickToBottomRef.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentSteps, currentResults, autoScrollEnabled]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      const isNearBottom = distanceFromBottom < 120;
      shouldStickToBottomRef.current = isNearBottom;
      setAutoScrollEnabled(isNearBottom);
    };

    handleScroll();
    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, [messages, currentSteps, currentResults]);

  const handleSubmit = async (question: string) => {
    if (!activeConnectionId) return;
    shouldStickToBottomRef.current = true;
    setAutoScrollEnabled(true);
    addMessage({ role: "user", content: question });
    await runQuery(question, activeConnectionId);
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
        {messages.length === 0 ? (
          <div className="mx-auto flex min-h-[70vh] w-full max-w-6xl items-center">
            <section className="grid w-full gap-6 lg:grid-cols-[1.08fr,0.92fr]">
              <Card className="overflow-hidden">
                <CardHeader className="border-b border-white/10">
                  <Badge className="mb-4 w-fit border-accent/20 bg-accent/10 text-accent">Analytical workspace</Badge>
                  <CardTitle className="max-w-3xl text-4xl leading-tight md:text-5xl">
                    Ask a business question and inspect the full reasoning path.
                  </CardTitle>
                  <CardDescription className="mt-3 max-w-2xl text-base leading-7 text-fg/72">
                    Start from one prompt, let the system inspect schema context, run the required SQL, and return a narrative grounded in the evidence.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.24em] text-muted-fg">Try a question</p>
                    <div className="mt-4 grid gap-3">
                      {EXAMPLE_QUERIES.map((query) => (
                        <button
                          key={query}
                          onClick={() => handleSubmit(query)}
                          className="group flex items-center justify-between rounded-[22px] border border-white/10 bg-white/5 px-4 py-4 text-left transition hover:border-white/16 hover:bg-white/8"
                        >
                          <span className="pr-4 text-sm leading-6 text-fg/88">{query}</span>
                          <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-fg transition group-hover:text-accent" />
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    {PROMISE_POINTS.map((point) => {
                      const Icon = point.icon;
                      return (
                        <div key={point.title} className="rounded-[22px] border border-white/10 bg-[rgba(10,16,27,0.92)] px-4 py-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
                            <Icon className="h-4 w-4 text-accent" />
                          </div>
                          <p className="mt-4 text-sm font-medium text-fg">{point.title}</p>
                          <p className="mt-2 text-sm leading-6 text-fg/66">{point.description}</p>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </section>
          </div>
        ) : (
          <div className="mx-auto max-w-5xl space-y-5">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}

        <div className="mx-auto mt-5 max-w-5xl space-y-5">
          {isStreaming && <ThinkingSteps steps={currentSteps} />}
          {currentResults && <ResultsPanel results={currentResults} />}
        </div>

        {isStreaming && !autoScrollEnabled ? (
          <div className="sticky bottom-4 mt-4 flex justify-center">
            <button
              onClick={() => {
                shouldStickToBottomRef.current = true;
                setAutoScrollEnabled(true);
                messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
              }}
              className="rounded-full border border-white/10 bg-[rgba(8,13,22,0.94)] px-4 py-2 text-xs text-fg shadow-glow transition hover:border-white/16 hover:bg-[rgba(12,18,30,0.96)]"
            >
              Jump to latest response
            </button>
          </div>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-white/10 bg-[rgba(6,10,17,0.76)] px-4 py-4 backdrop-blur-xl md:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <QueryInput
            onSubmit={handleSubmit}
            disabled={isStreaming || !activeConnectionId}
            placeholder={!activeConnectionId ? "Connect a database first..." : "Ask a business question..."}
          />
        </div>
      </div>
    </div>
  );
}
