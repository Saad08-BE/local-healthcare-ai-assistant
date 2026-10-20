import { afterEach, expect, test, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

const { mockConversation } = vi.hoisted(() => ({
  mockConversation: {
    id: "conversation-1",
    title: "New chat",
    updatedAt: 1,
    messages: [],
  },
}));

vi.mock("./api", () => ({
  api: {
    health: vi.fn().mockResolvedValue({
      status: "ok",
      app: "HealthAI",
      ollama: "online",
      pipeline_loaded: false,
      privacy_mode: "local-only",
    }),
    models: vi.fn().mockResolvedValue({
      models: ["qwen2.5:3b"],
      default_model: "qwen2.5:3b",
      ollama_online: true,
    }),
    csrf: vi.fn().mockResolvedValue("test-csrf-token"),
    me: vi.fn().mockResolvedValue({
      user: { id: 1, email: "test@example.com" },
    }),
    conversations: vi.fn().mockResolvedValue([]),
    createConversation: vi.fn().mockResolvedValue(mockConversation),
    getConversation: vi.fn().mockResolvedValue({
      conversation: mockConversation,
      documents: [],
    }),
    documents: vi.fn().mockResolvedValue({ documents: [] }),
    chat: vi.fn(),
    upload: vi.fn(),
    removeDocument: vi.fn(),
    deleteConversation: vi.fn(),
    logout: vi.fn(),
  },
}));

import App from "./App";

afterEach(() => cleanup());

test("renders the HealthAI workspace and privacy indicator", async () => {
  render(<App />);
  // Wait for the authenticated workspace rather than matching the transient loading screen.
  expect(await screen.findByPlaceholderText(/ask healthai/i)).toBeInTheDocument();
  expect(screen.getByText("HealthAI")).toBeInTheDocument();
  expect(screen.getByText(/private by design/i)).toBeInTheDocument();
});
