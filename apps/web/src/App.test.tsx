import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";


afterEach(() => vi.restoreAllMocks());

test("shows the honest scaffold state returned by the API", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const path = String(input);
    const body = path.endsWith("/api/health")
      ? { status: "ok", service: "speccraft-project-scaffold" }
      : {
          project: "SpecCraft AI Agent",
          mode: "project-scaffold",
          implemented_capabilities: ["React 与 FastAPI 最小链路"],
          deferred_capabilities: ["LLM Provider 与模型调用"],
          stages: [
            {
              id: "requirement_context",
              title: "需求上下文构建",
              description: "建立可信来源。",
              implemented: false,
            },
          ],
        };
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  }));

  render(<App />);

  expect(await screen.findByText("API 已连接")).toBeInTheDocument();
  expect(screen.getByText("需求上下文构建")).toBeInTheDocument();
  expect(screen.getByText("待实现")).toBeInTheDocument();
});
