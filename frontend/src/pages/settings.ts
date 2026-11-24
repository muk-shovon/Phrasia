import { api, errorMessage } from "../api";
import type { ProviderSetting, SettingsResponse } from "../types";
import {
  badge, button, card, clear, confirmDialog, el, fieldWrap, getToggle, input, pageHead,
  setButtonLoading, toast, toggle,
} from "../ui";

export async function renderSettings(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead("Settings", "Manage providers, model configurations, API connections, and application preferences."),
  );

  const providersSection = el("section", "mb-8");
  providersSection.append(el("h2", "text-lg font-semibold text-[var(--color-text)] mb-4", "Providers"));
  const providersGrid = el("div", "grid gap-5 xl:grid-cols-2");
  providersSection.append(providersGrid);
  root.append(providersSection);

  const prefHost = el("section");
  root.append(prefHost);

  async function load(): Promise<void> {
    try {
      const settings = await api.settings();
      clear(providersGrid);
      for (const p of settings.providers) providersGrid.append(providerCard(p, load));
      clear(prefHost);
      prefHost.append(preferredSection(settings, load));
    } catch (err) { toast(errorMessage(err), "error"); }
  }

  await load();
}

function providerCard(p: ProviderSetting, reload: () => Promise<void>): HTMLElement {
  const c = card("flex flex-col min-w-0");
  const head = el("div", "flex flex-wrap items-start justify-between gap-3 mb-4");
  const nameWrap = el("div");
  nameWrap.append(el("h3", "text-lg font-semibold text-[var(--color-text)]", p.name));
  nameWrap.append(el("p", "text-xs text-[var(--color-text-subtle)] mt-0.5", p.anonymous ? "Anonymous / free endpoint" : (p.requires_key ? "API key required" : "Configurable provider")));
  head.append(nameWrap);
  head.append(p.configured ? badge("Configured", "success") : badge("Not configured", "neutral"));
  c.append(head);

  const meta = el("div", "grid grid-cols-2 gap-3 mb-5 text-sm");
  meta.append(metaItem("Model", p.model || "Default"));
  meta.append(metaItem("Rate limit", `${p.rate_limit_requests_per_minute}/min`));
  meta.append(metaItem("Source", p.source === "saved" ? "Saved settings" : "None"));
  meta.append(metaItem("Status", p.enabled ? "Enabled" : "Disabled"));
  c.append(meta);

  // API key
  let keyInput: HTMLInputElement | null = null;
  if (p.requires_key || p.anonymous) {
    const keyWrap = el("div", "mb-4");
    keyWrap.append(el("label", "field-label", "API key"));
    const row = el("div", "flex gap-2");
    keyInput = input("password", p.masked_key ? `Saved: ${p.masked_key}` : (p.anonymous ? "Optional — not required" : "Enter API key"));
    keyInput.autocomplete = "off";
    const showBtn = button("Show", "ghost", () => {
      if (!keyInput) return;
      const showing = keyInput.type === "text";
      keyInput.type = showing ? "password" : "text";
      showBtn.textContent = showing ? "Show" : "Hide";
      showBtn.setAttribute("aria-label", showing ? "Show API key" : "Hide API key");
    }, { size: "sm" });
    showBtn.setAttribute("aria-label", "Show API key");
    row.append(keyInput, showBtn);
    keyWrap.append(row);
    keyWrap.append(el("p", "mt-1.5 text-xs text-[var(--color-text-subtle)]", "Leave blank to keep the currently saved key."));
    c.append(keyWrap);
  }

  // Model
  const modelWrap = fieldWrap("Model name", (() => {
    const m = input("text", p.model || "Model name");
    m.value = p.model || "";
    m.dataset.role = "model";
    return m;
  })());
  c.append(modelWrap);

  // Base URL (if present/customizable) - keep functionality
  const baseWrap = fieldWrap("Base URL", (() => {
    const b = input("text", p.base_url || "https://...");
    b.value = p.base_url || "";
    b.dataset.role = "base";
    return b;
  })(), "Advanced: custom OpenAI-compatible endpoint. Leave as default unless you know you need to change it.");
  baseWrap.classList.add("mt-4");
  c.append(baseWrap);

  // Enabled toggle
  const toggleRow = el("div", "mt-5 flex items-center justify-between gap-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-cornsilk-600)] px-4 py-3");
  const toggleLabel = el("div");
  toggleLabel.append(el("p", "text-sm font-medium text-[var(--color-text)]", "Provider enabled"));
  toggleLabel.append(el("p", "text-xs text-[var(--color-text-subtle)]", "Disabled providers are skipped during routing."));
  const enabledToggle = toggle(p.enabled !== 0, `Enable ${p.name}`);
  toggleRow.append(toggleLabel, enabledToggle);
  c.append(toggleRow);

  // Connection status
  const statusLine = el("div", "mt-4 text-sm text-[var(--color-text-muted)] min-h-[1.5rem]");
  statusLine.setAttribute("aria-live", "polite");
  c.append(statusLine);

  // Actions
  const actions = el("div", "mt-5 flex flex-wrap gap-2");
  const saveBtn = button("Save", "primary", () => void save());
  const testBtn = button("Test connection", "secondary", () => void testConn());
  const clearBtn = button("Clear key", "danger", () => void clearKey());
  actions.append(saveBtn, testBtn, clearBtn);
  c.append(actions);

  async function save(): Promise<void> {
    setButtonLoading(saveBtn, true, "Saving...");
    try {
      const modelVal = (c.querySelector('[data-role="model"]') as HTMLInputElement | null)?.value.trim() ?? "";
      const baseVal = (c.querySelector('[data-role="base"]') as HTMLInputElement | null)?.value.trim() ?? "";
      const keyVal = keyInput?.value.trim() ?? "";
      const payload: { api_key?: string; model?: string; base_url?: string; enabled?: boolean } = {
        model: modelVal || undefined,
        base_url: baseVal || undefined,
        enabled: getToggle(enabledToggle),
      };
      if (keyVal) payload.api_key = keyVal;
      await api.saveProvider(p.id, payload);
      toast(`${p.name} settings saved.`, "success");
      await reload();
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(saveBtn, false); saveBtn.textContent = "Save"; }
  }

  async function testConn(): Promise<void> {
    setButtonLoading(testBtn, true, "Testing...");
    statusLine.textContent = "Testing connection...";
    statusLine.className = "mt-4 text-sm text-[var(--color-text-muted)] min-h-[1.5rem]";
    try {
      const result = await api.testProvider(p.id);
      statusLine.textContent = result.message;
      statusLine.className = `mt-4 text-sm min-h-[1.5rem] ${result.ok ? "text-[var(--color-forest-600)]" : "text-[var(--color-danger)]"}`;
      toast(result.ok ? "Connection successful." : result.message, result.ok ? "success" : "error");
    } catch (err) {
      const msg = errorMessage(err);
      statusLine.textContent = msg;
      statusLine.className = "mt-4 text-sm text-[var(--color-danger)] min-h-[1.5rem]";
      toast(msg, "error");
    } finally { setButtonLoading(testBtn, false); testBtn.textContent = "Test connection"; }
  }

  async function clearKey(): Promise<void> {
    const ok = await confirmDialog(`Clear the saved API key for ${p.name}?`, "Clear key", true);
    if (!ok) return;
    try { await api.clearProviderKey(p.id); toast("API key cleared.", "success"); await reload(); }
    catch (err) { toast(errorMessage(err), "error"); }
  }

  return c;
}

function metaItem(label: string, value: string): HTMLElement {
  const w = el("div", "rounded-md bg-[var(--color-cornsilk-600)] px-3 py-2 border border-[var(--color-border)]");
  w.append(el("div", "text-[11px] uppercase tracking-wide text-[var(--color-text-subtle)]", label));
  w.append(el("div", "text-sm font-medium text-[var(--color-text)] mt-0.5 truncate", value));
  return w;
}

function preferredSection(settings: SettingsResponse, reload: () => Promise<void>): HTMLElement {
  const c = card();
  c.append(el("h2", "text-lg font-semibold text-[var(--color-text)]", "Preferred provider"));
  c.append(el("p", "mt-1 text-sm text-[var(--color-text-muted)] mb-4", "Choose which provider Phrasia tries first when humanizing. Catalog order is used when no preference is set."));

  const row = el("div", "flex flex-col sm:flex-row gap-3 sm:items-end max-w-xl");
  const selWrap = el("div", "flex-1");
  selWrap.append(el("label", "field-label", "Preferred provider"));
  const sel = el("select", "field-select") as HTMLSelectElement;
  const none = el("option", "", "Catalog order (default)") as HTMLOptionElement; none.value = ""; sel.append(none);
  for (const p of settings.providers) { const o = el("option", "", p.name) as HTMLOptionElement; o.value = p.id; sel.append(o); }
  sel.value = settings.preferred_provider ?? "";
  selWrap.append(sel);
  const save = button("Save preference", "primary", () => void savePref());
  row.append(selWrap, save);
  c.append(row);

  async function savePref(): Promise<void> {
    setButtonLoading(save, true, "Saving...");
    try { await api.savePreferences(sel.value || null); toast("Preferred provider saved.", "success"); await reload(); }
    catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(save, false); save.textContent = "Save preference"; }
  }
  return c;
}
