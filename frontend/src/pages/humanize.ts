import { api, errorMessage } from "../api";
import type { JobDetail } from "../types";
import {
  badge,
  button,
  card,
  el,
  formatNumber,
  pageHead,
  setDraft,
  toast,
  wordCount,
} from "../ui";

const POLL_MS = 1200;

// ── word-level diff (pure TS, no library) ──────────────────────────────────
interface DiffChunk {
  kind: "context" | "delete" | "insert";
  text: string;
}

function diffWords(a: string[], b: string[]): DiffChunk[] {
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const chunks: DiffChunk[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      chunks.push({ kind: "context", text: a[i] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      chunks.push({ kind: "delete", text: a[i] });
      i++;
    } else {
      chunks.push({ kind: "insert", text: b[j] });
      j++;
    }
  }
  while (i < n) chunks.push({ kind: "delete", text: a[i++] });
  while (j < m) chunks.push({ kind: "insert", text: b[j++] });
  return chunks;
}

// ── small shared helpers ───────────────────────────────────────────────────
function select(
  label: string,
  options: Array<{ value: string; label: string }>,
  value = "",
): HTMLSelectElement {
  const wrapper = el("div", "flex items-center gap-3");
  wrapper.append(el("span", "w-28 shrink-0 text-sm font-semibold text-[#25352A]", label));
  const selectEl = el(
    "select",
    "w-full max-w-xs rounded-lg border border-[#CFD8C7] bg-white px-3 py-2.5 text-base text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15",
  );
  for (const option of options) {
    const o = el("option", "", option.label);
    o.value = option.value;
    selectEl.append(o);
  }
  if (value) selectEl.value = value;
  wrapper.append(selectEl);
  return selectEl;
}

function segments(value: string): string[] {
  return value.split(/(\s+)/).filter((part) => part);
}

// ── page ───────────────────────────────────────────────────────────────────
const TEXT_AREA_CLASS =
  "w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-3 text-base leading-7 text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15";

export async function renderHumanize(root: HTMLElement): Promise<void> {
  const [meta, settings] = await Promise.all([api.meta(), api.settings()]);
  const configured = settings.providers.filter((provider) => provider.configured);

  root.replaceChildren(
    pageHead(
      "Humanizer",
      "Paste text, rewrite it, review and export. You stay in control of every step.",
    ),
  );

  if (configured.length === 0) {
    const warning = card("border-[#F0E7D4] bg-[#FDF6E7]");
    warning.append(
      el("h3", "text-base font-semibold text-[#7D5A12]", "No provider is configured yet."),
      el(
        "p",
        "mt-2 text-sm text-[#7D5A12]",
        "Add a free anonymous endpoint in Settings, or humanize against the catalog defaults.",
      ),
    );
    root.append(warning, el("div", "h-6"));
  }

  // ── controls bar ───────────────────────────────────────────────────────
  const controls = card();
  const controlRow = el("div", "flex flex-wrap items-center gap-4");
  const modeSelect = select(
    "Mode",
    meta.modes.map((m) => ({ value: m.id, label: m.label })),
    "balanced",
  );
  const intensitySelect = select(
    "Tone / intensity",
    meta.intensities.map((m) => ({ value: m.id, label: m.label })),
    "medium",
  );
  const providerSelect = select(
    "Provider",
    [
      { value: "", label: "Auto — free lanes (no key)" },
      ...configured.map((provider) => ({ value: provider.id, label: provider.name })),
    ],
    "",
  );
  controlRow.append(modeSelect, intensitySelect, providerSelect);

  const preserveWrap = el("label", "flex items-center gap-3 text-sm font-medium text-[#25352A]");
  const preserveToggle = el("input", "h-5 w-9 accent-[#1F6B4A]");
  preserveToggle.type = "checkbox";
  preserveToggle.checked = true;
  preserveWrap.append(preserveToggle, el("span", "", "Preserve formatting"));
  controlRow.append(preserveWrap);

  controls.append(el("div", "text-sm font-semibold text-[#16251C]", "Settings"), controlRow);
  root.append(controls);

  // ── two-column layout ─────────────────────────────────────────────────
  const columns = el("div", "grid gap-6 xl:grid-cols-2 xl:gap-8");
  root.append(columns);

  const leftPanel = card();
  columns.append(leftPanel);
  const leftTitle = el("div", "mb-3 flex items-center justify-between gap-4");
  leftTitle.append(el("h3", "text-lg font-semibold text-[#16251C]", "Original"));
  const wordsCounter = el("span", "text-xs text-[#5C6C62]");
  leftTitle.append(wordsCounter);
  const originalArea = el("textarea", `${TEXT_AREA_CLASS} min-h-[360px]`);
  originalArea.value = takeDraft();
  originalArea.spellcheck = true;
  leftPanel.append(leftTitle, originalArea);

  const rightPanel = card();
  columns.append(rightPanel);
  const rightTitle = el("div", "mb-3 flex flex-wrap items-center justify-between gap-4");
  rightTitle.append(el("h3", "text-lg font-semibold text-[#16251C]", "Rewritten"));
  const statusHost = el("span", "text-sm font-medium text-[#5C6C62]");
  rightTitle.append(statusHost);
  const progressTrack = el("div", "ml-auto h-1.5 w-full max-w-48 overflow-hidden rounded-full bg-[#E8EBE5] md:max-w-40");
  const progressFill = el("div", "h-full w-0 rounded-full bg-[#1F6B4A] transition-all");
  progressTrack.append(progressFill);
  rightTitle.append(progressTrack);

  const outputArea = el("textarea", `${TEXT_AREA_CLASS} min-h-[420px] bg-white text-[#3D4B41]`);
  outputArea.readOnly = true;
  outputArea.placeholder = "Your rewritten text appears here when the job finishes.";

  const errorNote = el("p", "mt-3 hidden text-sm leading-6 text-[#8B2020]");

  const copyBtn = button("Copy", "secondary", () => void copy(outputArea.value), { disabled: true });
  const useAsInputBtn = button("Use as input", "primary", () => useAsInput(), { disabled: true });
  const retryBtn = button("Retry failed chunks", "secondary", () => void retryJob(), { disabled: true, className: "hidden" });
  const cancelBtn = button("Cancel", "danger", () => void cancelJob(), { disabled: true, className: "hidden" });

  const showDiffToggle = el("label", "mt-4 flex items-center gap-3 text-sm font-medium text-[#25352A]");
  const showDiffInput = el("input", "h-5 w-9 accent-[#1F6B4A]");
  showDiffInput.type = "checkbox";
  showDiffInput.checked = false;
  showDiffToggle.append(showDiffInput, el("span", "", "Show changes"));

  const diffHost = el("div", "mt-4 hidden space-y-3 rounded-xl bg-[#F5F7F3] p-5");
  const diffOriginal = el("p", "text-sm text-[#3D4B41]");
  const diffOutput = el("p", "text-sm text-[#1B5E3B]");
  diffHost.append(diffOriginal, el("div", "h-3"), diffOutput);

  rightPanel.append(rightTitle, outputArea, errorNote,
    el("div", "mt-5 flex flex-wrap items-center gap-2", [copyBtn, useAsInputBtn, retryBtn, cancelBtn]),
    showDiffToggle,
    diffHost,
  );

  // ── behaviour ─────────────────────────────────────────────────────────
  let currentJob: JobDetail | null = null;

  const wordCountUpdater = (): void => {
    wordsCounter.textContent = `${formatNumber(wordCount(originalArea.value))} words`;
  };
  originalArea.addEventListener("input", wordCountUpdater);
  wordCountUpdater();

  function currentText(): string {
    return originalArea.value.trim();
  }

  function renderDiff(): void {
    const chunks = diffWords(segments(currentText()), segments(outputArea.value));
    diffOriginal.replaceChildren(
      ...chunks.map((chunk) => {
        if (chunk.kind === "delete") return el("del", "text-[#B31F1F] decoration-solid line-through", chunk.text);
        if (chunk.kind === "insert") return el("ins", "bg-[#E4F1E8] text-[#1B5E3B]", chunk.text);
        return el("span", "", chunk.text);
      }),
    );
    diffOutput.replaceChildren(
      ...chunks.map((chunk) => (chunk.kind === "insert" ? el("span", "font-medium text-[#1B5E3B]", chunk.text) : el("span", "", chunk.text))),
    );
  }

  showDiffInput.addEventListener("change", () => {
    diffHost.classList.toggle("hidden", !showDiffInput.checked);
    if (showDiffInput.checked) renderDiff();
  });

  function applyJob(job: JobDetail): void {
    currentJob = job;
    statusHost.replaceChildren(badge(job.status, job.status === "failed" ? "error" : "accent"));
    progressFill.style.width = `${Math.min(100, Math.max(0, job.progress_percent))}%`;
    if (job.status === "completed") {
      statusHost.textContent += ` · ${job.provider_id ?? "provider"} · chunks ${job.completed_chunks}/${job.total_chunks}`;
    }
    errorNote.classList.toggle("hidden", !job.error);
    errorNote.textContent = job.error ?? "";
    const hasOutput = Boolean(job.output_text);
    if (hasOutput && outputArea.value !== (job.output_text ?? "")) outputArea.value = job.output_text ?? "";
    if (hasOutput) diffHost.classList.remove("hidden");
    for (const control of [copyBtn, useAsInputBtn]) control.disabled = !hasOutput;
    retryBtn.classList.toggle("hidden", job.status !== "failed");
    cancelBtn.classList.toggle("hidden", ["queued", "running", "paused"].includes(job.status));
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
    const text = currentText();
    if (!text) {
      toast("There is no text to humanize.", "error");
      return;
    }
    startBtn.disabled = true;
    try {
      const created = await api.humanize({
        text,
        mode: modeSelect.value,
        intensity: intensitySelect.value,
        provider_id: providerSelect.value || undefined,
        preserve_formatting: preserveToggle.checked,
      });
      currentJob = null;
      outputArea.value = "";
      progressFill.style.width = "0%";
      statusHost.textContent = "queued";
      await poll(created.job_id);
    } catch (error) {
      toast(errorMessage(error), "error");
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = "Humanize";
    }
  }

  const startBtn = button("Humanize", "primary", () => void submitJob());

  function useAsInput(): void {
    const text = outputArea.value.trim();
    if (!text) return;
    originalArea.value = text;
    toast("Applied output as the new input.", "success");
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

  async function cancelJob(): Promise<void> {
    if (!currentJob) return;
    try {
      await api.cancelJob(currentJob.id);
      toast("Cancellation requested.", "info");
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  async function copy(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to clipboard.", "success");
    } catch {
      toast("Could not copy. Select the text and copy manually.", "error");
    }
  }

  // Buttons
  const clearBtn = button("Clear", "secondary", () => {
    originalArea.value = "";
    wordCountUpdater();
    toast("Original cleared.", "success");
  });
  const upload = button("Upload .txt / .docx", "secondary", () => undefined);
  attachFileInput(upload, ".txt,.md,.markdown,.docx", (file: File) => {
    void (async () => {
      upload.textContent = "Reading…";
      upload.disabled = true;
      try {
        const extracted = await api.extractFile(file);
        originalArea.value = extracted.text;
        wordCountUpdater();
        toast(`Loaded ${extracted.filename}.`, "success");
      } catch (error) {
        toast(errorMessage(error), "error");
      } finally {
        upload.textContent = "Upload .txt / .docx";
        upload.disabled = false;
      }
    })();
  });
  rightTitle.append(el("div", "w-full md:w-auto"), startBtn, clearBtn);

  // Also expose input-pane buttons
  leftTitle.append(upload, clearBtn);
}
