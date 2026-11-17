// UI text of the Status screen (spec "Screens", Status).

export const statusCopy = {
  title: "Status",
  loading: "Loading the status…",
  loadFailed: "The status could not be loaded.",
  settingLabel: "Setting:",
  tryAgain: "Try again",
  checkAgain: "Check again",
  settingsSummary: (count: number): string =>
    count === 0
      ? "No settings to fix."
      : `${count} ${count === 1 ? "setting" : "settings"} to fix in the configuration file.`,
  settingsToFixHeading: "Settings to fix",
  settingsToFixHint:
    "Edit the configuration file (.env) in the Card Factory folder, then check again. Changes take effect without a restart, except the port.",
  configurationHeading: "Configuration",
  fileUnreadable: "The configuration file cannot be read, so its settings are not shown.",
  noTextKeyBefore: "No text key is set. Set",
  noTextKeyAfter: "in the configuration file to generate cards.",
  nextStartPort: (port: number): string =>
    `The port changes to ${port} at the next start. After restarting, open http://127.0.0.1:${port}.`,
  textProvider: "Text provider",
  textModel: "Text model",
  textKeyConfigured: "Text key configured",
  imageProvider: "Image provider",
  imageModel: "Image model",
  yes: "Yes",
  no: "No",
  notSet: "Not set",
  invalid: "Invalid — see Settings to fix",
  databaseHeading: "Reference database",
  databaseReady: "The reference database is ready.",
  databaseMissingBefore: "The reference database is not ready. Build it or follow its progress on the",
  databaseMissingLink: "Setup",
  databaseMissingAfter: "screen.",
  dataSources: "Data sources",
  noSources: "No data sources are recorded.",
  origin: "Origin",
  published: "Published",
  downloaded: "Downloaded",
  unknownDate: "Unknown",
  ignoredHeading: "Ignored settings",
  sourceNames: { scryfall_oracle: "Scryfall Oracle cards" } as Record<string, string>,
  providerNames: { openai: "OpenAI", anthropic: "Anthropic", google: "Google" } as Record<string, string>,
};
