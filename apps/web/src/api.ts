export type StageSummary = {
  id: string;
  title: string;
  description: string;
  implemented: boolean;
};

export type Scaffold = {
  project: string;
  mode: "project-scaffold";
  implemented_capabilities: string[];
  deferred_capabilities: string[];
  stages: StageSummary[];
};

export type Health = {
  status: "ok";
  service: string;
};

export type SourceSnapshot = {
  source: { source_type: "inline_requirement" | "requirement_file" | "repository_guide" | "repository_metadata"; path: string | null };
  normalized_path: string | null;
  sha256: string;
  read_status: "read";
  content: string;
};

export type Run = {
  run_id: string;
  requirement: string;
  status: "prd_awaiting_approval" | "td_awaiting_approval" | "completed";
  prd_draft: { revision: number; content: string };
  prd_approval: { revision: number; approved_at: string } | null;
  td_draft: { revision: number; content: string } | null;
  td_approval: { revision: number; approved_at: string } | null;
  delivery_spec: {
    run_id: string;
    prd_revision: number;
    td_revision: number;
    prd_content: string;
    td_content: string;
  } | null;
  available_commands: Array<"approve_prd" | "approve_td">;
  source_snapshot: SourceSnapshot;
  repository_binding: {
    repository_id: string;
    root_path: string;
    permission: "read_only";
    context_mode: "guide_only" | "indexed_readonly";
  };
  harness_context: {
    entries: Array<{ snapshot: SourceSnapshot; selection_reason: string }>;
    sha256: string;
  };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  scaffold: () => request<Scaffold>("/api/scaffold"),
  createRun: (requirement: string) => request<Run>("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirement }),
  }),
  approvePrd: (run: Run) => request<Run>(`/api/runs/${run.run_id}/approvals/prd`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision: run.prd_draft.revision }),
  }),
  approveTd: (run: Run) => request<Run>(`/api/runs/${run.run_id}/approvals/td`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision: run.td_draft?.revision }),
  }),
};
