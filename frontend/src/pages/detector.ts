import { api, errorMessage } from "../api";
import type { DetectorPatternGroup, DetectorReport } from "../types";
import { badge, button, card, clear, el, emptyState, loadingState, pageHead, setButtonLoading, textarea, toast, wordCount } from "../ui";

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function mergeSpans(groups: DetectorPatternGroup[]): Array<{ start: number; end: number }> {
  const spans = groups.flatMap((g) => g.matches.map((m) => ({ start: m.start, end: m.end })))
    .filter((s) => s.end > s.start)
    .sort((a, b) => a.start - b.start || a.end - b.end);
  const merged: Array<{ start: number; end: number }> = [];
  for (const s of spans) {
    const last = merged[merged.length - 1];
    if (!last || s.start > last.end) merged.push({ ...s });
    else last.end = Math.max(last.end, s.end);
  }
  return merged;
}

function renderHighlighted(text: string, groups: DetectorPatternGroup[]): HTMLElement {
  const box = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-sm leading-7 text-[var(--color-text)] whitespace-pre-wrap break-words");
  const spans = mergeSpans(groups);
  let i = 0;
  let html = "";
  for (const s of spans) {
    const start = Math.max(0, Math.min(text.length, s.start));
    const end = Math.max(start, Math.min(text.length, s.end));
    if (start > i) html += escapeHtml(text.slice(i, start));
    html += `<mark class="rounded px-0.5 bg-[#f5edd0] text-[var(--color-text)]">${escapeHtml(text.slice(start, end))}</mark>`;
    i = end;
  }
  if (i < text.length) html += escapeHtml(text.slice(i));
  box.innerHTML = html || escapeHtml(text);
  return box;
}

export async function renderDetector(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead("Style Signal", "See common writing patterns highlighted in your text. This is a style signal, not proof of authorship."));

  const workspace = el("div", "workspace-grid");
  const left = card("flex flex-col min-w-0");
  const leftHead = el("div", "flex flex-wrap items-center justify-between gap-3 mb-4");
  leftHead.append(el("h2", "text-lg font-semibold text-[var(--color-text)]", "Text to inspect"));
  const count = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  leftHead.append(count);
  const input = textarea("Paste text to inspect for common writing patterns.", 18);
  input.classList.add("min-h-[320px]", "md:min-h-[460px]", "flex-1");
  input.addEventListener("input", () => { count.textContent = `${wordCount(input.value).toLocaleString()} words`; });
  const actions = el("div", "mt-5 flex flex-wrap gap-2");
  const analyzeBtn = button("Read style signals", "primary", () => void run());
  const clearBtn = button("Clear", "ghost", () => { input.value = ""; count.textContent = "0 words"; showEmpty(); }, { size: "sm" });
  actions.append(analyzeBtn, clearBtn);
  left.append(leftHead, input, actions);
  workspace.append(left);

  const right = card("flex flex-col min-w-0");
  right.append(el("h2", "text-lg font-semibold text-[var(--color-text)] mb-4", "Style analysis"));
  const resultHost = el("div", "flex-1");
  right.append(resultHost);
  workspace.append(right);
  root.append(workspace);

  function showEmpty(): void {
    clear(resultHost);
    resultHost.append(emptyState("No analysis yet", "Paste text on the left to see pattern highlights. This is a local style signal, not proof of authorship.", "?"));
  }
  function showLoading(): void { clear(resultHost); resultHost.append(loadingState("Analyzing writing patterns locally...")); }
  function showError(msg: string): void {
    clear(resultHost);
    const box = el("div", "rounded-lg border border-[rgba(122,59,46,0.2)] bg-[var(--color-danger-bg)] p-4");
    box.append(el("p", "font-semibold text-[var(--color-danger)]", "Analysis failed"));
    box.append(el("p", "mt-1 text-sm text-[var(--color-danger)]", msg));
    resultHost.append(box);
  }

  function renderReport(text: string, r: DetectorReport): void {
    clear(resultHost);
    const overview = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] p-4 mb-5");
    const head = el("div", "flex flex-wrap items-center gap-2 mb-2");
    head.append(el("p", "text-base font-semibold text-[var(--color-text)]", "Local style signal"));
    head.append(badge(`${r.total_matches} match${r.total_matches === 1 ? "" : "es"}`, r.total_matches > 0 ? "warn" : "success"));
    overview.append(head);
    overview.append(el("p", "text-sm text-[var(--color-text-muted)]", `${r.word_count.toLocaleString()} words inspected. Patterns below are writing signals, not authorship proof.`));
    resultHost.append(overview);

    resultHost.append(el("h3", "text-sm font-semibold text-[var(--color-text)] mb-3", "Highlighted text"));
    resultHost.append(renderHighlighted(text, r.patterns));

    resultHost.append(el("h3", "text-sm font-semibold text-[var(--color-text)] mt-6 mb-3", "Patterns found"));
    if (!r.patterns.length) {
      resultHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "No common pattern matches were found in this text."));
    } else {
      const list = el("div", "space-y-3");
      for (const p of r.patterns) {
        const item = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4");
        const row = el("div", "flex flex-wrap items-center justify-between gap-2 mb-1.5");
        row.append(el("p", "text-sm font-semibold text-[var(--color-text)]", p.name));
        row.append(badge(`${p.count} match${p.count === 1 ? "" : "es"}`, p.weight === "strong" ? "warn" : "neutral"));
        item.append(row);
        item.append(el("p", "text-sm text-[var(--color-text-muted)] leading-6", p.hint));
        list.append(item);
      }
      resultHost.append(list);
    }

    const disclaimer = el("div", "mt-5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3");
    disclaimer.append(el("p", "text-xs leading-5 text-[var(--color-text-subtle)]", r.disclaimer));
    resultHost.append(disclaimer);
  }

  async function run(): Promise<void> {
    const text = input.value.trim();
    if (!text) { toast("Paste text to analyze first.", "error"); input.focus(); return; }
    setButtonLoading(analyzeBtn, true, "Analyzing...");
    showLoading();
    try { renderReport(text, await api.detect(text)); }
    catch (err) { const msg = errorMessage(err); showError(msg); toast(msg, "error"); }
    finally { setButtonLoading(analyzeBtn, false); analyzeBtn.textContent = "Read style signals"; }
  }

  showEmpty();
}
