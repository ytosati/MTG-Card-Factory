// Concept E "Starfield" (tasks.md T251): the complete Request screen as a local mockup; nothing is sent.
import { useEffect, useId, useState, type FormEvent } from "react";

import { requestCopy, type GenerationStep } from "../../../screens/request/copy";
import { ManaCostSymbols } from "../forge/symbols/ManaSymbol";
import { CardOutline } from "./CardOutline";
import { Constellation } from "./Constellation";
import { StarGlyph } from "./glyphs";
import {
  ART_DESCRIPTION_MAX,
  EMPTY_DRAFT,
  IDEA_MAX,
  baseCardOf,
  lengthOf,
  searchBaseCards,
  starfieldCopy as copy,
  type RequestDraft,
} from "./model";
import { Chips, Choices, Count, Field, Section, parts } from "./parts";
import styles from "./request.module.css";
import { Shell } from "./Shell";

/** Time each running step stays on screen in the mockup. */
const STEP_MS = 1800;

type Patch = (change: Partial<RequestDraft>) => void;

/** The running steps of this request: a custom art version has only art; art shows only when requested (RN-55). */
function stepsOf(draft: RequestDraft): { value: GenerationStep; name: string }[] {
  if (draft.kind === "custom-art") return requestCopy.steps.filter((step) => step.value === "art");
  return requestCopy.steps.filter((step) => step.value !== "art" || draft.art !== "none");
}

/** The required parts still missing, named as their fields. */
function missingOf(draft: RequestDraft): string[] {
  if (draft.kind === "custom-art") {
    const missing = draft.baseCardId ? [] : [copy.baseCardLabel];
    if (draft.art === "uploaded" && !draft.uploadName) missing.push(copy.artLabel);
    return missing;
  }
  const missing: string[] = [];
  if (draft.idea.trim() === "") missing.push(requestCopy.fieldLabels.idea);
  if (draft.colors.length === 0) missing.push(requestCopy.fieldLabels.color_identity);
  if (draft.powerLevel === null) missing.push(requestCopy.fieldLabels.power_level);
  return missing;
}

/** The base card: a search by name with its matches, then the chosen card's printing and face. */
function BaseCardPicker({ draft, patch }: { draft: RequestDraft; patch: Patch }) {
  const searchId = useId();
  const hintId = useId();
  const printingId = useId();
  const faceId = useId();
  const base = baseCardOf(draft.baseCardId);

  if (base) {
    return (
      <div className={styles.chosen}>
        <div className={styles.chosenHead}>
          <div>
            <p className={styles.chosenName}>{base.name}</p>
            <p className={styles.chosenType}>{base.faces.map((face) => face.typeLine).join(" // ")}</p>
          </div>
          <button type="button" className={styles.textButton} onClick={() => patch({ baseCardId: null, printingId: null, faceIndex: 0 })}>
            {copy.change}
            <span className={parts.srOnly}> {copy.baseCardLabel.toLowerCase()}</span>
          </button>
        </div>
        <div className={styles.selectRow}>
          <Field label={copy.printingLabel} htmlFor={printingId} wide>
            <select id={printingId} className={styles.select} value={draft.printingId ?? ""} onChange={(event) => patch({ printingId: event.target.value })}>
              {base.printings.map((printing) => (
                <option key={printing.id} value={printing.id}>
                  {printing.label}
                </option>
              ))}
            </select>
          </Field>
          {base.faces.length > 1 ? (
            <Field label={copy.faceLabel} htmlFor={faceId}>
              <select id={faceId} className={styles.select} value={draft.faceIndex} onChange={(event) => patch({ faceIndex: Number(event.target.value) })}>
                {base.faces.map((face, index) => (
                  <option key={face.name} value={index}>
                    {face.name}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
        </div>
      </div>
    );
  }

  const matches = searchBaseCards(draft.baseQuery, draft.kind);
  return (
    <div>
      <Field label={copy.searchLabel} htmlFor={searchId} hint={draft.kind === "custom-art" ? copy.oneFaceHint : copy.baseCardHint} hintId={hintId}>
        <span className={styles.searchWrap}>
          <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
            <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.2" />
            <path d="M11 11 L14.5 14.5" stroke="currentColor" strokeWidth="1.2" />
          </svg>
          <input
            id={searchId}
            type="search"
            className={`${styles.input} ${styles.search}`}
            placeholder={copy.searchPlaceholder}
            autoComplete="off"
            value={draft.baseQuery}
            aria-describedby={hintId}
            onChange={(event) => patch({ baseQuery: event.target.value })}
          />
        </span>
      </Field>
      {draft.baseQuery.trim() !== "" ? (
        matches.length > 0 ? (
          <ul className={styles.results} aria-label={copy.resultsLabel}>
            {matches.map((card) => (
              <li key={card.id}>
                <button
                  type="button"
                  className={styles.result}
                  onClick={() => patch({ baseCardId: card.id, printingId: card.printings[0]?.id ?? null, faceIndex: 0 })}
                >
                  <span className={styles.resultName}>{card.name}</span>
                  <span className={styles.resultType}>{card.faces.map((face) => face.typeLine).join(" // ")}</span>
                  {card.faces[0]?.cost ? <ManaCostSymbols cost={card.faces[0].cost} size={16} className={styles.resultCost} /> : null}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.noMatch} role="status">
            {copy.noMatch}
          </p>
        )
      ) : null}
    </div>
  );
}

/** The art: none, generated with an optional description and the billing notice, or an uploaded image. */
function ArtPicker({ draft, patch, labelledBy }: { draft: RequestDraft; patch: Patch; labelledBy: string }) {
  const descriptionId = useId();
  const countId = useId();
  const hintId = useId();
  const fileId = useId();
  const fileHintId = useId();
  const choices = draft.kind === "custom-art" ? copy.arts.filter((art) => art.value !== "none") : copy.arts;
  const length = lengthOf(draft.artDescription);

  return (
    <div className={styles.stack}>
      <Choices labelledBy={labelledBy} layout="inline" choices={choices} value={draft.art} onChange={(art) => patch({ art })} />
      {draft.art === "generated" ? (
        <div className={styles.reveal}>
          <Field label={copy.artDescriptionLabel} htmlFor={descriptionId} hint={copy.artDescriptionHint} hintId={hintId}>
            <textarea
              id={descriptionId}
              className={`${styles.input} ${styles.artDescription}`}
              rows={2}
              value={draft.artDescription}
              aria-describedby={`${countId} ${hintId}`}
              onChange={(event) => patch({ artDescription: event.target.value })}
            />
          </Field>
          <div className={styles.countRow}>
            <Count id={countId} count={length} max={ART_DESCRIPTION_MAX} text={requestCopy.characterCount(length, ART_DESCRIPTION_MAX)} />
          </div>
          <p className={styles.billing}>
            <StarGlyph size={8} className={styles.billingStar} />
            {copy.billing}
          </p>
        </div>
      ) : null}
      {draft.art === "uploaded" ? (
        <div className={`${styles.reveal} ${styles.upload}`}>
          <input
            id={fileId}
            type="file"
            className={`${parts.srOnly} ${styles.fileInput}`}
            accept="image/png,image/jpeg,image/webp"
            aria-describedby={fileHintId}
            onChange={(event) => patch({ uploadName: event.target.files?.[0]?.name ?? null })}
          />
          <label htmlFor={fileId} className={styles.fileButton}>
            {copy.uploadAction}
          </label>
          <span className={styles.fileName} data-empty={draft.uploadName ? "false" : "true"}>
            {draft.uploadName ?? copy.uploadNone}
          </span>
          <p id={fileHintId} className={styles.fileHint}>
            {copy.uploadHint}
          </p>
        </div>
      ) : null}
    </div>
  );
}

/** The advanced options, every one optional (RN-54). */
function AdvancedFields({ draft, patch }: { draft: RequestDraft; patch: Patch }) {
  const subtypesId = useId();
  const subtypesHint = useId();
  const manaValueId = useId();
  const manaValueHint = useId();
  const powerId = useId();
  const toughnessId = useId();
  const statsHint = useId();
  const loyaltyId = useId();
  const loyaltyHint = useId();

  return (
    <div className={`${styles.stack} ${styles.reveal}`}>
      <p className={styles.lede}>{requestCopy.advancedHint}</p>
      <Chips legend={requestCopy.cardTypesLabel} options={requestCopy.cardTypes} value={draft.cardTypes} onChange={(cardTypes) => patch({ cardTypes })} />
      <Chips legend={requestCopy.supertypesLabel} options={requestCopy.supertypes} value={draft.supertypes} onChange={(supertypes) => patch({ supertypes })} />
      <div className={styles.grid}>
        <Field label={requestCopy.subtypesLabel} htmlFor={subtypesId} hint={requestCopy.subtypesHint} hintId={subtypesHint} wide>
          <input id={subtypesId} className={styles.input} value={draft.subtypes} aria-describedby={subtypesHint} onChange={(event) => patch({ subtypes: event.target.value })} />
        </Field>
        <Field label={requestCopy.manaValueLabel} htmlFor={manaValueId} hint={requestCopy.manaValueHint} hintId={manaValueHint}>
          <input id={manaValueId} className={`${styles.input} ${styles.number}`} type="number" min={0} max={16} step={1} inputMode="numeric" value={draft.manaValue} aria-describedby={manaValueHint} onChange={(event) => patch({ manaValue: event.target.value })} />
        </Field>
        <div className={styles.pair}>
          <div className={styles.pairFields}>
            <Field label={requestCopy.powerLabel} htmlFor={powerId}>
              <input id={powerId} className={`${styles.input} ${styles.number}`} type="number" min={0} max={99} step={1} inputMode="numeric" value={draft.power} aria-describedby={statsHint} onChange={(event) => patch({ power: event.target.value })} />
            </Field>
            <span className={styles.slash} aria-hidden="true">
              /
            </span>
            <Field label={requestCopy.toughnessLabel} htmlFor={toughnessId}>
              <input id={toughnessId} className={`${styles.input} ${styles.number}`} type="number" min={0} max={99} step={1} inputMode="numeric" value={draft.toughness} aria-describedby={statsHint} onChange={(event) => patch({ toughness: event.target.value })} />
            </Field>
          </div>
          <p id={statsHint} className={parts.hint}>
            {requestCopy.powerToughnessHint}
          </p>
        </div>
        <Field label={requestCopy.loyaltyLabel} htmlFor={loyaltyId} hint={requestCopy.loyaltyHint} hintId={loyaltyHint}>
          <input id={loyaltyId} className={`${styles.input} ${styles.number}`} type="number" min={1} max={99} step={1} inputMode="numeric" value={draft.loyalty} aria-describedby={loyaltyHint} onChange={(event) => patch({ loyalty: event.target.value })} />
        </Field>
      </div>
    </div>
  );
}

/** The Request screen: the request on the left in editorial rows, the observatory with the card outline on the right. */
export function RequestScreen({ initial }: { initial?: Partial<RequestDraft> }) {
  const [draft, setDraft] = useState<RequestDraft>({ ...EMPTY_DRAFT, ...initial });
  const [step, setStep] = useState<number | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const ideaCountId = useId();
  const colorHintId = useId();
  const languageHintId = useId();
  const advancedId = useId();
  const statusId = useId();
  const patch: Patch = (change) => {
    setDraft((current) => ({ ...current, ...change }));
    setMissing([]);
  };

  const steps = stepsOf(draft);
  const generating = step !== null;
  const custom = draft.kind === "custom-art";
  const ideaLength = lengthOf(draft.idea);

  useEffect(() => {
    document.title = `${requestCopy.title} · Card Factory`;
  }, []);

  useEffect(() => {
    if (step === null || step >= steps.length - 1) return undefined;
    const timer = window.setTimeout(() => setStep(step + 1), STEP_MS);
    return () => window.clearTimeout(timer);
  }, [step, steps.length]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const gaps = missingOf(draft);
    setMissing(gaps);
    if (gaps.length === 0) setStep(0);
  }

  const running = step !== null ? steps[Math.min(step, steps.length - 1)] : undefined;

  return (
    <Shell current="Request" speed={generating ? "generating" : "rest"}>
      <div className={styles.page}>
        <header className={styles.head}>
          <div>
            <h1 className={styles.title}>{requestCopy.title}</h1>
            <p className={styles.summary}>{custom ? copy.customSummary : requestCopy.summary}</p>
          </div>
          <div className={styles.kind}>
            <span id="sf-kind" className={parts.srOnly}>
              {copy.kindLabel}
            </span>
            <Choices
              labelledBy="sf-kind"
              layout="inline"
              choices={copy.kinds}
              value={draft.kind}
              onChange={(kind) =>
                patch({
                  kind,
                  baseCardId: null,
                  printingId: null,
                  faceIndex: 0,
                  baseQuery: "",
                  art: kind === "custom-art" ? "generated" : "none",
                })
              }
            />
          </div>
        </header>

        <div className={styles.layout}>
          <form className={styles.form} onSubmit={submit} noValidate>
            {custom ? null : (
              <>
                <Section id="sf-idea" title={requestCopy.fieldLabels.idea} note={copy.required}>
                  <textarea
                    className={styles.idea}
                    rows={3}
                    value={draft.idea}
                    aria-labelledby="sf-idea"
                    aria-describedby={ideaCountId}
                    aria-invalid={ideaLength > IDEA_MAX ? true : undefined}
                    placeholder="A lighthouse keeper who trades memories with the tide"
                    onChange={(event) => patch({ idea: event.target.value })}
                  />
                  <div className={styles.countRow}>
                    <Count id={ideaCountId} count={ideaLength} max={IDEA_MAX} text={requestCopy.characterCount(ideaLength, IDEA_MAX)} />
                  </div>
                </Section>

                <Section id="sf-colors" title={requestCopy.fieldLabels.color_identity} note={copy.required}>
                  <Constellation colors={draft.colors} onChange={(colors) => patch({ colors })} labelledBy="sf-colors" describedBy={colorHintId} />
                  <p id={colorHintId} className={parts.hint}>
                    {requestCopy.colorHint}
                  </p>
                </Section>

                <Section id="sf-power" title={requestCopy.fieldLabels.power_level} note={copy.required}>
                  <Choices labelledBy="sf-power" choices={requestCopy.powerLevels} value={draft.powerLevel} onChange={(powerLevel) => patch({ powerLevel })} />
                </Section>

                <Section id="sf-effort" title={requestCopy.effortLabel}>
                  <Choices labelledBy="sf-effort" choices={requestCopy.efforts} value={draft.effort} onChange={(effort) => patch({ effort })} />
                </Section>

                <Section id="sf-language" title={requestCopy.languageLabel}>
                  <Choices
                    labelledBy="sf-language"
                    layout="inline"
                    choices={requestCopy.languages}
                    value={draft.language}
                    onChange={(language) => patch({ language })}
                    describedBy={languageHintId}
                  />
                  <p id={languageHintId} className={parts.hint}>
                    {requestCopy.languageHint}
                  </p>
                </Section>
              </>
            )}

            <Section id="sf-base" title={copy.baseCardLabel} note={custom ? copy.required : copy.optional}>
              <BaseCardPicker draft={draft} patch={patch} />
            </Section>

            <Section id="sf-art" title={copy.artLabel} note={custom ? copy.required : copy.optional}>
              <ArtPicker draft={draft} patch={patch} labelledBy="sf-art" />
            </Section>

            {custom ? null : (
              <section className={`${parts.section} ${styles.advanced}`} aria-labelledby="sf-advanced">
                <div className={parts.margin}>
                  <h2 id="sf-advanced" className={parts.heading}>
                    <button type="button" className={styles.disclosure} aria-expanded={draft.advancedOpen} aria-controls={advancedId} onClick={() => patch({ advancedOpen: !draft.advancedOpen })}>
                      <StarGlyph size={8} className={styles.disclosureStar} />
                      {requestCopy.advancedToggle}
                    </button>
                  </h2>
                  <p className={parts.note}>{copy.optional}</p>
                </div>
                <div id={advancedId} className={parts.body}>
                  {draft.advancedOpen ? (
                    <AdvancedFields draft={draft} patch={patch} />
                  ) : (
                    <p className={styles.collapsed}>
                      {[requestCopy.cardTypesLabel, requestCopy.supertypesLabel, requestCopy.subtypesLabel, requestCopy.manaValueLabel, `${requestCopy.powerLabel} and ${requestCopy.toughnessLabel.toLowerCase()}`, requestCopy.loyaltyLabel].join(" · ")}
                    </p>
                  )}
                </div>
              </section>
            )}

            <div className={styles.action}>
              <button type="submit" className={styles.generate} disabled={generating} aria-describedby={statusId}>
                <StarGlyph size={10} className={styles.generateStar} />
                {generating ? requestCopy.generating : requestCopy.generate}
              </button>
              <p id={statusId} className={styles.status} aria-live="polite" data-tone={missing.length > 0 ? "missing" : "info"}>
                {missing.length > 0
                  ? `${requestCopy.missingPrefix}${missing.join(", ")}.`
                  : running
                    ? requestCopy.stepOf((step ?? 0) + 1, steps.length, running.name)
                    : missingOf(draft).length === 0
                      ? copy.ready
                      : ""}
              </p>
            </div>
          </form>

          <aside className={styles.observatory}>
            <CardOutline draft={draft} generating={generating} />
          </aside>
        </div>
      </div>
    </Shell>
  );
}
