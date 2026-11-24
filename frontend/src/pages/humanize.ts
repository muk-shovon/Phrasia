import { api, errorMessage } from "../api";
import type { DiffReport, DiffSegment, JobDetail } from "../types";
import {
  button, card, clear, el, fieldWrap, getToggle, pageHead, select, setButtonLoading, setDraft,
  statusBadge, takeDraft, textarea, toast, toggle, wordCount,
} from "../ui";

const POLL_MS = 1200;

function mergeAdjacentChanged(segments: DiffSegment[]): DiffSegment[] {
  const out: DiffSegment[] = [];
  for (const s of segments) {
    const prev = out[out.length - 1];
    if (s.type === "changed" && prev && prev.type === "changed") {
      prev.original = `${prev.original} ${s.original}`.trim();
      prev.rewritten = `${prev.rewritten} ${s.rewritten}`.trim();
      prev.risk = prev.risk === "number" || s.risk === "number" ? "number" : prev.risk === "meaning" || s.risk === "meaning" ? "meaning" : "none";
    } else out.push({ ...s });
  }
  return out;
}

function appendText(parent: HTMLElement, text: string): void {
  parent.append(document.createTextNode(text));
}

function renderSegmentInline(parent: HTMLElement, seg: DiffSegment, showOriginal: boolean): void {
  if (seg.type === "equal") { appendText(parent, (seg.text ?? seg.rewritten ?? "")); return; }
  const changed = el("span", "text-indigo-600 font-medium");
  if (seg.risk === "meaning") changed.classList.add("underline", "decoration-amber-500", "decoration-solid", "underline-offset-2");
  if (seg.risk === "number") changed.classList.add("underline", "decoration-red-500", "decoration-solid", "underline-offset-2");
  if (showOriginal && seg.original) {
    const old = el("span", "text-[var(--color-text-subtle)] line-through mr-1 text-[0.85em]");
    old.textContent = seg.original;
    changed.append(old);
  }
  const neu = document.createElement("span");
  neu.textContent = seg.rewritten || "";
  changed.append(neu);
  if (seg.risk === "meaning" || seg.risk === "number") {
    const mark = el("span", seg.risk === "number" ? "text-red-600 ml-0.5" : "text-amber-600 ml-0.5", "!");
    changed.append(mark);
  }
  parent.append(changed);
}

function renderHighlighted(out: HTMLElement, segments: DiffSegment[], showOriginal: boolean): void {
  clear(out);
  const hasSentenceMarks = segments.some((s) => s.sentence_start || s.sentence_end || s.low_change !== undefined);
  const merged = mergeAdjacentChanged(segments);
  if (!hasSentenceMarks) {
    merged.forEach((seg, idx) => {
      renderSegmentInline(out, seg, showOriginal);
      if (idx < merged.length - 1) appendText(out, " ");
    });
    return;
  }
  // group into sentences
  let current: DiffSegment[] = [];
  const sentences: DiffSegment[][] = [];
  for (const seg of merged) {
    if ((seg as any).sentence_space) { if (current.length) { sentences.push(current); current = []; } continue; }
    current.push(seg);
    if (seg.sentence_end) { sentences.push(current); current = []; }
  }
  if (current.length) sentences.push(current);
  sentences.forEach((group, gi) => {
    const low = group.some((g) => g.low_change);
    const restructured = !low && group.some((g) => g.type === "changed" || !g.low_change);
    const wrap = el("span", restructured ? "inline border-l-2 border-[var(--color-olive-400)] bg-[rgba(96,108,56,0.04)] pl-1.5 pr-0.5 rounded-sm" : "inline");
    group.forEach((seg, idx) => { renderSegmentInline(wrap, seg, showOriginal); if (idx < group.length - 1) appendText(wrap, " "); });
    if (low) {
      const marker = el("span", "ml-1 text-[10px] text-[var(--color-text-subtle)] align-middle", "unchanged structure");
      wrap.append(marker);
    }
    if (group.some((g) => g.flat_rhythm)) {
      const marker = el("span", "ml-1 text-[10px] text-[var(--color-text-subtle)] align-middle", "flat rhythm");
      wrap.append(marker);
    }
    out.append(wrap);
    if (gi < sentences.length - 1) appendText(out, " ");
  });
}

export async function renderHumanize(root: HTMLElement): Promise<void> {
  const [meta, settings] = await Promise.all([api.meta(), api.settings()]);
  const configured = settings.providers.filter((p) => p.configured);
  const maxWords = meta.limits.max_words_per_request ?? 1500;

  root.replaceChildren(pageHead("Humanizer", "Paste your text, refine it, and review the result."));

  const settingsCard = card("mb-4 p-4 md:p-5");
  settingsCard.append(el("h2", "text-sm font-semibold text-[var(--color-text)] mb-3", "Rewrite settings"));
  const settingsGrid = el("div", "grid gap-3 sm:grid-cols-2 xl:grid-cols-4");
  const modeSel = select(meta.modes.map((m) => ({ value: m.id, label: m.label }))); modeSel.value = "balanced";
  settingsGrid.append(fieldWrap("Writing style", modeSel));
  const intensitySel = select(meta.intensities.map((m) => ({ value: m.id, label: m.label }))); intensitySel.value = "medium";
  settingsGrid.append(fieldWrap("Rewrite intensity", intensitySel));
  const providerSel = select([{ value: "", label: "Auto (free catalog)" }, ...configured.map((p) => ({ value: p.id, label: p.name }))]);
  settingsGrid.append(fieldWrap("Provider", providerSel));
  const preserveWrap = el("div", "flex flex-col justify-end");
  const preserveRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const preserveToggle = toggle(true, "Preserve formatting");
  preserveRow.append(preserveToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Preserve formatting"));
  preserveWrap.append(el("span", "field-label", "Formatting"), preserveRow);
  settingsGrid.append(preserveWrap);
  settingsCard.append(settingsGrid);

  const more = el("details", "mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)]");
  const moreSummary = el("summary", "cursor-pointer px-3 py-2 text-sm font-semibold text-[var(--color-text)] select-none", "More options");
  more.append(moreSummary);
  const moreBody = el("div", "px-3 pb-3 pt-1 space-y-2");
  const cleanRow = el("label", "flex items-center gap-3 cursor-pointer w-fit");
  const cleanToggle = toggle(true, "Clean invisible characters");
  const cleanLabel = el("span", "text-sm font-medium text-[var(--color-text)]", "Clean invisible characters");
  cleanLabel.addEventListener("click", () => cleanToggle.click());
  cleanRow.append(cleanToggle, cleanLabel);
  moreBody.append(cleanRow, el("p", "text-xs text-[var(--color-text-subtle)] ml-14", "Removes zero-width characters and normalizes odd spaces before processing."));
  more.append(moreBody);
  settingsCard.append(more);
  root.append(settingsCard);

  const workspace = el("div", "grid gap-4 xl:grid-cols-2");
  const left = card("flex flex-col min-w-0 p-4");
  const leftHead = el("div", "flex items-center justify-between gap-3 mb-3");
  leftHead.append(el("h2", "text-base font-semibold text-[var(--color-text)]", "Original text"));
  const leftMeta = el("div", "flex items-center gap-3");
  const leftCount = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", `0 / ${maxWords.toLocaleString()} words`);
  const clearBtn = button("Clear", "ghost", () => { original.value = ""; syncLeft(); }, { size: "sm" });
  leftMeta.append(leftCount, clearBtn); leftHead.append(leftMeta);
  const original = textarea("Paste or type the text you want to refine...", 10);
  original.className = "field-textarea h-56 md:h-64 min-h-[14rem] md:min-h-[16rem] max-h-[24rem] resize-y overflow-auto p-4 text-base leading-relaxed";
  original.spellcheck = true;
  left.append(leftHead, original);
  workspace.append(left);

  const right = card("flex flex-col min-w-0 p-4");
  const rightHead = el("div", "flex items-center justify-between gap-3 mb-3");
  rightHead.append(el("h2", "text-base font-semibold text-[var(--color-text)]", "Rewritten text"));
  const rightMeta = el("div", "flex items-center gap-2");
  const statusHost = el("div", "text-sm text-[var(--color-text-muted)]"); statusHost.setAttribute("aria-live", "polite");
  const rightCount = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  rightMeta.append(statusHost, rightCount); rightHead.append(rightMeta);
  const outputWrap = el("div", "relative");
  const output = textarea("Your rewritten text will appear here after processing.", 10);
  output.className = "field-textarea h-56 md:h-64 min-h-[14rem] md:min-h-[16rem] max-h-[24rem] resize-y overflow-auto p-4 text-base leading-relaxed bg-[var(--color-cornsilk-600)]";
  output.readOnly = true;
  const highlightBox = el("div", "hidden h-56 md:h-64 min-h-[14rem] md:min-h-[16rem] max-h-[24rem] overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border-strong)] bg-[var(--color-cornsilk-600)] p-4 text-base leading-relaxed text-[var(--color-text)] whitespace-pre-wrap break-words");
  outputWrap.append(output, highlightBox);
  right.append(rightHead, outputWrap);

  const progressWrap = el("div", "mt-3 hidden");
  const progressLabel = el("div", "flex justify-between text-xs text-[var(--color-text-muted)] mb-1");
  const progressText = el("span", "", "Processing..."); const progressPct = el("span", "", "0%");
  progressLabel.append(progressText, progressPct);
  const progressTrack = el("div", "progress-track"); const progressFill = el("div", "progress-fill"); progressFill.style.width = "0%";
  progressTrack.append(progressFill); progressWrap.append(progressLabel, progressTrack);
  right.append(progressWrap);

  const errorNote = el("div", "mt-3 hidden rounded-lg border border-[rgba(122,59,46,0.2)] bg-[var(--color-danger-bg)] px-3 py-2 text-sm text-[var(--color-danger)]");
  right.append(errorNote);

  const actions = el("div", "mt-4 flex flex-wrap gap-2");
  const startBtn = button("Humanize", "primary", () => void submitJob());
  const copyBtn = button("Copy", "secondary", () => void copyOutput());
  const useBtn = button("Use as input", "secondary", () => useAsInput());
  const txtBtn = button("Download .txt", "secondary", () => void download("txt"));
  const docxBtn = button("Download .docx", "secondary", () => void download("docx"));
  const retryBtn = button("Retry failed chunks", "secondary", () => void retryJob());
  const cancelBtn = button("Cancel job", "danger", () => void cancelJob());
  retryBtn.classList.add("hidden"); cancelBtn.classList.add("hidden");
  for (const b of [copyBtn, useBtn, txtBtn, docxBtn]) b.disabled = true;
  actions.append(startBtn, copyBtn, useBtn, txtBtn, docxBtn, retryBtn, cancelBtn);
  const modelInfo = el("p", "mt-2 text-xs text-[var(--color-text-subtle)] hidden");
  right.append(actions, modelInfo);

  const togglesRow = el("div", "mt-3 flex flex-wrap gap-x-5 gap-y-2");
  const hlRow = el("div", "flex items-center gap-2"); const hlToggle = toggle(true, "Highlight changes");
  const hlLabel = el("span", "text-sm font-medium text-[var(--color-text)] cursor-pointer", "Highlight changes");
  hlLabel.addEventListener("click", () => hlToggle.click()); hlRow.append(hlToggle, hlLabel);
  const origRow = el("div", "flex items-center gap-2"); const origToggle = toggle(false, "Show original wording");
  const origLabel = el("span", "text-sm font-medium text-[var(--color-text)] cursor-pointer", "Show original wording");
  origLabel.addEventListener("click", () => origToggle.click()); origRow.append(origToggle, origLabel);
  togglesRow.append(hlRow, origRow);
  right.append(togglesRow);
  workspace.append(right);
  root.append(workspace);

  // Style check
  const styleCard = card("mt-4 p-4 md:p-5");
  styleCard.append(el("h2", "text-base font-semibold text-[var(--color-text)] mb-3", "Style check"));
  const styleHost = el("div");
  styleCard.append(styleHost);
  root.append(styleCard);

  let currentJob: JobDetail | null = null;
  let currentDiff: DiffReport | null = null;
  let plainOutput = "";

  const syncLeft = (): void => {
    const n = wordCount(original.value);
    leftCount.textContent = `${n.toLocaleString()} / ${maxWords.toLocaleString()} words`;
    leftCount.className = "text-xs font-medium " + (n > maxWords ? "text-[var(--color-danger)]" : n >= Math.floor(maxWords * 0.9) ? "text-[#8a6a12]" : "text-[var(--color-text-subtle)]");
  };
  const syncRight = (): void => { rightCount.textContent = `${wordCount(plainOutput).toLocaleString()} words`; };
  original.addEventListener("input", syncLeft);
  original.value = takeDraft(); syncLeft(); syncRight();
  original.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); void submitJob(); } });

  function setOutputControls(has: boolean): void { for (const b of [copyBtn, useBtn, txtBtn, docxBtn]) b.disabled = !has; }

  function renderStyle(report: DiffReport | null): void {
    clear(styleHost);
    if (!report) { styleHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "Run Humanize to see style pattern changes.")); return; }
    const s = report.style;
    const top = el("div", "flex flex-wrap items-center gap-3 mb-3");
    top.append(el("p", "text-sm font-semibold text-[var(--color-text)]", `AI-writing tells: ${s.before.total} - ${s.after.total}`));
    const bar = el("div", "flex h-2 w-40 overflow-hidden rounded-full bg-[var(--color-border)]");
    const b1 = el("div", "h-full bg-[#8a6a12]"); b1.style.width = `${Math.min(100, s.before.total * 10)}%`;
    const b2 = el("div", "h-full bg-[var(--color-forest-600)] -ml-px"); b2.style.width = `${Math.min(100, s.after.total * 10)}%`;
    bar.append(b1, b2); top.append(bar);
    styleHost.append(top);
    const still = s.remaining.length ? s.remaining.map((p) => p.name).join(", ") : "None";
    styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-1", `Still present: ${still}`));
    styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-1", `${report.changed} changes, ${report.review} to review (!)`));
    styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-1", `Words changed: ${s.changed_words_pct}%`));
    if (s.structure && s.structure.sentences_total > 0) {
      styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-1", `Sentences restructured: ${s.structure.sentences_restructured} of ${s.structure.sentences_total}`));
      styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-1", `Average change per sentence: ${s.structure.average_change_pct}%`));
    }
    styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-1", `Banned words removed: ${s.banned_words_removed ?? 0}`));
    styleHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-3", `Rhythm varied: ${s.rhythm_varied ?? 0} of ${s.paragraphs_total ?? 0} paragraphs`));
    styleHost.append(el("p", "text-xs text-[var(--color-text-subtle)] border-t border-[var(--color-border)] pt-3", "Style check on our own pattern list. Not an AI-detector result and not proof of authorship."));
  }

  function renderOutput(): void {
    const on = getToggle(hlToggle) && !!currentDiff && plainOutput.length > 0;
    output.classList.toggle("hidden", on);
    highlightBox.classList.toggle("hidden", !on);
    if (on && currentDiff) renderHighlighted(highlightBox, currentDiff.segments, getToggle(origToggle));
  }

  hlToggle.addEventListener("click", () => { setTimeout(renderOutput, 0); });
  origToggle.addEventListener("click", () => { setTimeout(renderOutput, 0); });

  function jobAlignment(): unknown[] | undefined {
    if (!currentJob) return undefined;
    const pairs: unknown[] = [];
    for (const ch of currentJob.chunks || []) {
      const mj = (ch as any).mapping_json;
      if (!mj) continue;
      try { const arr = JSON.parse(mj); if (Array.isArray(arr)) pairs.push(...arr); } catch {}
    }
    return pairs.length ? pairs : undefined;
  }

  async function refreshDiff(): Promise<void> {
    const src = original.value.trim();
    if (!src || !plainOutput.trim()) { currentDiff = null; renderStyle(null); renderOutput(); return; }
    try {
      currentDiff = await api.diff(src, plainOutput, jobAlignment());
      renderStyle(currentDiff);
      renderOutput();
    } catch { /* diff is optional UI; keep plain output */ }
  }

  function applyJob(job: JobDetail): void {
    currentJob = job;
    clear(statusHost); statusHost.append(statusBadge(job.status));
    const pct = Math.min(100, Math.max(0, job.progress_percent));
    progressFill.style.width = `${pct}%`; progressPct.textContent = `${pct}%`;
    progressText.textContent = `${job.status.charAt(0).toUpperCase() + job.status.slice(1)} - ${job.completed_chunks}/${job.total_chunks} chunks`;
    progressWrap.classList.remove("hidden");
    errorNote.classList.toggle("hidden", !job.error); errorNote.textContent = job.error ?? "";
    const has = Boolean(job.output_text && job.output_text.length > 0);
    if (has && plainOutput !== (job.output_text ?? "")) { plainOutput = job.output_text ?? ""; output.value = plainOutput; syncRight(); void refreshDiff(); }
    setOutputControls(has);
    retryBtn.classList.toggle("hidden", job.status !== "failed");
    cancelBtn.classList.toggle("hidden", !["queued", "running", "paused"].includes(job.status));
    const attempts = (job.chunks || []).reduce((a, c) => a + (c.attempt_count || 0), 0);
    let low = 0;
    for (const ch of job.chunks || []) {
      const mj = (ch as any).mapping_json;
      if (!mj) continue;
      try { const arr = JSON.parse(mj); for (const m of arr) if (m.low_change) low += Math.max(1, (m.source_indices || []).length); } catch {}
    }
    const model = [job.provider_id, job.model_id].filter(Boolean).join("/");
    if (model || attempts || job.status === "completed" || job.status === "failed") {
      modelInfo.textContent = `Model: ${model || "unknown"} - attempts: ${attempts} - low-change sentences: ${low}`;
      modelInfo.classList.remove("hidden");
    } else {
      modelInfo.classList.add("hidden");
    }
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
    const wc = wordCount(text);
    if (wc > maxWords) { toast(`This text is ${wc.toLocaleString()} words. The limit is ${maxWords.toLocaleString()} words per request.`, "error"); return; }
    setButtonLoading(startBtn, true, "Humanizing...");
    progressWrap.classList.remove("hidden"); progressFill.style.width = "0%"; progressPct.textContent = "0%"; progressText.textContent = "Starting...";
    clear(statusHost); errorNote.classList.add("hidden"); currentDiff = null; renderStyle(null);
    try {
      const created = await api.humanize({
        text, mode: modeSel.value, intensity: intensitySel.value,
        provider_id: providerSel.value || undefined,
        preserve_formatting: getToggle(preserveToggle), keep_quotes: getToggle(preserveToggle),
        clean_invisible: getToggle(cleanToggle),
      });
      currentJob = null; plainOutput = ""; output.value = ""; syncRight(); setOutputControls(false); renderOutput();
      await poll(created.job_id);
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(startBtn, false); startBtn.textContent = "Humanize"; }
  }

  async function retryJob(): Promise<void> { if (!currentJob) return; try { await api.retryJob(currentJob.id); toast("Retrying failed chunks.", "info"); void poll(currentJob.id); } catch (err) { toast(errorMessage(err), "error"); } }
  async function cancelJob(): Promise<void> { if (!currentJob) return; try { await api.cancelJob(currentJob.id); toast("Cancellation requested.", "info"); } catch (err) { toast(errorMessage(err), "error"); } }
  async function download(fmt: "txt" | "docx"): Promise<void> { if (!currentJob) return; try { await api.downloadJob(currentJob.id, fmt, currentJob.title || "phrasia"); toast(`Downloaded .${fmt} file.`, "success"); } catch (err) { toast(errorMessage(err), "error"); } }
  async function copyOutput(): Promise<void> { if (!plainOutput) return; try { await navigator.clipboard.writeText(plainOutput); toast("Copied to clipboard.", "success"); } catch { toast("Could not copy automatically. Select and copy manually.", "error"); } }
  function useAsInput(): void { if (!plainOutput.trim()) return; original.value = plainOutput; setDraft(plainOutput); syncLeft(); toast("Rewritten text moved to input.", "success"); original.focus(); }

  renderStyle(null); renderOutput();
}
