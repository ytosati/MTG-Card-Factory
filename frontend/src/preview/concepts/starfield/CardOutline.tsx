// Concept E "Starfield" (tasks.md T251): the observatory: an empty card outline that follows the request as it is filled.
import { useId, type CSSProperties } from "react";

import { requestCopy } from "../../../screens/request/copy";
import { RUNE_WRITE } from "../forge/fx/effects";
import { PixelFx } from "../forge/fx/PixelFx";
import { ManaCostSymbols } from "../forge/symbols/ManaSymbol";
import type { ManaColor } from "../forge/symbols/manaSymbols";
import styles from "./card.module.css";
import { baseCardOf, starfieldCopy as copy, type RequestDraft } from "./model";

type Vars = CSSProperties & Record<`--${string}`, string>;

const ORDER: ManaColor[] = ["W", "U", "B", "R", "G", "C"];

/** The violet and cyan ramp the rune writing is drawn in, dark to bright. */
const STARLIGHT_RUNES = ["#140a26", "#2b1252", "#481c88", "#8b3dff", "#b07cff", "#5bd2fe", "#c8f0ff", "#ffffff"];

/**
 * The frame's line in the chosen colors: one color tints it whole, several split it into equal hard bands in
 * W U B R G order, so the frame reads as the identity rather than as a decoration.
 */
export function frameOf(colors: readonly ManaColor[]): string {
  const chosen = ORDER.filter((color) => colors.includes(color));
  if (chosen.length === 0) return "var(--sf-rule-strong)";
  const tint = (color: ManaColor) => `var(--sf-tint-${color.toLowerCase()})`;
  if (chosen.length === 1) return tint(chosen[0]!);
  const share = 100 / chosen.length;
  const stops = chosen.map((color, index) => `${tint(color)} ${index * share}% ${(index + 1) * share}%`);
  return `linear-gradient(135deg, ${stops.join(", ")})`;
}

function typeLineOf(draft: RequestDraft): string | null {
  const types = [...draft.supertypes, ...draft.cardTypes].join(" ");
  const subtypes = draft.subtypes
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .join(" ");
  if (!types && !subtypes) return null;
  return subtypes ? `${types || "…"} — ${subtypes}` : types;
}

function artLabelOf(draft: RequestDraft): string {
  if (draft.art === "generated") return copy.generatedArt;
  if (draft.art === "uploaded") return draft.uploadName ?? copy.uploadedArt;
  return copy.noArt;
}

/** The outline of the card to come, then the request's readings beneath it. */
export function CardOutline({ draft, generating }: { draft: RequestDraft; generating: boolean }) {
  const titleId = useId();
  const base = baseCardOf(draft.baseCardId);
  const custom = draft.kind === "custom-art";
  const face = base?.faces[draft.faceIndex] ?? base?.faces[0];
  const typeLine = custom ? face?.typeLine ?? null : typeLineOf(draft);
  const hasPowerToughness = !custom && (draft.power !== "" || draft.toughness !== "");
  const hasLoyalty = !custom && draft.loyalty !== "";
  const power = requestCopy.powerLevels.find((level) => level.value === draft.powerLevel);
  const effort = requestCopy.efforts.find((level) => level.value === draft.effort);
  const language = requestCopy.languages.find((entry) => entry.value === draft.language);
  const printing = base?.printings.find((entry) => entry.id === draft.printingId);

  return (
    <section className={styles.stage} aria-labelledby={titleId}>
      <div className={styles.stageHead}>
        <h2 id={titleId} className={styles.stageTitle}>
          {copy.outlineLabel}
        </h2>
        <span className={styles.measure} aria-hidden="true">
          63 × 88
        </span>
      </div>

      <div className={styles.cardWrap}>
        <div className={styles.frame} style={{ "--frame": frameOf(custom ? [] : draft.colors) } as Vars} data-generating={generating ? "true" : "false"}>
          <div className={styles.card}>
            <div className={styles.titleBar}>
              <span className={styles.name} data-empty={custom && face ? "false" : "true"}>
                {custom && face ? face.name : copy.untitled}
              </span>
              {custom && face?.cost ? (
                <ManaCostSymbols cost={face.cost} size="4.6cqi" />
              ) : !custom && draft.manaValue !== "" ? (
                <span className={styles.manaValue}>{draft.manaValue}</span>
              ) : null}
            </div>
            <div className={styles.art} data-art={draft.art}>
              <span className={styles.artLabel}>{artLabelOf(draft)}</span>
            </div>
            <div className={styles.typeBar} data-empty={typeLine ? "false" : "true"}>
              {typeLine ?? copy.freeType}
            </div>
            <div className={styles.textBox}>
              {custom ? (
                <span className={styles.customMark}>{copy.customMark}</span>
              ) : (
                <p className={styles.idea} data-empty={draft.idea ? "false" : "true"}>
                  {draft.idea || copy.noIdea}
                </p>
              )}
              {generating ? (
                <span className={styles.runes} aria-hidden="true">
                  <PixelFx effect={RUNE_WRITE.effect} options={{ ...RUNE_WRITE.options, palette: STARLIGHT_RUNES }} width={RUNE_WRITE.width} height={RUNE_WRITE.height} scale={2} mode="loop" />
                </span>
              ) : null}
            </div>
            <div className={styles.footLine}>
              <span className={styles.lang}>{draft.language === "pt-BR" ? "PT-BR" : "EN"}</span>
              {hasPowerToughness ? (
                <span className={styles.stat}>
                  {draft.power || "?"} / {draft.toughness || "?"}
                </span>
              ) : hasLoyalty ? (
                <span className={styles.stat}>{draft.loyalty}</span>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <dl className={styles.readings}>
        {custom ? null : (
          <>
            <div>
              <dt>{copy.readings.power}</dt>
              <dd>{power?.name ?? copy.readings.unset}</dd>
            </div>
            <div>
              <dt>{copy.readings.effort}</dt>
              <dd>{effort?.name}</dd>
            </div>
            <div>
              <dt>{copy.readings.language}</dt>
              <dd>{language?.name}</dd>
            </div>
          </>
        )}
        <div>
          <dt>{copy.readings.base}</dt>
          <dd>{base ? (printing ? `${face?.name ?? base.name}, ${printing.label}` : base.name) : copy.readings.none}</dd>
        </div>
      </dl>
    </section>
  );
}
