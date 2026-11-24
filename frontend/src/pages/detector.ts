import { api, errorMessage } from "../api";
import type { DetectorReport } from "../types";
import {
  badge,
  button,
  card,
  el,
  pageHead,
  toast,
} from "../ui";

export async function renderDetector(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead(
      "Style Signal",
      "A local reading of your text: named signals and a plain-language label. No verdict, no percentage.",
    ),
  );

  const columns = el("div", "grid gap-8 xl:grid-cols-2 xl:gap-8");
  root.append(columns);

  // ── left: input ────────────────────────────────────────────────────────
  const leftPanel = card();
  columns.append(leftPanel);
  leftPanel.append(
    el("h3", "text-lg font-semibold text-[#16251C]", "Text to inspect"),
    el("div", "h-4"),
  );
  const textArea = el(
    "textarea",
    "w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-3 text-base leading-7 text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15 min-h-[480px]",
  );
  textArea.placeholder = "Paste a passage (200–3,000 words work best).";
  const analyzeBtn = button("Read style signals", "primary", () => void run());
  leftPanel.append(textArea, el("div", "h-4"), analyzeBtn);

  // ── right: signal panel ───────────────────────────────────────────────
  const rightPanel = card();
  columns.append(rightPanel);
  const statusHost = el("p", "text-sm text-[#5C6C62]", "Pick a passage to start.");
  const resultHost = el("div", "mt-5 space-y-4");
  rightPanel.append(statusHost, resultHost);

  const run = async (): Promise<void> => {
    const text = textArea.value.trim();
    if (!text) {
      toast("Paste some text first.", "error");
      return;
    }
    statusHost.textContent = "Reading locally…";
    analyzeBtn.disabled = true;
    try {
      const report: DetectorReport = await api.detect(text);
      resultHost.replaceChildren(
        el("div", "flex flex-wrap items-center gap-3 rounded-xl bg-[#ECF5ED] p-5"),
      );
      const header = resultHost.firstElementChild as HTMLElement;
      header.append(
        el("span", "text-2xl font-semibold text-[#16251C]", report.label),
        badge("Local style signal", "accent"),
      );
      resultHost.append(
        el("p", "mt-4 text-sm text-[#3D4B41] leading-6", report.summary),
        el("p", "mt-3 text-sm text-[#7C8A80]", `Words: ${report.word_count} · Sentences: ${report.sentence_count}`),
      );
      const signalList = el("div", "mt-5 space-y-3");
      for (const signal of report.signals) {
        const cardEl = el("div", "rounded-lg border border-[#DDE2D6] bg-white px-4 py-3");
        cardEl.append(
          el("p", "text-xs font-semibold uppercase tracking-wide text-[#8C9890]", signal.name),
          el("p", "mt-1 text-sm text-[#3D4B41]", signal.detail),
        );
        signalList.append(cardEl);
      }
      resultHost.append(signalList);
      resultHost.append(
        el("p", "mt-5 rounded-lg border border-[#DDE2D6] bg-white px-4 py-3 text-sm text-[#7C8A80]", report.disclaimer),
      );
      statusHost.textContent = "";
    } catch (error) {
      statusHost.textContent = "";
      toast(errorMessage(error), "error");
    } finally {
      analyzeBtn.disabled = false;
    }
  };

  analyzeBtn.addEventListener("click", () => void run());
}
