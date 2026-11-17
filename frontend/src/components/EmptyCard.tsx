// A card-shaped area with no image yet, tinted with the card's colors like the frame of a printed card.
import type { ReactNode } from "react";

import { cx } from "./classNames";
import styles from "./EmptyCard.module.css";

const MANA_COLORS = ["W", "U", "B", "R", "G"];

/** The tint of a frame: one color, gold for two or more, grey for colorless, none when colors are unknown. */
function tintOf(colors: string[] | null): string | undefined {
  if (colors === null) return undefined;
  const known = MANA_COLORS.filter((color) => colors.includes(color));
  if (known.length > 1) return styles.multi;
  if (known.length === 1) return styles[`tint-${known.join("").toLowerCase()}`];
  return styles.colorless;
}

/** The colors written in a mana cost, such as W and B for {1}{W}{B}. */
export function colorsOfCost(cost: string | null): string[] {
  if (cost === null) return [];
  return MANA_COLORS.filter((color) => cost.toUpperCase().includes(color));
}

interface EmptyCardProps {
  /** The card's colors (W, U, B, R, G); an empty list is colorless and null leaves the area neutral. */
  colors: string[] | null;
  className?: string | undefined;
  /** Text for assistive technology, such as "No image"; the area itself is drawn only. */
  children?: ReactNode;
}

export function EmptyCard({ colors, className, children }: EmptyCardProps) {
  return <span className={cx(styles.card, tintOf(colors), className)}>{children}</span>;
}
