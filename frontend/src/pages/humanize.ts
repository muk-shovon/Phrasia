import { api, errorMessage } from "../api";
import type {
  DiffSegment, HumanizeMeta, HumanizeResult, SkillReviewItem,
} from "../types";
import {
  button, card, clear, el, fieldWrap, getToggle, pageHead, select, setButtonLoading,
  setDraft, takeDraft, textarea, toast, toggle, wordCount,
} from "../ui";

const MAX_WORDS = 1500;
const TONES = ["casual", "professional", "academic", "marketing", "storytelling"];
const INTENSITIES = ["light", "medium", "heavy", "ninja"];
const INTENSITY_HELP: Record<string, string> = {
  light: "One sentence-level round.",
  medium: "Up to two rounds; flagged sentences are re-humanized once.",
  heavy: "Up to three rounds.",
  ninja: "Up to four rounds with tighter validation.",
};

function appendText(parent: HTMLElement, text: string): void {
  parent.append(document.createTextNode(text));
}

function strengthFor(intensity: string): string {
  return intensity === "ninja" ? "heavy" : intensity;
}

interface IndexedReview extends SkillReviewItem { index: number }

function appendReviewedText(
  parent: HTMLElement,
  text: string,
  start: number,
  reviews: IndexedReview[],
  badged: Set<number>,
): void {
  if (!text) return;
  const end = start + text.length;
  const overlaps = reviews
    .filter((item) => item.span[0] < end && item.span[1] > start)
    .sort((a, b) => a.span[0] - b.span[0]);
  if (!overlaps.length) { appendText(parent, text); return; }
  let position = start;
  for (const item of overlaps) {
    const left = Math.max(position, start, item.span[0]);
    const right = Math.min(end, item.span[1]);
    if (left > position) appendText(parent, text.slice(position - start, left - start));
    if (right <= left) continue;
    const marked = el("span", "underline decoration-violet-500 decoration-dotted decoration-2 underline-offset-4");
    if (!badged.has(item.index)) marked.id = `review-span-${item.index}`;
    marked.dataset.review = String(item.index);
    appendText(marked, text.slice(left - start, right - start));
    if (!badged.has(item.index)) {
      const tag = el("span", "ml-1 inline-block rounded bg-violet-100 px-1 py-0.5 text-[10px] font-semibold leading-none text-violet-700 align-middle", "review");
      tag.style.textDecoration = "none";
      marked.append(tag);
      badged.add(item.index);
    }
    parent.append(marked);
    position = right;
  }
  if (position < end) appendText(parent, text.slice(position - start));
}

function renderSegment(
  parent: HTMLElement,
  segment: DiffSegment,
  showOriginal: boolean,
  output: string,
  outputCursor: { value: number },
  reviews: IndexedReview[],
  badged: Set<number>,
): void {
  const displayed = segment.type === "equal"
    ? (segment.text ?? segment.rewritten ?? "")
    : (segment.rewritten || "");
  const found = displayed ? output.indexOf(displayed, outputCursor.value) : outputCursor.value;
  const start = found >= 0 ? found : outputCursor.value;
  if (segment.type === "equal") {
    appendReviewedText(parent, displayed, start, reviews, badged);
    outputCursor.value = start + displayed.length;
    return;
  }
  const span = el("span", "text-indigo-600 font-medium");
  if (segment.risk === "meaning") span.classList.add("underline", "decoration-amber-500", "decoration-solid", "underline-offset-2");
  if (segment.risk === "number") span.classList.add("underline", "decoration-red-500", "decoration-solid", "underline-offset-2");
  if (showOriginal && segment.original) {
    const old = el("span", "text-[var(--color-text-subtle)] line-through mr-1 text-[0.85em]");
    old.textContent = segment.original;
    span.append(old);
  }
  const neu = document.createElement("span");
  appendReviewedText(neu, displayed, start, reviews, badged);
  span.append(neu);
  if (segment.risk === "meaning" || segment.risk === "number") {
    span.append(el("span", segment.risk === "number" ? "text-red-600 ml-0.5" : "text-amber-600 ml-0.5", "!"));
  }
  parent.append(span);
  outputCursor.value = start + displayed.length;
}

function renderHighlighted(
  host: HTMLElement,
  segments: DiffSegment[],
  showOriginal: boolean,
  output: string,
  reviewItems: SkillReviewItem[],
): void {
  clear(host);
  const reviews: IndexedReview[] = reviewItems.map((item, index) => ({ ...item, index }));
  const outputCursor = { value: 0 };
  const badged = new Set<number>();
  const groups: DiffSegment[][] = [];
  let current: DiffSegment[] = [];
  for (const segment of segments) {
    if (segment.sentence_space) {
      if (current.length) groups.push(current);
      current = [];
      continue;
    }
    current.push(segment);
    if (segment.sentence_end) { groups.push(current); current = []; }
  }
  if (current.length) groups.push(current);
  groups.forEach((group, index) => {
    const unchanged = group.some((segment) => segment.low_change);
    const wrap = el("span", "inline whitespace-pre-wrap");
    group.forEach((segment, item) => {
      renderSegment(wrap, segment, showOriginal, output, outputCursor, reviews, badged);
      if (item < group.length - 1) appendText(wrap, " ");
    });
    if (unchanged) wrap.append(el("span", "ml-1 text-[10px] text-[var(--color-text-subtle)] align-middle", "unchanged"));
    host.append(wrap);
    if (index < groups.length - 1) appendText(host, " ");
  });
}

function describeMeta(meta: HumanizeMeta): string {
  if (meta.mode === "online") {
    const provider = meta.provider || "hosted provider";
    const model = meta.model ? ` (${meta.model})` : "";
    const rounds = meta.rounds ? ` · ${meta.rounds} round${meta.rounds === 1 ? "" : "s"}` : "";
    return `Hosted rewrite: ${provider}${model}${rounds}.`;
  }
  return "Local rule engine. No hosted provider was used.";
}

export async function renderHumanize(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead(
    "Humanizer",
    "Hosted rewriting first, then the local safety pass. The rule engine is the fallback.",
  ));

  const controls = card("mb-4 p-4 md:p-5");
  const grid = el("div", "grid gap-3 sm:grid-cols-2 lg:grid-cols-4");
  const toneSel = select(TONES.map((value) => ({ value, label: value[0]!.toUpperCase() + value.slice(1) })));
  toneSel.value = "casual";
  grid.append(fieldWrap("Tone", toneSel));

  const intensitySel = select(INTENSITIES.map((value) => ({
    value,
    label: value[0]!.toUpperCase() + value.slice(1),
  })));
  intensitySel.value = "medium";
  grid.append(fieldWrap("Intensity", intensitySel));

  const providerSel = select([{ value: "auto", label: "Auto (first ready)" }]);
  providerSel.value = "auto";
  grid.append(fieldWrap("Provider", providerSel));

  const cleanRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const cleanToggle = toggle(true, "Clean invisible characters");
  cleanRow.append(cleanToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Clean invisible characters"));
  grid.append(fieldWrap("Input", cleanRow));

  const providerHint = el("p", "mt-3 hidden text-xs text-[var(--color-text-subtle)]");
  const settingsLink = el("a", "font-medium text-[var(--color-accent)] underline underline-offset-2", "Open Settings");
  settingsLink.href = "#/settings";

  const more = el("details", "mt-4 border-t border-[var(--color-border)] pt-3");
  more.append(el("summary", "cursor-pointer select-none text-sm font-semibold text-[var(--color-text)]", "More options"));
  const moreGrid = el("div", "mt-3 grid gap-3 sm:grid-cols-2");
  const originalRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const originalToggle = toggle(false, "Show original wording");
  originalRow.append(originalToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Show original wording"));
  moreGrid.append(originalRow);
  const fallbackRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const fallbackToggle = toggle(true, "Offline fallback");
  fallbackRow.append(fallbackToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Offline fallback"));
  moreGrid.append(fallbackRow);
  const dashRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const dashToggle = toggle(true, "Replace dashes");
  dashRow.append(dashToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Replace dashes"));
  moreGrid.append(dashRow);
  const quoteRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const quoteToggle = toggle(true, "Straight quotes");
  quoteRow.append(quoteToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Straight quotes"));
  moreGrid.append(quoteRow);
  more.append(moreGrid);
  const intensityNote = el("p", "mt-2 text-xs text-[var(--color-text-subtle)]", INTENSITY_HELP.medium!);
  more.append(intensityNote);
  intensitySel.addEventListener("change", () => {
    intensityNote.textContent = INTENSITY_HELP[intensitySel.value] ?? "";
  });
  controls.append(grid, providerHint, more);
  root.append(controls);

  const workspace = el("div", "grid gap-4 xl:grid-cols-2");
  const left = card("flex flex-col min-w-0 p-4");
  const leftHead = el("div", "flex items-center justify-between gap-3 mb-3");
  leftHead.append(el("h2", "text-base font-semibold text-[var(--color-text)]", "Original"));
  const leftCount = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", `0 / ${MAX_WORDS} words`);
  const clearBtn = button("Clear", "ghost", () => { original.value = ""; syncLeft(); }, { size: "sm" });
  leftHead.append(leftCount, clearBtn);
  const original = textarea("Paste text here...", 10);
  original.className = "field-textarea h-56 md:h-64 min-h-[14rem] md:min-h-[16rem] resize-y overflow-auto p-4 text-base leading-relaxed whitespace-pre-wrap";
  original.spellcheck = true;
  left.append(leftHead, original);
  workspace.append(left);

  const right = card("flex flex-col min-w-0 p-4");
  const rightHead = el("div", "flex items-center justify-between gap-3 mb-3");
  rightHead.append(el("h2", "text-base font-semibold text-[var(--color-text)]", "Rewritten"));
  const rightCount = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  rightHead.append(rightCount);
  const plain = textarea("Your rewritten text appears here.", 10);
  plain.className = "field-textarea h-56 md:h-64 min-h-[14rem] md:min-h-[16rem] resize-y overflow-auto p-4 text-base leading-relaxed whitespace-pre-wrap";
  plain.readOnly = true;
  const highlighted = el("div", "hidden h-56 md:h-64 min-h-[14rem] md:min-h-[16rem] overflow-auto rounded-[var(--radius-md)] border border-[var(--color-border-strong)] bg-[var(--color-cornsilk-600)] p-4 text-base leading-relaxed text-[var(--color-text)] whitespace-pre-wrap");
  right.append(rightHead, plain, highlighted);
  workspace.append(right);
  root.append(workspace);

  const actions = card("mt-4 p-4 md:p-5");
  const row = el("div", "flex flex-wrap gap-2");
  const humanizeBtn = button("Humanize", "primary", () => void submit(0));
  const regenerateBtn = button("Regenerate", "secondary", () => void submit(variation + 1));
  const copyBtn = button("Copy", "secondary", () => void copyOutput());
  const txtBtn = button("Download .txt", "secondary", () => void download("txt"));
  const docxBtn = button("Download .docx", "secondary", () => void download("docx"));
  const useBtn = button("Use as input", "secondary", () => useAsInput());
  for (const item of [copyBtn, txtBtn, docxBtn, useBtn]) item.disabled = true;
  row.append(humanizeBtn, regenerateBtn, copyBtn, txtBtn, docxBtn, useBtn);

  const progress = el("div", "mt-3 hidden");
  const progressLabel = el("p", "text-xs font-medium text-[var(--color-text-muted)]", "Starting");
  const barOuter = el("div", "mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-cornsilk-600)]");
  const barFill = el("div", "h-full w-0 bg-[var(--color-accent)] transition-all duration-300");
  barOuter.append(barFill);
  progress.append(progressLabel, barOuter);

  const notice = el("p", "mt-2 hidden text-xs text-[var(--color-text-subtle)]", "Already rewritten; rewriting again changes little.");
  const aidNote = el(
    "p",
    "mt-2 text-xs text-[var(--color-text-subtle)]",
    "Results are a writing aid. They cannot guarantee anything about third-party detectors.",
  );
  actions.append(row, progress, notice, aidNote);
  root.append(actions);

  const feedbackCard = card("mt-4 p-4 md:p-5");
  feedbackCard.append(el("h2", "text-base font-semibold text-[var(--color-text)] mb-2", "Keep or correct this result"));
  feedbackCard.append(el(
    "p",
    "text-sm text-[var(--color-text-muted)]",
    "Accepted and edited results become examples for later prompts. Nothing is sent anywhere by this action.",
  ));
  const feedbackRow = el("div", "mt-3 flex flex-wrap gap-2");
  const upBtn = button("Looks good", "secondary", () => void sendFeedback("accepted", plainOutput), { size: "sm" });
  const downBtn = button("Not useful", "ghost", () => void sendFeedback("rejected", ""), { size: "sm" });
  upBtn.disabled = true;
  downBtn.disabled = true;
  feedbackRow.append(upBtn, downBtn);
  const editArea = textarea("Adjust the result, then save it as an example.", 4);
  editArea.className = "field-textarea mt-3 min-h-[6rem]";
  editArea.disabled = true;
  const saveEditBtn = button("Save edited version", "secondary", () => void sendFeedback("edited", editArea.value), { size: "sm" });
  saveEditBtn.disabled = true;
  saveEditBtn.classList.add("mt-2");
  feedbackCard.append(feedbackRow, editArea, saveEditBtn);
  root.append(feedbackCard);

  const styleCard = card("mt-4 p-4 md:p-5");
  styleCard.append(el("h2", "text-base font-semibold text-[var(--color-text)] mb-3", "Style check"));
  const styleHost = el("div");
  styleCard.append(styleHost);
  root.append(styleCard);

  const sentenceCard = card("mt-4 p-4 md:p-5");
  sentenceCard.append(el("h2", "text-base font-semibold text-[var(--color-text)] mb-1", "Sentence by sentence"));
  sentenceCard.append(el(
    "p",
    "text-sm text-[var(--color-text-muted)] mb-3",
    "One rewrite call per sentence, or per adjacent pair. Revert a sentence to its source or re-humanize only that sentence.",
  ));
  const sentenceHost = el("div", "space-y-2");
  sentenceCard.append(sentenceHost);
  root.append(sentenceCard);

  let current: HumanizeResult | null = null;
  let variation = 0;
  let plainOutput = "";
  let staleDiff = false;

  const syncLeft = (): void => {
    const n = wordCount(original.value);
    leftCount.textContent = `${n.toLocaleString()} / ${MAX_WORDS} words`;
    leftCount.className = "text-xs font-medium " + (n > MAX_WORDS ? "text-[var(--color-danger)]" : "text-[var(--color-text-subtle)]");
  };
  const syncRight = (): void => { rightCount.textContent = `${wordCount(plainOutput).toLocaleString()} words`; };
  original.addEventListener("input", syncLeft);
  original.value = takeDraft();
  syncLeft();
  syncRight();

  function setProgress(message: string, at: number, total: number): void {
    progress.classList.remove("hidden");
    progressLabel.textContent = message;
    const pct = total > 0 ? Math.max(8, Math.min(100, Math.round((at / total) * 100))) : 20;
    barFill.style.width = `${pct}%`;
  }
  function hideProgress(): void {
    window.setTimeout(() => progress.classList.add("hidden"), 900);
  }

  async function runJob(payload: Parameters<typeof api.startJob>[0]): Promise<HumanizeResult> {
    const started = await api.startJob(payload);
    for (let attempt = 0; attempt < 1200; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      const job = await api.job(started.job_id);
      setProgress(job.message || "Working", job.current, job.total);
      if (job.status === "done") {
        if (!job.result) throw new Error("The rewrite finished without a result.");
        return job.result;
      }
      if (job.status === "error") throw new Error(job.error || "The rewrite failed.");
    }
    throw new Error("The rewrite took too long. Try a shorter passage.");
  }

  function renderSentences(result: HumanizeResult | null): void {
    clear(sentenceHost);
    if (!result || !result.sentences.length) {
      sentenceHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "No sentence data yet."));
      return;
    }
    result.sentences.forEach((sentence, index) => {
      const row = el("div", "rounded-lg border border-[var(--color-border)] px-3 py-2");
      const head = el("div", "flex flex-wrap items-center justify-between gap-2");
      const title = el("p", "text-xs font-semibold text-[var(--color-text)]", `Sentence ${sentence.index ?? index + 1}`);
      const op = el("span", "rounded-full bg-[var(--color-cornsilk-600)] px-2 py-0.5 text-[11px] font-semibold text-[var(--color-text-muted)]", sentence.operation_label ?? sentence.operation ?? "Nearly unchanged");
      head.append(title, op);
      row.append(head);
      if (sentence.source && sentence.source !== sentence.text) {
        row.append(el("p", "mt-1 text-xs text-[var(--color-text-subtle)] line-through", sentence.source));
      }
      row.append(el("p", "mt-1 text-sm text-[var(--color-text)]", sentence.text || "(dropped)"));
      const note = el("p", "mt-1 text-[11px] text-[var(--color-text-subtle)]",
        `${sentence.validator ?? "passed"}${sentence.remaining_flags?.length ? ` · ${sentence.remaining_flags.join(", ")}` : ""}`);
      row.append(note);
      const actions = el("div", "mt-2 flex flex-wrap gap-2");
      actions.append(button("Re-humanize", "secondary", () => void rehumanizeSentence(index), { size: "sm" }));
      actions.append(button("Revert", "ghost", () => revertSentence(index), { size: "sm" }));
      actions.append(button("Thumbs up", "ghost", () => void sendSentenceFeedback(index, "accepted"), { size: "sm" }));
      actions.append(button("Thumbs down", "ghost", () => void sendSentenceFeedback(index, "rejected"), { size: "sm" }));
      row.append(actions);
      sentenceHost.append(row);
    });
  }

  function renderStyle(result: HumanizeResult | null): void {
    clear(styleHost);
    if (!result) {
      styleHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "Run Humanize to see how the text was cleaned."));
      return;
    }
    const s = result.style_check;
    const report = result.report;
    const meta = result.meta;

    styleHost.append(el("p", "text-sm font-semibold text-[var(--color-text)]", describeMeta(meta)));
    const density = meta.mode === "online"
      ? `Pattern density: ${meta.density_before} to ${meta.density_after} per 100 words.`
      : "";
    if (density) styleHost.append(el("p", "mt-1 text-xs text-[var(--color-text-subtle)]", density));
    if (meta.fallback_used) {
      styleHost.append(el(
        "p",
        "mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800",
        "The hosted providers did not answer, so the local engine finished this rewrite.",
      ));
    }
    if (meta.errors && meta.errors.length) {
      const details = el("details", "mt-2 text-xs text-[var(--color-text-subtle)]");
      details.append(el("summary", "cursor-pointer select-none", "Provider messages"));
      for (const item of meta.errors) {
        details.append(el("p", "mt-1", `${item.provider}: ${item.error}`));
      }
      styleHost.append(details);
    }

    styleHost.append(el(
      "p",
      "mt-3 text-sm font-semibold text-[var(--color-text)]",
      `Tells found ${report.found}, fixed ${report.fixed}, still present ${report.survived}`,
    ));
    if (report.reason) styleHost.append(el("p", "mt-1 text-xs text-[var(--color-text-subtle)]", `Kept unchanged: ${report.reason}.`));

    if (report.sections.length) {
      const sectionList = el("div", "mt-3 divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]");
      for (const section of report.sections) {
        const rowText = `§${section.section} ${section.name}: ${section.found} found, ${section.fixed} fixed${section.survived ? `, ${section.survived} still present` : ""}`;
        sectionList.append(el("p", "px-3 py-2 text-sm text-[var(--color-text-muted)]", rowText));
      }
      styleHost.append(sectionList);
    }

    const reviewHead = el("h3", "mt-5 text-sm font-semibold text-[var(--color-text)]", "Needs review");
    styleHost.append(reviewHead);
    if (!report.review.length) {
      styleHost.append(el("p", "mt-1 text-sm text-[var(--color-text-muted)]", "No flagged passages remain."));
    } else {
      const reviewList = el("div", "mt-2 space-y-2");
      report.review.forEach((item, index) => {
        const row = el("div", "rounded-lg border border-violet-200 bg-violet-50 px-3 py-2");
        const head = el("button", "block w-full text-left focus:outline-none focus:ring-2 focus:ring-violet-400 rounded");
        head.type = "button";
        head.append(el("p", "text-xs font-semibold text-violet-800", `§${item.section} ${item.name}`));
        head.append(el("p", "mt-1 text-sm text-[var(--color-text)]", `“${item.snippet}”`));
        head.append(el("p", "mt-1 text-xs text-[var(--color-text-muted)]", item.hint));
        head.addEventListener("click", () => {
          renderOutput();
          window.setTimeout(() => {
            document.getElementById(`review-span-${index}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
          }, 0);
        });
        const refresh = button("Re-humanize this passage", "secondary", (event) => {
          event.stopPropagation();
          void rehumanize(item, refresh);
        }, { size: "sm" });
        refresh.classList.add("mt-2");
        row.append(head, refresh);
        reviewList.append(row);
      });
      styleHost.append(reviewList);
    }
    styleHost.append(el("p", "mt-4 border-t border-[var(--color-border)] pt-3 text-xs text-[var(--color-text-subtle)]", `Sentences restructured: ${s.sentences_restructured} of ${s.sentences_total}. Words changed: ${s.words_changed_pct}%. These are writing-pattern signals, not proof of authorship.`));
  }

  function renderOutput(): void {
    const on = !!current && plainOutput.length > 0;
    plain.classList.toggle("hidden", on && !staleDiff);
    highlighted.classList.toggle("hidden", !on || staleDiff);
    if (on && current && !staleDiff) renderHighlighted(
      highlighted,
      current.diff.segments,
      getToggle(originalToggle),
      plainOutput,
      current.report.review,
    );
  }
  originalToggle.addEventListener("click", () => { window.setTimeout(renderOutput, 0); });

  function applyResult(result: HumanizeResult): void {
    current = result;
    plainOutput = result.rewritten;
    staleDiff = false;
    plain.value = plainOutput;
    editArea.value = plainOutput;
    setDraft(plainOutput);
    for (const item of [copyBtn, txtBtn, docxBtn, useBtn, upBtn, downBtn, saveEditBtn]) item.disabled = false;
    editArea.disabled = false;
    syncRight();
    renderStyle(current);
    renderSentences(current);
    renderOutput();
  }

  async function submit(nextVariation: number): Promise<void> {
    const text = original.value.trim();
    if (!text) { toast("Paste some text first.", "error"); original.focus(); return; }
    if (wordCount(text) > MAX_WORDS) { toast(`The limit is ${MAX_WORDS.toLocaleString()} words per request.`, "error"); return; }
    variation = nextVariation;
    setButtonLoading(humanizeBtn, true, "Rewriting...");
    setProgress("Sending the passage", 0, 1);
    try {
      const result = await runJob({
        text,
        tone: toneSel.value,
        strength: strengthFor(intensitySel.value),
        variation,
        clean_invisible: getToggle(cleanToggle),
        replace_dashes: getToggle(dashToggle),
        straight_quotes: getToggle(quoteToggle),
        intensity: intensitySel.value,
        provider: providerSel.value,
        offline_fallback: getToggle(fallbackToggle),
      });
      applyResult(result);
      toast("Rewrite complete.", "success");
    } catch (err) { toast(errorMessage(err), "error"); }
    finally {
      setButtonLoading(humanizeBtn, false);
      humanizeBtn.textContent = "Humanize";
      hideProgress();
    }
  }

  async function rehumanizeSentence(index: number): Promise<void> {
    if (!current) return;
    const sentence = current.sentences[index];
    if (!sentence) return;
    const oldText = sentence.text;
    try {
      const result = await api.rehumanize({
        text: oldText || sentence.source,
        tone: toneSel.value,
        strength: strengthFor(intensitySel.value),
        provider: providerSel.value,
        replace_dashes: getToggle(dashToggle),
        straight_quotes: getToggle(quoteToggle),
      });
      if (result.text && result.text !== oldText) {
        const target = oldText || sentence.source;
        if (plainOutput.includes(target)) plainOutput = plainOutput.replace(target, result.text);
        sentence.text = result.text;
        sentence.operation = "synonym";
        sentence.operation_label = "Re-humanized";
        staleDiff = true;
        plain.value = plainOutput;
        editArea.value = plainOutput;
        setDraft(plainOutput);
        syncRight();
      }
      renderSentences(current);
      renderOutput();
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  function revertSentence(index: number): void {
    if (!current) return;
    const sentence = current.sentences[index];
    if (!sentence || !sentence.source) return;
    const currentText = sentence.text;
    if (currentText && plainOutput.includes(currentText)) {
      plainOutput = plainOutput.replace(currentText, sentence.source);
    }
    sentence.text = sentence.source;
    sentence.operation = "keep";
    sentence.operation_label = "Nearly unchanged";
    sentence.validator = "reverted";
    staleDiff = true;
    plain.value = plainOutput;
    editArea.value = plainOutput;
    setDraft(plainOutput);
    syncRight();
    renderSentences(current);
    renderOutput();
  }

  async function sendSentenceFeedback(index: number, action: "accepted" | "rejected"): Promise<void> {
    if (!current) return;
    const sentence = current.sentences[index];
    if (!sentence) return;
    try {
      await api.feedback({
        action,
        version_id: current.version_id,
        sentence_idx: index,
        operation: sentence.operation ?? "keep",
        source_text: sentence.source,
        final_text: action === "rejected" ? "" : sentence.text,
        tone: toneSel.value,
        strength: strengthFor(intensitySel.value),
      });
      toast(action === "accepted" ? "Sentence saved as an example." : "Feedback recorded.", "success");
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  async function rehumanize(item: SkillReviewItem, btn: HTMLButtonElement): Promise<void> {
    setButtonLoading(btn, true, "Rewriting...");
    try {
      const result = await api.rehumanize({
        text: item.snippet,
        tone: toneSel.value,
        strength: strengthFor(intensitySel.value),
        provider: providerSel.value,
        replace_dashes: getToggle(dashToggle),
        straight_quotes: getToggle(quoteToggle),
      });
      if (!result.text || result.text === item.snippet) {
        toast("That passage is already clean.", "info");
        return;
      }
      if (!plainOutput.includes(item.snippet)) {
        toast("The passage moved. Run Humanize again.", "error");
        return;
      }
      plainOutput = plainOutput.replace(item.snippet, result.text);
      plain.value = plainOutput;
      editArea.value = plainOutput;
      if (current) {
        current.report.review = current.report.review.filter((entry) => entry !== item);
        staleDiff = true;
        renderStyle(current);
        renderOutput();
      }
      setDraft(plainOutput);
      syncRight();
      toast("Passage refreshed.", "success");
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(btn, false); }
  }

  async function sendFeedback(action: "accepted" | "rejected" | "edited", finalText: string): Promise<void> {
    if (!current) { toast("Run Humanize first.", "error"); return; }
    try {
      const result = await api.feedback({
        action,
        version_id: current.version_id,
        sentence_idx: null,
        source_text: original.value,
        final_text: action === "rejected" ? "" : finalText,
        tone: toneSel.value,
        strength: strengthFor(intensitySel.value),
      });
      if (action === "rejected") toast("Noted. No example was saved.", "success");
      else if (result.saved_example) toast("Saved as an example for later prompts.", "success");
      else toast("Feedback recorded.", "success");
      upBtn.disabled = true;
      downBtn.disabled = true;
      saveEditBtn.disabled = true;
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  async function copyOutput(): Promise<void> {
    if (!plainOutput) return;
    try { await navigator.clipboard.writeText(plainOutput); toast("Copied to clipboard.", "success"); }
    catch { toast("Could not copy automatically.", "error"); }
  }
  function useAsInput(): void {
    if (!plainOutput) return;
    original.value = plainOutput;
    setDraft(plainOutput);
    syncLeft();
    notice.classList.remove("hidden");
    original.focus();
  }
  async function download(format: "txt" | "docx"): Promise<void> {
    if (!plainOutput) return;
    const title = original.value.trim().split(/\s+/).slice(0, 6).join("-") || "phrasia";
    try { await api.download(plainOutput, title, format); toast(`Downloaded .${format} file.`, "success"); }
    catch (err) { toast(errorMessage(err), "error"); }
  }

  renderStyle(null);
  renderSentences(null);
  renderOutput();

  try {
    const loaded = await api.settings();
    const ready = loaded.providers.filter((item) => item.configured);
    providerSel.replaceChildren();
    const auto = el("option", "", "Auto (first ready)");
    auto.value = "auto";
    providerSel.append(auto);
    for (const item of ready) {
      const option = el("option", "", item.label);
      option.value = item.id;
      providerSel.append(option);
    }
    if (loaded.preferred_provider !== "auto" && ready.some((item) => item.id === loaded.preferred_provider)) {
      providerSel.value = loaded.preferred_provider;
    }
    if (!loaded.enabled) {
      providerHint.classList.remove("hidden");
      providerHint.replaceChildren(
        el("span", "", "Hosted rewriting is switched off. The local engine will be used. "),
        settingsLink,
      );
    } else if (!ready.length) {
      providerHint.classList.remove("hidden");
      providerHint.replaceChildren(
        el("span", "", "No hosted key yet. The local engine will be used until you add one. "),
        settingsLink,
      );
    }
  } catch {
    providerHint.classList.remove("hidden");
    providerHint.replaceChildren(
      el("span", "", "Could not read provider settings. The local engine is available. "),
      settingsLink,
    );
  }
}
