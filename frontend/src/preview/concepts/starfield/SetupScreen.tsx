// Concept E "Starfield" (tasks.md T251): the first-run Setup screen as a local mockup: what the build needs, the
// action that starts it and the build's progress as an orbit being closed.
import { useEffect, useState } from "react";

import type { SetupResponse } from "../../../api/types";
import { setupCopy } from "../../../screens/setup/copy";
import { StarGlyph } from "./glyphs";
import { sceneCopy } from "./scenes";
import ui from "./screen.module.css";
import { Shell } from "./Shell";
import styles from "./setup.module.css";

/** How often and by how much the mockup's build advances. */
const TICK_MS = 700;
const TICK = 0.011;
const MOCK_LIMIT = 0.96;

const UNITS = ["B", "KB", "MB", "GB", "TB"] as const;

/** A size in bytes as a number and its unit, in powers of 1000 as drives are labelled. */
function sizeOf(bytes: number | null): { value: string; unit: string } {
  if (bytes === null) return { value: "—", unit: "" };
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < UNITS.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return { value: value >= 100 || unit === 0 ? value.toFixed(0) : value.toFixed(1), unit: UNITS[unit] ?? "B" };
}

function Figure({ label, bytes }: { label: string; bytes: number | null }) {
  const size = sizeOf(bytes);
  return (
    <div className={styles.figure}>
      <dt>{label}</dt>
      <dd>
        <span className={styles.figureValue}>{size.value}</span>
        <span className={styles.figureUnit}>{size.unit}</span>
      </dd>
    </div>
  );
}

/** The build's progress: an orbit closed as the build advances, with a cyan moon at its leading edge. */
function OrbitProgress({ share }: { share: number }) {
  const angle = share * Math.PI * 2 - Math.PI / 2;
  const moon = { x: 90 + Math.cos(angle) * 72, y: 90 + Math.sin(angle) * 72 };
  return (
    <div
      className={styles.progress}
      role="progressbar"
      aria-label={setupCopy.progressLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(share * 100)}
    >
      <svg viewBox="0 0 180 180" aria-hidden="true" focusable="false">
        <circle cx="90" cy="90" r="84" className={styles.outer} />
        <circle cx="90" cy="90" r="72" className={styles.track} />
        <circle cx="90" cy="90" r="72" className={styles.done} pathLength={1} style={{ strokeDashoffset: 1 - share }} transform="rotate(-90 90 90)" />
        {Array.from({ length: 24 }, (_, index) => {
          const a = (index / 24) * Math.PI * 2;
          return <line key={index} x1={90 + Math.cos(a) * 60} y1={90 + Math.sin(a) * 60} x2={90 + Math.cos(a) * (index % 6 === 0 ? 54 : 57)} y2={90 + Math.sin(a) * (index % 6 === 0 ? 54 : 57)} className={styles.tick} />;
        })}
        <circle cx={moon.x} cy={moon.y} r="3.4" className={styles.moon} />
      </svg>
      <span className={styles.percent}>{sceneCopy.percent(share)}</span>
    </div>
  );
}

export function SetupScreen({ setup }: { setup: SetupResponse }) {
  const [share, setShare] = useState<number | null>(setup.job?.status === "running" ? setup.job.progress : null);
  const building = share !== null;

  useEffect(() => {
    document.title = `${setupCopy.title} · Card Factory`;
  }, []);

  useEffect(() => {
    if (share === null || share >= MOCK_LIMIT) return undefined;
    const timer = window.setTimeout(() => setShare((current) => (current === null ? null : Math.min(MOCK_LIMIT, current + TICK))), TICK_MS);
    return () => window.clearTimeout(timer);
  }, [share]);

  return (
    <Shell>
      <div className={`${ui.page} ${styles.layout}`}>
        <div className={styles.intro}>
          <p className={ui.rubric}>
            <StarGlyph size={8} className={ui.rubricStar} />
            {building ? setupCopy.progressLabel : sceneCopy.firstRun}
          </p>
          <h1 className={ui.title}>{building ? sceneCopy.setupBuildingTitle : setupCopy.title}</h1>
          <p className={ui.summary}>{setupCopy.summary}</p>
          {setup.settings.length > 0 ? (
            <p className={styles.notice}>
              {setupCopy.settingsToFix}{" "}
              <a className={ui.link} href="#/preview/concept-starfield/status">
                {setupCopy.settingsToFixLink}
              </a>
            </p>
          ) : null}
        </div>

        <section className={`${ui.stage} ${styles.panel}`} aria-labelledby="sf-setup-panel">
          <h2 id="sf-setup-panel" className={ui.label}>
            {setupCopy.panelLabel}
          </h2>
          {building ? (
            <div className={styles.building}>
              <OrbitProgress share={share} />
              <p className={styles.running} role="status">
                {setupCopy.statusRunning}
              </p>
            </div>
          ) : (
            <>
              <dl className={styles.figures}>
                <Figure label={setupCopy.download} bytes={setup.download_size} />
                <Figure label={setupCopy.spaceNeeded} bytes={setup.space_needed} />
                <Figure label={setupCopy.freeOnDrive} bytes={setup.free_space} />
              </dl>
              <div className={styles.start}>
                <button type="button" className={ui.primary} onClick={() => setShare(0.02)}>
                  <StarGlyph size={10} className={ui.primaryStar} />
                  {setupCopy.startBuild}
                </button>
                <p className={styles.quiet}>{setupCopy.statusNothingDownloaded}</p>
              </div>
            </>
          )}
        </section>
      </div>
    </Shell>
  );
}
