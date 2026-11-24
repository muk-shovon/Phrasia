import { api, errorMessage } from "../api";
import type { DocumentDetail, DocumentSummary, JobDetail } from "../types";
import {
  CARD,
  INPUT,
  button,
  el,
  emptyState,
  formatDate,
  pageHeader,
  reportError,
  setDraft,
  statusBadge,
  toast,
} from "../ui";

export async function renderHistory(root: HTMLElement): Promise<void> {
  root.append(
    pageHeader(
      "History",
      "Every document you humanize is saved in your local database. Reopen it, export it, or run it again.",
    ),
  );

  const host = el("div", "space-y-3");
  root.append(host);

  async function showList(): Promise<void> {
    host.replaceChildren(el("p", "text-sm text-[#7A877C]", "Loading documents…"));
    try {
      const { documents } = await api.documents(100);
      host.replaceChildren();
      if (documents.length === 0) {
        host.append(
          emptyState(
            "No documents yet. Humanize something and it will show up here automatically.",
          ),
        );
        return;
      }
      for (const document of documents) {
        host.append(listItem(document));
      }
    } catch (error) {
      host.replaceChildren();
      host.append(emptyState(errorMessage(error)));
    }
  }

  function listItem(document: DocumentSummary): HTMLElement {
    const card = el(
      "article",
      "flex flex-col gap-3 rounded-xl border border-[#DDE3D8] bg-white p-4 shadow-[0_1px_2px_rgba(23,37,28,0.04)] md:flex-row md:items-start md:justify-between",
    );

    const main = el("div", "min-w-0");
    const titleRow = el("div", "flex flex-wrap items-center gap-2");
    const open = el(
      "button",
      "truncate text-left text-base font-semibold text-[#17251C] hover:text-[#1C6B4A]",
      document.title,
    );
    open.type = "button";
    open.addEventListener("click", () => void showDetail(document.id));
    titleRow.append(open);
    if (document.latest_job_status) titleRow.append(statusBadge(document.latest_job_status));

    const excerpt = el(
      "p",
      "mt-1.5 line-clamp-2 text-sm leading-6 text-[#5C6B60]",
      document.latest_excerpt ?? "No content yet.",
    );
    const meta = el(
      "p",
      "mt-1.5 text-xs text-[#8B978D]",
      `${formatDate(document.created_at)} · ${document.version_count} version${
        document.version_count === 1 ? "" : "s"
      }`,
    );
    main.append(titleRow, excerpt, meta);

    const actions = el("div", "flex shrink-0 flex-wrap gap-2");
    actions.append(
      button("Open", "secondary", () => void showDetail(document.id)),
      button("Delete", "danger", () => void removeDocument(document)),
    );

    card.append(main, actions);
    return card;
  }

  async function removeDocument(document: DocumentSummary): Promise<void> {
    if (!window.confirm(`Delete “${document.title}” and all of its versions?`)) return;
    try {
      await api.deleteDocument(document.id);
      toast("Document deleted.", "success");
      await showList();
    } catch (error) {
      reportError(error);
    }
  }

  async function showDetail(documentId: number): Promise<void> {
    host.replaceChildren(el("p", "text-sm text-[#7A877C]", "Loading document…"));
    let document: DocumentDetail;
    try {
      document = await api.document(documentId);
    } catch (error) {
      host.replaceChildren(
        emptyState(errorMessage(error)),
        button("Back to history", "secondary", () => void showList()),
      );
      return;
    }

    let job: JobDetail | null = null;
    const latestJob = document.jobs[0];
    if (latestJob) {
      try {
        job = await api.job(latestJob.id);
      } catch {
        job = null;
      }
    }

    host.replaceChildren();
    const back = button("← Back to history", "ghost", () => void showList());

    const head = el("div", "mt-3 flex flex-wrap items-center gap-2");
    head.append(
      el("h2", "text-xl font-semibold text-[#17251C]", document.title),
      statusBadge(job?.status ?? "saved"),
    );

    const meta = el(
      "p",
      "mt-1 text-xs text-[#8B978D]",
      `Created ${formatDate(document.created_at)} · Updated ${formatDate(document.updated_at)}`,
    );

    const actions = el("div", "mt-4 flex flex-wrap gap-2");
    const text = job?.output_text ?? job?.input_text ?? document.content;
    actions.append(
      button("Reopen in Humanizer", "primary", () => {
        setDraft(text);
        window.location.hash = "#/humanize";
      }),
    );
    if (job) {
      const txt = button("Download .txt", "secondary", () => void download(job!, "txt"));
      const docx = button("Download .docx", "secondary", () => void download(job!, "docx"));
      txt.disabled = !job.output_text;
      docx.disabled = !job.output_text;
      actions.append(txt, docx);

      if (job.status === "failed" || job.status === "cancelled" || job.status === "paused") {
        actions.append(
          button("Retry job", "secondary", () => {
            void (async () => {
              try {
                await api.retryJob(job!.id);
                toast("Job queued again.", "info");
                window.location.hash = "#/humanize";
              } catch (error) {
                reportError(error);
              }
            })();
          }),
        );
      }
    }
    actions.append(
      button("Delete document", "danger", () => {
        void (async () => {
          if (!window.confirm(`Delete “${document.title}” and all of its versions?`)) return;
          try {
            await api.deleteDocument(document.id);
            toast("Document deleted.", "success");
            await showList();
          } catch (error) {
            reportError(error);
          }
        })();
      }),
    );

    host.append(back, head, meta, actions);

    if (job?.error) {
      const error = el(
        "p",
        "mt-4 rounded-lg border border-[#E7C9C9] bg-[#FBF0F0] px-3.5 py-2.5 text-sm text-[#7C2323]",
        job.error,
      );
      host.append(error);
    }

    const panels = el("div", "mt-5 grid gap-5 xl:grid-cols-2");
    panels.append(
      textPanel("Original", job?.input_text ?? document.content),
      textPanel("Result", job?.output_text ?? "No result yet."),
    );
    host.append(panels);

    if (document.versions.length > 1) {
      const versions = el("div", "mt-5");
      versions.append(
        el("h3", "text-sm font-semibold uppercase tracking-wider text-[#5C6B60]", "Versions"),
      );
      const lines = el("ul", "mt-2 space-y-1 text-sm text-[#5C6B60]");
      for (const version of document.versions) {
        lines.append(
          el(
            "li",
            "",
            `${version.version_type} · ${version.word_count} words · ${formatDate(version.created_at)}`,
          ),
        );
      }
      versions.append(lines);
      host.append(versions);
    }
  }

  function textPanel(label: string, value: string): HTMLElement {
    const panel = el("section", CARD);
    panel.append(
      el("p", "text-sm font-semibold uppercase tracking-wider text-[#5C6B60]", label),
    );
    const area = el("textarea", `${INPUT} mt-2 min-h-[260px] resize-y bg-[#FAFBF7] leading-6`);
    area.readOnly = true;
    area.value = value;
    panel.append(area);
    return panel;
  }

  async function download(job: JobDetail, format: "txt" | "docx"): Promise<void> {
    try {
      await api.downloadJob(job.id, format, job.title);
    } catch (error) {
      toast(errorMessage(error), "error");
    }
  }

  await showList();
}
