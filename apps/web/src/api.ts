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

export type FactDimension = "role" | "workflow" | "permission" | "failure" | "acceptance";

export type ClarificationProposal = {
  question_id: string;
  gap_id: string;
  question: string;
  options: Array<{ option_id: string; label: string }>;
  recommended_option_id: string | null;
  recommendation_reason: string | null;
};

export type ClarificationAnswer = {
  question_id: string;
  selected_option_id?: string;
  custom_answer?: string;
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
  status: "awaiting_clarification" | "prd_awaiting_approval" | "td_awaiting_approval" | "completed";
  prd_draft: { revision: number; content: string } | null;
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
  available_commands: Array<"submit_clarification" | "approve_prd" | "approve_td">;
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
  ledger: {
    revision: number;
    facts: Array<{
      fact_id: string;
      kind: "fact" | "decision";
      dimension: FactDimension | null;
      claim: string;
      source?: { sha256: string; excerpt: string } | null;
      decision_evidence?: {
        batch_id: string;
        question_id: string;
        command_id: string;
        expected_revision: number;
        answer: string;
        decided_at: string;
      } | null;
    }>;
  };
  completeness: {
    ledger_revision: number;
    gaps: Array<{
      gap_id: string;
      dimension: FactDimension;
      blocking: boolean;
      reason: string;
      ledger_revision: number;
    }>;
  };
  clarification_batch: {
    batch_id: string;
    revision: number;
    ledger_revision: number;
    gap_ids: string[];
    blocking_gap_ids: string[];
    proposals: ClarificationProposal[];
  } | null;
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
    body: JSON.stringify({ revision: run.prd_draft?.revision }),
  }),
  submitClarification: (run: Run, answers: ClarificationAnswer[]) =>
    request<Run>(`/api/runs/${run.run_id}/clarifications/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_revision: run.ledger.revision,
        command_id: `${run.run_id}:clarification:${run.ledger.revision}`,
        answers,
      }),
    }),
  approveTd: (run: Run) => request<Run>(`/api/runs/${run.run_id}/approvals/td`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision: run.td_draft?.revision }),
  }),
};
