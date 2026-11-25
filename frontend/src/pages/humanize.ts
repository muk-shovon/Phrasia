import { api, errorMessage } from "../api";
import type { DiffSegment, HumanizeResult, SkillReviewItem } from "../types";
import {
  button, card, clear, el, fieldWrap, getToggle, pageHead, select, setButtonLoading,
  setDraft, takeDraft, textarea, toast, toggle, wordCount,
} from "../ui";

const MAX_WORDS = 1500;
const TONES = ["casual", "professional", "academic", "marketing", "storytelling"];
const STRENGTHS = ["light", "medium", "heavy"];

function appendText(parent: HTMLElement, text: string): void {
  parent.append(document.createTextNode(text));
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

export async function renderHumanize(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead("Humanizer", "Local, deterministic sentence rewriting. No model, key or network call."));

  const controls = card("mb-4 p-4 md:p-5");
  const grid = el("div", "grid gap-3 sm:grid-cols-2 lg:grid-cols-4");
  const toneSel = select(TONES.map((value) => ({ value, label: value[0].toUpperCase() + value.slice(1) })));
  toneSel.value = "casual";
  grid.append(fieldWrap("Tone", toneSel));
  const strengthSel = select(STRENGTHS.map((value) => ({ value, label: value[0].toUpperCase() + value.slice(1) })));
  strengthSel.value = "medium";
  grid.append(fieldWrap("Strength", strengthSel));
  const cleanRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const cleanToggle = toggle(true, "Clean invisible characters");
  cleanRow.append(cleanToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Clean invisible characters"));
  grid.append(fieldWrap("Input", cleanRow));
  const originalRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const originalToggle = toggle(false, "Show original wording");
  originalRow.append(originalToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Show original wording"));
  grid.append(fieldWrap("Review", originalRow));
  const more = el("details", "mt-4 border-t border-[var(--color-border)] pt-3");
  more.append(el("summary", "cursor-pointer select-none text-sm font-semibold text-[var(--color-text)]", "More options"));
  const moreGrid = el("div", "mt-3 grid gap-3 sm:grid-cols-2");
  const dashRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const dashToggle = toggle(true, "Replace dashes");
  dashRow.append(dashToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Replace dashes"));
  moreGrid.append(dashRow);
  const quoteRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const quoteToggle = toggle(true, "Straight quotes");
  quoteRow.append(quoteToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Straight quotes"));
  moreGrid.append(quoteRow);
  more.append(moreGrid);
  controls.append(grid, more);
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
  const notice = el("p", "mt-2 hidden text-xs text-[var(--color-text-subtle)]", "Already rewritten; rewriting again changes little.");
  actions.append(row, notice);
  root.append(actions);

  const styleCard = card("mt-4 p-4 md:p-5");
  styleCard.append(el("h2", "text-base font-semibold text-[var(--color-text)] mb-3", "Style check"));
  const styleHost = el("div");
  styleCard.append(styleHost);
  root.append(styleCard);

  let current: HumanizeResult | null = null;
  let variation = 0;
  let plainOutput = "";

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

  function renderStyle(result: HumanizeResult | null): void {
    clear(styleHost);
    if (!result) {
      styleHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "Run Humanize to see local pattern changes."));
      return;
    }
    const s = result.style_check;
    const report = result.report;
    styleHost.append(el(
      "p",
      "text-sm font-semibold text-[var(--color-text)]",
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
        const row = el("button", "block w-full rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-left hover:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-400");
        row.type = "button";
        row.append(el("p", "text-xs font-semibold text-violet-800", `§${item.section} ${item.name}`));
        row.append(el("p", "mt-1 text-sm text-[var(--color-text)]", `“${item.snippet}”`));
        row.append(el("p", "mt-1 text-xs text-[var(--color-text-muted)]", item.hint));
        row.addEventListener("click", () => {
          renderOutput();
          window.setTimeout(() => {
            document.getElementById(`review-span-${index}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
          }, 0);
        });
        reviewList.append(row);
      });
      styleHost.append(reviewList);
    }
    styleHost.append(el("p", "mt-4 border-t border-[var(--color-border)] pt-3 text-xs text-[var(--color-text-subtle)]", `Sentences restructured: ${s.sentences_restructured} of ${s.sentences_total}. Words changed: ${s.words_changed_pct}%. These are writing-pattern signals, not proof of authorship.`));
  }

  function renderOutput(): void {
    const on = !!current && plainOutput.length > 0;
    plain.classList.toggle("hidden", on);
    highlighted.classList.toggle("hidden", !on);
    if (on && current) renderHighlighted(
      highlighted,
      current.diff.segments,
      getToggle(originalToggle),
      plainOutput,
      current.report.review,
    );
  }
  originalToggle.addEventListener("click", () => { window.setTimeout(renderOutput, 0); });

  async function submit(nextVariation: number): Promise<void> {
    const text = original.value.trim();
    if (!text) { toast("Paste some text first.", "error"); original.focus(); return; }
    if (wordCount(text) > MAX_WORDS) { toast(`The limit is ${MAX_WORDS.toLocaleString()} words per request.`, "error"); return; }
    variation = nextVariation;
    setButtonLoading(humanizeBtn, true, "Rewriting...");
    try {
      current = await api.humanize({
        text,
        tone: toneSel.value,
        strength: strengthSel.value,
         variation,
         clean_invisible: getToggle(cleanToggle),
         replace_dashes: getToggle(dashToggle),
         straight_quotes: getToggle(quoteToggle),
       });
      plainOutput = current.rewritten;
      plain.value = plainOutput;
      setDraft(plainOutput);
      for (const item of [copyBtn, txtBtn, docxBtn, useBtn]) item.disabled = false;
      syncRight();
      renderStyle(current);
      renderOutput();
      toast("Rewrite complete.", "success");
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(humanizeBtn, false); humanizeBtn.textContent = "Humanize"; }
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
  renderOutput();
}
