// Concept E "Starfield" (tasks.md T251): the Studio, a layout test where Request, generation, reveal and Result are
// one page. The card holds the centre and never moves; only the elements around it change. Nothing is sent.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import type { PowerLevel } from "../../../api/types";
import { requestCopy } from "../../../screens/request/copy";
import { resultCopy } from "../../../screens/result/copy";
import type { PreviewCard } from "../../fixtureTypes";
import { FxLayers } from "../forge/fx/FxLayers";
import { ManaCostSymbols } from "../forge/symbols/ManaSymbol";
import { OutlineFace } from "./CardOutline";
import { CardBack, ChartCard, ChartInProgress, RulesText } from "./ChartCard";
import { Constellation } from "./Constellation";
import { StarGlyph } from "./glyphs";
import { EMPTY_DRAFT, IDEA_MAX, baseCardOf, lengthOf, starfieldCopy as copy, type RequestDraft } from "./model";
import { Choices, Count, parts } from "./parts";
import ready from "./ready.module.css";
import request from "./request.module.css";
import { AdvancedFields, ArtPicker, BaseCardPicker, missingOf, type Patch } from "./RequestScreen";
import result from "./result.module.css";
import { Comparables, PowerLine, UsageTable, Validation, type ResultExtras } from "./ResultScreen";
import { STAR_REVEAL, sceneCopy } from "./scenes";
import ui from "./screen.module.css";
import { Shell } from "./Shell";
import { StepConstellation } from "./StepConstellation";
import stepStyles from "./steps.module.css";
import styles from "./studio.module.css";

export type StudioPhase = "compose" | "generating" | "ready" | "result";

/** Time each generation step stays on screen in the mockup. */
const STEP_MS = 2000;
/** The pause after the last step before the card turns face down. */
const SETTLE_MS = 700;
/** How long the surrounding elements take to leave before the next phase's arrive. */
const LEAVE_MS = 240;
/** When the burst plays: at the turn of a casual or medium card, at the landing of a strong one. */
const BURST_DELAY_MS: Record<PowerLevel, number> = { casual: 240, medium: 300, strong: 760 };
/** When the result's elements arrive after the reveal: once the turn has landed. */
const RESULT_DELAY_MS: Record<PowerLevel, number> = { casual: 900, medium: 1100, strong: 1500 };
const STILL_RESULT_DELAY_MS = 450;

const EFFORTS = ["low", "medium", "high"] as const;

/** What each generation step does, in a few words, in the order of requestCopy.steps. */
const STEP_NOTES = [
  "What the card is for",
  "Cards like it in the database",
  "Name, cost, type and text",
  "The rules checks, run as code",
  "Fixes for any failed check",
  "The image in the frame",
];

/** A duration in seconds with one decimal, as the steps show it. */
function seconds(ms: number): string {
  return `${(Math.max(0, ms) / 1000).toFixed(1)} s`;
}

const studioCopy = {
  phasesLabel: "Phases",
  phases: [
    { value: "compose", name: "Request" },
    { value: "generating", name: "Generating" },
    { value: "ready", name: "Ready" },
    { value: "result", name: "Result" },
  ] as { value: StudioPhase; name: string }[],
  titles: { compose: "Request", generating: "Generating", ready: "Card ready", result: "Result" } as Record<StudioPhase, string>,
  studio: "Studio",
  stepRubric: (step: number, total: number): string => `Step ${String(step).padStart(2, "0")} / ${String(total).padStart(2, "0")}`,
  requestLabel: "Your request",
  generateAgain: "Generate again",
  openImage: "Open image",
  resultStatus: (name: string, approved: boolean): string => `Result: ${name}, ${approved ? "approved" : "rejected"}.`,
};

const TIER_WORDS: Record<PowerLevel, string> = { casual: "Casual", medium: "Medium", strong: "Strong" };

/** Whether motion is reduced, by the system setting or by the preview's ancestor switch. */
function motionReduced(node: HTMLElement | null): boolean {
  if (node?.closest('[data-reduced-motion="true"]')) return true;
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** A compact group of the Studio: its heading and note above, its controls below. */
function Panel({ title, note, wide, children }: { title: string; note?: string; wide?: boolean; children: (headingId: string) => ReactNode }) {
  const id = useId();
  return (
    <section className={styles.panel} data-wide={wide ? "true" : "false"} aria-labelledby={id}>
      <div className={styles.panelHead}>
        <h2 id={id} className={parts.heading}>
          <StarGlyph size={8} className={parts.headingStar} />
          {title}
        </h2>
        {note ? <p className={styles.panelNote}>{note}</p> : null}
      </div>
      {children(id)}
    </section>
  );
}

/** The four phases as a short line of stars: the passed ones lit, the current one ringed. */
function PhaseTrack({ phase }: { phase: StudioPhase }) {
  const current = studioCopy.phases.findIndex((entry) => entry.value === phase);
  return (
    <ol className={styles.track} aria-label={studioCopy.phasesLabel}>
      {studioCopy.phases.map((entry, index) => (
        <li key={entry.value} data-state={index < current ? "done" : index === current ? "current" : "waiting"} aria-current={index === current ? "step" : undefined}>
          <StarGlyph size={9} className={styles.trackStar} />
          <span className={styles.trackName}>{entry.name}</span>
        </li>
      ))}
    </ol>
  );
}

/** The settings of a new card on the left: the idea, the power level and the effort. */
function ComposeLeft({ draft, patch, ideaCountId }: { draft: RequestDraft; patch: Patch; ideaCountId: string }) {
  if (draft.kind === "custom-art") {
    return (
      <Panel title={copy.baseCardLabel} note={copy.required}>
        {() => <BaseCardPicker draft={draft} patch={patch} />}
      </Panel>
    );
  }
  const ideaLength = lengthOf(draft.idea);
  const power = requestCopy.powerLevels.find((level) => level.value === draft.powerLevel);
  return (
    <>
      <Panel title={requestCopy.fieldLabels.idea} note={copy.required}>
        {(headingId) => (
          <>
            <textarea
              className={`${request.idea} ${styles.idea}`}
              rows={4}
              value={draft.idea}
              aria-labelledby={headingId}
              aria-describedby={ideaCountId}
              aria-invalid={ideaLength > IDEA_MAX ? true : undefined}
              placeholder="A lighthouse keeper who trades memories with the tide"
              onChange={(event) => patch({ idea: event.target.value })}
            />
            <div className={request.countRow}>
              <Count id={ideaCountId} count={ideaLength} max={IDEA_MAX} text={requestCopy.characterCount(ideaLength, IDEA_MAX)} />
            </div>
          </>
        )}
      </Panel>
      <Panel title={requestCopy.fieldLabels.power_level} note={copy.required}>
        {(headingId) => (
          <>
            <Choices labelledBy={headingId} layout="inline" choices={requestCopy.powerLevels.map(({ value, name }) => ({ value, name }))} value={draft.powerLevel} onChange={(powerLevel) => patch({ powerLevel })} />
            {power ? <p className={parts.hint}>{power.meaning}</p> : null}
          </>
        )}
      </Panel>
      <Panel title={requestCopy.effortLabel}>
        {(headingId) => (
          <>
            <Choices labelledBy={headingId} layout="inline" choices={requestCopy.efforts.map(({ value, name }) => ({ value, name }))} value={draft.effort} onChange={(effort) => patch({ effort })} />
            <p className={request.tokenNote}>
              <span className={request.tokenMeter} aria-hidden="true">
                {EFFORTS.map((level, index) => (
                  <span key={level} data-on={index <= EFFORTS.indexOf(draft.effort) ? "true" : "false"} />
                ))}
              </span>
              {copy.tokens[draft.effort]}
            </p>
            <p className={parts.hint}>{requestCopy.efforts.find((level) => level.value === draft.effort)?.meaning}</p>
          </>
        )}
      </Panel>
    </>
  );
}

/** The settings on the right: the color identity, the request kind and the language side by side, then the art. */
function ComposeRight({ draft, patch, languageHintId, colorHintId }: { draft: RequestDraft; patch: Patch; languageHintId: string; colorHintId: string }) {
  const custom = draft.kind === "custom-art";
  return (
    <>
      {custom ? null : (
        <Panel title={requestCopy.fieldLabels.color_identity} note={copy.required}>
          {(headingId) => (
            <>
              <div className={styles.colors}>
                <Constellation colors={draft.colors} onChange={(colors) => patch({ colors })} labelledBy={headingId} describedBy={colorHintId} />
              </div>
              <p id={colorHintId} className={parts.hint}>
                {requestCopy.colorHint}
              </p>
            </>
          )}
        </Panel>
      )}
      <div className={styles.pairRow}>
        <Panel title={copy.kindLabel}>
          {(headingId) => (
            <Choices
              labelledBy={headingId}
              layout="inline"
              choices={copy.kinds}
              value={draft.kind}
              onChange={(kind) =>
                patch({ kind, baseCardId: null, printingId: null, faceIndex: 0, baseQuery: "", art: kind === "custom-art" ? "generated" : "none" })
              }
            />
          )}
        </Panel>
        {custom ? null : (
          <Panel title={requestCopy.languageLabel}>
            {(headingId) => (
              <>
                <Choices labelledBy={headingId} layout="inline" choices={requestCopy.languages} value={draft.language} onChange={(language) => patch({ language })} describedBy={languageHintId} />
                <p id={languageHintId} className={parts.hint}>
                  {requestCopy.languageHint}
                </p>
              </>
            )}
          </Panel>
        )}
      </div>
      <Panel title={copy.artLabel} note={custom ? copy.required : copy.optional}>
        {(headingId) => <ArtPicker draft={draft} patch={patch} labelledBy={headingId} />}
      </Panel>
    </>
  );
}

/** The settings along the bottom: the base card and the advanced options, both optional. */
function ComposeBottom({ draft, patch, advancedId }: { draft: RequestDraft; patch: Patch; advancedId: string }) {
  if (draft.kind === "custom-art") return null;
  return (
    <>
      <Panel title={copy.baseCardLabel} note={copy.optional}>
        {() => <BaseCardPicker draft={draft} patch={patch} />}
      </Panel>
      <section className={styles.panel} aria-labelledby={`${advancedId}-heading`}>
        <div className={styles.panelHead}>
          <h2 id={`${advancedId}-heading`} className={parts.heading}>
            <button type="button" className={request.disclosure} aria-expanded={draft.advancedOpen} aria-controls={advancedId} onClick={() => patch({ advancedOpen: !draft.advancedOpen })}>
              <StarGlyph size={8} className={request.disclosureStar} />
              {requestCopy.advancedToggle}
            </button>
          </h2>
          <p className={styles.panelNote}>{copy.optional}</p>
        </div>
        <div id={advancedId}>
          {draft.advancedOpen ? (
            <AdvancedFields draft={draft} patch={patch} />
          ) : (
            <p className={request.collapsed}>
              {[requestCopy.cardTypesLabel, requestCopy.supertypesLabel, requestCopy.subtypesLabel, requestCopy.manaValueLabel, `${requestCopy.powerLabel} and ${requestCopy.toughnessLabel.toLowerCase()}`, requestCopy.loyaltyLabel].join(" · ")}
            </p>
          )}
        </div>
      </section>
    </>
  );
}

/** The request as a quiet readout while the card is made: the idea, then each choice on a ruled row. */
function RequestReadout({ draft }: { draft: RequestDraft }) {
  const id = useId();
  const custom = draft.kind === "custom-art";
  const power = requestCopy.powerLevels.find((level) => level.value === draft.powerLevel);
  const effort = requestCopy.efforts.find((level) => level.value === draft.effort);
  const language = requestCopy.languages.find((entry) => entry.value === draft.language);
  const art = copy.arts.find((entry) => entry.value === draft.art);
  const base = baseCardOf(draft.baseCardId);
  const rows: { term: string; value: ReactNode }[] = custom
    ? [
        { term: copy.readings.base, value: base?.name ?? copy.readings.none },
        { term: copy.artLabel, value: art?.name },
      ]
    : [
        {
          term: requestCopy.fieldLabels.color_identity,
          value: draft.colors.length > 0 ? <ManaCostSymbols cost={draft.colors.map((color) => `{${color}}`).join("")} size={16} /> : copy.readings.unset,
        },
        { term: copy.readings.power, value: power?.name ?? copy.readings.unset },
        { term: copy.readings.effort, value: effort?.name },
        { term: copy.readings.language, value: language?.name },
        { term: copy.artLabel, value: art?.name },
        { term: copy.readings.base, value: base?.name ?? copy.readings.none },
      ];
  return (
    <section className={styles.readout} aria-labelledby={id}>
      <h2 id={id} className={ui.label}>
        {studioCopy.requestLabel}
      </h2>
      <p className={styles.summaryIdea}>{custom ? copy.customMark : draft.idea}</p>
      <dl className={styles.readings}>
        {rows.map((row) => (
          <div key={row.term}>
            <dt>{row.term}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** The card text in rules format, with its rarity and art. */
function RulesColumn({ entry, extras }: { entry: PreviewCard; extras: ResultExtras }) {
  const version = entry.current_version;
  const nameId = useId();
  return (
    <article className={styles.rules} aria-labelledby={nameId}>
      <div className={result.nameRow}>
        <h2 id={nameId} className={styles.cardName}>
          {version.name}
        </h2>
        {version.mana_cost ? <ManaCostSymbols cost={version.mana_cost} size={22} className={result.cost} /> : null}
      </div>
      <p className={result.typeLine}>{version.type_line}</p>
      <RulesText text={version.rules_text} className={`${result.rulesText} ${styles.rulesText}`} />
      {version.power !== null && version.toughness !== null ? (
        <p className={result.stat}>
          {version.power} / {version.toughness}
        </p>
      ) : extras.loyalty ? (
        <p className={result.stat}>Loyalty {extras.loyalty}</p>
      ) : null}
      <dl className={`${ui.facts} ${styles.facts}`}>
        <div>
          <dt>{sceneCopy.rarity}</dt>
          <dd className={result.capital}>{version.rarity}</dd>
        </div>
        <div>
          <dt>{sceneCopy.artist}</dt>
          <dd>{extras.art ? sceneCopy.artGenerated(extras.art.model) : sceneCopy.noArt}</dd>
        </div>
      </dl>
    </article>
  );
}

/** The verdicts on the right: the validation, the power indicator, then the cards it was compared against. */
function VerdictColumn({ entry, extras }: { entry: PreviewCard; extras: ResultExtras }) {
  const version = entry.current_version;
  return (
    <>
      <Validation version={version} />
      <PowerLine version={version} />
      <Comparables version={version} faces={extras.comparableFaces} />
    </>
  );
}

/** The design along the bottom: intent and rationale, the text usage and the notes. */
function DesignRow({ entry, extras }: { entry: PreviewCard; extras: ResultExtras }) {
  const version = entry.current_version;
  return (
    <>
      <Panel title={resultCopy.intentHeading}>
        {() => (
          <p className={result.prose} data-empty={version.design_intent ? "false" : "true"}>
            {version.design_intent || resultCopy.noIntent}
          </p>
        )}
      </Panel>
      <Panel title={resultCopy.rationaleHeading}>
        {() => (
          <p className={result.prose} data-empty={version.rationale ? "false" : "true"}>
            {version.rationale || resultCopy.noRationale}
          </p>
        )}
      </Panel>
      <Panel title={resultCopy.usageHeading}>{() => (entry.usage.text.length > 0 ? <UsageTable entry={entry} /> : <p className={result.quiet}>{resultCopy.noUsage}</p>)}</Panel>
      {extras.notes.length > 0 ? (
        <Panel title={sceneCopy.notesHeading}>
          {() => (
            <ul className={result.notes}>
              {extras.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </Panel>
      ) : null}
    </>
  );
}

/**
 * The Studio. `phase` drives the card and the live status at once; `around` is the phase of the surrounding
 * elements, which lags by the time the old ones take to leave, so they fade out before the new ones arrive.
 */
export function StudioScreen(props: { phase?: StudioPhase; initial?: Partial<RequestDraft>; entry: PreviewCard; extras: ResultExtras }) {
  const { entry, extras } = props;
  const start = props.phase ?? "compose";
  const [draft, setDraft] = useState<RequestDraft>({ ...EMPTY_DRAFT, ...props.initial });
  const [phase, setPhase] = useState<StudioPhase>(start);
  const [around, setAround] = useState<StudioPhase>(start);
  const [step, setStep] = useState(0);
  const [missing, setMissing] = useState<string[]>([]);
  const [revealed, setRevealed] = useState(start === "result");
  const [burst, setBurst] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const revealRef = useRef<HTMLButtonElement>(null);
  const firstAround = useRef(true);
  const ideaCountId = useId();
  const colorHintId = useId();
  const languageHintId = useId();
  const advancedId = useId();
  const stepsId = useId();

  const version = entry.current_version;
  const tier: PowerLevel = draft.powerLevel ?? "medium";
  const total = requestCopy.steps.length;
  const leaving = around !== phase;

  const patch: Patch = (change) => {
    setDraft((current) => ({ ...current, ...change }));
    setMissing([]);
  };

  // The page keeps room for a scroll bar in every phase, so its appearing never moves the card sideways.
  useEffect(() => {
    const root = document.documentElement;
    const before = root.style.getPropertyValue("scrollbar-gutter");
    root.style.setProperty("scrollbar-gutter", "stable");
    return () => {
      if (before) root.style.setProperty("scrollbar-gutter", before);
      else root.style.removeProperty("scrollbar-gutter");
    };
  }, []);

  useEffect(() => {
    document.title = `${studioCopy.studio} · Card Factory`;
  }, []);

  // The surrounding elements follow the phase once the old ones have left; without motion they swap at once.
  useEffect(() => {
    if (around === phase) return undefined;
    const timer = window.setTimeout(() => setAround(phase), motionReduced(rootRef.current) ? 0 : LEAVE_MS);
    return () => window.clearTimeout(timer);
  }, [around, phase]);

  // Focus follows the new elements: the reveal when the card is face down, otherwise the page title.
  useEffect(() => {
    if (firstAround.current) {
      firstAround.current = false;
      return;
    }
    if (around === "ready") revealRef.current?.focus();
    else titleRef.current?.focus();
  }, [around]);

  // The mockup walks the steps, then lets the card settle face down.
  useEffect(() => {
    if (phase !== "generating") return undefined;
    const timer = window.setTimeout(() => (step < total ? setStep(step + 1) : setPhase("ready")), step < total ? STEP_MS : SETTLE_MS);
    return () => window.clearTimeout(timer);
  }, [phase, step, total]);

  // The running step's time, counted from its start.
  useEffect(() => {
    if (phase !== "generating") return undefined;
    const started = Date.now();
    setElapsed(0);
    const timer = window.setInterval(() => setElapsed(Date.now() - started), 100);
    return () => window.clearInterval(timer);
  }, [phase, step]);

  // Once turned, the burst plays at its moment and the result's elements arrive when the turn has landed.
  useEffect(() => {
    if (!revealed || phase !== "ready") return undefined;
    const still = motionReduced(rootRef.current);
    const burstTimer = still ? undefined : window.setTimeout(() => setBurst(true), BURST_DELAY_MS[tier]);
    const resultTimer = window.setTimeout(() => setPhase("result"), still ? STILL_RESULT_DELAY_MS : RESULT_DELAY_MS[tier]);
    return () => {
      window.clearTimeout(burstTimer);
      window.clearTimeout(resultTimer);
    };
  }, [revealed, phase, tier]);

  function generate() {
    const gaps = missingOf(draft);
    setMissing(gaps);
    if (gaps.length > 0) return;
    setStep(0);
    setRevealed(false);
    setBurst(false);
    setPhase("generating");
  }

  function newRequest() {
    setRevealed(false);
    setBurst(false);
    setPhase("compose");
  }

  const approved = version.validation.status === "approved";
  const running = requestCopy.steps[step];
  const status =
    phase === "compose"
      ? missing.length > 0
        ? `${requestCopy.missingPrefix}${missing.join(", ")}.`
        : missingOf(draft).length === 0
          ? copy.ready
          : ""
      : phase === "generating"
        ? running
          ? requestCopy.stepOf(step + 1, total, running.name)
          : sceneCopy.generatedStatus
        : phase === "ready"
          ? revealed
            ? sceneCopy.revealed(version.name)
            : sceneCopy.readyLede
          : studioCopy.resultStatus(version.name, approved);

  const rubric =
    phase === "compose"
      ? `${studioCopy.studio} · ${draft.kind === "custom-art" ? copy.kinds[1]?.name : copy.kinds[0]?.name}`
      : phase === "generating"
        ? studioCopy.stepRubric(Math.min(step + 1, total), total)
        : phase === "ready"
          ? sceneCopy.readyRubric(TIER_WORDS[tier])
          : approved
            ? resultCopy.approved
            : resultCopy.rejected;

  const face = phase === "ready" || phase === "result";

  return (
    <Shell current="Request" speed={phase === "generating" ? "generating" : "rest"}>
      <div ref={rootRef} className={styles.page}>
        <header className={styles.head}>
          <div className={styles.headText}>
            <p className={`${ui.rubric} ${styles.rubric}`}>
              <StarGlyph size={8} className={ui.rubricStar} />
              {rubric}
            </p>
            <h1 ref={titleRef} tabIndex={-1} className={styles.title}>
              {studioCopy.titles[phase]}
            </h1>
          </div>
          <PhaseTrack phase={phase} />
        </header>

        <div className={styles.stage} data-phase={around}>
          {/* The card: one slot of fixed size; each phase draws a layer inside it and nothing outside moves it. */}
          <div className={styles.slot} data-studio-card="true">
            <span className={styles.orbit} data-on={phase === "generating" || phase === "ready" ? "true" : "false"} aria-hidden="true" />
            {phase === "compose" || phase === "generating" ? (
              <div className={`${styles.layer} ${styles.outline}`} aria-hidden={phase === "generating" ? "true" : undefined}>
                <OutlineFace draft={draft} generating={false} />
              </div>
            ) : null}
            {phase === "generating" || (phase === "ready" && !revealed) ? (
              <div className={styles.layer} data-out={phase === "ready" ? "true" : "false"}>
                <ChartInProgress step={step} colors={draft.kind === "custom-art" ? [] : draft.colors} />
              </div>
            ) : null}
            {face ? (
              <div className={`${styles.layer} ${styles.faceLayer} ${phase === "ready" ? styles.turnIn : ""}`}>
                {tier === "strong" && revealed && phase === "ready" ? <span className={ready.nova} aria-hidden="true" /> : null}
                <div className={`${ready.flipper} ${start === "result" ? styles.still : ""}`} data-tier={tier} data-revealed={revealed ? "true" : "false"}>
                  <div className={ready.back} aria-hidden="true">
                    <CardBack />
                  </div>
                  <div className={ready.front} aria-hidden={revealed ? undefined : "true"}>
                    <ChartCard version={version} image={entry.image} loyalty={extras.loyalty} textHidden={phase === "result"} />
                  </div>
                </div>
                {burst ? <FxLayers layers={STAR_REVEAL[tier]} scale={tier === "casual" ? 2 : 3} mode="once" className={ready.burst} /> : null}
              </div>
            ) : null}
          </div>

          <div className={styles.left} data-area="left" data-leaving={leaving ? "true" : "false"}>
            {around === "compose" ? <ComposeLeft draft={draft} patch={patch} ideaCountId={ideaCountId} /> : null}
            {around === "generating" ? <RequestReadout draft={draft} /> : null}
            {around === "result" ? <RulesColumn entry={entry} extras={extras} /> : null}
          </div>

          <div className={styles.right} data-area="right" data-leaving={leaving ? "true" : "false"}>
            {around === "compose" ? <ComposeRight draft={draft} patch={patch} languageHintId={languageHintId} colorHintId={colorHintId} /> : null}
            {around === "generating" ? (
              <section className={styles.steps} aria-labelledby={stepsId}>
                <h2 id={stepsId} className={ui.label}>
                  {requestCopy.stepsLabel}
                </h2>
                <StepConstellation
                  current={step}
                  labelledBy={stepsId}
                  label={(index, stepPhase) => (
                    <>
                      <span className={styles.stepText}>
                        <span className={stepStyles.name}>{requestCopy.steps[index]?.name}</span>
                        <span className={styles.stepNote}>{STEP_NOTES[index]}</span>
                      </span>
                      <span className={styles.stepTime} aria-hidden="true">
                        {stepPhase === "done" ? seconds(STEP_MS) : stepPhase === "running" ? seconds(elapsed) : "—"}
                      </span>
                    </>
                  )}
                />
              </section>
            ) : null}
            {around === "result" ? <VerdictColumn entry={entry} extras={extras} /> : null}
          </div>

          <div className={styles.bottom} data-area="bottom" data-leaving={leaving ? "true" : "false"}>
            {around === "compose" ? <ComposeBottom draft={draft} patch={patch} advancedId={advancedId} /> : null}
            {around === "result" ? <DesignRow entry={entry} extras={extras} /> : null}
          </div>

          <div className={styles.under}>
            <div className={styles.actions} data-area="under" data-leaving={leaving ? "true" : "false"}>
              {around === "compose" ? (
                <button type="button" className={request.generate} onClick={generate}>
                  <StarGlyph size={10} className={request.generateStar} />
                  {requestCopy.generate}
                </button>
              ) : null}
              {around === "generating" ? (
                <div className={styles.running} aria-hidden="true">
                  <span className={styles.runningName}>{running?.name ?? sceneCopy.generatedTitle}</span>
                  <span className={styles.progress}>
                    <span style={{ transform: `scaleX(${Math.min(step + 1, total) / total})` }} />
                  </span>
                </div>
              ) : null}
              {around === "ready" && !revealed ? (
                <button ref={revealRef} type="button" className={ui.primary} onClick={() => setRevealed(true)}>
                  <StarGlyph size={10} className={ui.primaryStar} />
                  {sceneCopy.reveal}
                </button>
              ) : null}
              {around === "result" ? (
                <>
                  <button type="button" className={ui.primary} onClick={newRequest}>
                    <StarGlyph size={10} className={ui.primaryStar} />
                    {sceneCopy.newRequest}
                  </button>
                  <button type="button" className={ui.secondary} onClick={generate}>
                    {studioCopy.generateAgain}
                  </button>
                  {entry.image ? (
                    <a className={ui.link} href={entry.image.src} target="_blank" rel="noreferrer">
                      {studioCopy.openImage}
                    </a>
                  ) : null}
                </>
              ) : null}
            </div>
            <p className={styles.status} role="status" aria-live="polite" data-tone={phase === "compose" && missing.length > 0 ? "missing" : "info"}>
              {status}
            </p>
          </div>
        </div>
      </div>
    </Shell>
  );
}
