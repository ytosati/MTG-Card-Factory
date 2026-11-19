// Concept B "Drafting Table" (tasks.md T251): the Result screen, the card under review with callouts to its parts.
import type { CSSProperties, ReactNode } from "react";

import { resultCopy } from "../../../screens/result/copy";
import { cardWithImage } from "../../fixtures";
import type { PreviewCard } from "../../fixtureTypes";
import { CARD_PARTS, DraftCard, Pips } from "./DraftCard";
import type { CardPart } from "./DraftCard";
import { CropMarks, Mat, MatFooter, RegistrationMark, Sheet, TitleBlock } from "./parts";
import styles from "./result.module.css";

const COUNT = new Intl.NumberFormat("en-US");

/** The fixture card with art, given fictional design notes and comparables for the review. */
export const reviewCard: PreviewCard = {
  ...cardWithImage,
  current_version: {
    ...cardWithImage.current_version,
    design_intent:
      "A patient defender for a white deck that wins slowly: it holds the line and makes every other creature " +
      "a little harder to remove in combat.",
    rationale:
      "Four mana for a 2/4 with vigilance is fair on its own; the toughness bonus is small enough to stay common.",
    power_justification: "Close to other four-mana defenders; stronger only in decks with many small creatures.",
    comparables: [
      { oracle_id: "00000000-0000-4000-8000-0000000000b3", name: "Ashgrove Bannerman", role: "defensive anthem" },
      { oracle_id: "00000000-0000-4000-8000-0000000000b4", name: "Duskwall Keeper", role: "four-mana wall" },
    ],
  },
};

type Tone = "pass" | "fail" | "note";

interface Callout {
  part: CardPart;
  side: "left" | "right";
  label: string;
  value: ReactNode;
  check: { tone: Tone; text: string } | null;
}

function calloutsOf(card: PreviewCard): Callout[] {
  const version = card.current_version;
  const passed = new Set(version.validation.status === "approved" ? version.validation.checks_run : []);
  const lines = version.rules_text.split("\n").length;
  return [
    {
      part: "name",
      side: "left",
      label: "Name",
      value: version.name,
      check: { tone: "note", text: `${[...version.name].length} characters` },
    },
    {
      part: "cost",
      side: "right",
      label: "Mana cost",
      value: (
        <>
          {version.mana_cost !== null && <Pips cost={version.mana_cost} className={styles.notePips} />} mana value {version.mana_value}
        </>
      ),
      check: passed.has("mana_cost") ? { tone: "pass", text: "Mana cost check" } : null,
    },
    {
      part: "art",
      side: "left",
      label: "Art",
      value: card.image !== null ? "Generated, 745 × 1040 px" : "No art",
      check: { tone: "note", text: "Crop shown; open for the whole image" },
    },
    {
      part: "type",
      side: "right",
      label: "Type line",
      value: version.type_line,
      check: { tone: "note", text: `Rarity: ${version.rarity}` },
    },
    {
      part: "rules",
      side: "left",
      label: "Rules text",
      value: `${lines} ${lines === 1 ? "line" : "lines"}`,
      check: passed.has("color_identity") ? { tone: "pass", text: "Color identity check" } : null,
    },
    {
      part: "stats",
      side: "right",
      label: "Power / toughness",
      value: `${version.power ?? "–"} / ${version.toughness ?? "–"}`,
      check: { tone: "note", text: `Power indicator: ${resultCopy.powerWords[version.power_indicator]}` },
    },
  ];
}

const TONE_WORD: Record<Tone, string> = { pass: "Pass", fail: "Fail", note: "Note" };

export function ResultMockup() {
  const card = reviewCard;
  const version = card.current_version;
  const callouts = calloutsOf(card);
  const checks = version.validation.checks_run.length;
  const usage = card.usage.text;
  const totalIn = usage.reduce((sum, record) => sum + record.input_tokens, 0);
  const totalOut = usage.reduce((sum, record) => sum + record.output_tokens, 0);

  return (
    <Mat
      current="result"
      sheetLabel="Sheet 02 · Result"
      title={version.name}
      titleNote={`${resultCopy.approved} ${resultCopy.checksPassed(checks)}`}
    >
      <section className={styles.review} aria-labelledby="drafting-review">
        <h2 id="drafting-review" className={styles.reviewHeading}>
          Card under review <span>63 × 88 mm · scale 1:1.6</span>
        </h2>
        <RegistrationMark className={styles.regTl} />
        <RegistrationMark className={styles.regBr} />
        <div className={styles.cardRow}>
          <div className={styles.cardSlot}>
            <span className={styles.dimWidth} aria-hidden="true">
              <span>63 mm</span>
            </span>
            <span className={styles.dimHeight} aria-hidden="true">
              <span>88 mm</span>
            </span>
            <CropMarks />
            <DraftCard
              card={card}
              arrive
              markers={callouts.map((callout, index) => ({ part: callout.part, number: index + 1, side: callout.side }))}
            />
          </div>
          <ol className={styles.callouts} aria-label="Parts of the card">
            {callouts.map((callout, index) => (
              <li
                key={callout.part}
                className={styles.callout}
                data-side={callout.side}
                style={{ "--y": `${CARD_PARTS[callout.part]}%`, "--i": index } as CSSProperties}
              >
                <div className={styles.note}>
                  <p className={styles.noteLabel}>
                    <span className={styles.noteNum} aria-hidden="true">
                      {index + 1}
                    </span>
                    {callout.label}
                  </p>
                  <p className={styles.noteValue}>{callout.value}</p>
                  {callout.check !== null && (
                    <p className={styles.noteCheck} data-tone={callout.check.tone}>
                      <span className={styles.tag}>{TONE_WORD[callout.check.tone]}</span> {callout.check.text}
                    </p>
                  )}
                </div>
                <span className={styles.leader} aria-hidden="true" />
              </li>
            ))}
          </ol>
        </div>
      </section>

      <div className={styles.sheets}>
        <Sheet hold="pin" className={styles.pinned} aria-labelledby="drafting-power">
          <h2 id="drafting-power" className={styles.sheetTitle}>
            {resultCopy.powerHeading}
          </h2>
          <PowerGauge indicator={version.power_indicator} />
          <p>{version.power_justification || resultCopy.noJustification}</p>
          <p className={styles.hint}>{resultCopy.powerHint}</p>
        </Sheet>

        <Sheet hold="tape" className={styles.pinned} aria-labelledby="drafting-design">
          <h2 id="drafting-design" className={styles.sheetTitle}>
            Design notes
          </h2>
          <h3 className={styles.subTitle}>{resultCopy.intentHeading}</h3>
          <p>{version.design_intent || resultCopy.noIntent}</p>
          <h3 className={styles.subTitle}>{resultCopy.rationaleHeading}</h3>
          <p>{version.rationale || resultCopy.noRationale}</p>
          <h3 className={styles.subTitle}>{resultCopy.comparablesHeading}</h3>
          <ul className={styles.comparables}>
            {version.comparables.map((comparable) => (
              <li key={comparable.oracle_id}>
                <span>{comparable.name}</span> <span className={styles.role}>{comparable.role}</span>
              </li>
            ))}
          </ul>
        </Sheet>

        <Sheet hold="pin" className={styles.pinned} aria-labelledby="drafting-usage">
          <h2 id="drafting-usage" className={styles.sheetTitle}>
            {resultCopy.usageHeading}
          </h2>
          <table className={styles.usage}>
            <thead>
              <tr>
                <th scope="col">{resultCopy.usageCall}</th>
                <th scope="col">Model</th>
                <th scope="col">In</th>
                <th scope="col">Out</th>
              </tr>
            </thead>
            <tbody>
              {usage.map((record, index) => (
                <tr key={index}>
                  <th scope="row">{index + 1}</th>
                  <td>{record.model}</td>
                  <td>{COUNT.format(record.input_tokens)}</td>
                  <td>{COUNT.format(record.output_tokens)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row" colSpan={2}>
                  {resultCopy.usageTotal}
                </th>
                <td>{COUNT.format(totalIn)}</td>
                <td>{COUNT.format(totalOut)}</td>
              </tr>
            </tfoot>
          </table>
        </Sheet>
      </div>

      <div className={styles.closing}>
        <a className={styles.newRequest} href="#/request">
          New request
        </a>
        <TitleBlock
          className={styles.titleBlock}
          label="Title block of the card"
          cells={[
            { term: "Card", value: version.name, wide: true },
            { term: "Status", value: resultCopy.approved.replace(".", "") },
            { term: "Checks", value: `${checks} passed` },
            { term: "Rarity", value: version.rarity },
            { term: "Version", value: "1" },
          ]}
        />
      </div>
      <MatFooter>Concept B · Drafting Table · Result mockup with a fictional card</MatFooter>
    </Mat>
  );
}

/** The power indicator as a short scale: too weak, in range, too strong, with the reading marked by the pen. */
function PowerGauge({ indicator }: { indicator: keyof typeof resultCopy.powerWords }) {
  const order = ["too_weak", "in_range", "too_strong"] as const;
  return (
    <>
      <p className={styles.reading}>
        Reading: <strong>{resultCopy.powerWords[indicator]}</strong>
      </p>
      <div className={styles.gauge} aria-hidden="true">
        {order.map((step) => (
          <span key={step} className={styles.gaugeStep} data-on={step === indicator || undefined}>
            {resultCopy.powerWords[step]}
          </span>
        ))}
      </div>
    </>
  );
}
