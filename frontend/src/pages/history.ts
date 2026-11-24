import { api, errorMessage } from "../api";
import type { DocumentSummary, JobDetail } from "../types";
import {
  badge,
  button,
  card,
  el,
  formatDate,
  pageHead,
  toast,
} from "../ui";

export async function renderHistory(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead("History", "Your documents and jobs from this workspace."));

  const host = el("div", "space-y-4");
  root.append(host);

  async function loadDocuments(): Promise<void> {
    try {
      const { documents } = await api.documents(100);
      host.replaceChildren();
      if (!documents.length) {
        host.append(el("p", "text-sm text-[#5C6C62]", "No documents yet."));
        return;
      }
      for (const document of documents) host.append(documentItem(document));
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  function documentItem(document: DocumentSummary): HTMLElement {
    const box = card();
    const head = el("div", "flex flex-wrap items-center justify-between gap-3");
    head.append(
      el("h3", "text-lg font-semibold text-[#16251C]", document.title),
      badge(document.latest_job_status ?? "saved", "accent"),
    );
    box.append(head);
    box.append(el("p", "mt-2 text-sm text-[#5C6C62]", document.latest_excerpt || "No preview."));
    box.append(
      el(
        "p",
        "mt-2 text-sm text-[#5C6C62]",
        `Created ${formatDate(document.created_at)} · ${document.version_count} version${document.version_count === 1 ? "" : "s"}`,
      ),
    );
    box.append(
      el("div", "mt-5 flex flex-wrap gap-2"),
      button("Open", "secondary", () => void openDocument(document.id)),
      button("Delete", "danger", () => void deleteDocument(document.id)),
    );
    return box;
  }

  async function deleteDocument(id: number): Promise<void> {
    try {
      await api.deleteDocument(id);
      toast("Document deleted.", "success");
      await loadDocuments();
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  async function openDocument(id: number): Promise<void> {
    const doc = await api.document(id);
    let job: JobDetail | null = null;
    if (doc.jobs?.length) {
      job = await api.job(doc.jobs[0].id).catch(() => null);
    }

    root.replaceChildren();
    root.append(pageHead("Document", doc.title), el("div", "h-6"));
    const grid = el("div", "grid gap-5 xl:grid-cols-2");
    grid.append(panel("Original", job?.input_text ?? doc.content));
    grid.append(panel("Humanized", job?.output_text ?? "No result yet."));
    root.append(grid);
    if (doc.versions.length > 1) {
      const list = el("ul", "mt-3 space-y-2");
      for (const v of doc.versions) list.append(el("li", "text-sm text-[#5C6C62]", `${v.version_type} · ${v.word_count} words · ${formatDate(v.created_at)}`));
      root.append(el("h3", "mt-8 text-base font-semibold text-[#16251C]", "Versions"), list);
    }
    root.append(
      el("div", "h-6"),
      button("Back to history", "secondary", () => void loadDocuments()),
    );
  }

  function panel(label: string, value: string): HTMLElement {
    const node = card();
    const textarea = el(
      "textarea",
      "w-full resize-y rounded-lg border border-[#DDE2D6] bg-white px-3.5 py-3 leading-6 text-[#1D3026]",
    );
    textarea.readOnly = true;
    textarea.value = value;
    textarea.rows = 14;
    node.append(el("h3", "text-base font-semibold text-[#16251C]", label), textarea);
    return node;
  }

  await loadDocuments();
}
