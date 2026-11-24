import { errorMessage } from "./api";

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------
export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function clear(node: HTMLElement): void {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function setDraft(text: string): void {
  try { sessionStorage.setItem("phrasia:draft", text); } catch { /* ignore */ }
}
export function takeDraft(): string {
  try {
    const v = sessionStorage.getItem("phrasia:draft") ?? "";
    sessionStorage.removeItem("phrasia:draft");
    return v;
  } catch { return ""; }
}

export function wordCount(value: string): number {
  const t = value.trim();
  return t ? t.split(/\s+/).length : 0;
}
export function formatNumber(value: number): string { return value.toLocaleString(); }
export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}
export function formatDateShort(value: string | null | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Icons (inline SVG, 20x20, stroke)
// ---------------------------------------------------------------------------
const ico = (d: string, extra = "") =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="shrink-0" ${extra}>${d}</svg>`;

export const ICONS = {
  humanize: ico('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
  plagiarism: ico('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/><path d="M8 11h6"/>'),
  detector: ico('<path d="M12 3v18"/><path d="M3 12h18"/><circle cx="12" cy="12" r="7"/>'),
  history: ico('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>'),
  menu: ico('<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>'),
  close: ico('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
  collapse: ico('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/><path d="m15 10-2 2 2 2"/>'),
  expand: ico('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/><path d="m14 10 2 2-2 2"/>'),
  copy: ico('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
  download: ico('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>'),
  check: ico('<path d="M20 6 9 17l-5-5"/>'),
  search: ico('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  trash: ico('<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'),
  eye: ico('<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>'),
  eyeOff: ico('<path d="M10.7 5.1A10.9 10.9 0 0 1 12 5c7 0 10 7 10 7a15.7 15.7 0 0 1-4.1 4.9"/><path d="M6.2 6.2C3.3 8.2 2 12 2 12s3 7 10 7a10.8 10.8 0 0 0 5.8-1.6"/><line x1="2" x2="22" y1="2" y2="22"/>'),
  plus: ico('<path d="M12 5v14"/><path d="M5 12h14"/>'),
};

// ---------------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------------
type BtnVariant = "primary" | "secondary" | "danger" | "ghost";
interface BtnOpts { disabled?: boolean; className?: string; type?: "button" | "submit"; title?: string; icon?: string; size?: "sm" | "md"; }

export function button(
  label: string,
  variant: BtnVariant = "secondary",
  onClick?: (ev: MouseEvent) => void,
  opts: BtnOpts = {},
): HTMLButtonElement {
  const cls = ["btn", `btn-${variant}`, opts.size === "sm" ? "btn-sm" : "", opts.className ?? ""].filter(Boolean).join(" ");
  const node = el("button", cls);
  node.type = opts.type ?? "button";
  node.disabled = opts.disabled ?? false;
  if (opts.title) node.title = opts.title;
  if (opts.icon) {
    const iconWrap = document.createElement("span");
    iconWrap.className = "inline-flex";
    iconWrap.innerHTML = opts.icon;
    node.append(iconWrap);
  }
  node.append(document.createTextNode(label));
  if (onClick) node.addEventListener("click", onClick);
  return node;
}

export function iconButton(icon: string, label: string, onClick?: (ev: MouseEvent) => void, variant: BtnVariant = "ghost"): HTMLButtonElement {
  const node = el("button", `btn btn-${variant} btn-icon`);
  node.type = "button";
  node.title = label;
  node.setAttribute("aria-label", label);
  node.innerHTML = icon;
  if (onClick) node.addEventListener("click", onClick);
  return node;
}

export function setButtonLoading(btn: HTMLButtonElement, loading: boolean, label?: string): void {
  btn.disabled = loading;
  btn.dataset.loading = loading ? "1" : "";
  if (loading) {
    if (!btn.dataset.originalLabel) btn.dataset.originalLabel = btn.textContent ?? "";
    btn.innerHTML = `<span class="spinner" aria-hidden="true"></span><span>${label ?? btn.dataset.originalLabel}</span>`;
  } else {
    const orig = btn.dataset.originalLabel;
    if (orig) { btn.textContent = orig; delete btn.dataset.originalLabel; }
  }
}

// ---------------------------------------------------------------------------
// Inputs
// ---------------------------------------------------------------------------
export function fieldWrap(label: string, control: HTMLElement, hint?: string): HTMLElement {
  const wrap = el("div");
  const id = control.id || `field-${Math.random().toString(36).slice(2, 9)}`;
  control.id = id;
  const lab = el("label", "field-label", label);
  lab.htmlFor = id;
  wrap.append(lab, control);
  if (hint) wrap.append(el("p", "mt-1.5 text-xs text-[var(--color-text-subtle)]", hint));
  return wrap;
}

export function input(type = "text", placeholder = ""): HTMLInputElement {
  const node = el("input", "field-input");
  node.type = type;
  node.placeholder = placeholder;
  return node;
}

export function textarea(placeholder = "", rows = 10): HTMLTextAreaElement {
  const node = el("textarea", "field-textarea");
  node.placeholder = placeholder;
  node.rows = rows;
  return node;
}

export function select(options: Array<{ value: string; label: string }>, className = ""): HTMLSelectElement {
  const node = el("select", `field-select ${className}`.trim());
  for (const opt of options) {
    const o = el("option", "", opt.label);
    o.value = opt.value;
    node.append(o);
  }
  return node;
}

export function toggle(checked = false, ariaLabel = "Toggle"): HTMLButtonElement {
  const node = el("button", "toggle");
  node.type = "button";
  node.role = "switch";
  node.setAttribute("aria-checked", checked ? "true" : "false");
  node.setAttribute("aria-label", ariaLabel);
  node.addEventListener("click", () => {
    if (node.disabled) return;
    const next = node.getAttribute("aria-checked") !== "true";
    node.setAttribute("aria-checked", next ? "true" : "false");
  });
  return node;
}

export function setToggle(node: HTMLButtonElement, checked: boolean): void {
  node.setAttribute("aria-checked", checked ? "true" : "false");
}
export function getToggle(node: HTMLButtonElement): boolean {
  return node.getAttribute("aria-checked") === "true";
}

// ---------------------------------------------------------------------------
// Layout & display
// ---------------------------------------------------------------------------
export function pageHead(title: string, subtitle: string): HTMLElement {
  const wrap = el("header", "page-header");
  wrap.append(el("h1", "page-title", title));
  if (subtitle) wrap.append(el("p", "page-subtitle", subtitle));
  return wrap;
}

export function card(className = ""): HTMLElement {
  return el("section", `card p-5 md:p-6 ${className}`.trim());
}

export function badge(label: string, variant: "neutral" | "accent" | "success" | "warn" | "danger" = "neutral"): HTMLElement {
  return el("span", `badge badge-${variant}`, label);
}

export function emptyState(title: string, detail: string, icon = "◌"): HTMLElement {
  const wrap = el("div", "flex flex-col items-center justify-center py-12 px-4 text-center");
  wrap.append(
    el("div", "mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-cornsilk-600)] text-xl text-[var(--color-text-subtle)]", icon),
    el("p", "text-base font-semibold text-[var(--color-text)]", title),
    el("p", "mt-1 max-w-sm text-sm text-[var(--color-text-muted)]", detail),
  );
  return wrap;
}

export function skeleton(height = "1rem", width = "100%"): HTMLElement {
  const s = el("div", "skeleton");
  s.style.height = height;
  s.style.width = width;
  return s;
}

export function loadingState(label = "Loading…"): HTMLElement {
  const wrap = el("div", "flex items-center gap-3 py-8 text-[var(--color-text-muted)]");
  wrap.append(el("span", "spinner"), el("span", "text-sm", label));
  wrap.setAttribute("role", "status");
  wrap.setAttribute("aria-live", "polite");
  return wrap;
}

export function hr(): HTMLElement {
  return el("hr", "my-6 border-0 border-t border-[var(--color-border)]");
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------
export function toast(message: string, tone: "success" | "error" | "info" = "info"): void {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const node = el("div", `toast toast-${tone}`);
  node.setAttribute("role", tone === "error" ? "alert" : "status");
  node.append(el("span", "flex-1", message));
  root.append(node);
  window.setTimeout(() => {
    node.style.opacity = "0";
    node.style.transition = "opacity 150ms ease";
    window.setTimeout(() => node.remove(), 160);
  }, 3200);
}

export function reportError(target: HTMLElement, err: unknown): void {
  clear(target);
  const box = el("div", "rounded-lg border border-[rgba(122,59,46,0.2)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger)]");
  box.textContent = errorMessage(err);
  target.append(box);
}

export async function confirmDialog(message: string, confirmLabel = "Confirm", danger = false): Promise<boolean> {
  return new Promise((resolve) => {
    const backdrop = el("div", "fixed inset-0 z-[60] flex items-center justify-center bg-[rgba(16,21,9,0.45)] p-4");
    const dialog = el("div", "card w-full max-w-md p-6");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.append(el("p", "text-base text-[var(--color-text)] leading-6", message));
    const actions = el("div", "mt-5 flex justify-end gap-3");
    const cancel = button("Cancel", "secondary", () => { backdrop.remove(); resolve(false); });
    const ok = button(confirmLabel, danger ? "danger" : "primary", () => { backdrop.remove(); resolve(true); });
    actions.append(cancel, ok);
    dialog.append(actions);
    backdrop.append(dialog);
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) { backdrop.remove(); resolve(false); } });
    document.body.append(backdrop);
    ok.focus();
  });
}
