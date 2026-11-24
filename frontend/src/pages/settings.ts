import { api, errorMessage } from "../api";
import type { ModelOption, ProviderSetting, SettingsResponse } from "../types";
import {
  CARD,
  INPUT,
  button,
  el,
  formatNumber,
  pageHeader,
  reportError,
  setBusy,
  toast,
} from "../ui";

export async function renderSettings(root: HTMLElement): Promise<void> {
  root.append(
    pageHeader(
      "Settings",
      "Connect one online model provider. Free tiers first; paid models stay off unless you explicitly enable them.",
    ),
  );

  const host = el("div", "space-y-5");
  root.append(host);

  async function load(): Promise<void> {
    host.replaceChildren(el("p", "text-sm text-[#7A877C]", "Loading settings…"));
    try {
      const settings = await api.settings();
      host.replaceChildren();
      host.append(providersGrid(settings), preferredCard(settings), aboutCard(settings));
    } catch (error) {
      host.replaceChildren(el("p", "text-sm text-[#8B2020]", errorMessage(error)));
    }
  }

  function providersGrid(settings: SettingsResponse): HTMLElement {
    const section = el("div", "");
    section.append(
      el(
        "h2",
        "mb-3 text-sm font-semibold uppercase tracking-wider text-[#5C6B60]",
        "Providers",
      ),
    );
    const grid = el("div", "grid items-start gap-4 lg:grid-cols-2");
    for (const provider of settings.providers) {
      grid.append(providerCard(provider));
    }
    section.append(grid);
    return section;
  }

  function providerCard(provider: ProviderSetting): HTMLElement {
    const card = el("section", CARD);

    const header = el("div", "flex flex-wrap items-center gap-2");
    header.append(el("h3", "text-base font-semibold text-[#17251C]", provider.name));
    header.append(
      el(
        "span",
        `rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
          provider.tier === "paid"
            ? "bg-[#FBF1DC] text-[#8A5A12]"
            : "bg-[#E4F1E8] text-[#1B5E3B]"
        }`,
        provider.tier,
      ),
    );
    const sourceLabel =
      provider.source === "saved"
        ? "key saved locally"
        : provider.source === "env"
          ? "key from .env"
          : "no key";
    header.append(
      el(
        "span",
        `rounded-full px-2 py-0.5 text-[11px] font-medium ${
          provider.configured
            ? "bg-[#E4F1E8] text-[#1B5E3B]"
            : "bg-[#EEEDE6] text-[#5E5B4A]"
        }`,
        provider.configured ? `ready · ${sourceLabel}` : sourceLabel,
      ),
    );

    const notes = el("p", "mt-2 text-sm leading-6 text-[#5C6B60]", provider.notes);
    card.append(header, notes);

    const keyLabel = el(
      "p",
      "mt-3 text-xs text-[#7A877C]",
      provider.masked_key
        ? `Stored key: ${provider.masked_key}`
        : provider.requires_key
          ? `No key yet. You can also set ${provider.env_key} in .env.`
          : `Optional key. You can also set ${provider.env_key} in .env.`,
    );

    const keyInput = el("input", `${INPUT} mt-1`);
    keyInput.type = "password";
    keyInput.autocomplete = "off";
    keyInput.placeholder = provider.masked_key
      ? "Paste a new key to replace it"
      : "Paste your API key";

    const modelControl = buildModelControl(provider);

    const baseInput = el("input", `${INPUT} mt-1`);
    baseInput.type = "url";
    baseInput.placeholder = "https://…";
    baseInput.value = provider.base_url;

    const enabledWrap = el("label", "mt-3 flex cursor-pointer items-center gap-2 text-sm text-[#25352A]");
    const enabledInput = el("input", "h-4 w-4 accent-[#1C6B4A]");
    enabledInput.type = "checkbox";
    enabledInput.checked = provider.enabled !== 0;
    enabledWrap.append(enabledInput, el("span", "", "Enabled"));

    const save = button("Save", "primary", () => void saveProvider());
    const test = button("Test connection", "secondary", () => void testProvider());
    const clear = button("Clear key", "danger", () => void clearKey());
    clear.disabled = !provider.masked_key;

    const message = el("p", "mt-2 hidden text-sm leading-6");

    const actions = el("div", "mt-4 flex flex-wrap gap-2");
    actions.append(save, test, clear);

    card.append(
      keyLabel,
      keyInput,
      el("div", "mt-3"),
      labeled("Model", modelControl),
      el("div", "mt-3"),
      labeled(
        "Base URL",
        baseInput,
        provider.requires_base_url
          ? "Required for a custom endpoint. Must be a public http(s) URL."
          : "Optional override. Leave as-is to use the default endpoint.",
      ),
      enabledWrap,
      actions,
      message,
    );

    function showMessage(text: string, tone: "ok" | "bad"): void {
      message.textContent = text;
      message.className = `mt-2 text-sm leading-6 ${
        tone === "ok" ? "text-[#1B5E3B]" : "text-[#8B2020]"
      }`;
    }

    async function saveProvider(): Promise<void> {
      setBusy(save, true, "Saving…");
      try {
        const payload: {
          api_key?: string;
          model?: string;
          base_url?: string;
          enabled?: boolean;
        } = {
          model: modelControl.value,
          base_url: baseInput.value.trim(),
          enabled: enabledInput.checked,
        };
        if (keyInput.value.trim()) payload.api_key = keyInput.value.trim();
        await api.saveProvider(provider.id, payload);
        toast(`${provider.name} saved.`, "success");
        await load();
      } catch (error) {
        showMessage(errorMessage(error), "bad");
        toast(errorMessage(error), "error");
      } finally {
        setBusy(save, false);
      }
    }

    async function testProvider(): Promise<void> {
      setBusy(test, true, "Testing…");
      try {
        const result = await api.testProvider(provider.id);
        showMessage(result.message, result.ok ? "ok" : "bad");
        toast(result.ok ? `${provider.name} is reachable.` : `${provider.name}: ${result.message}`, result.ok ? "success" : "error");
      } catch (error) {
        showMessage(errorMessage(error), "bad");
        reportError(error);
      } finally {
        setBusy(test, false);
      }
    }

    async function clearKey(): Promise<void> {
      if (!window.confirm(`Remove the saved key for ${provider.name}?`)) return;
      setBusy(clear, true, "Clearing…");
      try {
        await api.clearProviderKey(provider.id);
        toast("Key removed.", "success");
        await load();
      } catch (error) {
        reportError(error);
      } finally {
        setBusy(clear, false);
      }
    }

    return card;
  }

  function buildModelControl(provider: ProviderSetting): HTMLInputElement | HTMLSelectElement {
    const models: ModelOption[] = provider.models.filter(
      (model) => model.enabled || model.id === provider.model,
    );
    if (models.length === 0) {
      const input = el("input", `${INPUT} mt-1`);
      input.placeholder = "Model name";
      input.value = provider.model;
      return input;
    }
    const select = el("select", `${INPUT} mt-1`);
    if (!models.some((model) => model.id === provider.model)) {
      const extra = el("option", "", provider.model || "Default");
      extra.value = provider.model;
      select.append(extra);
    }
    for (const model of models) {
      const option = el(
        "option",
        "",
        model.paid ? `${model.label} — paid` : model.label,
      );
      option.value = model.id;
      select.append(option);
    }
    select.value = provider.model;
    return select;
  }

  function labeled(
    label: string,
    control: HTMLElement,
    hint?: string,
  ): HTMLElement {
    const wrap = el("div", "");
    wrap.append(el("span", "block text-sm font-medium text-[#25352A]", label));
    wrap.append(control);
    if (hint) wrap.append(el("span", "mt-1.5 block text-xs leading-5 text-[#7A877C]", hint));
    return wrap;
  }

  function preferredCard(settings: SettingsResponse): HTMLElement {
    const card = el("section", CARD);
    card.append(
      el("h3", "text-base font-semibold text-[#17251C]", "Preferred provider"),
      el(
        "p",
        "mt-1 text-sm leading-6 text-[#5C6B60]",
        "Used first when a job is set to Auto. Other configured providers are tried if it fails.",
      ),
    );
    const select = el("select", `${INPUT} mt-3`);
    const none = el("option", "", "No preference — follow the catalog order");
    none.value = "";
    select.append(none);
    for (const provider of settings.providers) {
      const option = el(
        "option",
        "",
        provider.configured ? provider.name : `${provider.name} (not configured)`,
      );
      option.value = provider.id;
      select.append(option);
    }
    select.value = settings.preferred_provider ?? "";

    const save = button("Save preference", "secondary", () => {
      void (async () => {
        setBusy(save, true, "Saving…");
        try {
          await api.savePreferences(select.value || null);
          toast("Preference saved.", "success");
        } catch (error) {
          reportError(error);
        } finally {
          setBusy(save, false);
        }
      })();
    });
    card.append(select, el("div", "mt-3"), save);
    return card;
  }

  function aboutCard(settings: SettingsResponse): HTMLElement {
    const card = el("section", CARD);
    card.append(
      el("h3", "text-base font-semibold text-[#17251C]", "Local storage & limits"),
    );

    const list = el("dl", "mt-3 grid gap-3 text-sm sm:grid-cols-2");
    const row = (term: string, value: string): void => {
      const box = el("div", "");
      box.append(
        el("dt", "text-xs uppercase tracking-wide text-[#8B978D]", term),
        el("dd", "mt-0.5 break-words text-[#25352A]", value),
      );
      list.append(box);
    };
    row("Database", settings.database_path);
    row("Paid models", settings.paid_models_enabled ? "Enabled" : "Off (default)");
    row("Max input", `${formatNumber(settings.limits.max_input_chars)} characters`);
    row("Chunk size", `${formatNumber(settings.limits.chunk_chars)} characters`);

    card.append(
      list,
      el(
        "p",
        "mt-4 rounded-lg border border-[#EBD9B5] bg-[#FDF7EA] px-3.5 py-2.5 text-sm leading-6 text-[#7A5410]",
        "Keys are stored in your local SQLite file in plain text. Keep data/phrasia.db private, never commit it, and never sync it to a shared drive.",
      ),
    );
    return card;
  }

  await load();
}
