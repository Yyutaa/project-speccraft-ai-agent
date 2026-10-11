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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  scaffold: () => request<Scaffold>("/api/scaffold"),
};
