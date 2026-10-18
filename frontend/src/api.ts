import type { ChatResult, HealthStatus, LocalDocument } from "./types";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(API_BASE + path, init); } catch { throw new Error("Cannot reach the local HealthAI API. Start the backend and try again."); }
  if (!response.ok) { let message = "Request failed (" + response.status + ")."; try { const body = await response.json() as { detail?: string }; if (body.detail) message = body.detail; } catch { /* Keep the safe generic error. */ } throw new Error(message); }
  return response.json() as Promise<T>;
}
export const api = {
  health: () => request<HealthStatus>("/api/health"),
  models: () => request<{ models: string[]; default_model: string; ollama_online: boolean }>("/api/models"),
  documents: () => request<{ documents: LocalDocument[] }>("/api/documents"),
  chat: (payload: { question: string; model: string; document_filename: string }) => request<ChatResult>("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  upload: (file: File) => { const form = new FormData(); form.append("file", file); return request<{ filename: string; chunks_indexed: number; stored_locally: boolean }>("/api/documents", { method: "POST", body: form }); },
  removeDocument: (filename: string) => request<{ deleted: boolean; filename: string }>("/api/documents/" + encodeURIComponent(filename), { method: "DELETE" }),
};
