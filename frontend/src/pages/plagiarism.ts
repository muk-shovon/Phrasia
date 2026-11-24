import { api, errorMessage } from "../api";
import type { PlagiarismReport } from "../types";
import {
  badge,
  button,
  card,
  el,
  pageHead,
  toast,
} from "../ui";

export async function renderPlagiarism(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead(
      "Similarity Check",
      "Local reference check against your saved library, plus a real web search via ddgs.",
    ),
  );

  const columns = el("div", "grid gap-8 xl:grid-cols-2 xl:gap-8");
  root.append(columns);

  // ── left: input ────────────────────────────────────────────────────────
  const leftPanel = card();
  columns.append(leftPanel);
  leftPanel.append(el("h3", "text-lg font-semibold text-[#16251C]", "Text to check"), el("div", "h-4"));
  const inputArea = el(
    "textarea",
    "w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-3 text-base leading-7 text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15 min-h-[500px]",
  );
  inputArea.placeholder = "Paste the passage you want to compare (100–3,000 words work best).";
  const checkBtn = button("Check similarity", "primary", () => void run());
  leftPanel.append(inputArea, el("div", "h-4"), checkBtn);

  // ── right: results ─────────────────────────────────────────────────────
  const rightPanel = card();
  columns.append(rightPanel);
  const statusHost = el("p", "mt-4 text-sm font-medium text-[#5C6C62]", "Check a passage to start.");
  const resultHost = el("div", "mt-5 space-y-5");
  rightPanel.append(statusHost, resultHost);

  let report: PlagiarismReport | null = null;

  const run = async (): Promise<void> => {
    const text = inputArea.value.trim();
    if (!text) {
      toast("Paste text first.", "error");
      return;
    }
    statusHost.textContent = "Checking locally…";
    checkBtn.disabled = true;
    try {
      const res = await api.checkPlagiarism(text);
      report = res;
      renderResults();
      statusHost.textContent = "";
    } catch (error) {
      statusHost.textContent = "";
      toast(errorMessage(error), "error");
    } finally {
      checkBtn.disabled = false;
    }
  };
  checkBtn.addEventListener("click", () => void run());

  function renderResults(): void {
    const res = report as PlagiarismReport;
    resultHost.replaceChildren(
      el("div", "rounded-xl bg-[#ECF5ED] p-5"),
    );
    (resultHost.lastElementChild as HTMLElement).append(
      el("p", "text-3xl font-semibold text-[#16251C]", `${res.coverage_percent}%`),
      el("p", "mt-1 text-sm text-[#5C6C62]", `matched ${res.word_count} words of input against ${res.checked_references} reference(s)`),
    );

    if (!res.matches.length) {
      resultHost.append(
        el("p", "text-sm text-[#5C6C62]", "No overlap found with your saved references."),
      );
    }
    for (const match of res.matches) {
      const item = card("border-[#DDE2D6] bg-[#FAFBF7]");
      const head = el("div", "flex flex-wrap items-center justify-between gap-3");
      head.append(el("h4", "text-base font-semibold text-[#16251C]", match.title));
      head.append(badge(`${match.similarity_percent}% similar`, "warn"));
      item.append(head, el("p", "mt-2 text-sm text-[#3D4B41]", match.excerpt.slice(0, 200)));
      resultHost.append(item);
    }

    const web = res.web;
    const webBox = card("border-[#DDE2D6] bg-[#FAFBF7]");
    webBox.append(
      el("h4", "text-base font-semibold text-[#16251C]", "Web search (ddgs)"),
    );
    if (!web.available) {
      webBox.append(el("p", "mt-2 text-sm text-[#7C8A80]", web.error || "not available"));
    } else {
      for (const result of web.results.slice(0, 5)) {
        webBox.append(el("p", "mt-2 text-sm text-[#5C6C62]", result.snippet || result.url));
      }
    }
    resultHost.append(webBox);
  }
}
