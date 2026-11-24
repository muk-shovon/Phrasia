import { api, errorMessage } from "../api";
import type { JobDetail } from "../types";
import {
  CARD,
  INPUT,
  attachFileInput,
  button,
  copyText,
  el,
  field,
  formatNumber,
  notice,
  pageHeader,
  reportError,
  setBusy,
  setDraft,
  statusBadge,
  takeDraft,
  toast,
  wordCount,
} from "../ui";

const FILE_ACCEPT = ".txt,.md,.markdown,.docx";

export async function renderHumanize(root: HTMLElement): Promise<void> {
  const [meta, settings] = await Promise.all([api.meta(), api.settings()]);
  const configured = settings.providers.filter((provider) => provider.configured);

  root.append(
    pageHeader(
      "Humanizer",
      "Rewrite text so it reads naturally, without changing facts, citations or formatting. Runs through an external model you configure yourself.",
    ),
  );

  if (configured.length === 0) {
    const warning = notice(
      "No provider is configured yet. Add a free API key in Settings before humanizing.",
      "warn",
    );
    warning.append(
      el("a", "ml-1 font-semibold underline", "Open Settings"),
    );
    const link = warning.querySelector("a");
    if (link) link.setAttribute("href", "#/settings");
    root.append(warning);
    root.append(el("div", "h-4"));
  }

  const grid = el("div", "grid items-start gap-5 xl:grid-cols-2");

  // ── input panel ───────────────────────────────────────────────────────────
  const inputCard = el("section", CARD);
  const titleInput = el("input", INPUT);
  titleInput.type = "text";
  titleInput.placeholder = "Untitled document";

  const textArea = el(
    "textarea",
    `${INPUT} min-h-[320px] resize-y font-normal leading-6`,
  );
  textArea.placeholder =
    "Paste your text here. Paragraph breaks are preserved, and nothing is uploaded to a third party except the model you choose.";
  textArea.spellcheck = true;
  textArea.value = takeDraft();

  const counter = el("span", "text-xs text-[#7A877C]", "0 words");

  const upload = button("Upload .txt / .docx", "secondary", () => undefined);
  attachFileInput(upload, FILE_ACCEPT, (file) => {
    void (async () => {
      setBusy(upload as HTMLButtonElement, true, "Reading…");
      try {
        const extracted = await api.extractFile(file);
        textArea.value = extracted.text;
        titleInput.value = titleInput.value || extracted.filename;
        updateCounter();
        toast(`Loaded ${extracted.filename}.`, "success");
      } catch (error) {
        reportError(error);
      } finally {
        setBusy(upload as HTMLButtonElement, false);
      }
    })();
  });

  const updateCounter = (): void => {
    const words = wordCount(textArea.value);
    counter.textContent = `${formatNumber(words)} word${words === 1 ? "" : "s"}`;
  };
  textArea.addEventListener("input", updateCounter);
  updateCounter();

  const metaRow = el("div", "flex flex-wrap items-center justify-between gap-2");
  metaRow.append(counter, upload);

  const modeSelect = el("select", INPUT);
  for (const mode of meta.modes) {
    const option = el("option", "", mode.label);
    option.value = mode.id;
    modeSelect.append(option);
  }
  modeSelect.value = "balanced";

  const intensitySelect = el("select", INPUT);
  for (const intensity of meta.intensities) {
    const option = el("option", "", intensity.label);
    option.value = intensity.id;
    intensitySelect.append(option);
  }
  intensitySelect.value = "medium";

  const selectRow = el("div", "grid gap-3 sm:grid-cols-2");
  selectRow.append(
    field("Mode", modeSelect),
    field("Editing strength", intensitySelect),
  );

  const check = (label: string, checked: boolean): { wrap: HTMLElement; input: HTMLInputElement } => {
    const wrap = el("label", "flex cursor-pointer items-start gap-2.5 text-sm text-[#25352A]");
    const input = el("input", "mt-0.5 h-4 w-4 accent-[#1C6B4A]");
    input.type = "checkbox";
    input.checked = checked;
    const text = el("span", "leading-5", label);
    wrap.append(input, text);
    return { wrap, input };
  };

  const preserve = check("Preserve paragraph and line structure", true);
  const quotes = check("Leave quotes, URLs, code and citations untouched", true);

  const providerSelect = el("select", INPUT);
  const autoOption = el("option", "", "Auto — use the preferred configured provider");
  autoOption.value = "";
  providerSelect.append(autoOption);
  for (const provider of configured) {
    const option = el("option", "", `${provider.name} · ${provider.model}`);
    option.value = provider.id;
    providerSelect.append(option);
  }
  if (settings.preferred_provider) {
    const preferred = configured.find((item) => item.id === settings.preferred_provider);
    if (preferred) {
      autoOption.textContent = `Auto — ${preferred.name} first`;
      providerSelect.value = "";
    }
  }

  const submit = button("Humanize text", "primary", () => void submitJob());
  const cancel = button("Cancel job", "danger", () => void cancelJob());
  cancel.disabled = true;

  const actions = el("div", "flex flex-wrap items-center gap-2 pt-1");
  actions.append(submit, cancel);

  inputCard.append(
    field("Document title", titleInput, "Optional. Used for History and file names."),
    el("div", "h-3"),
    field("Text to rewrite", textArea),
    el("div", "mt-2"),
    metaRow,
    el("div", "h-4"),
    selectRow,
    el("div", "mt-4 space-y-2"),
    preserve.wrap,
    quotes.wrap,
    el("div", "mt-4"),
    field("Provider", providerSelect),
    el("div", "mt-4"),
    actions,
    el(
      "p",
      "mt-3 text-xs leading-5 text-[#7A877C]",
      `Up to ${formatNumber(meta.limits.max_input_chars)} characters per document. Long text is split into chunks and saved as it goes.`,
    ),
  );

  // ── output panel ──────────────────────────────────────────────────────────
  const outputCard = el("section", `${CARD} xl:sticky xl:top-6`);
  const statusRow = el("div", "flex flex-wrap items-center gap-2");
  const statusHost = el("div", "flex flex-wrap items-center gap-2");
  statusRow.append(statusHost);

  const progressTrack = el("div", "mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#EDF0E8]");
  const progressBar = el("div", "h-full w-0 rounded-full bg-[#1C6B4A] transition-all");
  progressTrack.append(progressBar);

  const progressLabel = el("p", "mt-1.5 text-xs text-[#7A877C]", "Ready when you are.");

  const outputArea = el(
    "textarea",
    `${INPUT} mt-4 min-h-[360px] resize-y bg-[#FAFBF7] leading-6`,
  );
  outputArea.readOnly = true;
  outputArea.placeholder =
    "Your rewritten text appears here when the job finishes. Nothing is saved until you start a job.";

  const errorNote = el("p", "mt-3 hidden text-sm leading-6 text-[#8B2020]");

  const copy = button("Copy", "secondary", () => void copyText(outputArea.value));
  const txt = button("Download .txt", "secondary", () => void download("txt"));
  const docx = button("Download .docx", "secondary", () => void download("docx"));
  const retry = button("Retry", "secondary", () => void retryJob());
  const toDetector = button("Open in style signal", "ghost", () => {
    setDraft(outputArea.value);
    window.location.hash = "#/detector";
  });
  const toSimilarity = button("Check similarity", "ghost", () => {
    setDraft(outputArea.value);
    window.location.hash = "#/plagiarism";
  });

  for (const control of [copy, txt, docx, retry]) control.disabled = true;
  toDetector.disabled = true;
  toSimilarity.disabled = true;

  const toolbar = el("div", "mt-3 flex flex-wrap gap-2");
  toolbar.append(copy, txt, docx, retry);
  const jumpRow = el("div", "mt-2 flex flex-wrap items-center gap-4");
  jumpRow.append(toDetector, toSimilarity);

  outputCard.append(
    statusRow,
    progressTrack,
    progressLabel,
    outputArea,
    errorNote,
    toolbar,
    jumpRow,
  );

  grid.append(inputCard, outputCard);
  root.append(grid);

  // ── behaviour ─────────────────────────────────────────────────────────────
  let currentJob: JobDetail | null = null;
  let timer: number | undefined;
  let submitting = false;

  function applyJob(job: JobDetail): void {
    currentJob = job;
    statusHost.replaceChildren(statusBadge(job.status));
    if (job.status === "completed") {
      statusHost.append(
        el(
          "span",
          "text-xs text-[#5C6B60]",
          `${job.provider_id ?? "provider"} · ${job.model_id ?? "model"}`,
        ),
      );
    }

    progressBar.style.width = `${job.progress_percent}%`;
    const chunkLine =
      job.total_chunks > 1 ? ` · ${job.completed_chunks}/${job.total_chunks} chunks` : "";
    progressLabel.textContent =
      job.status === "completed"
        ? `Finished${chunkLine}. Saved to History.`
        : job.status === "failed"
          ? `Stopped${chunkLine}. Retry to continue from here.`
          : job.status === "cancelled"
            ? `Cancelled${chunkLine}. Retry when you are ready.`
            : `Working… ${job.progress_percent}%${chunkLine}`;

    if (job.output_text) outputArea.value = job.output_text;
    const failed = job.status === "failed" || job.status === "cancelled";
    errorNote.classList.toggle("hidden", !job.error);
    errorNote.textContent = job.error ?? "";

    const finished = job.status === "completed";
    submit.disabled = submitting || ["queued", "running"].includes(job.status);
    cancel.disabled = !["queued", "running", "paused"].includes(job.status);
    retry.disabled = !failed;
    for (const control of [copy, txt, docx]) control.disabled = !finished || !job.output_text;
    toDetector.disabled = !job.output_text;
    toSimilarity.disabled = !job.output_text;
    if (outputArea.value) copy.dataset.hasText = "true";
  }

  async function poll(jobId: number): Promise<void> {
    if (!root.isConnected) return;
    try {
      const job = await api.job(jobId);
      if (!root.isConnected) return;
      applyJob(job);
      if (["queued", "running"].includes(job.status)) {
        timer = window.setTimeout(() => void poll(jobId), 1200);
      } else {
        submitting = false;
        submit.disabled = false;
        if (job.status === "completed") toast("Humanization complete.", "success");
        if (job.status === "failed") toast(job.error ?? "The job failed.", "error");
      }
    } catch (error) {
      submitting = false;
      submit.disabled = false;
      reportError(error);
    }
  }

  async function submitJob(): Promise<void> {
    const text = textArea.value.trim();
    if (!text) {
      toast("Paste some text first.", "error");
      return;
    }
    submitting = true;
    window.clearTimeout(timer);
    setBusy(submit, true, "Starting…");
    try {
      const created = await api.humanize({
        text,
        title: titleInput.value.trim() || null,
        mode: modeSelect.value,
        intensity: intensitySelect.value,
        preserve_formatting: preserve.input.checked,
        keep_quotes: quotes.input.checked,
        provider_id: providerSelect.value || null,
      });
      setBusy(submit, false);
      currentJob = null;
      outputArea.value = "";
      errorNote.classList.add("hidden");
      progressBar.style.width = "0%";
      progressLabel.textContent = "Queued…";
      statusHost.replaceChildren(statusBadge("queued"));
      cancel.disabled = false;
      await poll(created.job_id);
    } catch (error) {
      submitting = false;
      reportError(error);
    } finally {
      setBusy(submit, false);
      submit.disabled = ["queued", "running"].includes(currentJob?.status ?? "");
    }
  }

  async function cancelJob(): Promise<void> {
    if (!currentJob) return;
    try {
      await api.cancelJob(currentJob.id);
      toast("Cancellation requested.", "info");
    } catch (error) {
      reportError(error);
    }
  }

  async function retryJob(): Promise<void> {
    if (!currentJob) return;
    submitting = true;
    try {
      await api.retryJob(currentJob.id);
      await poll(currentJob.id);
    } catch (error) {
      submitting = false;
      reportError(error);
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

  // Keep the latest job visible if the user reloads and a job is running.
  try {
    const recent = await api.jobs(1);
    const job = recent.jobs[0];
    if (job && ["queued", "running", "paused"].includes(job.status)) {
      await poll(job.id);
    }
  } catch {
    /* history is optional on this page */
  }
}
