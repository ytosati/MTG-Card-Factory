// UI text of the Setup screen (spec "Screens", First-run setup).

export const setupCopy = {
  title: "Setup",
  summary:
    "Card Factory checks every card it designs against a local database of existing Magic cards. Build it once to open the other screens.",
  settingsToFix: "Some settings need fixing. You can still build the database now.",
  settingsToFixLink: "See them on the Status screen",
  panelLabel: "Card database",
  startBuild: "Start the build",
  tryAgain: "Try again",
  checkAgain: "Check again",
  shortOfSpace: "This drive does not have enough free space for the build.",
  freeSpace: (missing: string | null): string =>
    `${missing === null ? "Free some space" : `Free ${missing} on this drive`}, then check again.`,
  download: "Download",
  spaceNeeded: "Space needed",
  freeOnDrive: "Free on this drive",
  notEnoughSpace: "Not enough space",
  progressLabel: "Building the card database",
  lost: "Card Factory lost track of the build. Try again to follow or restart it.",
  failed: "The build failed. Try again.",
  unknownFailure: "Something went wrong in Card Factory. Try again.",
  statusReading: "Reading what the build needs…",
  statusOpening: "Opening Card Factory…",
  statusNothingDownloaded: "Nothing is downloaded until you start.",
  statusStarting: "Starting the build…",
  statusWaiting: "Waiting to start…",
  statusDone: "Done. Opening Card Factory…",
  statusRunning:
    "Downloading the card data and building the database. The build keeps running if you close this tab.",
  statusStopped: "The build stopped.",
};
