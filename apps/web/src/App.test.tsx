import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";

const scaffold = {
  project: "SpecCraft AI Agent",
  mode: "project-scaffold",
  implemented_capabilities: ["进程内存 Run"],
  deferred_capabilities: ["持久化 Run"],
  stages: [{ id: "prd", title: "产品规格设计", description: "编制 PRD。", implemented: false }],
};

function run(status: string) {
  const base = {
    run_id: "run-1",
    requirement: "做一个问候页面",
    status,
    prd_draft: { revision: 1, content: "# PRD\n问候页面" },
    prd_approval: null,
    td_draft: null,
    td_approval: null,
    delivery_spec: null,
    available_commands: ["approve_prd"],
    source_snapshot: {
      source: { source_type: "inline_requirement", path: null },
      normalized_path: null,
      sha256: "a".repeat(64),
      read_status: "read",
      content: "做一个问候页面",
    },
    repository_binding: {
      repository_id: "exportflow-sample",
      root_path: "/workspace/exportflow-sample",
      permission: "read_only",
      context_mode: "guide_only",
    },
    harness_context: {
      entries: [{
        snapshot: {
          source: { source_type: "repository_guide", path: "AGENTS.md" },
          normalized_path: "AGENTS.md",
          sha256: "b".repeat(64),
          read_status: "read",
          content: "技术约束",
        },
        selection_reason: "repository guide supplies engineering constraints",
      }],
      sha256: "c".repeat(64),
    },
  };
  if (status === "td_awaiting_approval") {
    return {
      ...base,
      prd_approval: { revision: 1, approved_at: "2026-10-12T00:00:00Z" },
      td_draft: { revision: 1, content: "# TD\n使用 React" },
      available_commands: ["approve_td"],
    };
  }
  if (status === "completed") {
    return {
      ...base,
      prd_approval: { revision: 1, approved_at: "2026-10-12T00:00:00Z" },
      td_draft: { revision: 1, content: "# TD\n使用 React" },
      td_approval: { revision: 1, approved_at: "2026-10-12T00:01:00Z" },
      delivery_spec: { run_id: "run-1", prd_revision: 1, td_revision: 1, prd_content: "# PRD\n问候页面", td_content: "# TD\n使用 React" },
      available_commands: [],
    };
  }
  return base;
}

function installApi(fetcher: typeof fetch) {
  vi.stubGlobal("fetch", fetcher);
}

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("runs the PRD-first happy path from API-projected state", async () => {
  let current = run("prd_awaiting_approval");
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/health") return json({ status: "ok", service: "speccraft-project-scaffold" });
    if (path === "/api/scaffold") return json(scaffold);
    if (path === "/api/runs" && init?.method === "POST") return json(current, 201);
    if (path.endsWith("/approvals/prd")) {
      current = run("td_awaiting_approval");
      return json(current);
    }
    if (path.endsWith("/approvals/td")) {
      current = run("completed");
      return json(current);
    }
    return json(current);
  });
  installApi(fetcher as typeof fetch);
  render(<App />);

  expect(await screen.findByText("API 已连接")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("一句话需求"), { target: { value: "做一个问候页面" } });
  fireEvent.click(screen.getByRole("button", { name: "创建 Run" }));
  expect(await screen.findByText("等待 PRD 人工审批")).toBeInTheDocument();
  expect(screen.getByText("# PRD 问候页面")).toBeInTheDocument();
  expect(screen.getByText("只读工程上下文 · guide_only")).toBeInTheDocument();
  expect(screen.getByText("AGENTS.md")).toBeInTheDocument();
  expect(screen.getByText(/repository guide supplies engineering constraints/)).toBeInTheDocument();
  expect(screen.getByText(`SHA-256 ${"b".repeat(64)}`)).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledWith("/api/runs", expect.objectContaining({
    method: "POST",
    body: JSON.stringify({ requirement: "做一个问候页面" }),
  }));

  fireEvent.click(screen.getByRole("button", { name: "批准 PRD" }));
  expect(await screen.findByText("等待 TD 人工审批")).toBeInTheDocument();
  expect(screen.getByText("# TD 使用 React")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "批准 TD" }));
  expect(await screen.findByText("已完成")).toBeInTheDocument();
  expect(screen.getByText(/\"prd_revision\": 1/)).toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledWith("/api/runs/run-1/approvals/td", expect.objectContaining({
    method: "POST",
    body: JSON.stringify({ revision: 1 }),
  }));
});

test("keeps the last server state when an approval is rejected", async () => {
  const fetcher = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/health") return json({ status: "ok", service: "speccraft-project-scaffold" });
    if (path === "/api/scaffold") return json(scaffold);
    if (path === "/api/runs" && init?.method === "POST") return json(run("prd_awaiting_approval"), 201);
    if (path.endsWith("/approvals/prd")) return json({ detail: { code: "invalid_transition" } }, 409);
    return json(run("prd_awaiting_approval"));
  });
  installApi(fetcher as typeof fetch);
  render(<App />);

  expect(await screen.findByText("API 已连接")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("一句话需求"), { target: { value: "做一个问候页面" } });
  fireEvent.click(screen.getByRole("button", { name: "创建 Run" }));
  expect(await screen.findByText("等待 PRD 人工审批")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "批准 PRD" }));

  expect(await screen.findByText(/请求失败：409/)).toBeInTheDocument();
  expect(screen.getByText("等待 PRD 人工审批")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "批准 PRD" })).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText("等待 TD 人工审批")).not.toBeInTheDocument());
});
