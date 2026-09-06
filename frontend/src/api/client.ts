export type User = {
  id: number;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
};

export type Project = {
  id: number;
  owner_id: number;
  name: string;
  topic: string;
  genre: string;
  num_chapters: number;
  word_number: number;
  model_routing: Record<string, unknown> | null;
  architecture: string;
  character_state: string;
  global_summary: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AppSettings = {
  id: number;
  llm_configs: Record<string, unknown>;
  embedding_configs: Record<string, unknown>;
  choose_configs: Record<string, unknown>;
  updated_at: string;
};

export type Job = {
  id: number;
  project_id: number;
  user_id: number;
  type: string;
  status: string;
  progress: number;
  result_ref: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

const TOKEN_KEY = "ba_token";
const USER_KEY = "ba_user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function isLoggedIn(): boolean {
  return Boolean(getToken());
}

export function setAuth(token: string, user: User): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    clearAuth();
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join("; ")
          : res.statusText;
    throw new ApiError(res.status, message || "Request failed");
  }
  return data as T;
}

export function login(username: string, password: string) {
  return api<{ access_token: string; token_type: string; user: User }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function listProjects() {
  return api<Project[]>("/api/projects");
}

export function createProject(payload: {
  name: string;
  topic?: string;
  genre?: string;
  num_chapters?: number;
  word_number?: number;
}) {
  return api<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProject(id: number) {
  return api<Project>(`/api/projects/${id}`);
}

export function updateProject(id: number, payload: Partial<Project>) {
  return api<Project>(`/api/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteProject(id: number) {
  return api<void>(`/api/projects/${id}`, { method: "DELETE" });
}

export function getSettings() {
  return api<AppSettings>("/api/settings");
}

export function putSettings(payload: {
  llm_configs: Record<string, unknown>;
  embedding_configs: Record<string, unknown>;
  choose_configs: Record<string, unknown>;
}) {
  return api<AppSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getJob(id: number) {
  return api<Job>(`/api/jobs/${id}`);
}

export function cancelJob(id: number) {
  return api<Job>(`/api/jobs/${id}/cancel`, { method: "POST" });
}

export type BlueprintItem = {
  chapter_number: number;
  title: string;
  summary: string;
  raw_text: string;
};

export type Chapter = {
  id: number;
  project_id: number;
  chapter_number: number;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export function generateArchitecture(projectId: number) {
  return api<{ job_id: number }>(`/api/projects/${projectId}/architecture/generate`, {
    method: "POST",
  });
}

export function generateBlueprint(projectId: number) {
  return api<{ job_id: number }>(`/api/projects/${projectId}/blueprint/generate`, {
    method: "POST",
  });
}

export function getBlueprint(projectId: number) {
  return api<{ items: BlueprintItem[] }>(`/api/projects/${projectId}/blueprint`);
}

export function putBlueprint(projectId: number, items: BlueprintItem[]) {
  return api<{ items: BlueprintItem[] }>(`/api/projects/${projectId}/blueprint`, {
    method: "PUT",
    body: JSON.stringify({ items }),
  });
}

export function getChapter(projectId: number, n: number) {
  return api<Chapter>(`/api/projects/${projectId}/chapters/${n}`);
}

export function putChapter(projectId: number, n: number, content: string) {
  return api<Chapter>(`/api/projects/${projectId}/chapters/${n}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export function finalizeChapter(projectId: number, n: number) {
  return api<{ job_id: number }>(`/api/projects/${projectId}/chapters/${n}/finalize`, {
    method: "POST",
  });
}

export function ragQuery(projectId: number, query: string, top_k?: number) {
  return api<{ hits: Array<{ id: number; chapter_number: number; chunk_index: number; content: string }> }>(
    `/api/projects/${projectId}/rag/query`,
    {
      method: "POST",
      body: JSON.stringify({ query, top_k }),
    },
  );
}

export type SseHandlers = {
  onMeta?: (data: Record<string, unknown>) => void;
  onToken?: (text: string) => void;
  onUsage?: (data: Record<string, unknown>) => void;
  onDone?: (data: Record<string, unknown>) => void;
  onError?: (message: string) => void;
};

export async function streamChapterDraft(
  projectId: number,
  n: number,
  guidance: string,
  handlers: SseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`/api/projects/${projectId}/chapters/${n}/draft`, {
    method: "POST",
    headers,
    body: JSON.stringify({ guidance }),
    signal,
  });
  if (res.status === 401) {
    clearAuth();
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok || !res.body) {
    throw new ApiError(res.status, "Draft stream failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part
        .split("\n")
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      const raw = line.slice(5).trim();
      try {
        const evt = JSON.parse(raw) as Record<string, unknown>;
        const event = String(evt.event || "");
        if (event === "meta") handlers.onMeta?.(evt);
        else if (event === "token") handlers.onToken?.(String(evt.text || ""));
        else if (event === "usage") handlers.onUsage?.(evt);
        else if (event === "done") handlers.onDone?.(evt);
        else if (event === "error") handlers.onError?.(String(evt.message || "error"));
      } catch {
        /* ignore partial */
      }
    }
  }
}

export async function pollJobUntilDone(
  jobId: number,
  onUpdate?: (job: Job) => void,
  intervalMs = 1500,
): Promise<Job> {
  while (true) {
    const job = await getJob(jobId);
    onUpdate?.(job);
    if (["succeeded", "failed", "cancelled"].includes(job.status)) {
      return job;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export type AgentChatResponse = {
  intent: string;
  tool: string | null;
  job_id: number | null;
  sse_endpoint: string | null;
  message: string;
  data: Record<string, unknown> | null;
};

export type AuditLog = {
  id: number;
  project_id: number;
  user_id: number;
  user_message: string;
  intent: string;
  tool_name: string | null;
  tool_args: Record<string, unknown> | null;
  status: string;
  result_summary: string;
  created_at: string;
};

export type ConsistencyReview = {
  id: number;
  project_id: number;
  chapter_number: number;
  job_id: number | null;
  conflicts: {
    summary?: string;
    conflicts?: Array<{
      type?: string;
      severity?: string;
      detail?: string;
      locations?: unknown[];
    }>;
  };
  raw_text: string;
  created_at: string;
};

export function agentChat(
  projectId: number,
  payload: { message: string; chapter_number?: number; guidance?: string },
) {
  return api<AgentChatResponse>(`/api/projects/${projectId}/agent/chat`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listAudits(projectId: number, limit = 50) {
  return api<AuditLog[]>(`/api/projects/${projectId}/agent/audits?limit=${limit}`);
}

export function consistencyCheck(projectId: number, n: number) {
  return api<{ job_id: number }>(`/api/projects/${projectId}/chapters/${n}/consistency-check`, {
    method: "POST",
  });
}

export function listReviews(projectId: number, n: number) {
  return api<ConsistencyReview[]>(`/api/projects/${projectId}/chapters/${n}/reviews`);
}
