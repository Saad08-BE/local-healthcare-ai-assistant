import type { ChatMessage, ChatResult, Conversation, HealthStatus, LocalDocument } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
let csrfToken = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      ...init,
      credentials: "include",
      headers: new Headers(init?.headers),
    });
  } catch {
    throw new Error("Cannot reach the local HealthAI API. Start the backend and try again.");
  }
  if (!response.ok) {
    let message = "Request failed (" + response.status + ").";
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) message = body.detail;
    } catch { /* Keep the safe generic error. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

async function ensureCsrf(): Promise<string> {
  if (!csrfToken) {
    const result = await request<{ csrf_token: string }>("/api/auth/csrf");
    csrfToken = result.csrf_token;
  }
  return csrfToken;
}

async function write<T>(path: string, init: RequestInit): Promise<T> {
  const token = await ensureCsrf();
  const headers = new Headers(init.headers);
  headers.set("X-CSRF-Token", token);
  return request<T>(path, { ...init, headers });
}

function dateMillis(value: string | number | undefined): number {
  if (typeof value === "number") return value;
  if (!value) return Date.now();
  const normalized = value.includes("Z") ? value : value.replace(" ", "T") + "Z";
  const parsed = Date.parse(normalized);
  return Number.isNaN(parsed) ? Date.now() : parsed;
}

type DbMessage = { id: number; role: "user" | "assistant" | "system"; content: string; metadata_json?: string | null; created_at: string };
type DbConversation = { id: string; title: string; created_at?: string; updated_at?: string };
function mapMessage(row: DbMessage): ChatMessage | null {
  if (row.role !== "user" && row.role !== "assistant") return null;
  let metadata: Record<string, unknown> = {};
  try { metadata = row.metadata_json ? JSON.parse(row.metadata_json) as Record<string, unknown> : {}; } catch { /* Older rows may have no metadata. */ }
  const createdAt = dateMillis(row.created_at);
  let result: ChatResult | undefined;
  if (row.role === "assistant" && Object.keys(metadata).length) {
    result = {
      question: "",
      answer: row.content,
      model: typeof metadata.model === "string" ? metadata.model : null,
      offline_fallback: Boolean(metadata.offline_fallback),
      urgent_warning: Boolean(metadata.urgent_warning),
      latency_seconds: typeof metadata.latency_seconds === "number" ? metadata.latency_seconds : 0,
      disclaimer: typeof metadata.disclaimer === "string" ? metadata.disclaimer : "",
      document_sources: Array.isArray(metadata.document_sources) ? metadata.document_sources as ChatResult["document_sources"] : [],
      retrieved_cases: Array.isArray(metadata.retrieved_cases) ? metadata.retrieved_cases as ChatResult["retrieved_cases"] : [],
      cohort_statistics: metadata.cohort_statistics && typeof metadata.cohort_statistics === "object" ? metadata.cohort_statistics as Record<string, unknown> : {},
    };
  }
  return { id: String(row.id), role: row.role, content: row.content, createdAt, ...(result ? { result } : {}) };
}
function mapConversation(row: DbConversation): Conversation {
  return { id: row.id, title: row.title || "New chat", updatedAt: dateMillis(row.updated_at || row.created_at), messages: [] };
}

export const api = {
  health: () => request<HealthStatus>("/api/health"),
  models: () => request<{ models: string[]; default_model: string; ollama_online: boolean }>("/api/models"),
  csrf: ensureCsrf,
  me: () => request<{ user: { id: number; email: string } }>("/api/auth/me"),
  register: async (email: string, password: string) => write<{ user: { id: number; email: string } }>("/api/auth/register", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
  }),
  login: async (email: string, password: string) => write<{ user: { id: number; email: string } }>("/api/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
  }),
  logout: async () => {
    const result = await write<{ logged_out: boolean }>("/api/auth/logout", { method: "POST" });
    csrfToken = "";
    return result;
  },
  conversations: async () => {
    const result = await request<{ conversations: DbConversation[] }>("/api/conversations");
    return result.conversations.map(mapConversation);
  },
  createConversation: async (title = "New chat") => {
    const result = await write<{ conversation: DbConversation }>("/api/conversations", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }),
    });
    return mapConversation(result.conversation);
  },
  getConversation: async (id: string) => {
    const result = await request<{ conversation: DbConversation; messages: DbMessage[]; documents: Array<{ id: string; original_filename: string; created_at: string }> }>("/api/conversations/" + encodeURIComponent(id));
    const conversation = mapConversation(result.conversation);
    conversation.messages = result.messages.map(mapMessage).filter((message): message is ChatMessage => message !== null);
    return { conversation, documents: result.documents };
  },
  deleteConversation: (id: string) => write<{ deleted: boolean }>("/api/conversations/" + encodeURIComponent(id), { method: "DELETE" }),
  documents: async (conversationId: string) => request<{ documents: LocalDocument[] }>("/api/conversations/" + encodeURIComponent(conversationId) + "/documents"),
  chat: (payload: { question: string; model: string; document_filename: string; conversation_id: string; document_id?: string }) => write<ChatResult>("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }),
  upload: (conversationId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return write<{ document: { id: string; filename: string; size_bytes: number; sha256: string }; stored_locally: boolean; conversation_id: string }>(
      "/api/conversations/" + encodeURIComponent(conversationId) + "/documents", { method: "POST", body: form },
    );
  },
  removeDocument: (conversationId: string, documentId: string) => write<{ deleted: boolean }>(
    "/api/conversations/" + encodeURIComponent(conversationId) + "/documents/" + encodeURIComponent(documentId), { method: "DELETE" },
  ),
};
