import { api, errorMessage } from "../api";
import type { ProviderSetting, SettingsResponse } from "../types";
import {
  badge,
  button,
  card,
  el,
  pageHead,
  toast,
} from "../ui";

export async function renderSettings(root: HTMLElement): Promise<void> {
  root.replaceChildren(
    pageHead(
      "Settings",
      "Manage providers: enable or disable, edit model and base URL, test connections, clear keys.",
    ),
  );

  const grid = el("div", "grid gap-6 md:grid-cols-2 lg:grid-cols-3");
  root.append(grid);

  const load = async (): Promise<void> => {
    const settings = await api.settings();
    grid.replaceChildren();
    for (const provider of settings.providers) grid.append(providerCard(provider));
    grid.append(preferredCard(settings));
  };

  const providerCard = (provider: ProviderSetting): HTMLElement => {
    const cardEl = card();
    cardEl.dataset.provider = provider.id;
    const nameRow = el("div", "flex items-center gap-3");
    nameRow.append(
      el("h3", "text-base font-semibold text-[#16251C]", provider.name),
      badge("anonymous", "accent"),
    );
    cardEl.append(nameRow);
    cardEl.append(nameRow);
    const infoRow = el("div", "mt-3 flex flex-wrap gap-2");
    infoRow.append(info("Model", provider.model || "default"));
    infoRow.append(info("Rate limit", `${provider.rate_limit_requests_per_minute}/min`));
    infoRow.append(info("Source", provider.source));
    cardEl.append(infoRow);

    const keyInput = el(
      "input",
      "mt-3 rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15",
    );
    keyInput.type = "password";
    keyInput.placeholder = provider.masked_key || "Optional — not needed for anonymous endpoints";
    keyInput.autocomplete = "off";

    const modelInput = el(
      "input",
      "mt-3 rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition placeholder:text-[#8C9890] focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15",
    );
    modelInput.placeholder = provider.model || "model";

    const enabledLabel = el(
      "label",
      "mt-4 flex items-center gap-3 text-sm text-[#25352A]",
    );
    const enabledBox = el("input");
    enabledBox.type = "checkbox";
    enabledBox.checked = provider.enabled !== 0;
    enabledLabel.append(enabledBox, el("span", "", "Enabled"));

    const status = el("p", "mt-3 text-sm text-[#5C6C62]", provider.configured ? "Configured" : "Not configured");
    const actions = el("div", "mt-5 flex flex-wrap items-center gap-2");
    const saveBtn = button("Save", "primary", () => void save(provider.id));
    const testBtn = button("Test", "secondary", () => void test(provider.id));
    const clearBtn = button("Clear key", "danger", () => void clearKey(provider.id));
    actions.append(saveBtn, testBtn, clearBtn);

    cardEl.append(
      el("span", "mt-1 text-sm text-[#8C9890]", "Save leaves the key empty to use the catalog default."),
      keyInput,
      modelInput,
      enabledLabel,
      status,
      actions,
    );

    async function save(providerId: string): Promise<void> {
      const card = document.querySelector(`[data-provider="${providerId}"]`);
      const keyInput = card?.querySelector("input[type='password']") as HTMLInputElement | null;
      const modelInput = card?.querySelector("input[placeholder]") as HTMLInputElement | null;
      const enabledBox = card?.querySelector("input[type='checkbox']") as HTMLInputElement | null;
      try {
        await api.saveProvider(providerId, {
          api_key: keyInput?.value || undefined,
          model: modelInput?.value || undefined,
          enabled: enabledBox?.checked,
        });
        toast("Saved.", "success");
        load();
      } catch (error) {
        toast(errorMessage(error), "error");
      }
    }

    async function test(providerId: string): Promise<void> {
      const result = await api.testProvider(providerId);
      toast(result.ok ? `Reachable. (${result.message})` : result.message, result.ok ? "success" : "error");
    }

    async function clearKey(providerId: string): Promise<void> {
      try {
        await api.clearProviderKey(providerId);
        toast("Key cleared.", "success");
        load();
      } catch (error) {
        toast(errorMessage(error), "error");
      }
    }

    return cardEl;
  };

  const preferredCard = (settings: SettingsResponse): HTMLElement => {
    const cardEl = card();
    cardEl.append(
      el("h3", "text-base font-semibold text-[#16251C]", "Preferred provider"),
      el("p", "mt-2 text-sm text-[#5C6C62]", "Used first. All catalog providers are anonymous and free."),
    );
    const selectEl = el(
      "select",
      "mt-4 w-full rounded-lg border border-[#CFD8C7] bg-white px-3.5 py-2.5 text-base text-[#1D3026] outline-none transition focus:border-[#1F6B4A] focus:ring-2 focus:ring-[#1F6B4A]/15",
    );
    const none = el("option", "", "Catalog order");
    none.value = "";
    selectEl.append(none);
    for (const provider of settings.providers) {
      const o = el("option", "", provider.name);
      o.value = provider.id;
      selectEl.append(o);
    }
    selectEl.value = settings.preferred_provider ?? "";
    const save = button("Save", "primary", () => void savePref());
    cardEl.append(selectEl, el("div", "h-3"), save);

    async function savePref(): Promise<void> {
      save.disabled = true;
      try {
        await api.savePreferences(selectEl.value || null);
        toast("Preference saved.", "success");
        await load();
      } catch (error) {
        toast(errorMessage(error), "error");
      } finally {
        save.disabled = false;
      }
    }
    return cardEl;
  };

  const info = (label: string, value: string): HTMLElement =>
    el(
      "span",
      "inline-block rounded-full bg-[#E8EBE5] px-2.5 py-1 text-[11px] font-medium text-[#1D3026]",
      `${label}: ${value}`,
    );

  await load();
}
