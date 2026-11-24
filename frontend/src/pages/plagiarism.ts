import { api, errorMessage } from "../api";
import type { PlagiarismReport, Reference } from "../types";
import {
  attachFileInput,
  badge,
  button,
  card,
  el,
  formatDate,
  input,
  pageHead,
  reportError,
  toast,
  takeDraft,
} from "../ui";

export async function renderPlagiarism(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead(
      "Similarity Check",
      "Local library check against your references, plus a real web search via ddgs.",
    ),
  );

  const layout = el("div", "grid gap-6 xl:grid-cols-2");
  root.append(layout);

  const checkCard = card();
  layout.append(checkCard);
  const refCard = card();
  layout.append(refCard);

  const textArea = el(
    "textarea",
    "w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-3 text-base leading-6 text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15 min-h-[280px]",
  );
  textArea.value = takeDraft();
  textArea.placeholder = "Paste text to compare against the reference library and the web.";
  checkCard.append(
    el("label", "mb-2 block text-sm font-semibold text-[#25352A]", "Text to check"),
    textArea,
  );
  const checkBtn = button("Check similarity", "primary", () => void run());
  checkCard.append(el("div", "h-4"), checkBtn);

  const resultHost = el("div", "mt-5 space-y-4");
  checkCard.append(resultHost);

  const refListHost = el("div", "space-y-3");
  const addForm = card();
  refCard.append(
    el(
      "h3",
      "text-base font-semibold uppercase tracking-wider text-[#5C6C62]",
      "Reference library",
    ),
    el("p", "mt-2 text-sm text-[#5C6C62]", "Saved locally. Used for similarity checks and, if installed, ddgs web search."),
    refListHost,
    addForm,
  );
  refListHost.append(
    button("Add reference", "secondary", () => void addReference()),
    addFileUpload(),
  );

  const addFormTitle = input("Reference title (optional)", { placeholder: "e.g. My earlier essay" });
  const addFormText = el("textarea", `${addFormTitle.className ? "" : ""}w-full resize-y rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-sm text-[#1D3026] outline-none transition focus:border-[#1F6B4A] min-h-[100px]`);
  addFormText.placeholder = "Paste reference text (also works with uploaded files)";

  async function addReference(): Promise<void> {
    const title = addFormTitle.querySelector("input")?.value || undefined;
    const text = addFormText.value.trim();
    if (!text) {
      toast("Reference text is empty.", "error");
      return;
    }
    try {
      await api.addReference(title ?? "", text);
      addFormText.value = "";
      toast("Reference added.", "success");
      await loadReferences();
    } catch (error) {
      reportError(error);
    }
  }

  function addFileUpload(): HTMLButtonElement {
    const btn = button("Upload file", "secondary", () => undefined);
    attachFileInput(btn, ".txt,.md,.markdown,.docx", (file) => {
      void (async () => {
        btn.textContent = "Reading…";
        btn.disabled = true;
        try {
          const extracted = await api.extractFile(file);
          addFormTitle.querySelector("input")!.value = extracted.filename.replace(/\.[^.]+$/, "");
          addFormText.value = extracted.text;
          toast(`Loaded ${extracted.filename}.`, "success");
        } catch (error) {
          reportError(error);
        } finally {
          btn.textContent = "Upload file";
          btn.disabled = false;
        }
      })();
    });
    return btn;
  }

  async function loadReferences(): Promise<void> {
    try {
      const { references } = await api.references();
      refListHost.replaceChildren();
      refListHost.append(
        button("Add reference", "secondary", () => void addReference()),
        addFileUpload(),
      );
      for (const reference of references) refListHost.append(refRow(reference));
    } catch (error) {
      reportError(error);
    }
  }

  function refRow(reference: Reference): HTMLElement {
    const row = el("div", "flex items-center gap-3 rounded-lg border border-[#DDE2D6] bg-white px-4 py-3");
    row.append(el("span", "text-sm font-medium text-[#1D3026]", reference.title));
    row.append(el("span", "text-sm text-[#5C6C62]", ` — ${formatDate(reference.created_at)} · ${reference.word_count} words`));
    row.append(el("span", "ml-auto", ""));
    row.append(button("Remove", "danger", () => void removeReference(reference.id)));
    return row;
  }

  async function removeReference(id: number): Promise<void> {
    try {
      await api.deleteReference(id);
      toast("Reference removed.", "success");
      await loadReferences();
    } catch (error) {
      reportError(error);
    }
  }

  async function run(): Promise<void> {
    const text = textArea.value.trim();
    if (!text) {
      toast("Paste text to check.", "error");
      return;
    }
    checkBtn.disabled = true;
    resultHost.replaceChildren(el("p", "text-sm text-[#5C6C62]", "Checking locally…"), el("p", "text-sm text-[#5C6C62]", "Running web search via ddgs…"), el("div", "h-4"));
    try {
      const report: PlagiarismReport = await api.checkPlagiarism(text);
      renderReport(report);
    } catch (error) {
      resultHost.replaceChildren(el("p", "text-sm text-[#8B2020]", errorMessage(error)));
    } finally {
      checkBtn.disabled = false;
    }
  }

  function renderReport(report: PlagiarismReport): void {
    const box = card();
    box.append(el("h3", "text-base font-semibold text-[#16251C]", "Similarity check results"));
    const coverRow = el("div", "mt-3 flex flex-wrap items-center gap-3");
    coverRow.append(el("span", "text-2xl font-semibold text-[#16251C]", `${report.coverage_percent}%`));
    coverRow.append(el("span", "text-sm text-[#5C6C62]", `of sentences matched a source (${report.word_count} words)`));
    box.append(coverRow);
    for (const note of report.notes) box.append(el("p", "mt-2 text-sm text-[#5C6C62]", note));

    for (const match of report.matches) {
      const item = card("border-[#DDE2D6] bg-[#FAFBF7]");
      const head = el("div", "flex flex-wrap items-center justify-between gap-3");
      head.append(el("span", "font-semibold text-[#16251C]", match.title), badge(`${match.similarity_percent}%`, "warn"));
      item.append(head, el("p", "mt-2 line-clamp-2 text-sm text-[#5C6C62]", match.excerpt));
      for (const passage of match.matched_passages) item.append(el("p", "mt-2 text-sm text-[#3D4B41]", `…${passage.passage}…`));
      box.append(item, el("div", "h-2"));
    }

    const web = report.web;
    const webBox = card("border-[#DDE2D6] bg-[#FAFBF7]");
    webBox.append(el("h4", "text-sm font-semibold uppercase tracking-wide text-[#5C6C62]", "Web search (ddgs)"));
    if (!web.available) {
      webBox.append(el("p", "mt-2 text-sm text-[#7C8A80]", `Not available: ${web.error || "search failed"}`));
    } else {
      for (const result of web.results.slice(0, 5)) {
        const anchor = el("a", "mt-2 block text-sm text-[#1F6B4A] hover:underline");
        anchor.href = result.url;
        anchor.textContent = result.title;
        webBox.append(anchor, el("p", "mt-1 text-xs text-[#7C8A80]", result.snippet || result.url));
      }
    }
    box.append(el("div", "h-2"), webBox);

    const repeated = report.repeated_phrases.slice(0, 5);
    if (repeated.length) {
      box.append(
        el("h4", "mt-4 text-sm font-semibold uppercase tracking-wide text-[#5C6C62]", "Repeated phrases in the text"),
      );
      for (const rp of repeated) box.append(el("p", "mt-2 text-sm text-[#5C6C62]", `"${rp.phrase}" (×${rp.count})`));
    }

    resultHost.replaceChildren(box);
  }

  await loadReferences();
}
