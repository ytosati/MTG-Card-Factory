// @vitest-environment jsdom
// Tests for the configuration part of the Status screen (spec RN-08, RN-30, RN-40, RN-49; CA-46, CA-73, CA-74).
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StatusScreen } from "./StatusScreen";
import {
  errorNotFound,
  statusFullConfiguration,
  statusImageKeyIgnored,
  statusImageModelIgnored,
  statusInvalidImageProvider,
  statusMissingTextKey,
  statusNextStartPort,
  statusUnreadableConfiguration,
} from "../api/contract/samples";
import { calledUrl, jsonResponse, stubFetch } from "../test/fetchMock";

const FIELD_LABELS = [
  "Text provider",
  "Text model",
  "Text key configured",
  "Image provider",
  "Image model",
] as const;

const SETTINGS_TO_FIX = "Settings to fix";
const IGNORED_SETTINGS = "Ignored settings";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

/** Renders the screen with one status answer and waits until the fields are shown. */
async function renderWithStatus(body: unknown) {
  const fetchMock = stubFetch(async () => jsonResponse(body));
  render(<StatusScreen />);
  await screen.findByText("Text provider");
  return fetchMock;
}

/** The value shown for a field: the element right after its visible label (for example dt/dd). */
function valueOf(label: string): HTMLElement {
  const labelElement = screen.getByText(label);
  const value = labelElement.nextElementSibling;
  expect(value, `no value element after the label "${label}"`).not.toBeNull();
  return value as HTMLElement;
}

function valueText(label: string): string {
  return (valueOf(label).textContent ?? "").trim();
}

function settingsToFixRegion(): HTMLElement | null {
  return screen.queryByRole("region", { name: SETTINGS_TO_FIX });
}

function ignoredSettingsRegion(): HTMLElement | null {
  return screen.queryByRole("region", { name: IGNORED_SETTINGS });
}

function itemsIn(region: HTMLElement | null): HTMLElement[] {
  return region ? within(region).queryAllByRole("listitem") : [];
}

describe("StatusScreen: configuration fields", () => {
  it("RN-30, RN-49: has an English level-1 heading named Status", async () => {
    await renderWithStatus(statusFullConfiguration);

    expect(screen.getByRole("heading", { level: 1, name: "Status" })).toBeTruthy();
  });

  it("RN-08, RN-49: every configuration field has a visible English label followed by its value", async () => {
    await renderWithStatus(statusFullConfiguration);

    for (const label of FIELD_LABELS) {
      expect(valueText(label), `empty value for "${label}"`).not.toBe("");
    }
  });

  it("RN-08: shows the text provider, text model, image provider and image model of a full configuration", async () => {
    await renderWithStatus(statusFullConfiguration);

    expect(valueText("Text provider").toLowerCase()).toContain(statusFullConfiguration.text_provider);
    expect(valueText("Text model")).toBe(statusFullConfiguration.text_model);
    expect(valueText("Image provider").toLowerCase()).toContain(statusFullConfiguration.image_provider);
    expect(valueText("Image model")).toBe(statusFullConfiguration.image_model);
  });

  it("RN-08: a configured key is shown as Yes, never as the key", async () => {
    await renderWithStatus(statusFullConfiguration);

    expect(valueText("Text key configured")).toMatch(/^yes$/i);
  });

  it("RN-08, CA-46: a missing key is shown as No", async () => {
    await renderWithStatus(statusMissingTextKey);

    expect(valueText("Text key configured")).toMatch(/^no$/i);
  });

  it("RN-08: empty values are shown as readable text, never as null, undefined or blank", async () => {
    await renderWithStatus({
      ...statusMissingTextKey,
      text_provider: null,
      text_model: null,
      image_provider: null,
      image_model: null,
    });

    for (const label of ["Text provider", "Text model", "Image provider", "Image model"]) {
      const text = valueText(label);
      expect(text, `blank value for "${label}"`).not.toBe("");
      expect(text).not.toMatch(/\bnull\b|\bundefined\b|NaN|\[object Object\]/);
    }
  });

  it("RN-08 (Status screen shows the configuration, never the key): fields outside the contract are not rendered", async () => {
    const fakeKey = "sk-fake-0000aaaa1111bbbb2222cccc3333dddd";
    await renderWithStatus({ ...statusFullConfiguration, llm_api_key: fakeKey, image_api_key: fakeKey });

    expect(document.body.textContent ?? "").not.toContain(fakeKey);
    expect(document.body.innerHTML).not.toContain(fakeKey);
  });

  it("RN-30: the screen has no Portuguese interface words", async () => {
    await renderWithStatus(statusMissingTextKey);

    const text = document.body.textContent ?? "";
    for (const word of ["Provedor", "Modelo", "Chave", "Configuração", "Sim", "Não", "Carregando", "Erro"]) {
      const wholeWord = new RegExp(String.raw`(^|[^\p{L}])` + word + String.raw`($|[^\p{L}])`, "iu");
      expect(text, `unexpected Portuguese word "${word}"`).not.toMatch(wholeWord);
    }
  });
});

describe("StatusScreen: settings to fix and ignored settings", () => {
  it("CA-46, RN-40: a missing key names LLM_API_KEY as a setting to fix, with its message", async () => {
    await renderWithStatus(statusMissingTextKey);

    const items = itemsIn(settingsToFixRegion());
    expect(items).toHaveLength(1);
    const setting = statusMissingTextKey.settings[0]!;
    expect(items[0]!.textContent).toContain(setting.setting);
    expect(items[0]!.textContent).toContain(setting.message);
  });

  it("CA-74: an image provider that cannot generate images (Anthropic) names IMAGE_PROVIDER as a setting to fix", async () => {
    await renderWithStatus(statusInvalidImageProvider);

    const items = itemsIn(settingsToFixRegion());
    expect(items).toHaveLength(1);
    const setting = statusInvalidImageProvider.settings[0]!;
    expect(items[0]!.textContent).toContain("IMAGE_PROVIDER");
    expect(items[0]!.textContent).toContain(setting.message);
  });

  it("CA-74: an image key with no image provider is shown as ignored, not as a setting to fix", async () => {
    await renderWithStatus(statusImageKeyIgnored);

    const setting = statusImageKeyIgnored.settings[0]!;
    const ignored = itemsIn(ignoredSettingsRegion());
    expect(ignored).toHaveLength(1);
    expect(ignored[0]!.textContent).toContain("IMAGE_API_KEY");
    expect(ignored[0]!.textContent).toContain(setting.message);
    expect(itemsIn(settingsToFixRegion())).toHaveLength(0);
  });

  it("CA-74: an image model with no image provider and Anthropic as text provider is shown as ignored, not as a setting to fix", async () => {
    await renderWithStatus(statusImageModelIgnored);

    const setting = statusImageModelIgnored.settings[0]!;
    const ignored = itemsIn(ignoredSettingsRegion());
    expect(ignored).toHaveLength(1);
    expect(ignored[0]!.textContent).toContain("IMAGE_MODEL");
    expect(ignored[0]!.textContent).toContain(setting.message);
    expect(itemsIn(settingsToFixRegion())).toHaveLength(0);
  });

  it("CA-74, CA-73: a full configuration reports no setting to fix and no ignored setting", async () => {
    await renderWithStatus(statusFullConfiguration);

    expect(itemsIn(settingsToFixRegion())).toHaveLength(0);
    expect(itemsIn(ignoredSettingsRegion())).toHaveLength(0);
    const text = document.body.textContent ?? "";
    for (const name of ["LLM_API_KEY", "IMAGE_PROVIDER", "IMAGE_API_KEY", "IMAGE_MODEL"]) {
      expect(text).not.toContain(name);
    }
  });

  it("CA-74: with no image settings, no setting to fix is reported", async () => {
    await renderWithStatus(statusNextStartPort);

    expect(itemsIn(settingsToFixRegion())).toHaveLength(0);
  });

  it("CA-77, RN-40: an unreadable configuration file names .env with its fix as the only setting to fix", async () => {
    await renderWithStatus(statusUnreadableConfiguration);

    const items = itemsIn(settingsToFixRegion());
    expect(items).toHaveLength(1);
    const setting = statusUnreadableConfiguration.settings[0]!;
    expect(setting.setting).toBe(".env");
    expect(items[0]!.textContent).toContain(".env");
    expect(items[0]!.textContent).toContain(setting.message);
    expect(itemsIn(ignoredSettingsRegion())).toHaveLength(0);
    expect(document.body.textContent ?? "").not.toMatch(/next start/i);
    for (const name of ["LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL", "IMAGE_PROVIDER", "IMAGE_MODEL"]) {
      expect(document.body.textContent ?? "").not.toContain(name);
    }
  });

  it("RN-08: several settings are split by code and keep the order of the response", async () => {
    await renderWithStatus({
      ...statusMissingTextKey,
      settings: [
        ...statusMissingTextKey.settings,
        ...statusImageKeyIgnored.settings,
        ...statusInvalidImageProvider.settings,
      ],
    });

    const toFix = itemsIn(settingsToFixRegion());
    expect(toFix).toHaveLength(2);
    expect(toFix[0]!.textContent).toContain("LLM_API_KEY");
    expect(toFix[1]!.textContent).toContain("IMAGE_PROVIDER");
    const ignored = itemsIn(ignoredSettingsRegion());
    expect(ignored).toHaveLength(1);
    expect(ignored[0]!.textContent).toContain("IMAGE_API_KEY");
  });

  it("RN-08: a setting message with markup, odd characters and huge length is shown as plain text", async () => {
    const base = statusMissingTextKey.settings[0]!;
    const odd = `<img src=x onerror=alert(1)> & "quotes" 'ç ã é' {W}{U/B} ${"x".repeat(5000)}`;
    await renderWithStatus({
      ...statusMissingTextKey,
      settings: [{ ...base, message: odd }],
    });

    const items = itemsIn(settingsToFixRegion());
    expect(items).toHaveLength(1);
    expect(items[0]!.textContent).toContain(odd);
    expect(document.querySelector('img[src="x"]')).toBeNull();
  });
});

describe("StatusScreen: port for the next start", () => {
  it("RN-08: a changed port is reported as taking effect at the next start", async () => {
    await renderWithStatus(statusNextStartPort);

    const port = String(statusNextStartPort.next_start_port);
    const matches = Array.from(document.body.querySelectorAll<HTMLElement>("*")).filter((element) => {
      const text = element.textContent ?? "";
      return text.includes(port) && /next start/i.test(text);
    });
    expect(matches.length, "no element names the port and the next start").toBeGreaterThan(0);
    const deepest = matches.filter((element) => !matches.some((other) => other !== element && element.contains(other)));
    expect(deepest.some((element) => (element.textContent ?? "").length < 300)).toBe(true);
  });

  it("RN-08: with no port change, no next-start notice is shown", async () => {
    await renderWithStatus(statusFullConfiguration);

    expect(document.body.textContent ?? "").not.toMatch(/next start/i);
  });
});

describe("StatusScreen: loading, error and reload", () => {
  it("RN-49: shows a loading state while the status is requested", async () => {
    stubFetch(() => new Promise<Response>(() => {}));

    render(<StatusScreen />);

    expect(await screen.findByText(/loading/i)).toBeTruthy();
    expect(screen.queryByText("Text provider")).toBeNull();
  });

  it("RN-08: requests GET /api/status when it opens", async () => {
    const fetchMock = await renderWithStatus(statusFullConfiguration);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(calledUrl(fetchMock.mock.calls[0]![0])).toBe("/api/status");
  });

  it("plan section 6: an error envelope is shown as an alert with its message and no configuration values", async () => {
    stubFetch(async () => jsonResponse(errorNotFound, 404));

    render(<StatusScreen />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(errorNotFound.error.message);
    expect(screen.queryByText("Text provider")).toBeNull();
    expect(screen.queryByText(/loading/i)).toBeNull();
  });

  it("RN-08: a network failure is shown as an alert with readable text", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });

    render(<StatusScreen />);

    const alert = await screen.findByRole("alert");
    expect((alert.textContent ?? "").trim()).not.toBe("");
    expect(alert.textContent ?? "").not.toMatch(/\bundefined\b|\[object Object\]/);
    expect(screen.queryByText("Text provider")).toBeNull();
  });

  it("CA-73: reopening the screen after a fix reads the status again and shows the new state", async () => {
    const fetchMock = stubFetch(
      async () => jsonResponse(statusMissingTextKey),
      async () => jsonResponse(statusFullConfiguration),
    );

    const first = render(<StatusScreen />);
    await screen.findByText("Text provider");
    expect(valueText("Text key configured")).toMatch(/^no$/i);
    expect(itemsIn(settingsToFixRegion())).toHaveLength(1);
    first.unmount();

    render(<StatusScreen />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    await screen.findByText("Text provider");
    await waitFor(() => expect(valueText("Text key configured")).toMatch(/^yes$/i));
    expect(itemsIn(settingsToFixRegion())).toHaveLength(0);
    expect(document.body.textContent ?? "").not.toContain("LLM_API_KEY");
    for (const call of fetchMock.mock.calls) {
      expect(calledUrl(call[0])).toBe("/api/status");
    }
  });
});
