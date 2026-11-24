import { api, errorMessage } from "../api";
import type { PlagiarismReport, Reference } from "../types";
import {
  CARD,
  INPUT,
  attachFileInput,
  button,
  el,
  emptyState,
  formatDate,
  formatNumber,
  notice,
  pageHeader,
  reportError,
  setBusy,
  takeDraft,
  toast,
} from "../ui";

export async function renderPlagiarism(root: HTMLElement): Promise<void> {
  root.append(
    pageHeader(
      "Similarity check",
      "Compare a passage against your own reference library. This runs entirely on this machine and does not search the internet.",
    ),
  );

  root.append(
    notice(
      "Local similarity signal only. A low result does not prove originality, and a high result only means the text overlaps your saved references.",
    ),
  );
  root.append(el("div", "h-5"));

  const grid = el("div", "grid items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]");

  // ── check panel ───────────────────────────────────────────────────────────
  const checkCard = el("section", CARD);
  const textArea = el("textarea", `${INPUT} min-h-[240px] resize-y leading-6`);
  textArea.placeholder = "Paste the passage you want to compare. 40+ words gives a steadier result.";
  textArea.value = takeDraft();

  const checkButton = button("Check similarity", "primary", () => void runCheck());
  const resultHost = el("div", "mt-5");

  checkCard.append(
    el("h2", "text-sm font-semibold uppercase tracking-wider text-[#5C6B60]", "Text to check"),
    el("div", "mt-3"),
    textArea,
    el("div", "mt-3 flex flex-wrap items-center gap-3"),
    checkButton,
    el("span", "text-xs text-[#7A877C]", "Nothing is uploaded anywhere."),
    resultHost,
  );

  // ── reference library ─────────────────────────────────────────────────────
  const libraryCard = el("section", CARD);
  const listHost = el("div", "mt-3 space-y-2");

  const addFile = button("Upload reference file", "secondary", () => undefined);
  attachFileInput(addFile, ".txt,.md,.markdown,.docx", (file) => {
    void (async () => {
      setBusy(addFile as HTMLButtonElement, true, "Uploading…");
      try {
        await api.uploadReference(file);
        toast("Reference added.", "success");
        await loadReferences();
      } catch (error) {
        reportError(error);
      } finally {
        setBusy(addFile as HTMLButtonElement, false);
      }
    })();
  });

  const titleInput = el("input", `${INPUT} mt-2`);
  titleInput.placeholder = "Reference title";
  const pasteArea = el("textarea", `${INPUT} mt-2 min-h-[110px] resize-y`);
  pasteArea.placeholder = "Paste reference text here…";
  const addPaste = button("Add pasted reference", "secondary", () => {
    void (async () => {
      const text = pasteArea.value.trim();
      if (!text) {
        toast("Paste the reference text first.", "error");
        return;
      }
      setBusy(addPaste, true, "Adding…");
      try {
        await api.addReference(titleInput.value.trim(), text);
        titleInput.value = "";
        pasteArea.value = "";
        toast("Reference added.", "success");
        await loadReferences();
      } catch (error) {
        reportError(error);
      } finally {
        setBusy(addPaste, false);
      }
    })();
  });

  libraryCard.append(
    el("h2", "text-sm font-semibold uppercase tracking-wider text-[#5C6B60]", "Reference library"),
    el(
      "p",
      "mt-1 text-sm leading-6 text-[#5C6B60]",
      "Saved locally. Used only for similarity checks on this device.",
    ),
    listHost,
    el("div", "mt-4 border-t border-[#EDF0E8] pt-4"),
    addFile,
    titleInput,
    pasteArea,
    el("div", "mt-2"),
    addPaste,
  );

  grid.append(checkCard, libraryCard);
  root.append(grid);

  // ── behaviour ─────────────────────────────────────────────────────────────
  async function loadReferences(): Promise<void> {
    try {
      const { references } = await api.references();
      listHost.replaceChildren();
      if (references.length === 0) {
        listHost.append(emptyState("No references yet. Add an essay, article or previous draft."));
        return;
      }
      for (const reference of references) {
        listHost.append(referenceRow(reference));
      }
    } catch (error) {
      listHost.replaceChildren(emptyState(errorMessage(error)));
    }
  }

  function referenceRow(reference: Reference): HTMLElement {
    const row = el(
      "div",
      "flex items-start justify-between gap-3 rounded-lg border border-[#E7EBE3] bg-[#FAFBF7] px-3 py-2.5",
    );
    const info = el("div", "min-w-0");
    info.append(
      el("p", "truncate text-sm font-medium text-[#25352A]", reference.title),
      el(
        "p",
        "text-xs text-[#8B978D]",
        `${formatNumber(reference.word_count)} words · ${formatDate(reference.created_at)}`,
      ),
    );
    const remove = button("Remove", "ghost", () => {
      void (async () => {
        if (!window.confirm(`Remove “${reference.title}” from the library?`)) return;
        try {
          await api.deleteReference(reference.id);
          toast("Reference removed.", "success");
          await loadReferences();
        } catch (error) {
          reportError(error);
        }
      })();
    });
    remove.classList.add("text-[#8B2020]", "shrink-0");
    row.append(info, remove);
    return row;
  }

  async function runCheck(): Promise<void> {
    const text = textArea.value.trim();
    if (!text) {
      toast("Paste some text to check.", "error");
      return;
    }
    setBusy(checkButton, true, "Checking…");
    try {
      const report = await api.checkPlagiarism(text);
      renderReport(report);
    } catch (error) {
      reportError(error);
    } finally {
      setBusy(checkButton, false);
    }
  }

  function renderReport(report: PlagiarismReport): void {
    resultHost.replaceChildren();

    const summary = el(
      "div",
      "rounded-xl border border-[#DDE3D8] bg-[#FAFBF7] p-4",
    );
    summary.append(
      el(
        "p",
        "text-3xl font-semibold tracking-tight text-[#17251C]",
        `${report.coverage_percent}%`,
      ),
      el(
        "p",
        "mt-1 text-sm leading-6 text-[#5C6B60]",
        `of ${report.sentence_count} analysed sentence(s) closely matched a reference. Checked against ${report.checked_references} reference document(s).`,
      ),
    );
    const words = el(
      "p",
      "mt-2 text-xs text-[#8B978D]",
      `${formatNumber(report.word_count)} words in the checked passage.`,
    );
    summary.append(words);

    resultHost.append(summary);

    if (report.matches.length === 0) {
      resultHost.append(
        el(
          "p",
          "mt-4 text-sm leading-6 text-[#5C6B60]",
          "No overlap with your reference library was found.",
        ),
      );
    }

    for (const match of report.matches) {
      const card = el("div", "mt-4 rounded-xl border border-[#DDE3D8] bg-white p-4");
      const head = el("div", "flex flex-wrap items-center justify-between gap-2");
      head.append(
        el("h3", "text-sm font-semibold text-[#17251C]", match.title),
        el(
          "span",
          "rounded-full bg-[#FBF1DC] px-2.5 py-0.5 text-xs font-semibold text-[#8A5A12]",
          `${match.similarity_percent}% of your text overlaps`,
        ),
      );
      card.append(head);
      card.append(
        el("p", "mt-2 line-clamp-3 text-xs leading-5 text-[#7A877C]", match.excerpt),
      );
      if (match.matched_sentences.length) {
        const list = el("ul", "mt-3 space-y-1.5");
        for (const hit of match.matched_sentences) {
          list.append(
            el(
              "li",
              "rounded-md bg-[#FAFBF7] px-3 py-2 text-xs leading-5 text-[#3D4B41]",
              `${hit.overlap_percent}% overlap — ${hit.sentence}`,
            ),
          );
        }
        card.append(list);
      }
      resultHost.append(card);
    }

    if (report.repeated_phrases.length) {
      const box = el("div", "mt-4 rounded-xl border border-[#DDE3D8] bg-white p-4");
      box.append(
        el("h3", "text-sm font-semibold text-[#17251C]", "Repeated phrases inside the passage"),
      );
      const list = el("ul", "mt-2 space-y-1 text-xs leading-5 text-[#5C6B60]");
      for (const repeated of report.repeated_phrases) {
        list.append(el("li", "", `“${repeated.phrase}” — ${repeated.count}×`));
      }
      box.append(list);
      resultHost.append(box);
    }

    if (report.notes.length) {
      const notes = el("ul", "mt-4 list-disc space-y-1 pl-5 text-xs leading-5 text-[#7A877C]");
      for (const note of report.notes) notes.append(el("li", "", note));
      resultHost.append(notes);
    }
  }

  await loadReferences();
}
