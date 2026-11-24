import { errorMessage } from "./api";

export const BTN = {
  primary:
    "inline-flex items-center justify-center gap-2 rounded-lg bg-[#1C6B4A] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#15543A] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1C6B4A]/40 disabled:cursor-not-allowed disabled:opacity-50",
  secondary:
    "inline-flex items-center justify-center gap-2 rounded-lg border border-[#D5DCCF] bg-white px-3.5 py-2 text-sm font-medium text-[#25352A] transition hover:bg-[#F2F4EE] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1C6B4A]/25 disabled:opacity-50",
  danger:
    "inline-flex items-center justify-center gap-2 rounded-lg border border-[#E7C9C9] bg-white px-3.5 py-2 text-sm font-medium text-[#8B2020] transition hover:bg-[#FBF0F0] disabled:opacity-50",
  ghost: "text-sm font-semibold text-[#1C6B4A] hover:underline",
} as const;

export const INPUT =
  "w-full rounded-lg border border-[#D5DCCF] bg-white px-3 py-2.5 text-sm text-[#17251C] outline-none transition placeholder:text-[#98A49A] focus:border-[#1C6B4A] focus:ring-2 focus:ring-[#1C6B4A]/15";

export const CARD =
  "rounded-xl border border-[#DDE3D8] bg-white p-5 shadow-[0_1px_2px_rgba(23,37,28,0.04)]";

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-[#E4F1E8] text-[#1B5E3B]",
  running: "bg-[#E5EEF7] text-[#1F4E79]",
  queued: "bg-[#FBF1DC] text-[#8A5A12]",
  paused: "bg-[#EEEDE6] text-[#5E5B4A]",
  failed: "bg-[#F8E7E7] text-[#8B2020]",
  cancelled: "bg-[#EEEDE6] text-[#5E5B4A]",
  pending: "bg-[#EEEDE6] text-[#5E5B4A]",
  error: "bg-[#F8E7E7] text-[#8B2020]",
};

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

export function button(
  label: string,
  variant: keyof typeof BTN,
  onClick: () => void,
): HTMLButtonElement {
  const node = el("button", BTN[variant], label);
  node.type = "button";
  node.addEventListener("click", onClick);
  return node;
}

export function setBusy(target: HTMLButtonElement, busy: boolean, busyLabel = "Working…"): void {
  if (busy) {
    target.dataset.label ??= target.textContent ?? "";
    target.textContent = busyLabel;
    target.disabled = true;
  } else {
    target.textContent = target.dataset.label ?? target.textContent;
    target.disabled = false;
  }
}

export function pageHeader(title: string, subtitle: string): HTMLElement {
  const header = el("header", "mb-6");
  header.append(
    el("h1", "text-2xl font-semibold tracking-tight text-[#17251C] md:text-3xl", title),
    el("p", "mt-1.5 max-w-3xl text-sm leading-6 text-[#5C6B60]", subtitle),
  );
  return header;
}

export function field(label: string, control: HTMLElement, hint?: string): HTMLElement {
  const wrapper = el("label", "block");
  wrapper.append(el("span", "mb-1.5 block text-sm font-medium text-[#25352A]", label));
  wrapper.append(control);
  if (hint) wrapper.append(el("span", "mt-1.5 block text-xs text-[#7A877C]", hint));
  return wrapper;
}

export function statusBadge(status: string): HTMLElement {
  const classes = STATUS_STYLES[status] ?? "bg-[#EEEDE6] text-[#5E5B4A]";
  return el(
    "span",
    `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${classes}`,
    status,
  );
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function emptyState(message: string): HTMLElement {
  return el(
    "p",
    "rounded-lg border border-dashed border-[#D5DCCF] bg-[#FAFBF7] px-4 py-8 text-center text-sm text-[#7A877C]",
    message,
  );
}

export function notice(message: string, tone: "info" | "warn" = "info"): HTMLElement {
  const classes =
    tone === "warn"
      ? "border-[#EBD9B5] bg-[#FDF7EA] text-[#7A5410]"
      : "border-[#D5E4DA] bg-[#F1F7F3] text-[#2C5B41]";
  return el("p", `rounded-lg border px-3.5 py-2.5 text-sm leading-6 ${classes}`, message);
}

export function toast(message: string, kind: "info" | "success" | "error" = "info"): void {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const tone =
    kind === "error"
      ? "border-[#E7C9C9] bg-[#FBF0F0] text-[#7C2323]"
      : kind === "success"
        ? "border-[#CFE3D6] bg-[#F1F8F3] text-[#1B5E3B]"
        : "border-[#D5DCCF] bg-white text-[#25352A]";
  const node = el(
    "div",
    `pointer-events-auto rounded-lg border px-4 py-3 text-sm shadow-lg ${tone}`,
    message,
  );
  root.append(node);
  window.setTimeout(() => node.remove(), 4_200);
}

export function reportError(error: unknown): void {
  toast(errorMessage(error), "error");
}

export async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard.", "success");
  } catch {
    toast("Could not access the clipboard. Select the text and copy manually.", "error");
  }
}

export function attachFileInput(
  trigger: HTMLButtonElement,
  accept: string,
  onFile: (file: File) => void,
): void {
  const input = el("input");
  input.type = "file";
  input.accept = accept;
  input.className = "hidden";
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (file) onFile(file);
    input.value = "";
  });
  trigger.addEventListener("click", () => input.click());
  trigger.after(input);
}

const DRAFT_KEY = "phrasia:draft";

export function setDraft(text: string): void {
  try {
    localStorage.setItem(DRAFT_KEY, text);
  } catch {
    /* storage may be unavailable; the draft just is not shared */
  }
}

export function takeDraft(): string {
  try {
    const value = localStorage.getItem(DRAFT_KEY) ?? "";
    localStorage.removeItem(DRAFT_KEY);
    return value;
  } catch {
    return "";
  }
}

export function wordCount(text: string): number {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}
