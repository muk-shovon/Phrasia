import { api } from "../api";
import type { DetectorReport, DetectorSignal } from "../types";
import {
  CARD,
  INPUT,
  button,
  el,
  formatNumber,
  notice,
  pageHeader,
  reportError,
  setBusy,
  takeDraft,
  toast,
} from "../ui";

const DIRECTION_STYLES: Record<DetectorSignal["direction"], string> = {
  formulaic: "border-[#EBD9B5] bg-[#FDF7EA] text-[#7A5410]",
  conversational: "border-[#CFE3D6] bg-[#F1F8F3] text-[#1B5E3B]",
  neutral: "border-[#E3E7DD] bg-[#FAFBF7] text-[#5C6B60]",
};

export async function renderDetector(root: HTMLElement): Promise<void> {
  root.append(
    pageHeader(
      "Local style signal",
      "Read the surface patterns in a passage: stock transitions, inflated vocabulary, contractions, rhythm and repetition.",
    ),
  );

  root.append(
    notice(
      "This is a style signal, not proof of authorship. It cannot tell you who wrote a text, and it has no percentage verdict. Use it as an editing prompt, not a detector.",
    ),
  );
  root.append(el("div", "h-5"));

  const card = el("section", CARD);
  const textArea = el("textarea", `${INPUT} min-h-[240px] resize-y leading-6`);
  textArea.placeholder = "Paste a passage to inspect its writing patterns.";
  textArea.value = takeDraft();

  const analyze = button("Read style signals", "primary", () => void run());
  const resultHost = el("div", "mt-5");

  card.append(
    el("h2", "text-sm font-semibold uppercase tracking-wider text-[#5C6B60]", "Text to inspect"),
    el("div", "mt-3"),
    textArea,
    el("div", "mt-3 flex flex-wrap items-center gap-3"),
    analyze,
    el("span", "text-xs text-[#7A877C]", "Runs locally. Nothing is sent to a provider."),
    resultHost,
  );
  root.append(card);

  async function run(): Promise<void> {
    const text = textArea.value.trim();
    if (!text) {
      toast("Paste some text first.", "error");
      return;
    }
    setBusy(analyze, true, "Reading…");
    try {
      renderReport(await api.detect(text));
    } catch (error) {
      reportError(error);
    } finally {
      setBusy(analyze, false);
    }
  }

  function renderReport(report: DetectorReport): void {
    resultHost.replaceChildren();

    const summary = el("div", "rounded-xl border border-[#DDE3D8] bg-[#FAFBF7] p-4");
    summary.append(
      el(
        "p",
        "text-xs font-semibold uppercase tracking-wider text-[#8B978D]",
        "Style signal",
      ),
      el(
        "p",
        "mt-1 text-2xl font-semibold capitalize tracking-tight text-[#17251C]",
        report.label,
      ),
      el("p", "mt-2 text-sm leading-6 text-[#3D4B41]", report.summary),
      el(
        "p",
        "mt-2 text-xs text-[#8B978D]",
        `${formatNumber(report.word_count)} words · ${formatNumber(report.sentence_count)} sentences`,
      ),
    );
    resultHost.append(summary);

    const grid = el("div", "mt-3 grid gap-2 sm:grid-cols-2");
    for (const signal of report.signals) {
      const box = el("div", `rounded-lg border px-3 py-2.5 ${DIRECTION_STYLES[signal.direction]}`);
      box.append(
        el("p", "text-xs font-semibold uppercase tracking-wide opacity-80", signal.name),
        el("p", "mt-1 text-sm leading-5", signal.detail),
      );
      grid.append(box);
    }
    resultHost.append(grid);

    resultHost.append(
      el(
        "p",
        "mt-4 rounded-lg border border-[#E7EBE3] bg-white px-3.5 py-2.5 text-xs leading-5 text-[#7A877C]",
        report.disclaimer,
      ),
    );
  }
}
