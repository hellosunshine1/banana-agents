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
