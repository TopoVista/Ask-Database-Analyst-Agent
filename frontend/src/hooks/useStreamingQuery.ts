"use client";

import { useCallback, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { API_URL } from "@/lib/constants";
import { consumeEventStream } from "@/lib/streaming";
import { useChatStore } from "@/stores/chatStore";
import type { AgentStep, QueryResult } from "@/types/agent";

export function useStreamingQuery() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentSteps, setCurrentSteps] = useState<AgentStep[]>([]);
  const [currentResults, setCurrentResults] = useState<QueryResult[] | null>(null);
  const { addMessage, updateLastMessage, currentSessionId } = useChatStore();
  const { getToken } = useAuth();

  const runQuery = useCallback(
    async (question: string, connectionId: string) => {
      setIsStreaming(true);
      setCurrentSteps([]);
      setCurrentResults(null);

      const token = await getToken();
      let insightBuffer = "";
      const queryResults: QueryResult[] = [];
      let intent: unknown = null;
      let analysis: unknown = null;

      addMessage({ role: "assistant", content: "", isStreaming: true });

      try {
        const response = await fetch(`${API_URL}/api/v1/queries/run`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            question,
            connection_id: connectionId,
            session_id: currentSessionId,
          }),
        });

        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || `HTTP ${response.status}`);
        }

        await consumeEventStream(response, (event) => {
          switch (event.type) {
            case "step":
              setCurrentSteps((prev) => [
                ...prev,
                { ...event.data, timestamp: Date.now() },
              ]);
              break;
            case "intent":
              intent = event.data;
              break;
            case "query_result":
              queryResults.push({
                taskId: event.data.task_id,
                taskDescription: event.data.task_description,
                sql: event.data.sql,
                rows: event.data.rows ?? [],
                columns: event.data.columns ?? [],
                success: Boolean(event.data.success),
                rowCount: event.data.row_count ?? event.data.rows?.length ?? 0,
                error: event.data.error ?? null,
              });
              setCurrentResults([...queryResults]);
              break;
            case "analysis":
              analysis = event.data;
              break;
            case "insight_token":
              insightBuffer += event.data.token;
              updateLastMessage(insightBuffer);
              break;
            case "done":
              updateLastMessage(insightBuffer, {
                isStreaming: false,
                metadata: {
                  intent,
                  analysis,
                  queryResults,
                  executionTimeMs: event.data.execution_time_ms,
                },
              });
              break;
            case "error":
              updateLastMessage(`Error: ${event.data.message}`, {
                isStreaming: false,
                isError: true,
              });
              break;
            default:
              break;
          }
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Something went wrong. Please try again.";
        updateLastMessage(message, {
          isStreaming: false,
          isError: true,
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [addMessage, updateLastMessage, currentSessionId, getToken]
  );

  return { runQuery, isStreaming, currentSteps, currentResults };
}
