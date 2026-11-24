import "./style.css";

import { errorMessage } from "./api";
import { renderDetector } from "./pages/detector";
import { renderHistory } from "./pages/history";
import { renderHumanize } from "./pages/humanize";
import { renderPlagiarism } from "./pages/plagiarism";
import { renderSettings } from "./pages/settings";
import { el } from "./ui";

type Page = (root: HTMLElement) => Promise<void>;

interface Route {
  hash: string;
  label: string;
  hint: string;
  page: Page;
}

const ROUTES: Route[] = [
  { hash: "#/humanize", label: "Humanize", hint: "Rewrite and refine", page: renderHumanize },
  { hash: "#/history", label: "History", hint: "Past documents", page: renderHistory },
  { hash: "#/plagiarism", label: "Similarity", hint: "Local reference check", page: renderPlagiarism },
  { hash: "#/detector", label: "Style signal", hint: "Local writing patterns", page: renderDetector },
  { hash: "#/settings", label: "Settings", hint: "Providers and keys", page: renderSettings },
];

const DEFAULT_HASH = "#/humanize";

function routeFor(hash: string): Route {
  return ROUTES.find((route) => route.hash === hash) ?? ROUTES[0]!;
}

function buildSidebar(active: string): void {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  sidebar.replaceChildren();

  const shell = el("div", "flex h-full flex-col");
  const brand = el("div", "px-5 pb-3 pt-5");
  brand.append(
    el("a", "font-serif text-2xl tracking-tight text-white", "Phrasia"),
    el("p", "mt-0.5 text-xs uppercase tracking-[0.18em] text-[#8FA795]", "Words, Refined."),
  );

  const nav = el(
    "nav",
    "flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:px-3",
  );
  for (const route of ROUTES) {
    const isActive = route.hash === active;
    const link = el(
      "a",
      `group min-w-max rounded-lg px-3 py-2 transition md:min-w-0 ${
        isActive
          ? "bg-[#25422F] text-white"
          : "text-[#A9BCAE] hover:bg-[#1B2C22] hover:text-white"
      }`,
    );
    link.href = route.hash;
    link.append(
      el("span", "block text-sm font-medium", route.label),
      el(
        "span",
        `hidden text-[11px] md:block ${
          isActive ? "text-[#C9DCCE]" : "text-[#7C947F] group-hover:text-[#A9BCAE]"
        }`,
        route.hint,
      ),
    );
    nav.append(link);
  }

  const footer = el("div", "mt-auto hidden border-t border-[#24382B] px-5 py-4 md:block");
  footer.append(
    el("p", "text-[11px] leading-5 text-[#7C947F]", "Local only · 127.0.0.1"),
    el("p", "text-[11px] leading-5 text-[#7C947F]", "Keys never leave this machine."),
  );

  shell.append(brand, nav, footer);
  sidebar.append(shell);
}

function renderFailure(root: HTMLElement, error: unknown): void {
  root.append(
    el("h1", "text-2xl font-semibold", "Something went wrong"),
    el("p", "mt-2 max-w-2xl text-sm text-[#7C2323]", errorMessage(error)),
    el(
      "p",
      "mt-4 text-sm text-[#5C6B60]",
      "Make sure the backend is running with `python -m backend.main`.",
    ),
  );
}

async function navigate(): Promise<void> {
  const hash = window.location.hash || DEFAULT_HASH;
  const route = routeFor(hash);
  if (hash !== route.hash) {
    window.location.hash = route.hash;
    return;
  }
  document.title = `${route.label} · Phrasia`;
  buildSidebar(route.hash);

  const view = document.getElementById("view");
  if (!view) return;
  view.replaceChildren();

  try {
    await route.page(view);
  } catch (error) {
    renderFailure(view, error);
  }
}

window.addEventListener("hashchange", () => void navigate());
if (!window.location.hash) {
  history.replaceState(
    null,
    "",
    `${window.location.pathname}${window.location.search}${DEFAULT_HASH}`,
  );
}
void navigate();
