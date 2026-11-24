import { api, errorMessage } from "../api";
import type { JobDetail } from "../types";
import {
  button,
  card,
  clear,
  el,
  fieldWrap,
  getToggle,
  ICONS,
  pageHead,
  select,
  setButtonLoading,
  setDraft,
  statusBadge,
  takeDraft,
  textarea,
  toast,
  toggle,
  wordCount,
} from "../ui";

const POLL_MS = 1200;

interface DiffChunk { kind: "context" | "delete" | "insert"; text: string; }
function diffWords(a: string[], b: string[]): DiffChunk[] {
  const n = a.length, m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: DiffChunk[] = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { out.push({ kind: "context", text: a[i++] }); j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ kind: "delete", text: a[i++] });
    else out.push({ kind: "insert", text: b[j++] });
  }
  while (i < n) out.push({ kind: "delete", text: a[i++] });
  while (j < m) out.push({ kind: "insert", text: b[j++] });
  return out;
}
const segments = (v: string): string[] => v.split(/(\s+)/).filter(Boolean);

export async function renderHumanize(root: HTMLElement): Promise<void> {
  const [meta, settings] = await Promise.all([api.meta(), api.settings()]);
  const configured = settings.providers.filter((p) => p.configured);

  root.replaceChildren(
    pageHead("Humanizer", "Paste your text, refine the writing, review changes, and export the result."),
  );

  // ---- Settings panel ----
  const settingsCard = card("mb-6");
  settingsCard.append(el("h2", "text-base font-semibold text-[var(--color-text)] mb-4", "Rewrite settings"));
  const settingsGrid = el("div", "grid gap-4 sm:grid-cols-2 xl:grid-cols-4");

  const modeSel = select(meta.modes.map((m) => ({ value: m.id, label: m.label })));
  modeSel.value = "balanced";
  settingsGrid.append(fieldWrap("Writing style", modeSel));

  const intensitySel = select(meta.intensities.map((m) => ({ value: m.id, label: m.label })));
  intensitySel.value = "medium";
  settingsGrid.append(fieldWrap("Rewrite intensity", intensitySel));

  const providerOpts = [{ value: "", label: "Auto (free catalog)" }, ...configured.map((p) => ({ value: p.id, label: p.name }))];
  const providerSel = select(providerOpts);
  settingsGrid.append(fieldWrap("Provider", providerSel));

  const preserveWrap = el("div", "flex flex-col justify-end");
  const preserveRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const preserveToggle = toggle(true, "Preserve formatting");
  preserveRow.append(preserveToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Preserve formatting"));
  preserveWrap.append(el("span", "field-label", "Formatting"), preserveRow);
  settingsGrid.append(preserveWrap);

  settingsCard.append(settingsGrid);
  if (configured.length === 0) {
    const note = el("div", "mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] px-4 py-3 text-sm text-[var(--color-text-muted)]");
    note.innerHTML = `No provider key saved. Anonymous free endpoints from the catalog are used by default. You can configure providers in <a href="#/settings" class="font-semibold text-[var(--color-primary)] underline underline-offset-2">Settings</a>.`;
    settingsCard.append(note);
  }
  root.append(settingsCard);

  // ---- Workspace ----
  const workspace = el("div", "workspace-grid");

  // Left panel
  const left = card("flex flex-col min-w-0");
  const leftHead = el("div", "flex flex-wrap items-center justify-between gap-3 mb-4");
  leftHead.append(el("h2", "text-lg font-semibold text-[var(--color-text)]", "Original text"));
  const leftMeta = el("div", "flex items-center gap-3");
  const leftCount = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  const clearBtn = button("Clear", "ghost", () => { original.value = ""; syncLeft(); }, { size: "sm" });
  leftMeta.append(leftCount, clearBtn);
  leftHead.append(leftMeta);
  const original = textarea("Paste or type the text you want to refine...", 18);
  original.classList.add("min-h-[320px]", "md:min-h-[420px]", "flex-1");
  original.spellcheck = true;
  left.append(leftHead, original);
  workspace.append(left);

  // Right panel
  const right = card("flex flex-col min-w-0");
  const rightHead = el("div", "flex flex-wrap items-center justify-between gap-3 mb-4");
  rightHead.append(el("h2", "text-lg font-semibold text-[var(--color-text)]", "Rewritten text"));
  const rightMeta = el("div", "flex items-center gap-2");
  const statusHost = el("div", "text-sm text-[var(--color-text-muted)]");
  statusHost.setAttribute("aria-live", "polite");
  const rightCount = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  rightMeta.append(statusHost, rightCount);
  rightHead.append(rightMeta);
  const output = textarea("Your rewritten text will appear here after processing.", 18);
  output.classList.add("min-h-[320px]", "md:min-h-[420px]", "flex-1", "bg-[var(--color-cornsilk-600)]");
  output.readOnly = true;
  right.append(rightHead, output);

  const progressWrap = el("div", "mt-4 hidden");
  const progressLabel = el("div", "flex justify-between text-xs text-[var(--color-text-muted)] mb-1.5");
  const progressText = el("span", "", "Processing...");
  const progressPct = el("span", "", "0%");
  progressLabel.append(progressText, progressPct);
  const progressTrack = el("div", "progress-track");
  const progressFill = el("div", "progress-fill");
  progressFill.style.width = "0%";
  progressTrack.append(progressFill);
  progressWrap.append(progressLabel, progressTrack);
  right.append(progressWrap);

  const errorNote = el("div", "mt-4 hidden rounded-lg border border-[rgba(122,59,46,0.2)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger)]");
  right.append(errorNote);

  // Actions
  const actions = el("div", "mt-5 flex flex-wrap gap-2");
  const startBtn = button("Humanize", "primary", () => void submitJob());
  const copyBtn = button("Copy", "secondary", () => void copyOutput(), { icon: ICONS.copy });
  const useBtn = button("Use as input", "secondary", () => useAsInput());
  const txtBtn = button("Download .txt", "secondary", () => void download("txt"), { icon: ICONS.download });
  const docxBtn = button("Download .docx", "secondary", () => void download("docx"), { icon: ICONS.download });
  const retryBtn = button("Retry failed chunks", "secondary", () => void retryJob());
  const cancelBtn = button("Cancel job", "danger", () => void cancelJob());
  retryBtn.classList.add("hidden");
  cancelBtn.classList.add("hidden");
  copyBtn.disabled = true; useBtn.disabled = true; txtBtn.disabled = true; docxBtn.disabled = true;
  actions.append(startBtn, copyBtn, useBtn, txtBtn, docxBtn, retryBtn, cancelBtn);
  right.append(actions);

  // Show changes
  const diffRow = el("div", "mt-5 flex items-center gap-3 w-fit");
  const diffToggle = toggle(false, "Show changes");
  const diffLabel = el("span", "text-sm font-medium text-[var(--color-text)] cursor-pointer", "Show changes");
  diffLabel.addEventListener("click", () => { diffToggle.click(); });
  diffRow.append(diffToggle, diffLabel);
  right.append(diffRow);

  const diffHost = el("div", "mt-4 hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] p-4");
  const diffHeading = el("p", "text-xs font-semibold uppercase tracking-wider text-[var(--color-text-subtle)] mb-3", "Changes");
  const diffContent = el("div", "text-sm leading-7 text-[var(--color-text)] whitespace-pre-wrap break-words");
  diffHost.append(diffHeading, diffContent);
  right.append(diffHost);

  workspace.append(right);
  root.append(workspace);

  // ---- State ----
  let currentJob: JobDetail | null = null;

  const syncLeft = (): void => { leftCount.textContent = `${wordCount(original.value).toLocaleString()} words`; };
  const syncRight = (): void => { rightCount.textContent = `${wordCount(output.value).toLocaleString()} words`; };
  original.addEventListener("input", syncLeft);
  original.value = takeDraft();
  syncLeft(); syncRight();

  original.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); void submitJob(); }
  });

  function setOutputControls(hasOutput: boolean): void {
    copyBtn.disabled = !hasOutput; useBtn.disabled = !hasOutput; txtBtn.disabled = !hasOutput; docxBtn.disabled = !hasOutput;
  }

  function renderDiff(): void {
    const chunks = diffWords(segments(original.value), segments(output.value));
    clear(diffContent);
    for (const c of chunks) {
      if (c.kind === "delete") diffContent.append(el("del", "diff-del", c.text));
      else if (c.kind === "insert") diffContent.append(el("ins", "diff-ins no-underline", c.text));
      else diffContent.append(document.createTextNode(c.text));
    }
  }

  diffToggle.addEventListener("click", () => {
    const on = getToggle(diffToggle);
    diffHost.classList.toggle("hidden", !on);
    if (on) renderDiff();
  });

  function applyJob(job: JobDetail): void {
    currentJob = job;
    clear(statusHost);
    statusHost.append(statusBadge(job.status));
    const pct = Math.min(100, Math.max(0, job.progress_percent));
    progressFill.style.width = `${pct}%`;
    progressPct.textContent = `${pct}%`;
    progressText.textContent = job.status === "completed"
      ? `Completed · ${job.completed_chunks}/${job.total_chunks} chunks`
      : `${job.status.charAt(0).toUpperCase() + job.status.slice(1)} · ${job.completed_chunks}/${job.total_chunks} chunks`;
    progressWrap.classList.toggle("hidden", !["queued", "running", "paused", "completed", "failed", "cancelled"].includes(job.status));

    errorNote.classList.toggle("hidden", !job.error);
    errorNote.textContent = job.error ?? "";

    const hasOutput = Boolean(job.output_text && job.output_text.length > 0);
    if (hasOutput && output.value !== (job.output_text ?? "")) {
      output.value = job.output_text ?? "";
      syncRight();
      if (getToggle(diffToggle)) renderDiff();
    }
    setOutputControls(hasOutput);
    retryBtn.classList.toggle("hidden", job.status !== "failed");
    cancelBtn.classList.toggle("hidden", !["queued", "running", "paused"].includes(job.status));
  }

  async function poll(jobId: number): Promise<void> {
    if (!root.isConnected) return;
    try {
      const job = await api.job(jobId);
      if (!root.isConnected) return;
      applyJob(job);
      if (["queued", "running", "paused"].includes(job.status)) window.setTimeout(() => void poll(jobId), POLL_MS);
      else if (job.status === "completed") toast("Rewrite complete.", "success");
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  async function submitJob(): Promise<void> {
    const text = original.value.trim();
    if (!text) { toast("Paste some text to humanize first.", "error"); original.focus(); return; }
    setButtonLoading(startBtn, true, "Humanizing...");
    progressWrap.classList.remove("hidden");
    progressFill.style.width = "0%"; progressPct.textContent = "0%"; progressText.textContent = "Starting...";
    clear(statusHost); errorNote.classList.add("hidden");
    try {
      const created = await api.humanize({
        text,
        mode: modeSel.value,
        intensity: intensitySel.value,
        provider_id: providerSel.value || undefined,
        preserve_formatting: getToggle(preserveToggle),
        keep_quotes: getToggle(preserveToggle),
      });
      currentJob = null; output.value = ""; syncRight(); setOutputControls(false);
      await poll(created.job_id);
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(startBtn, false); startBtn.textContent = "Humanize"; }
  }

  async function retryJob(): Promise<void> {
    if (!currentJob) return;
    try { await api.retryJob(currentJob.id); toast("Retrying failed chunks.", "info"); void poll(currentJob.id); }
    catch (err) { toast(errorMessage(err), "error"); }
  }
  async function cancelJob(): Promise<void> {
    if (!currentJob) return;
    try { await api.cancelJob(currentJob.id); toast("Cancellation requested.", "info"); }
    catch (err) { toast(errorMessage(err), "error"); }
  }
  async function download(fmt: "txt" | "docx"): Promise<void> {
    if (!currentJob) return;
    try { await api.downloadJob(currentJob.id, fmt, currentJob.title || "phrasia"); toast(`Downloaded .${fmt} file.`, "success"); }
    catch (err) { toast(errorMessage(err), "error"); }
  }
  async function copyOutput(): Promise<void> {
    const t = output.value;
    if (!t) return;
    try { await navigator.clipboard.writeText(t); toast("Copied to clipboard.", "success"); }
    catch { toast("Could not copy automatically. Select and copy manually.", "error"); }
  }
  function useAsInput(): void {
    const t = output.value.trim();
    if (!t) return;
    original.value = t; setDraft(t); syncLeft();
    toast("Rewritten text moved to input.", "success");
    original.focus();
  }
}
