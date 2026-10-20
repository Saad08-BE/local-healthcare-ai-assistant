export type Role = "user" | "assistant";
export interface SourceExcerpt { citation: string; score: number; text: string }
export interface RetrievedCase { score: number; text: string }
export interface ChatResult { question: string; answer: string; model: string | null; offline_fallback: boolean; urgent_warning: boolean; latency_seconds: number; disclaimer: string; document_sources: SourceExcerpt[]; retrieved_cases: RetrievedCase[]; cohort_statistics: Record<string, unknown> }
export interface ChatMessage { id: string; role: Role; content: string; createdAt: number; result?: ChatResult; error?: boolean }
export interface Conversation { id: string; title: string; updatedAt: number; messages: ChatMessage[] }
export interface LocalDocument { id: string; filename: string; size_bytes: number; sha256?: string; created_at?: string }
export interface HealthStatus { status: string; app: string; ollama: "online" | "offline"; pipeline_loaded: boolean; privacy_mode: string }
