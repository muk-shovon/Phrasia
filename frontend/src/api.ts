import type {
  DetectorReport,
  DocumentDetail,
  DocumentSummary,
  HumanizePayload,
  HumanizeResult,
  PlagiarismReport,
  Reference,
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
