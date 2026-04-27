import { API_URL } from "@/lib/constants";
import type { ConnectionCreate, ConnectionRead, QueryHistoryRead, SessionRead, SchemaResponse } from "@/types/api";

async function apiFetch<T>(path: string, token?: string | null, init: RequestInit = {}): Promise<T> {
  try {
    const url = `${API_URL}${path}`;
    console.log("CALLING:", url);
    const headers = new Headers(init.headers);

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const shouldSendJsonContentType = init.body !== undefined && !(init.body instanceof FormData) && !headers.has("Content-Type");
    if (shouldSendJsonContentType) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
    });

    console.log("STATUS:", response.status);

    if (!response.ok) {
      const text = await response.text();
      console.error("ERROR RESPONSE:", text);
      try {
        const parsed = JSON.parse(text);
        const message =
          typeof parsed?.detail === "string"
            ? parsed.detail
            : typeof parsed?.message === "string"
              ? parsed.message
              : text;
        throw new Error(message || `Request failed: ${response.status}`);
      } catch {
        throw new Error(text || `Request failed: ${response.status}`);
      }
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return await response.json();
  } catch (err) {
    console.error("FETCH FAILED:", err);
    throw err;
  }
}

export async function createConnection(payload: ConnectionCreate, token?: string | null) {
  return apiFetch<ConnectionRead>("/api/v1/connections", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function testConnection(connectionId: string, token?: string | null) {
  return apiFetch<{ success: boolean; message: string }>(`/api/v1/connections/${connectionId}/test`, token, {
    method: "POST",
  });
}

export async function deleteConnection(connectionId: string, token?: string | null) {
  return apiFetch<void>(`/api/v1/connections/${connectionId}`, token, {
    method: "DELETE",
  });
}

export async function getSchema(connectionId: string, token?: string | null) {
  return apiFetch<SchemaResponse>(`/api/v1/schema/${connectionId}`, token);
}

export async function listConnections(token?: string | null) {
  return apiFetch<ConnectionRead[]>("/api/v1/connections", token);
}

export async function listSessions(token?: string | null) {
  return apiFetch<SessionRead[]>("/api/v1/sessions", token);
}

export async function getSession(sessionId: string, token?: string | null) {
  return apiFetch<{ session: SessionRead; history: QueryHistoryRead[] }>(`/api/v1/sessions/${sessionId}`, token);
}
