import { api, errorMessage } from "../api";
import type { JobDetail } from "../types";
import {
  badge,
  button,
  card,
  clear,
  el,
  input,
  pageHead,
  setDraft,
  toast,
  takeDraft,
  wordCount,
  formatNumber,
  attachFileInput,
} from "../ui";

const POLL_MS = 1200;
const FILE_ACCEPT = ".txt,.md,.markdown,.docx";

export async function renderHumanize(root: HTMLElement): Promise<void> {
  clear(root);
  const [meta, settings] = await Promise.all([api.meta(), api.settings()]);
  const configured = settings.providers.filter((p) => p.configured);

  root.append(
    pageHead(
      "Humanize Text",
      "Rewrite it so it sounds like a thoughtful human: facts stay exact, quotes and code stay untouched.",
    ),
  );

  if (configured.length === 0) {
    const warning = card("flex gap-3 border-[#F0E7D4] bg-[#FDF6E7]");
    warning.append(el("span", "shrink-0 mt-0.5 text-xl leading-5", "⚠"));
    warning.append(
      el("span", "font-semibold text-[#7D5A12]", "No provider is configured yet. Add a free anonymous endpoint in Settings, or humanize against the catalog defaults."),
    );
    root.append(warning, el("div", "h-6"));
  }

  const layout = el("div", "grid gap-6 lg:grid-cols-2 lg:gap-8");
  root.append(layout);

  // ── input panel ───────────────────────────────────────────────────────────
  const inputCard = card();
  layout.append(inputCard);

  const titleEl = input("Document title (optional)", { placeholder: "Untitled document" });
  const textArea = el(
    "textarea",
    "w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-3 text-base leading-6 text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15 min-h-[360px]",
    "Paste or upload text to humanize…",
  );
  textArea.value = takeDraft();
  textArea.spellcheck = true;

  const counter = el("p", "text-sm text-[#5C6C62]");
  const updateCounter = (): void => {
    counter.textContent = `${formatNumber(wordCount(textArea.value))} words`;
  };
  textArea.addEventListener("input", updateCounter);
  updateCounter();

  const modeSelect = el(
    "select",
    "w-full rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15",
  );
  for (const m of meta.modes) {
    const o = el("option", "", m.label);
    o.value = m.id;
    modeSelect.append(o);
  }
  modeSelect.value = "balanced";
  const modeLabel = el("label", "mb-2 block text-sm font-semibold text-[#25352A]", "Mode");
  const modeBox = el("div", "");
  modeBox.append(modeLabel, modeSelect);

  const intensitySelect = el("select", "w-full rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15");
  for (const m of meta.intensities) {
    const o = el("option", "", m.label);
    o.value = m.id;
    intensitySelect.append(o);
  }
  intensitySelect.value = "medium";
  const intensityLabel = el("label", "mb-2 block text-sm font-semibold text-[#25352A]", "Editing strength");
  const intensityBox = el("div", "");
  intensityBox.append(intensityLabel, intensitySelect);

  const providerSelect = el("select", "w-full rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15");
  const autoOption = el("option", "", "Auto — catalog order");
  autoOption.value = "";
  providerSelect.append(autoOption);
  for (const provider of configured) {
    const o = el("option", "", provider.name);
    o.value = provider.id;
    providerSelect.append(o);
  }
  const providerLabel = el("label", "mb-2 block text-sm font-semibold text-[#25352A]", "Provider");
  const providerBox = el("div", "");
  providerBox.append(providerLabel, providerSelect);

  const upload = button("Upload .txt / .docx", "secondary", () => undefined);
  const uploadBox = el("div", "mt-6 flex items-center gap-3");
  uploadBox.append(upload);
  attachFileInput(upload, FILE_ACCEPT, (file: File) => {
    void (async () => {
      upload.textContent = "Reading…";
      upload.disabled = true;
      try {
        const extracted = await api.extractFile(file);
        textArea.value = extracted.text;
        const titleInput = titleEl.querySelector("input");
        if (titleInput && !titleInput.value) titleInput.value = extracted.filename;
        updateCounter();
        toast(`Loaded ${extracted.filename}.`, "success");
      } catch (error) {
        toast(errorMessage(error), "error");
      } finally {
        upload.textContent = "Upload .txt / .docx";
        upload.disabled = false;
      }
    })();
  });

  inputCard.append(
    el("label", "mb-2 block text-sm font-semibold text-[#25352A]", "Document title (optional)"),
    titleEl,
    textArea,
    uploadBox,
    counter,
    modeBox,
    intensityBox,
    providerBox,
  );

  // ── output panel ─────────────────────────────────────────────────────────
  const outputCard = card();
  layout.append(outputCard);

  const statusHost = el("div", "mt-2 flex items-center gap-2 text-sm font-medium text-[#1D3026]");
  const progressTrack = el("div", "mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#E8EBE5]");
  const progressBar = el("div", "h-full w-0 rounded-full bg-[#1F6B4A] transition-all");
  progressTrack.append(progressBar);
  const progressLabel = el("p", "mt-1.5 text-sm text-[#5C6C62]", "Ready when you are.");

  const outputArea = el(
    "textarea",
    "w-full resize-y rounded-lg border border-[#E0E4DA] bg-[#FAFBF7] px-3.5 py-3 text-base leading-6 text-[#1D3026] outline-none focus:border-[#1F6B4A] min-h-[420px]",
  );
  outputArea.readOnly = true;
  outputArea.placeholder = "Your rewritten text appears here when the job finishes.";

  const errorNote = el("p", "mt-3 hidden text-sm leading-6 text-[#8B2020]");

  const copy = button("Copy", "secondary", () => void copyText(outputArea.value), { disabled: true });
  const txt = button("Download .txt", "secondary", () => void download("txt"), { disabled: true });
  const docx = button("Download .docx", "secondary", () => void download("docx"), { disabled: true });
  const retry = button("Retry failed chunks", "secondary", () => void retryJob(), { disabled: true });
  const cancel = button("Cancel job", "danger", () => void cancelJob(), { disabled: true });
  const startBtn = button("Humanize text", "primary", () => void submitJob());
  const toDetector = button("Open style signal", "ghost", () => {
    setDraft(outputArea.value);
    window.location.hash = "#/detector";
  });
  const toSimilarity = button("Check similarity", "ghost", () => {
    setDraft(outputArea.value);
    window.location.hash = "#/plagiarism";
  });

  const toolbar = el("div", "mt-5 flex flex-wrap items-center gap-2");
  toolbar.append(startBtn, copy, txt, docx, retry, cancel, toDetector, toSimilarity);
  outputCard.append(statusHost, progressTrack, progressLabel, outputArea, errorNote, toolbar);

  // ── behaviour ─────────────────────────────────────────────────────────────
  let currentJob: JobDetail | null = null;

  function setProgress(pct: number): void {
    progressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
  }

  function applyJob(job: JobDetail): void {
    currentJob = job;
    statusHost.replaceChildren(badge(job.status, job.status === "failed" ? "error" : "accent"));
    setProgress(job.progress_percent);
    const finished = job.status === "completed";
    progressLabel.textContent = finished
      ? `Complete — ${job.provider_id ?? "provider"} · ${job.model_id ?? "model"} · chunks ${job.completed_chunks}/${job.total_chunks}`
      : job.status === "failed"
        ? job.error || "Failed."
        : job.status === "cancelled"
          ? "Cancelled."
          : `Working… ${job.progress_percent}%`;
    errorNote.classList.toggle("hidden", !job.error);
    errorNote.textContent = job.error ?? "";
    const hasOutput = Boolean(job.output_text);
    for (const control of [copy, txt, docx, toDetector, toSimilarity]) control.disabled = !hasOutput;
    if (hasOutput && outputArea.value !== (job.output_text ?? "")) outputArea.value = job.output_text ?? "";
  }

  async function poll(jobId: number): Promise<void> {
    if (!root.isConnected) return;
    try {
      const job = await api.job(jobId);
      if (!root.isConnected) return;
      applyJob(job);
      if (["queued", "running", "paused"].includes(job.status)) {
        window.setTimeout(() => void poll(jobId), POLL_MS);
      }
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  async function submitJob(): Promise<void> {
    const text = textArea.value.trim();
    if (!text) {
      toast("There is no text to humanize.", "error");
      return;
    }
    startBtn.disabled = true;
    startBtn.textContent = "Starting…";
    try {
      const created = await api.humanize({
        text,
        title: titleEl.querySelector("input")?.value || undefined,
        mode: modeSelect.value || "balanced",
        intensity: intensitySelect.value || "medium",
        provider_id: providerSelect.value || undefined,
        preserve_formatting: true,
        keep_quotes: true,
      });
      currentJob = null;
      outputArea.value = "";
      errorNote.classList.add("hidden");
      setProgress(0);
      await poll(created.job_id);
    } catch (error) {
      toast(errorMessage(error), "error");
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = "Humanize text";
    }
  }

  async function cancelJob(): Promise<void> {
    if (!currentJob) return;
    try {
      await api.cancelJob(currentJob.id);
      toast("Cancellation requested.", "info");
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  async function retryJob(): Promise<void> {
    if (!currentJob) return;
    try {
      await api.retryJob(currentJob.id);
      toast("Retrying…", "info");
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  async function download(format: "txt" | "docx"): Promise<void> {
    if (!currentJob) return;
    try {
      await api.downloadJob(currentJob.id, format, currentJob.title);
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  async function copyText(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to clipboard.", "success");
    } catch {
      toast("Could not copy — select the text and copy manually.", "error");
    }
  }
}


