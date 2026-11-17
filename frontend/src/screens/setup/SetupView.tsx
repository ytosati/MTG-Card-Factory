// Setup screen view: the sizes of the build, its action and its progress.
// Details: specs/spec.md, RN-28 and "Screens" (First-run setup).
import { useId } from "react";
import type { RefObject } from "react";

import type { JobResponse, SetupResponse } from "../../api/types";
import { cx } from "../../components/classNames";
import { ProgressBar, progressOf, progressStyles } from "../../components/ProgressBar";
import { Screen, screenStyles } from "../../components/Screen";
import { StatusIcon, toneStyles } from "../../components/StatusIcon";
import { setupCopy as copy } from "./copy";
import { formatSize } from "./formatSize";
import styles from "./SetupView.module.css";

/** What the action area shows. */
export type SetupAction =
  | { kind: "loading" }
  | { kind: "load-failed"; message: string }
  | { kind: "ready" }
  | { kind: "listing-failed"; message: string }
  | { kind: "start"; problem: { message: string } | null }
  | { kind: "short"; missing: string | null }
  | { kind: "starting" }
  | { kind: "building"; job: JobResponse }
  | { kind: "build-failed"; message: string };

interface SetupViewProps {
  action: SetupAction;
  /** The sizes and settings read on open; null hides the ledger. */
  setup: SetupResponse | null;
  settingsToFix: boolean;
  /** The server refused the build for lack of space. */
  lacksSpace: boolean;
  actionRef?: RefObject<HTMLDivElement | null> | undefined;
  onStart: () => void;
  onReadAgain: () => void;
}

function statusText(action: SetupAction): string {
  switch (action.kind) {
    case "loading":
      return copy.statusReading;
    case "ready":
      return copy.statusOpening;
    case "start":
      return action.problem === null ? copy.statusNothingDownloaded : "";
    case "starting":
      return copy.statusStarting;
    case "building":
      if (action.job.status === "queued") return copy.statusWaiting;
      if (action.job.status === "done") return copy.statusDone;
      return copy.statusRunning;
    case "build-failed":
      return copy.statusStopped;
    case "load-failed":
    case "listing-failed":
    case "short":
      return "";
  }
}

/** The Setup screen for one state of the build. */
export function SetupView({ action, setup, settingsToFix, lacksSpace, actionRef, onStart, onReadAgain }: SetupViewProps) {
  return (
    <Screen>
      <h1 tabIndex={-1}>{copy.title}</h1>
      <p className={screenStyles.summary}>{copy.summary}</p>

      {settingsToFix && (
        <div className={cx(styles.notice, toneStyles.tone)}>
          <StatusIcon tone="notice" />
          <p>
            {copy.settingsToFix} <a href="#/status">{copy.settingsToFixLink}</a>
          </p>
        </div>
      )}

      <section className={styles.panel} aria-label={copy.panelLabel}>
        {setup !== null && <SizeLedger setup={setup} lacksSpace={lacksSpace} />}

        {/* The focus target when the control that was used disappears. */}
        <div className={styles.action} ref={actionRef} tabIndex={-1}>
          <ActionContent action={action} onStart={onStart} onReadAgain={onReadAgain} />
          <p className={cx(screenStyles.hint, styles.status)} role="status">
            {statusText(action)}
          </p>
        </div>
      </section>
    </Screen>
  );
}

interface ActionContentProps {
  action: SetupAction;
  onStart: () => void;
  onReadAgain: () => void;
}

function ActionContent({ action, onStart, onReadAgain }: ActionContentProps) {
  switch (action.kind) {
    case "loading":
    case "ready":
      return null;
    case "load-failed":
    case "listing-failed":
      return <ProblemBlock message={action.message} actionLabel={copy.tryAgain} onAction={onReadAgain} />;
    case "build-failed":
      return <ProblemBlock message={action.message} actionLabel={copy.tryAgain} onAction={onStart} />;
    case "start":
      return action.problem === null ? (
        <div className={styles.start}>
          <button type="button" onClick={onStart}>
            {copy.startBuild}
          </button>
        </div>
      ) : (
        <ProblemBlock message={action.problem.message} actionLabel={copy.tryAgain} onAction={onStart} />
      );
    case "short":
      return (
        <div className={styles.start}>
          <div className={cx(styles.problem, toneStyles.tone)}>
            <StatusIcon tone="danger" />
            <p>
              {copy.shortOfSpace} {copy.freeSpace(action.missing)}
            </p>
          </div>
          <button type="button" onClick={onReadAgain}>
            {copy.checkAgain}
          </button>
        </div>
      );
    case "starting":
      return (
        <div className={styles.start}>
          <button type="button" disabled>
            {copy.startBuild}
          </button>
        </div>
      );
    case "building":
      return <BuildProgress job={action.job} />;
  }
}

function ProblemBlock({ message, actionLabel, onAction }: { message: string; actionLabel: string; onAction: () => void }) {
  return (
    <div className={styles.start}>
      <div className={cx(styles.problem, toneStyles.tone)} role="alert">
        <StatusIcon tone="danger" />
        <p>{message}</p>
      </div>
      <button type="button" onClick={onAction}>
        {actionLabel}
      </button>
    </div>
  );
}

function SizeLedger({ setup, lacksSpace }: { setup: SetupResponse; lacksSpace: boolean }) {
  const download = setup.download_size === null ? null : formatSize(setup.download_size);
  const needed = setup.space_needed === null ? null : formatSize(setup.space_needed);
  const free = setup.free_space === null ? null : formatSize(setup.free_space);
  if (download === null && needed === null && free === null) return null;
  const short =
    lacksSpace || (setup.free_space !== null && setup.space_needed !== null && setup.free_space < setup.space_needed);

  return (
    <dl className={styles.ledger}>
      {download !== null && <LedgerItem label={copy.download} size={download} />}
      {needed !== null && <LedgerItem label={copy.spaceNeeded} size={needed} />}
      {free !== null && <LedgerItem label={copy.freeOnDrive} size={free} short={short} />}
    </dl>
  );
}

function LedgerItem({ label, size, short = false }: { label: string; size: string; short?: boolean }) {
  return (
    <div className={cx(styles.ledgerItem, short && styles.ledgerShort)}>
      <dt>{label}</dt>
      {/* The trailing space keeps the size apart from the next label when the text is copied or read as one. */}
      <dd>
        {size}
        {short && <span className={styles.ledgerNote}> {copy.notEnoughSpace}</span>}{" "}
      </dd>
    </div>
  );
}

function BuildProgress({ job }: { job: JobResponse }) {
  const labelId = useId();
  const { fraction, percent } = progressOf(job.progress);

  return (
    <div>
      <div className={progressStyles.head}>
        <span id={labelId}>{copy.progressLabel}</span>
        <span className={progressStyles.value} aria-hidden="true">
          {percent}%
        </span>
      </div>
      <ProgressBar labelId={labelId} fraction={fraction} percent={percent} />
    </div>
  );
}
