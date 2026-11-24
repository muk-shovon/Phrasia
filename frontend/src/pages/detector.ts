import { api, errorMessage } from "../api";
import type { DetectorReport } from "../types";
import {
  badge,
  button,
  card,
  el,
  pageHead,
  spinner,
  toast,
  takeDraft,
} from "../ui";

export async function renderDetector(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead(
      "Style Signal",
      "A local reading of your text: named signals and a plain-language label. No verdict, no percentage.",
    ),
    card("mt-2"),
  );

  const cardEl = root.lastElementChild as HTMLElement;
  cardEl.append(
    el(
      "div",
      "mt-1 text-sm font-medium text-[#7A877C]",
      "Pick a passage (or a document) — it is analysed here on your device.",
    ),
  );

  const textArea = el(
    "textarea",
    "w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-3 text-base leading-6 text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15",
  );
  textArea.value = takeDraft();
  textArea.placeholder = "Paste a passage (200-3,000 words work best).";
  cardEl.append(el("div", "mt-4"), textArea);

  const analyzeBtn = button("Read style signals", "primary", () => void run());
  cardEl.append(el("div", "mt-6 flex items-center gap-3"), analyzeBtn, spinner(28));

  const resultHost = el("div", "mt-6");
  cardEl.append(resultHost);

  function renderReport(report: DetectorReport): void {
    resultHost.replaceChildren(
      el("div", "flex flex-wrap items-center gap-4 rounded-xl bg-[#ECF5ED] px-5 py-4 text-sm"),
    );
    const header = resultHost.firstElementChild as HTMLElement;
    header.append(
      el("span", "font-bold text-[#16251C]", "Label: "),
      badge(report.label, "accent"),
      el("span", "text-[#5C6C62]", ` — ${report.word_count} words`),
    );

    const box = el("div", "mt-5 space-y-3");
    for (const signal of report.signals) {
      const cardEl = el(
        "div",
        "rounded-lg border border-[#DDE2D6] bg-white px-4 py-3",
      );
      cardEl.append(
        el("p", "text-xs font-semibold uppercase tracking-wide text-[#8C9890]", signal.name),
        el("p", "mt-1 text-sm text-[#3D4B41]", signal.detail),
      );
      box.append(cardEl);
    }
    resultHost.append(box);
    resultHost.append(
      el("p", "mt-4 text-sm text-[#7C8A80]", report.summary),
      el("p", "mt-4 text-sm text-[#7C8A80]", report.disclaimer),
    );
  }

  async function run(): Promise<void> {
    const text = textArea.value.trim();
    if (!text) {
      toast("Paste some text to analyze.", "error");
      return;
    }
    analyzeBtn.disabled = true;
    resultHost.replaceChildren(el("p", "", "Analysing locally…"));
    try {
      const report = await api.detect(text);
      renderReport(report);
    } catch (error) {
      resultHost.replaceChildren(el("p", "text-sm text-[#8B2020]", errorMessage(error)));
    } finally {
      analyzeBtn.disabled = false;
    }
  }
}
