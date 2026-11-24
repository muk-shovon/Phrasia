import { api, errorMessage } from "../api";
import type { DetectorReport } from "../types";
import {
  badge, button, card, clear, el, emptyState, loadingState, pageHead,
  setButtonLoading, textarea, toast, wordCount,
} from "../ui";

export async function renderDetector(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead("Style Signal", "Understand your writing through named style signals and clear, plain-language explanations."),
  );

  const workspace = el("div", "workspace-grid");

  const left = card("flex flex-col min-w-0");
  const leftHead = el("div", "flex flex-wrap items-center justify-between gap-3 mb-4");
  leftHead.append(el("h2", "text-lg font-semibold text-[var(--color-text)]", "Text to inspect"));
  const count = el("span", "text-xs font-medium text-[var(--color-text-subtle)]", "0 words");
  leftHead.append(count);
  const input = textarea("Paste a passage to analyze. For clearer signals, use 200 words or more.", 18);
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
    resultHost.append(emptyState("No analysis yet", "Paste text on the left and read its style signals. This is a local, descriptive analysis — not a detector verdict.", "◔"));
  }
  function showLoading(): void { clear(resultHost); resultHost.append(loadingState("Analyzing writing signals locally...")); }
  function showError(msg: string): void {
    clear(resultHost);
    const box = el("div", "rounded-lg border border-[rgba(122,59,46,0.2)] bg-[var(--color-danger-bg)] p-4");
    box.append(el("p", "font-semibold text-[var(--color-danger)]", "Analysis failed"));
    box.append(el("p", "mt-1 text-sm text-[var(--color-danger)]", msg));
    resultHost.append(box);
  }

  function signalTone(dir: string): "neutral" | "accent" | "success" | "warn" {
    if (dir === "formulaic") return "warn";
    if (dir === "conversational") return "success";
    return "neutral";
  }
  function signalLabel(dir: string): string {
    if (dir === "formulaic") return "Formulaic";
    if (dir === "conversational") return "Conversational";
    return "Neutral";
  }

  function renderReport(r: DetectorReport): void {
    clear(resultHost);

    const overview = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] p-5 mb-5");
    const head = el("div", "flex flex-wrap items-center gap-3 mb-2");
    head.append(el("p", "text-xl font-semibold text-[var(--color-text)]", r.label));
    head.append(badge("Local style signal", "accent"));
    overview.append(head);
    overview.append(el("p", "text-sm leading-6 text-[var(--color-text-muted)]", r.summary));
    const meta = el("div", "mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-text-subtle)]");
    meta.append(el("span", "", `${r.word_count.toLocaleString()} words`), el("span", "", `${r.sentence_count.toLocaleString()} sentences`));
    overview.append(meta);
    resultHost.append(overview);

    resultHost.append(el("h3", "text-sm font-semibold text-[var(--color-text)] mb-3", "Identified signals"));
    if (!r.signals.length) {
      resultHost.append(el("p", "text-sm text-[var(--color-text-muted)]", "No notable signals reported."));
    } else {
      const list = el("div", "space-y-3");
      for (const s of r.signals) {
        const item = el("div", "rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4");
        const row = el("div", "flex flex-wrap items-center justify-between gap-2 mb-1.5");
        row.append(el("p", "text-sm font-semibold text-[var(--color-text)]", s.name));
        row.append(badge(signalLabel(s.direction), signalTone(s.direction)));
        item.append(row);
        item.append(el("p", "text-sm leading-6 text-[var(--color-text-muted)]", s.detail));
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
    try { renderReport(await api.detect(text)); }
    catch (err) { const msg = errorMessage(err); showError(msg); toast(msg, "error"); }
    finally { setButtonLoading(analyzeBtn, false); analyzeBtn.textContent = "Read style signals"; }
  }

  showEmpty();
}
