import { errorMessage } from "./api";

// ---------------------------------------------------------------------------
// Design system (calm neutrals + one accent, all Tailwind utilities, 16px min)
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Elements
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
  try {
    sessionStorage.setItem("phrasia:draft", text);
  } catch {
    /* storage may be unavailable */
  }
}

export function takeDraft(): string {
  try {
    const value = sessionStorage.getItem("phrasia:draft") ?? "";
    sessionStorage.removeItem("phrasia:draft");
    return value;
  } catch {
    return "";
  }
}

export function hr(): HTMLElement {
  return el("hr", "my-6 border-[#DDE2D6]");
}

// ---------------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------------
export function button(
  label: string,
  variant: "primary" | "secondary" | "ghost" | "danger",
  onClick: () => void,
  opts: { className?: string; disabled?: boolean; icon?: string; busy?: boolean } = {},
): HTMLButtonElement {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1F6B4A]/40 disabled:cursor-not-allowed disabled:opacity-50";
  const variants: Record<string, string> = {
    primary: `bg-[#1F6B4A] text-white hover:bg-[#1A5D3F]`,
    secondary: `border border-[#CFD8C7] text-[#25352A] hover:bg-[#F2F4EE]`,
    ghost: `text-[#1F6B4A] hover:bg-[#F0F3ED]`,
    danger: `border border-[#E4B3B3] text-[#8B2020] hover:bg-[#FBEBEB]`,
  };
  const node = el("button", `${base} ${variants[variant]} ${opts.className ?? ""}`);
  if (opts.disabled) node.disabled = true;
  if (opts.icon) node.append(el("span", "inline-flex", opts.icon));
  node.append(el("span", "", label));
  node.addEventListener("click", onClick);
  return node;
}

export function input(
  label: string,
  opts: {
    placeholder?: string;
    type?: string;
    className?: string;
    value?: string;
    onInput?: (value: string) => void;
    disabled?: boolean;
  } = {},
): HTMLElement {
  const wrapper = el("div", "");
  wrapper.append(
    el("label", "mb-2 block text-sm font-semibold text-[#25352A]", label),
  );
  const node = el(
    "input",
    `w-full rounded-lg border border-[#CFD8C7] bg-[#FFFFFF] px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15 ${opts.className ?? ""}`,
    opts.placeholder,
  );
  if (opts.type) node.type = opts.type;
  if (opts.value !== undefined) (node as HTMLInputElement).value = opts.value;
  if (opts.onInput) node.addEventListener("input", () => opts.onInput?.(node.value));
  if (opts.disabled) node.disabled = true;
  wrapper.append(node);
  return wrapper;
}

export function select(
  label: string,
  options: Array<{ value: string; label: string; disabled?: boolean }>,
  opts: { value?: string; className?: string; onChange?: (value: string) => void } = {},
): HTMLElement {
  const wrapper = el("div", "");
  wrapper.append(el("label", "mb-2 block text-sm font-semibold text-[#25352A]", label));
  const node = el(
    "select",
    `w-full rounded-lg border border-[#CFD8C7] bg-[#FFFFFF] px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15 ${opts.className ?? ""}`,
  );
  for (const option of options) {
    const elOption = el("option", "", option.label);
    elOption.value = option.value;
    if (option.disabled) elOption.disabled = true;
    node.append(elOption);
  }
  if (opts.value !== undefined) node.value = opts.value;
  node.addEventListener("change", () => opts.onChange?.(node.value));
  wrapper.append(node);
  return wrapper;
}

export function toggle(
  label: string,
  checked: boolean,
  opts: { onToggle?: (checked: boolean) => void; className?: string } = {},
): HTMLElement {
  const wrapper = el("label", "flex items-center justify-between gap-4", "");
  wrapper.append(
    el("span", "text-sm font-semibold text-[#25352A]", label),
    el(
      "button",
      `relative h-7 w-13 rounded-full transition ${
        checked ? "bg-[#1F6B4A]" : "bg-[#DCE1D7]"
      } ${opts.className ?? ""}`,
      "",
    ),
  );
  const switchEl = wrapper.lastElementChild as HTMLElement;
  const knob = el(
    "span",
    `absolute top-0.5 left-0.5 h-6 w-6 rounded-full bg-white shadow transition ${
      checked ? "translate-x-6" : ""
    }`,
    "",
  );
  switchEl.append(knob);
  switchEl.addEventListener("click", () => {
    checked = !checked;
    switchEl.classList.toggle("bg-[#1F6B4A]", checked);
    switchEl.classList.toggle("bg-[#DCE1D7]", !checked);
    knob.classList.toggle("translate-x-6", checked);
    opts.onToggle?.(checked);
  });
  return wrapper;
}

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------
export function card(className = ""): HTMLElement {
  return el(
    "section",
    `rounded-xl border border-[#DFE4DB] bg-white p-6 shadow-[0_1px_3px_rgba(20,32,22,0.06)] ${className}`,
  );
}

export function pageHead(title: string, subtitle?: string): HTMLElement {
  const box = el("header", "mb-7");
  box.append(el("h1", "text-3xl font-semibold tracking-tight text-[#16251C]", title));
  if (subtitle) box.append(el("p", "mt-2 text-base leading-6 text-[#5C6C62]", subtitle));
  return box;
}

export function badge(text: string, tone: "accent" | "neutral" | "warn" | "error" | "ok" = "neutral"): HTMLElement {
  const tones: Record<string, string> = {
    accent: "bg-[#E3EDE6] text-[#1F6B4A]",
    neutral: "bg-[#E8EBE5] text-[#4B5B52]",
    warn: "bg-[#FBF1DC] text-[#8A5A12]",
    error: "bg-[#FBE2E2] text-[#8B2020]",
    ok: "bg-[#E3EDE6] text-[#1B5E3B]",
  };
  return el(
    "span",
    `inline-block rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${tones[tone]}`,
    text,
  );
}

export function toast(message: string, kind: "error" | "success" | "info" = "info"): void {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const tone =
    kind === "error"
      ? "border-[#E4B3B3] bg-[#FBEEEB] text-[#7F2A2A]"
      : kind === "success"
        ? "border-[#C7E0D2] bg-[#ECF5ED] text-[#1B5E3B]"
        : "border-[#DCE1D7] bg-white text-[#25352A]";
  const node = el("div", `rounded-lg border px-4 py-3 text-sm shadow-[0_2px_8px_rgba(20,32,22,0.1)] ${tone}`, message);
  root.append(node);
  window.setTimeout(() => node.remove(), 3600);
}

export const ICONS = {
  humanize: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5"><path d="M12 20h0a8 8 0 0 0 8-8c0-2.5-2-5-4.5-7C11 2 11.5 0 9.5 0c-2 0-4.5 1-5 3.5C3 6 1.5 7.5 2 10c1 2 3.5 3.5 6 3.5H12v6z"/></svg>`,
  plagiarism: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5"><path d="M16 10.5l-6-3-3 6.5 9 3.5z"/><path d="M11 19l-5 4h14l-5-4z"/><line x1="3" y1="4.5" x2="21" y2="4.5"/></svg>`,
  detector: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5"><circle cx="12" cy="12" r="9"/><path d="M12 10l2.8 2.8L16 14"/><path d="M8 9.5l4 4.5"/></svg>`,
  history: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M6 6v4l2.5 1.5"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  search: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><circle cx="11" cy="11" r="7"/><line x1="20" y1="20" x2="16" y2="16"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>`,
  play: `<svg viewBox="0 0 24 24" fill="#1F6B4A" class="h-5 w-5"><polygon points="5 3 19 12 5 21"/></svg>`,
  copy: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
  save: `<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M19 21l-7-7-9 9"/><path d="M12 13v6M15 12l-3 3-3-3"/><path d="M8 12H7a3 3 0 0 1 0-6h10"/></svg>`,
};

export function wordCount(text: string): number {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export { errorMessage };
