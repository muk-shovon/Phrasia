import type {
  DetectorReport,
  DocumentDetail,
  DocumentSummary,
  HumanizePayload,
  JobDetail,
  JobSummary,
  MetaResponse,
  PlagiarismReport,
  Reference,
  SettingsResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function messageFromPayload(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : "",
      )
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  if (detail && typeof detail === "object" && "error" in detail) {
    const error = (detail as { error?: { message?: unknown } }).error;
    if (error && typeof error.message === "string") return error.message;
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new ApiError(
      messageFromPayload(payload, `Request failed (${response.status}).`),
      response.status,
      "request_failed",
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function json(method: string, body: unknown): RequestInit {
  return { method, body: JSON.stringify(body) };
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

function slug(title: string): string {
  const base = title
    .trim()
    .replace(/[^a-zA-Z0-9 -]/g, "")
    .replace(/\s+/g, "-")
    .slice(0, 60);
  return base || "phrasia";
}

export const api = {
  meta: () => request<MetaResponse>("/api/meta"),

  humanize: (payload: HumanizePayload) =>
    request<{ job_id: number }>("/api/humanize", json("POST", payload)),
  jobs: (limit = 50) => request<{ jobs: JobSummary[] }>(`/api/jobs?limit=${limit}`),
  job: (id: number) => request<JobDetail>(`/api/jobs/${id}`),
  retryJob: (id: number) =>
    request<{ job_id: number; status: string }>(`/api/jobs/${id}/retry`, {
      method: "POST",
    }),
  cancelJob: (id: number) =>
    request<{ job_id: number; status: string }>(`/api/jobs/${id}/cancel`, {
      method: "POST",
    }),
  deleteJob: (id: number) =>
    request<{ deleted: boolean }>(`/api/jobs/${id}`, { method: "DELETE" }),

  documents: (limit = 100) =>
    request<{ documents: DocumentSummary[] }>(`/api/documents?limit=${limit}`),
  document: (id: number) => request<DocumentDetail>(`/api/documents/${id}`),
  deleteDocument: (id: number) =>
    request<{ deleted: boolean }>(`/api/documents/${id}`, { method: "DELETE" }),

  settings: () => request<SettingsResponse>("/api/settings"),
  saveProvider: (
    id: string,
    payload: { api_key?: string; model?: string; base_url?: string; enabled?: boolean },
  ) => request<{ provider: unknown }>(`/api/settings/providers/${id}`, json("PUT", payload)),
  clearProviderKey: (id: string) =>
    request<{ cleared: boolean }>(`/api/settings/providers/${id}/key`, {
      method: "DELETE",
    }),
  testProvider: (id: string) =>
    request<{ ok: boolean; message: string }>(`/api/settings/providers/${id}/test`, {
      method: "POST",
    }),
  savePreferences: (preferred_provider: string | null) =>
    request<{ preferred_provider: string | null }>(
      "/api/settings/preferences",
      json("PUT", { preferred_provider }),
    ),

  references: () => request<{ references: Reference[] }>("/api/plagiarism/references"),
  addReference: (title: string, text: string) =>
    request<Reference>("/api/plagiarism/references", json("POST", { title, text })),
  deleteReference: (id: number) =>
    request<{ deleted: boolean }>(`/api/plagiarism/references/${id}`, {
      method: "DELETE",
    }),
  checkPlagiarism: (text: string) =>
    request<PlagiarismReport>("/api/plagiarism/check", json("POST", { text })),
  detect: (text: string) =>
    request<DetectorReport>("/api/detector/check", json("POST", { text })),



  async downloadJob(id: number, format: "txt" | "docx", title: string): Promise<void> {
    const response = await fetch(`/api/jobs/${id}/export?format=${format}`);
    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw new ApiError(
        messageFromPayload(payload, "Could not export this job."),
        response.status,
        "export_failed",
      );
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${slug(title)}.${format}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 2_000);
  },
};
