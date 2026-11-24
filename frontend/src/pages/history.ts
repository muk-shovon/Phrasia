import { api, errorMessage } from "../api";
import type { DocumentSummary } from "../types";
import {
  button, card, clear, confirmDialog, el, emptyState, formatDate, pageHead,
  setButtonLoading, toast,
} from "../ui";

type SortKey = "newest" | "oldest" | "title";

export async function renderHistory(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead("History", "Your documents and versions from this workspace."));

  const toolbar = el("div", "card p-4 md:p-5 mb-6");
  const grid = el("div", "grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_180px_auto] lg:items-end");
  const searchWrap = el("div");
  searchWrap.append(el("label", "field-label", "Search documents"));
  const searchInput = el("input", "field-input") as HTMLInputElement;
  searchInput.type = "search";
  searchInput.placeholder = "Search by title or preview...";
  searchWrap.append(searchInput);
  const sortWrap = el("div");
  sortWrap.append(el("label", "field-label", "Sort by"));
  const sortSel = el("select", "field-select") as HTMLSelectElement;
  for (const [v, l] of [["newest", "Newest first"], ["oldest", "Oldest first"], ["title", "Title A-Z"]] as const) {
    const o = el("option", "", l) as HTMLOptionElement; o.value = v; sortSel.append(o);
  }
  sortWrap.append(sortSel);
  const refreshBtn = button("Refresh", "secondary", () => void load(), { size: "sm" });
  const refreshWrap = el("div", "flex items-end");
  refreshWrap.append(refreshBtn);
  grid.append(searchWrap, sortWrap, refreshWrap);
  toolbar.append(grid);
  root.append(toolbar);

  const listHost = el("div", "space-y-4");
  root.append(listHost);
  let documents: DocumentSummary[] = [];

  function render(): void {
    clear(listHost);
    if (!documents.length) {
      listHost.append(emptyState("No history yet", "Documents you rewrite will appear here with their versions.", "?"));
      return;
    }
    const q = searchInput.value.trim().toLowerCase();
    const sort = sortSel.value as SortKey;
    const items = documents
      .filter((d) => !q || d.title.toLowerCase().includes(q) || (d.latest_excerpt ?? "").toLowerCase().includes(q))
      .slice()
      .sort((a, b) => {
        if (sort === "title") return a.title.localeCompare(b.title);
        const da = new Date(a.created_at).getTime();
        const db = new Date(b.created_at).getTime();
        return sort === "oldest" ? da - db : db - da;
      });
    if (!items.length) {
      listHost.append(emptyState("No matching documents", "Try a different search.", "?"));
      return;
    }
    for (const doc of items) {
      const item = card("transition-shadow hover:shadow-[var(--shadow-soft)]");
      const top = el("div", "flex flex-wrap items-start justify-between gap-3");
      const left = el("div", "min-w-0 flex-1");
      left.append(el("h3", "text-base font-semibold text-[var(--color-text)] truncate", doc.title || "Untitled"));
      left.append(el("p", "mt-1 text-sm text-[var(--color-text-muted)] leading-6 line-clamp-2", doc.latest_excerpt || "No preview available."));
      top.append(left);
      item.append(top);
      const meta = el("div", "mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-text-subtle)]");
      meta.append(el("span", "", `Created ${formatDate(doc.created_at)}`));
      meta.append(el("span", "", `${doc.version_count} versions`));
      item.append(meta);
      const actions = el("div", "mt-5 flex flex-wrap gap-2");
      actions.append(button("Open", "secondary", () => void openDocument(doc.id), { size: "sm" }));
      actions.append(button("Delete", "danger", () => void deleteDocument(doc.id, doc.title), { size: "sm" }));
      item.append(actions);
      listHost.append(item);
    }
  }

  async function load(): Promise<void> {
    setButtonLoading(refreshBtn, true, "Loading...");
    try { documents = (await api.documents(100)).documents; render(); }
    catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(refreshBtn, false); refreshBtn.textContent = "Refresh"; }
  }

  async function deleteDocument(id: number, title: string): Promise<void> {
    const ok = await confirmDialog(`Delete "${title}"? This removes the document and its versions from this workspace.`, "Delete", true);
    if (!ok) return;
    try { await api.deleteDocument(id); toast("Document deleted.", "success"); await load(); }
    catch (err) { toast(errorMessage(err), "error"); }
  }

  function textPanel(title: string, value: string): HTMLElement {
    const p = card("flex flex-col min-w-0");
    p.append(el("h3", "text-base font-semibold text-[var(--color-text)] mb-3", title));
    const ta = el("textarea", "field-textarea min-h-[300px] flex-1 bg-[var(--color-cornsilk-600)]") as HTMLTextAreaElement;
    ta.readOnly = true; ta.value = value;
    p.append(ta);
    return p;
  }

  async function openDocument(id: number): Promise<void> {
    try {
      const doc = await api.document(id);
      const source = doc.versions.find((v) => v.version_type === "source")?.content ?? "";
      const result = doc.versions.find((v) => v.version_type === "humanized")?.content ?? "";
      clear(root);
      root.append(pageHead("Document", doc.title));
      const backRow = el("div", "mb-5");
      backRow.append(button("Back to history", "ghost", () => void renderHistory(root), { size: "sm" }));
      root.append(backRow);
      const grid = el("div", "workspace-grid");
      grid.append(textPanel("Original", source));
      grid.append(textPanel("Rewritten output", result));
      root.append(grid);
      const vCard = card("mt-6");
      vCard.append(el("h3", "text-base font-semibold text-[var(--color-text)] mb-4", "Versions"));
      const vList = el("div", "space-y-2");
      for (const v of doc.versions) {
        const row = el("div", "flex flex-wrap items-center justify-between gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] px-3 py-2 text-sm");
        row.append(el("span", "text-[var(--color-text)]", `${v.version_type} - ${v.word_count.toLocaleString()} words`));
        row.append(el("span", "text-xs text-[var(--color-text-subtle)]", formatDate(v.created_at)));
        vList.append(row);
      }
      vCard.append(vList);
      root.append(vCard);
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  searchInput.addEventListener("input", render);
  sortSel.addEventListener("change", render);
  await load();
}
