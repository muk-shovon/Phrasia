import type {
  AppSettings,
  DetectorReport,
  DocumentDetail,
  DocumentSummary,
  HumanizePayload,
  HumanizeResult,
  JobStatus,
  PlagiarismReport,
  Reference,
  SentenceResult,
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
  if (detail && typeof detail === "object" && "error" in detail) {
    const error = (detail as { error?: { message?: unknown } }).error;
    if (error && typeof error.message === "string") return error.message;
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let payload: unknown = null;
    try { payload = await response.json(); } catch { payload = null; }
    throw new ApiError(messageFromPayload(payload, `Request failed (${response.status}).`), response.status, "request_failed");
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
  const base = title.trim().replace(/[^a-zA-Z0-9 -]/g, "").replace(/\s+/g, "-").slice(0, 60);
  return base || "phrasia";
}

export const api = {
  humanize: (payload: HumanizePayload) =>
    request<HumanizeResult>("/api/humanize", json("POST", payload)),

  startJob: (payload: HumanizePayload) =>
    request<{ job_id: string; status: string }>("/api/humanize/jobs", json("POST", payload)),
  job: (id: string) => request<JobStatus>(`/api/humanize/jobs/${id}`),
  rehumanize: (payload: {
    text: string; tone: string; strength: string; provider: string;
    replace_dashes: boolean; straight_quotes: boolean;
  }) => request<SentenceResult>("/api/humanize/sentence", json("POST", payload)),
  feedback: (payload: {
    action: "accepted" | "rejected" | "edited";
    version_id: number | null;
    sentence_idx: number | null;
    source_text: string;
    final_text: string;
    tone: string;
    strength: string;
    operation?: string;
  }) => request<{ id: number; saved_example: boolean }>("/api/feedback", json("POST", payload)),

  settings: () => request<AppSettings>("/api/settings"),
  saveSettings: (patch: Record<string, unknown>) =>
    request<AppSettings>("/api/settings", { method: "PUT", body: JSON.stringify(patch) }),
  saveKey: (provider: string, apiKey: string) =>
    request<{ saved: boolean }>("/api/settings/keys", json("POST", { provider, api_key: apiKey })),
  removeKey: (provider: string) =>
    request<{ deleted: boolean }>(`/api/settings/keys/${provider}`, { method: "DELETE" }),
  testProvider: (provider: string, apiKey?: string) =>
    request<{
      ok: boolean; provider: string; model?: string; latency_ms?: number; error?: string;
    }>("/api/settings/test", json("POST", { provider, api_key: apiKey || null })),
  clearCache: () =>
    request<{ deleted: number }>("/api/settings/cache/clear", { method: "POST" }),

  documents: (limit = 100) =>
    request<{ documents: DocumentSummary[] }>(`/api/documents?limit=${limit}`),
  document: (id: number) => request<DocumentDetail>(`/api/documents/${id}`),
  deleteDocument: (id: number) =>
    request<{ deleted: boolean }>(`/api/documents/${id}`, { method: "DELETE" }),

  references: () => request<{ references: Reference[] }>("/api/plagiarism/references"),
  addReference: (title: string, text: string) =>
    request<Reference>("/api/plagiarism/references", json("POST", { title, text })),
  deleteReference: (id: number) =>
    request<{ deleted: boolean }>(`/api/plagiarism/references/${id}`, { method: "DELETE" }),
  checkPlagiarism: (text: string) =>
    request<PlagiarismReport>("/api/plagiarism/check", json("POST", { text })),
  detect: (text: string) =>
    request<DetectorReport>("/api/detector/check", json("POST", { text })),

  async download(text: string, title: string, format: "txt" | "docx"): Promise<void> {
    const path = format === "docx" ? "/api/export/docx" : "/api/export";
    const response = await fetch(path, json("POST", { text, title }));
    if (!response.ok) {
      let payload: unknown = null;
      try { payload = await response.json(); } catch { payload = null; }
      throw new ApiError(messageFromPayload(payload, "Could not export this text."), response.status, "export_failed");
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
