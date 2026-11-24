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
  icon: string;
  page: Page;
}

const ROUTES: Route[] = [
  { hash: "#/humanize",   label: "Humanize",        helper: "Rewrite and refine",   icon: ICONS.humanize,   page: renderHumanize },
  { hash: "#/plagiarism", label: "Similarity Check", helper: "Local and web checks", icon: ICONS.plagiarism, page: renderPlagiarism },
  { hash: "#/detector",   label: "Style Signal",    helper: "Named writing signals", icon: ICONS.detector,   page: renderDetector },
  { hash: "#/history",    label: "History",         helper: "Documents and jobs",   icon: ICONS.history,    page: renderHistory },
  { hash: "#/settings",   label: "Settings",        helper: "Providers and preferences", icon: ICONS.settings, page: renderSettings },
];

const DEFAULT_HASH = "#/humanize";
const COLLAPSE_KEY = "phrasia:sidebar-collapsed";

const routeFor = (hash: string): Route => ROUTES.find((r) => r.hash === hash) ?? ROUTES[0]!;
const isCollapsed = (): boolean => { try { return localStorage.getItem(COLLAPSE_KEY) === "1"; } catch { return false; } };
const setCollapsed = (v: boolean): void => { try { localStorage.setItem(COLLAPSE_KEY, v ? "1" : "0"); } catch { /* ignore */ } };

function closeMobileDrawer(): void {
  document.getElementById("mobile-drawer")?.classList.remove("open");
  document.getElementById("mobile-drawer-backdrop")?.classList.remove("open");
  document.getElementById("mobile-menu-btn")?.setAttribute("aria-expanded", "false");
  document.getElementById("mobile-drawer")?.setAttribute("aria-hidden", "true");
}
function openMobileDrawer(): void {
  document.getElementById("mobile-drawer")?.classList.add("open");
  document.getElementById("mobile-drawer-backdrop")?.classList.add("open");
  document.getElementById("mobile-menu-btn")?.setAttribute("aria-expanded", "true");
  document.getElementById("mobile-drawer")?.setAttribute("aria-hidden", "false");
  (document.getElementById("mobile-drawer-close") as HTMLButtonElement | null)?.focus();
}

function navItem(route: Route, activeHash: string, onNavigate?: () => void): HTMLAnchorElement {
  const active = route.hash === activeHash;
  const a = el("a", `nav-item${active ? " active" : ""}`) as HTMLAnchorElement;
  a.href = route.hash;
  a.dataset.tooltip = route.label;
  if (active) a.setAttribute("aria-current", "page");
  const iconWrap = el("span", "inline-flex shrink-0");
  iconWrap.innerHTML = route.icon;
  const labelWrap = el("span", "nav-label-wrap min-w-0 flex-1");
  labelWrap.append(el("span", "nav-label block", route.label));
  labelWrap.append(el("span", "nav-desc", route.helper));
  a.append(iconWrap, labelWrap);
  a.addEventListener("click", () => { onNavigate?.(); });
  return a;
}

function buildSidebar(activeHash: string): void {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  sidebar.replaceChildren();
  const collapsed = isCollapsed();
  sidebar.classList.toggle("collapsed", collapsed);

  // Brand + collapse toggle (toggle replaces P mark)
  const brand = el("div", "sidebar-brand");
  const brandText = el("div", "sidebar-brand-text");
  brandText.append(el("div", "sidebar-brand-name", "Phrasia"), el("div", "sidebar-brand-tag", "Words, Refined."));

  const toggle = el("button", "sidebar-toggle");
  toggle.type = "button";
  toggle.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
  toggle.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
  toggle.innerHTML = collapsed ? ICONS.expand : ICONS.collapse;
  toggle.addEventListener("click", () => {
    const next = !isCollapsed();
    setCollapsed(next);
    buildSidebar(window.location.hash || DEFAULT_HASH);
  });

  const brandLeft = el("div", "flex items-center gap-3 min-w-0");
  brandLeft.append(toggle, brandText);
  brand.append(brandLeft);
  sidebar.append(brand);

  // Nav
  const nav = el("nav", "sidebar-nav");
  nav.setAttribute("aria-label", "Primary");
  for (const route of ROUTES) nav.append(navItem(route, activeHash));
  sidebar.append(nav);

  // Footer
  const footer = el("div", "sidebar-footer");
  footer.append(el("div", "", "Local, private, single-owner."));
  footer.append(el("div", "mt-1 text-[#88994f]/80", "Your writing stays on this machine."));
  sidebar.append(footer);
}

function buildMobileDrawer(activeHash: string): void {
  const nav = document.getElementById("mobile-drawer-nav");
  if (!nav) return;
  nav.replaceChildren();
  for (const route of ROUTES) nav.append(navItem(route, activeHash, closeMobileDrawer));
}

async function navigate(): Promise<void> {
  const hash = window.location.hash || DEFAULT_HASH;
  const route = routeFor(hash);
  if (hash !== route.hash) { window.location.hash = route.hash; return; }

  document.title = `${route.label} · Phrasia`;
  buildSidebar(route.hash);
  buildMobileDrawer(route.hash);
  closeMobileDrawer();

  const view = document.getElementById("view");
  if (!view) return;
  view.replaceChildren();
  try {
    await route.page(view);
  } catch (error) {
    view.append(
      el("h1", "page-title", "Something went wrong"),
      el("p", "mt-3 text-[var(--color-danger)]", error instanceof Error ? error.message : String(error)),
    );
  }
}

// Mobile drawer wiring
document.getElementById("mobile-menu-btn")?.addEventListener("click", openMobileDrawer);
document.getElementById("mobile-drawer-close")?.addEventListener("click", closeMobileDrawer);
document.getElementById("mobile-drawer-backdrop")?.addEventListener("click", closeMobileDrawer);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMobileDrawer(); });

window.addEventListener("hashchange", () => void navigate());
if (!window.location.hash) {
  history.replaceState(null, "", `${window.location.pathname}${window.location.search}${DEFAULT_HASH}`);
}
void navigate();
