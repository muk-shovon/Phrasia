import { api, errorMessage } from "../api";
import type { DocumentSummary, JobDetail } from "../types";
import {
  button, card, clear, confirmDialog, el, emptyState, formatDate, pageHead,
  setButtonLoading, statusBadge, toast,
} from "../ui";

type SortKey = "newest" | "oldest" | "title";

export async function renderHistory(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead("History", "Your documents and jobs from this workspace."));

  const toolbar = el("div", "card p-4 md:p-5 mb-6");
  const toolbarGrid = el("div", "grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_180px_180px_auto] lg:items-end");
  const searchWrap = el("div");
  searchWrap.append(el("label", "field-label", "Search documents"));
  const searchInput = el("input", "field-input") as HTMLInputElement;
  searchInput.type = "search";
  searchInput.placeholder = "Search by title or content preview...";
  searchWrap.append(searchInput);

  const filterWrap = el("div");
  filterWrap.append(el("label", "field-label", "Status"));
  const filterSel = el("select", "field-select") as HTMLSelectElement;
  for (const [v, l] of [["all","All statuses"],["completed","Completed"],["failed","Failed"],["running","Processing"],["queued","Queued"],["paused","Paused"],["cancelled","Cancelled"],["saved","Saved"]] as const) {
    const o = el("option", "", l) as HTMLOptionElement; o.value = v; filterSel.append(o);
  }
  filterWrap.append(filterSel);

  const sortWrap = el("div");
  sortWrap.append(el("label", "field-label", "Sort by"));
  const sortSel = el("select", "field-select") as HTMLSelectElement;
  for (const [v,l] of [["newest","Newest first"],["oldest","Oldest first"],["title","Title A–Z"]] as const) {
    const o = el("option", "", l) as HTMLOptionElement; o.value = v; sortSel.append(o);
  }
  sortWrap.append(sortSel);

  const refreshWrap = el("div", "flex items-end");
  const refreshBtn = button("Refresh", "secondary", () => void load(), { size: "sm" });
  refreshWrap.append(refreshBtn);

  toolbarGrid.append(searchWrap, filterWrap, sortWrap, refreshWrap);
  toolbar.append(toolbarGrid);
  root.append(toolbar);

  const listHost = el("div", "space-y-4");
  root.append(listHost);

  let documents: DocumentSummary[] = [];

  function applyFilters(): DocumentSummary[] {
    const q = searchInput.value.trim().toLowerCase();
    const status = filterSel.value;
    let items = documents.filter((d) => {
      const matchesQ = !q || d.title.toLowerCase().includes(q) || (d.latest_excerpt ?? "").toLowerCase().includes(q);
      const s = (d.latest_job_status ?? "saved").toLowerCase();
      const normalized = s === "canceled" ? "cancelled" : s;
      const matchesStatus = status === "all" || normalized === status || (status === "running" && ["running","queued","paused"].includes(normalized));
      return matchesQ && matchesStatus;
    });
    const sort = sortSel.value as SortKey;
    items = items.slice().sort((a, b) => {
      if (sort === "title") return a.title.localeCompare(b.title);
      const da = new Date(a.created_at).getTime();
      const db = new Date(b.created_at).getTime();
      return sort === "oldest" ? da - db : db - da;
    });
    return items;
  }

  function render(): void {
    clear(listHost);
    const items = applyFilters();
    if (!documents.length) {
      listHost.append(emptyState("No history yet", "Documents you humanize will appear here with their versions and job status.", "◷"));
      return;
    }
    if (!items.length) {
      listHost.append(emptyState("No matching documents", "Try adjusting your search or filters.", "⌕"));
      return;
    }
    for (const doc of items) listHost.append(docCard(doc));
  }

  function docCard(doc: DocumentSummary): HTMLElement {
    const item = card("transition-shadow hover:shadow-[var(--shadow-soft)]");
    const top = el("div", "flex flex-wrap items-start justify-between gap-3");
    const left = el("div", "min-w-0 flex-1");
    left.append(el("h3", "text-base font-semibold text-[var(--color-text)] truncate", doc.title || "Untitled"));
    left.append(el("p", "mt-1 text-sm text-[var(--color-text-muted)] leading-6 line-clamp-2", doc.latest_excerpt || "No preview available."));
    top.append(left, statusBadge(doc.latest_job_status ?? "saved"));
    item.append(top);

    const meta = el("div", "mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-text-subtle)]");
    meta.append(el("span", "", `Created ${formatDate(doc.created_at)}`));
    meta.append(el("span", "", `${doc.version_count} version${doc.version_count === 1 ? "" : "s"}`));
    meta.append(el("span", "", `Source: ${doc.source_type || "text"}`));
    item.append(meta);

    const actions = el("div", "mt-5 flex flex-wrap gap-2");
    actions.append(button("Open", "secondary", () => void openDocument(doc.id), { size: "sm" }));
    actions.append(button("Delete", "danger", () => void deleteDocument(doc.id, doc.title), { size: "sm" }));
    item.append(actions);
    return item;
  }

  async function load(): Promise<void> {
    setButtonLoading(refreshBtn, true, "Loading...");
    try {
      const res = await api.documents(100);
      documents = res.documents;
      render();
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(refreshBtn, false); refreshBtn.textContent = "Refresh"; }
  }

  async function deleteDocument(id: number, title: string): Promise<void> {
    const ok = await confirmDialog(`Delete "${title}"? This removes the document and its history from this workspace.`, "Delete", true);
    if (!ok) return;
    try { await api.deleteDocument(id); toast("Document deleted.", "success"); await load(); }
    catch (err) { toast(errorMessage(err), "error"); }
  }

  async function openDocument(id: number): Promise<void> {
    try {
      const doc = await api.document(id);
      let job: JobDetail | null = null;
      if (doc.jobs?.length) job = await api.job(doc.jobs[0].id).catch(() => null);

      clear(root);
      root.append(pageHead("Document", doc.title));
      const backRow = el("div", "mb-5");
      backRow.append(button("← Back to history", "ghost", () => void renderHistory(root), { size: "sm" }));
      root.append(backRow);

      const grid = el("div", "workspace-grid");
      grid.append(textPanel("Original", job?.input_text ?? doc.content ?? ""));
      grid.append(textPanel("Humanized output", job?.output_text ?? "No humanized output yet."));
      root.append(grid);

      if (doc.versions?.length) {
        const vCard = card("mt-6");
        vCard.append(el("h3", "text-base font-semibold text-[var(--color-text)] mb-4", "Versions"));
        const vList = el("div", "space-y-2");
        for (const v of doc.versions) {
          const row = el("div", "flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] px-3 py-2 text-sm");
          row.append(el("span", "text-[var(--color-text)]", `${v.version_type} · ${v.word_count.toLocaleString()} words`));
          row.append(el("span", "text-xs text-[var(--color-text-subtle)]", formatDate(v.created_at)));
          vList.append(row);
        }
        vCard.append(vList);
        root.append(vCard);
      }
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  function textPanel(title: string, value: string): HTMLElement {
    const p = card("flex flex-col min-w-0");
    p.append(el("h3", "text-base font-semibold text-[var(--color-text)] mb-3", title));
    const ta = el("textarea", "field-textarea min-h-[300px] flex-1 bg-[var(--color-cornsilk-600)]") as HTMLTextAreaElement;
    ta.readOnly = true; ta.value = value;
    p.append(ta);
    return p;
  }

  searchInput.addEventListener("input", render);
  filterSel.addEventListener("change", render);
  sortSel.addEventListener("change", render);
  await load();
}
