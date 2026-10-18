import { afterEach, expect, test, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "./App";
vi.mock("./api", () => ({api:{health:vi.fn().mockResolvedValue({status:"ok",app:"HealthAI",ollama:"online",pipeline_loaded:false,privacy_mode:"local-only"}),models:vi.fn().mockResolvedValue({models:["qwen2.5:3b"],default_model:"qwen2.5:3b",ollama_online:true}),documents:vi.fn().mockResolvedValue({documents:[]}),chat:vi.fn(),upload:vi.fn(),removeDocument:vi.fn()}}));
afterEach(()=>cleanup());
test("renders the HealthAI workspace and privacy indicator",async()=>{render(<App/>);expect(screen.getByText("HealthAI")).toBeInTheDocument();expect(screen.getByText(/private by design/i)).toBeInTheDocument();expect(await screen.findByPlaceholderText(/ask healthai/i)).toBeInTheDocument();});
