import { api, errorMessage } from "../api";
import type { PlagiarismReport } from "../types";
import {
  badge, button, card, clear, el, emptyState, loadingState, pageHead,
  setButtonLoading, textarea, toast, wordCount,
} from "../ui";

export async function renderPlagiarism(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead("Similarity Check", "Compare your text against your local reference library and live web search results."),
  );

  const workspace = el("div", "workspace-grid");

  // Left: input
  const left = card("flex flex-col min-w-0");
  const leftHead = el("div", "flex flex-wrap items-center justify-between gap-3 mb-4");
  leftHead.append(el("h2", "text-lg font-semibold text-[var(--color-text)]", "Text to check"));
  const count = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  leftHead.append(count);
  const input = textarea("Paste the passage you want to compare. For best results, use 100–3,000 words.", 18);
  input.classList.add("min-h-[320px]", "md:min-h-[460px]", "flex-1");
  input.addEventListener("input", () => { count.textContent = `${wordCount(input.value).toLocaleString()} words`; });
  const actions = el("div", "mt-5 flex flex-wrap gap-2");
  const checkBtn = button("Check similarity", "primary", () => void run());
  const clearBtn = button("Clear", "ghost", () => { input.value = ""; count.textContent = "0 words"; showEmpty(); }, { size: "sm" });
  actions.append(checkBtn, clearBtn);
  left.append(leftHead, input, actions);
  workspace.append(left);

  // Right: results
  const right = card("flex flex-col min-w-0");
  right.append(el("h2", "text-lg font-semibold text-[var(--color-text)] mb-4", "Similarity results"));
  const resultHost = el("div", "flex-1");
  right.append(resultHost);
  workspace.append(right);
  root.append(workspace);

  function showEmpty(): void {
    clear(resultHost);
    resultHost.append(emptyState("No check yet", "Paste text on the left and run a similarity check to see local and web matches here.", "◎"));
  }
  function showLoading(): void {
    clear(resultHost);
    resultHost.append(loadingState("Checking local references and searching the web..."));
  }
  function showError(msg: string): void {
    clear(resultHost);
    const box = el("div", "rounded-lg border border-[rgba(122,59,46,0.2)] bg-[var(--color-danger-bg)] p-4");
    box.append(el("p", "font-semibold text-[var(--color-danger)]", "Check failed"));
    box.append(el("p", "mt-1 text-sm text-[var(--color-danger)]", msg));
    resultHost.append(box);
  }

  function renderReport(r: PlagiarismReport): void {
    clear(resultHost);
    const summary = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] p-4 mb-5");
    const stats = el("div", "flex flex-wrap gap-x-6 gap-y-2 text-sm");
    stats.append(
      stat("Coverage", `${r.coverage_percent}%`),
      stat("Words checked", r.word_count.toLocaleString()),
      stat("Sentences", r.sentence_count.toLocaleString()),
      stat("References", r.checked_references.toLocaleString()),
    );
    summary.append(stats);
    if (r.disclaimer) summary.append(el("p", "mt-3 text-xs text-[var(--color-text-subtle)] leading-5", r.disclaimer));
    resultHost.append(summary);

    // Local matches
    resultHost.append(sectionTitle("Local reference matches"));
    if (!r.matches.length) {
      resultHost.append(el("p", "text-sm text-[var(--color-text-muted)] mb-5", "No overlapping passages found in your local reference library."));
    } else {
      const list = el("div", "space-y-3 mb-6");
      for (const m of r.matches) {
        const item = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4");
        const head = el("div", "flex flex-wrap items-center justify-between gap-2 mb-2");
        head.append(el("h3", "text-sm font-semibold text-[var(--color-text)]", m.title));
        head.append(badge(`${m.similarity_percent}% similar`, m.similarity_percent >= 30 ? "warn" : "neutral"));
        item.append(head);
        item.append(el("p", "text-xs text-[var(--color-text-subtle)] mb-2", `${m.overlap_words} overlapping words`));
        if (m.excerpt) item.append(el("p", "text-sm text-[var(--color-text-muted)] leading-6 border-l-2 border-[var(--color-border-strong)] pl-3", m.excerpt.slice(0, 280)));
        if (m.matched_sentences?.length) {
          const ms = el("div", "mt-3 space-y-1");
          for (const s of m.matched_sentences.slice(0, 3)) {
            ms.append(el("p", "text-xs text-[var(--color-text-muted)]", `• ${s.sentence.slice(0, 160)} (${s.overlap_percent}% overlap)`));
          }
          item.append(ms);
        }
        list.append(item);
      }
      resultHost.append(list);
    }

    // Web results
    resultHost.append(sectionTitle("Web search results"));
    const web = r.web;
    if (!web.available) {
      resultHost.append(el("p", "text-sm text-[var(--color-text-muted)]", web.error || "Web search is not available."));
    } else if (!web.results.length) {
      resultHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "No web matches returned for this text."));
    } else {
      const list = el("div", "space-y-3");
      for (const w of web.results.slice(0, 8)) {
        const item = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4");
        const title = el("a", "text-sm font-semibold text-[var(--color-primary)] hover:underline underline-offset-2", w.title || w.url);
        title.href = w.url; title.target = "_blank"; title.rel = "noopener noreferrer";
        item.append(title);
        item.append(el("p", "mt-1 text-xs text-[var(--color-text-subtle)] break-all", w.url));
        if (w.snippet) item.append(el("p", "mt-2 text-sm text-[var(--color-text-muted)] leading-6", w.snippet));
        list.append(item);
      }
      resultHost.append(list);
    }
    if (web.disclaimer) resultHost.append(el("p", "mt-4 text-xs text-[var(--color-text-subtle)]", web.disclaimer));

    if (r.repeated_phrases?.length) {
      resultHost.append(sectionTitle("Repeated phrases"));
      const wrap = el("div", "flex flex-wrap gap-2");
      for (const p of r.repeated_phrases.slice(0, 12)) wrap.append(badge(`${p.phrase} (${p.count})`, "neutral"));
      resultHost.append(wrap);
    }
  }

  function stat(label: string, value: string): HTMLElement {
    const s = el("div");
    s.append(el("div", "text-xs text-[var(--color-text-subtle)] uppercase tracking-wide", label));
    s.append(el("div", "text-base font-semibold text-[var(--color-text)]", value));
    return s;
  }
  function sectionTitle(t: string): HTMLElement {
    return el("h3", "text-sm font-semibold text-[var(--color-text)] mb-3 mt-1", t);
  }

  async function run(): Promise<void> {
    const text = input.value.trim();
    if (!text) { toast("Paste text to check first.", "error"); input.focus(); return; }
    setButtonLoading(checkBtn, true, "Checking...");
    showLoading();
    try {
      const report = await api.checkPlagiarism(text);
      renderReport(report);
    } catch (err) {
      const msg = errorMessage(err);
      showError(msg);
      toast(msg, "error");
    } finally {
      setButtonLoading(checkBtn, false);
      checkBtn.textContent = "Check similarity";
    }
  }

  showEmpty();
}
