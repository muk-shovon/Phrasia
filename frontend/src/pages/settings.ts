import { api, errorMessage } from "../api";
import type { AppSettings, ProviderInfo } from "../types";
import {
  badge, button, card, el, fieldWrap, getToggle, input, pageHead, select,
  setButtonLoading, toast, toggle,
} from "../ui";

function linkButton(label: string, href: string): HTMLAnchorElement {
  const anchor = el("a", "text-sm font-medium text-[var(--color-accent)] underline underline-offset-2", label);
  anchor.href = href;
  anchor.target = "_blank";
  anchor.rel = "noreferrer noopener";
  return anchor;
}

export async function renderSettings(root: HTMLElement): Promise<void> {
  root.replaceChildren(pageHead(
    "Settings",
    "Choose where rewriting runs. Only the text you rewrite leaves this machine, and only to the provider you pick.",
  ));
  const host = el("div");
  root.append(host);

  let settings: AppSettings;
  try {
    settings = await api.settings();
  } catch (err) {
    host.append(el("p", "text-sm text-[var(--color-danger)]", errorMessage(err)));
    return;
  }

  const reload = (): void => { void renderSettings(root); };
  const byId = new Map(settings.providers.map((item) => [item.id, item]));

  // -------------------------------------------------------------------------
  // Hosted provider
  // -------------------------------------------------------------------------
  const providerCard = card("mb-4");
  providerCard.append(el("h2", "page-title text-xl", "Hosted rewriting"));
  providerCard.append(el(
    "p",
    "mt-2 text-sm text-[var(--color-text-muted)]",
    "A key is stored in a private file on this machine and is never returned by the API. If every provider fails, the local rule engine takes over when the fallback is on.",
  ));

  const providerGrid = el("div", "mt-4 grid gap-3 sm:grid-cols-2");
  const providerSel = select(
    settings.providers.map((item) => ({
      value: item.id,
      label: item.configured ? `${item.label} (ready)` : item.label,
    })),
  );
  providerSel.value = settings.preferred_provider !== "auto"
    ? settings.preferred_provider
    : (settings.providers.find((item) => item.configured)?.id ?? settings.providers[0]?.id ?? "groq");
  const modelInput = input("text", "Model name");
  const keyInput = input("password", "Paste the provider key");
  keyInput.autocomplete = "off";
  providerGrid.append(fieldWrap("Provider", providerSel), fieldWrap("Model", modelInput));
  providerCard.append(providerGrid);

  const statusLine = el("p", "mt-2 text-xs text-[var(--color-text-subtle)]");
  const keyRow = el("div", "mt-3 grid gap-3 sm:grid-cols-[1fr_auto]");
  const keyField = fieldWrap("API key", keyInput);
  const keyButtons = el("div", "flex flex-wrap items-end gap-2 pb-0.5");
  const saveKeyBtn = button("Save key", "primary", () => void saveKey());
  const testKeyBtn = button("Test key", "secondary", () => void testKey());
  const removeKeyBtn = button("Remove key", "ghost", () => void removeKey());
  keyButtons.append(saveKeyBtn, testKeyBtn, removeKeyBtn);
  keyRow.append(keyField, keyButtons);
  providerCard.append(keyRow, statusLine);

  const current = (): ProviderInfo => byId.get(providerSel.value) ?? settings.providers[0]!;

  const syncProvider = (): void => {
    const provider = current();
    modelInput.value = provider.model;
    keyInput.value = "";
    keyInput.placeholder = provider.configured ? "A key is saved. Paste a new one to replace it." : "Paste the provider key";
    statusLine.replaceChildren();
    statusLine.append(
      badge(provider.configured ? `Key ready (${provider.key_source ?? "saved"})` : "No key saved", provider.configured ? "success" : "warn"),
      document.createTextNode(" "),
      el("span", "", `Env var: ${provider.env_keys.join(" or ")}. `),
      linkButton("Get a key", provider.docs_url),
    );
  };
  providerSel.addEventListener("change", syncProvider);
  syncProvider();

  async function saveKey(): Promise<void> {
    const value = keyInput.value.trim();
    if (!value) { toast("Paste a key first.", "error"); keyInput.focus(); return; }
    setButtonLoading(saveKeyBtn, true, "Saving...");
    try {
      await api.saveKey(providerSel.value, value);
      await api.saveSettings({
        models: { ...settings.models, [providerSel.value]: modelInput.value.trim() || current().default_model },
      });
      toast("Key saved locally.", "success");
      reload();
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(saveKeyBtn, false); }
  }

  async function testKey(): Promise<void> {
    setButtonLoading(testKeyBtn, true, "Testing...");
    try {
      const result = await api.testProvider(providerSel.value, keyInput.value.trim() || undefined);
      if (result.ok) toast(`Connected to ${result.model ?? providerSel.value} in ${result.latency_ms ?? 0} ms.`, "success");
      else toast(result.error ?? "The provider did not answer.", "error");
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(testKeyBtn, false); }
  }

  async function removeKey(): Promise<void> {
    setButtonLoading(removeKeyBtn, true, "Removing...");
    try {
      await api.removeKey(providerSel.value);
      toast("Key removed.", "success");
      reload();
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(removeKeyBtn, false); }
  }

  const toggleRow = el("div", "mt-5 grid gap-3 sm:grid-cols-2");
  const enabledRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const enabledToggle = toggle(settings.enabled, "Use hosted rewriting");
  enabledRow.append(enabledToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Use hosted rewriting"));
  const fallbackRow = el("label", "flex items-center gap-3 min-h-[42px] cursor-pointer");
  const fallbackToggle = toggle(settings.offline_fallback, "Offline fallback");
  fallbackRow.append(fallbackToggle, el("span", "text-sm font-medium text-[var(--color-text)]", "Fall back to the local engine"));
  toggleRow.append(enabledRow, fallbackRow);
  providerCard.append(toggleRow);

  const advanced = el("details", "mt-4 border-t border-[var(--color-border)] pt-3");
  advanced.append(el("summary", "cursor-pointer select-none text-sm font-semibold text-[var(--color-text)]", "Advanced"));
  const advancedGrid = el("div", "mt-3 grid gap-3 sm:grid-cols-3");
  const tempInput = input("number");
  tempInput.min = "0"; tempInput.max = "1.5"; tempInput.step = "0.1"; tempInput.value = String(settings.temperature);
  const timeoutInput = input("number");
  timeoutInput.min = "5"; timeoutInput.max = "180"; timeoutInput.step = "5"; timeoutInput.value = String(settings.timeout_seconds);
  const targetInput = input("number");
  targetInput.min = "0"; targetInput.max = "10"; targetInput.step = "0.1"; targetInput.value = String(settings.target_density);
  advancedGrid.append(
    fieldWrap("Temperature", tempInput, "Higher values vary more."),
    fieldWrap("Timeout (seconds)", timeoutInput, "Per provider call."),
    fieldWrap("Early-stop density", targetInput, "Skip extra rounds when the pattern count is at or below this."),
  );
  advanced.append(advancedGrid);
  providerCard.append(advanced);

  const saveRow = el("div", "mt-4 flex flex-wrap items-center gap-3");
  const saveBtn = button("Save settings", "primary", () => void saveSettings());
  const clearCacheBtn = button("Clear cached output", "secondary", () => void clearCache());
  saveRow.append(saveBtn, clearCacheBtn);
  providerCard.append(saveRow);
  host.append(providerCard);

  async function saveSettings(): Promise<void> {
    setButtonLoading(saveBtn, true, "Saving...");
    try {
      await api.saveSettings({
        enabled: getToggle(enabledToggle),
        offline_fallback: getToggle(fallbackToggle),
        preferred_provider: providerSel.value,
        models: { ...settings.models, [providerSel.value]: modelInput.value.trim() || current().default_model },
        temperature: Number(tempInput.value) || 0.7,
        timeout_seconds: Number(timeoutInput.value) || 60,
        target_density: Number(targetInput.value) || 0,
      });
      toast("Settings saved.", "success");
      reload();
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(saveBtn, false); }
  }

  async function clearCache(): Promise<void> {
    setButtonLoading(clearCacheBtn, true, "Clearing...");
    try {
      const result = await api.clearCache();
      toast(`Removed ${result.deleted} cached replies.`, "success");
    } catch (err) { toast(errorMessage(err), "error"); }
    finally { setButtonLoading(clearCacheBtn, false); }
  }

  // -------------------------------------------------------------------------
  // Privacy note
  // -------------------------------------------------------------------------
  const privacy = card("mb-4");
  privacy.append(el("h2", "text-base font-semibold text-[var(--color-text)]", "What leaves this machine"));
  privacy.append(el(
    "p",
    "mt-2 text-sm text-[var(--color-text-muted)]",
    "When hosted rewriting is on, the passage is sent to the provider you selected, along with a short style guide and up to four local examples. Your documents, reference library, keys and history stay in the local data folder. Results are a writing aid and cannot guarantee anything about third-party detectors.",
  ));
  privacy.append(el(
    "p",
    "mt-2 text-xs text-[var(--color-text-subtle)]",
    `Settings: ${settings.config_path} · Keys: ${settings.secrets_path}`,
  ));
  host.append(privacy);
}
