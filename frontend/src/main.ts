import "./style.css";

import { ICONS, el } from "./ui";
import { renderDetector } from "./pages/detector";
import { renderHistory } from "./pages/history";
import { renderHumanize } from "./pages/humanize";
import { renderPlagiarism } from "./pages/plagiarism";
import { renderSettings } from "./pages/settings";

type Page = (root: HTMLElement) => Promise<void>;

interface Route {
  hash: string;
  label: string;
  helper: string;
  page: Page;
  mobileIcon?: string;
}

const ROUTES: Route[] = [
  {
    hash: "#/humanize",
    label: "Humanize",
    helper: "Rewrite and refine text with an external model",
    page: renderHumanize,
    mobileIcon: ICONS.humanize,
  },
  {
    hash: "#/plagiarism",
    label: "Similarity",
    helper: "Local reference library check + web search",
    page: renderPlagiarism,
    mobileIcon: ICONS.plagiarism,
  },
  {
    hash: "#/detector",
    label: "Style signal",
    helper: "Local style analysis of your writing",
    page: renderDetector,
    mobileIcon: ICONS.detector,
  },
  {
    hash: "#/history",
    label: "History",
    helper: "Your documents and versions",
    page: renderHistory,
    mobileIcon: ICONS.history,
  },
  {
    hash: "#/settings",
    label: "Settings",
    helper: "Providers, keys and app info",
    page: renderSettings,
    mobileIcon: ICONS.settings,
  },
];

const DEFAULT_HASH = "#/humanize";

const routeFor = (hash: string): Route =>
  ROUTES.find((route) => route.hash === hash) ?? ROUTES[0]!;

function routeTitle(hash: string): string {
  const route = routeFor(hash);
  return hash === "#/settings" ? "Settings" : route.label;
}

// ---------------------------------------------------------------------------
// Sidebar (desktop)
// ---------------------------------------------------------------------------
function buildSidebar(activeHash: string): void {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  sidebar.replaceChildren();

  const shell = el("div", "flex h-full flex-col");
  const brand = el("div", "border-b border-[#223222] px-6 py-6");
  brand.append(
    el("span", "font-serif text-2xl tracking-tight text-[#E7EDE6]", "Phrasia"),
    el("span", "mt-1 block text-[11px] uppercase tracking-[0.22em] text-[#8FA795]", "Words, Refined."),
  );
  shell.append(brand);

  const nav = el("nav", "flex flex-1 flex-col gap-1 px-3 py-4");
  for (const route of ROUTES) {
    const isActive = route.hash === activeHash;
    const link = el(
      "a",
      `flex items-center gap-3 rounded-lg px-3 py-2.5 transition ${
        isActive
          ? "bg-[#25422F] text-white"
          : "text-[#B6C3AC] hover:bg-[#1E3224] hover:text-white"
      }`,
    );
    link.href = route.hash;
    link.innerHTML = route.mobileIcon ?? "";
    const labelBox = el("span", "min-w-0 flex-1", route.label);
    if (!isActive) labelBox.classList.add("hidden", "md:block");
    link.append(labelBox, el("span", `hidden text-[11px] text-[#A9B7AE] md:${isActive ? "text-white" : "block"}`, route.helper));
    nav.append(link);
  }
  shell.append(nav);

  const footer = el("div", "border-t border-[#223222] px-6 py-4");
  footer.append(
    el("p", "text-[12px] leading-5 text-[#8FA795]", "Local, private, single-owner."),
    el("p", "mt-1 text-[12px] leading-5 text-[#8FA795]", "Powered by your choice of free, anonymous LLM APIs."),
  );
  shell.append(footer);

  sidebar.append(shell);
}

// ---------------------------------------------------------------------------
// Mobile tab bar (bottom on small screens)
// ---------------------------------------------------------------------------
function buildMobileTabs(activeHash: string): void {
  const root = document.getElementById("mobile-tabs");
  if (!root) return;
  root.replaceChildren();
  const tabs = ROUTES;
  for (const route of tabs) {
    const isActive = route.hash === activeHash;
    const link = el(
      "a",
      `flex min-w-0 flex-1 flex-col items-center gap-0.5 px-1 py-2 transition ${
        isActive ? "text-[#1F6B4A]" : "text-[#5C6C62]"
      }`,
    );
    link.href = route.hash;
    link.append(el("span", "", route.mobileIcon), el("span", "mt-0.5 text-[10px] font-medium", route.label));
    root.append(link);
  }
}

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------
async function navigate(): Promise<void> {
  const hash = window.location.hash || DEFAULT_HASH;
  const route = routeFor(hash);
  if (hash !== route.hash) {
    window.location.hash = route.hash;
    return;
  }
  document.title = `${routeTitle(hash)} · Phrasia`;
  buildSidebar(route.hash);
  buildMobileTabs(route.hash);

  const view = document.getElementById("view");
  if (!view) return;
  view.replaceChildren();
  try {
    await route.page(view);
  } catch (error) {
    view.append(
      el("h1", "text-xl font-semibold", "Something went wrong"),
      el("p", "mt-2 text-base leading-6 text-[#8B2020]", error instanceof Error ? error.message : String(error)),
    );
  }
}

window.addEventListener("hashchange", () => void navigate());
if (!window.location.hash) {
  history.replaceState(null, "", `${window.location.pathname}${window.location.search}${DEFAULT_HASH}`);
}
void navigate();
