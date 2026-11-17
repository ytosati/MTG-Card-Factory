// Preview of the design direction: a sample of the list and table language, built from the fixtures.
// Details: frontend/DESIGN.md, "Lists and tables"; specs/tasks.md, T180. Not a screen: Library and Deck follow it.
import { useId } from "react";

import { EmptyCard, colorsOfCost } from "../components/EmptyCard";
import { Image } from "../components/Image";
import { ManaCost } from "../components/ManaCost";
import { Screen, screenStyles } from "../components/Screen";
import { VisuallyHidden } from "../components/VisuallyHidden";
import { cx } from "../components/classNames";
import styles from "./direction.module.css";
import {
  approvedCard,
  cardWithImage,
  cardWithoutImage,
  customArtVersion,
  designNotesCard,
  planeswalkerCard,
  rejectedCard,
} from "./fixtures";
import type { PreviewCard, PreviewImage } from "./fixtureTypes";
import type { PreviewState } from "./types";

/** The size of the stored card images; it reserves the thumbnail while the file loads. */
const CARD_IMAGE_WIDTH = 745;
const CARD_IMAGE_HEIGHT = 1040;

const RARITY_WORDS: Record<string, string> = {
  common: "Common",
  uncommon: "Uncommon",
  rare: "Rare",
  mythic: "Mythic",
};

/** Deck groups in the order a deck list prints them; the first type found in the type line decides. */
const DECK_GROUPS: [type: string, group: string][] = [
  ["Planeswalker", "Planeswalkers"],
  ["Creature", "Creatures"],
  ["Artifact", "Artifacts"],
  ["Enchantment", "Enchantments"],
  ["Instant", "Instants"],
  ["Sorcery", "Sorceries"],
  ["Land", "Lands"],
];

/** One saved entry of the sample list: a card or a custom art version of one, with the marks it carries. */
interface ListEntry {
  key: string;
  card: PreviewCard;
  image: PreviewImage | null;
  favorite: boolean;
  /** The number of the custom art version, or null for the card itself. */
  artVersion: number | null;
}

const LIST: ListEntry[] = [
  { key: "sentry", card: cardWithImage, image: cardWithImage.image, favorite: true, artVersion: null },
  {
    key: "ilvara-art",
    card: planeswalkerCard,
    image: customArtVersion.image,
    favorite: false,
    artVersion: customArtVersion.number,
  },
  { key: "ilvara", card: planeswalkerCard, image: planeswalkerCard.image, favorite: true, artVersion: null },
  { key: "archivist", card: designNotesCard, image: designNotesCard.image, favorite: false, artVersion: null },
  { key: "pathfinder", card: approvedCard, image: approvedCard.image, favorite: false, artVersion: null },
  { key: "ferryman", card: cardWithoutImage, image: cardWithoutImage.image, favorite: false, artVersion: null },
];

const DECK: PreviewCard[] = [
  planeswalkerCard,
  approvedCard,
  rejectedCard,
  designNotesCard,
  cardWithImage,
  cardWithoutImage,
];

function rarityOf(rarity: string): { word: string; mark: string | undefined } {
  return { word: RARITY_WORDS[rarity] ?? rarity, mark: styles[`rarity-${rarity}`] ?? styles["rarity-common"] };
}

function groupOf(typeLine: string): string {
  return DECK_GROUPS.find(([type]) => typeLine.includes(type))?.[1] ?? "Other";
}

/** The deck as groups in print order, each sorted by mana value, then name. */
function deckGroups(cards: PreviewCard[]): { name: string; cards: PreviewCard[] }[] {
  const order = [...DECK_GROUPS.map(([, group]) => group), "Other"];
  return order
    .map((name) => ({
      name,
      cards: cards
        .filter((card) => groupOf(card.current_version.type_line) === name)
        .sort(
          (a, b) =>
            a.current_version.mana_value - b.current_version.mana_value ||
            a.current_version.name.localeCompare(b.current_version.name),
        ),
    }))
    .filter((group) => group.cards.length > 0);
}

/** The card's image, or, without one, an empty card tinted with the colors of its cost. */
function Thumbnail({ image, cost }: { image: PreviewImage | null; cost: string | null }) {
  if (image === null) {
    return (
      <EmptyCard colors={colorsOfCost(cost)} className={cx(styles.thumb, styles.thumbEmpty)}>
        <VisuallyHidden>No image</VisuallyHidden>
      </EmptyCard>
    );
  }
  return (
    <span className={styles.thumb}>
      <Image
        className={styles.thumbImage}
        src={image.src}
        alt={image.alt}
        width={CARD_IMAGE_WIDTH}
        height={CARD_IMAGE_HEIGHT}
      />
    </span>
  );
}

function FavoriteMark() {
  return (
    <span className={styles.favorite} title="Favorite">
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
        <path d="M8 1.5 9.9 5.6l4.4.5-3.3 3 .9 4.4L8 11.3l-3.9 2.2.9-4.4-3.3-3 4.4-.5Z" fill="currentColor" />
      </svg>
      <VisuallyHidden>Favorite</VisuallyHidden>
    </span>
  );
}

// The spaces between blocks keep words apart when the list is copied or read as one string.
function CardRow({ entry }: { entry: ListEntry }) {
  const version = entry.card.current_version;
  const rarity = rarityOf(version.rarity);
  return (
    <li className={styles.cardRow}>
      <Thumbnail image={entry.image} cost={version.mana_cost} />{" "}
      <div className={styles.identity}>
        <p className={styles.cardName}>{version.name}</p> <p className={styles.typeLine}>{version.type_line}</p>
      </div>{" "}
      <div className={styles.cost}>{version.mana_cost !== null && <ManaCost cost={version.mana_cost} />}</div>{" "}
      <div className={styles.facts}>
        <p className={styles.rarity}>
          <span className={cx(styles.rarityMark, rarity.mark)} aria-hidden="true" />
          {rarity.word}
        </p>{" "}
        <p className={styles.marks}>
          {entry.artVersion !== null && <span className={styles.tag}>{`Art version ${entry.artVersion}`}</span>}{" "}
          {entry.favorite && <FavoriteMark />}
        </p>
      </div>
    </li>
  );
}

function DeckTable({ labelledBy }: { labelledBy: string }) {
  const groups = deckGroups(DECK);
  return (
    <table className={styles.deck} aria-labelledby={labelledBy}>
      <thead>
        <tr>
          <th scope="col" className={styles.count}>
            Count
          </th>
          <th scope="col">Name</th>
          <th scope="col" className={styles.costColumn}>
            Cost
          </th>
          <th scope="col" className={styles.typeColumn}>
            Type
          </th>
        </tr>
      </thead>
      {groups.map((group) => (
        <tbody key={group.name}>
          <tr className={styles.group}>
            <th scope="rowgroup" colSpan={4}>
              {group.name} <span className={styles.groupCount}>({group.cards.length})</span>
            </th>
          </tr>
          {group.cards.map((card) => (
            <tr key={card.id} className={styles.deckRow}>
              <td className={styles.count}>1</td>
              <th scope="row" className={styles.deckName}>
                {card.current_version.name}{" "}
                <span className={styles.typeInline}>{card.current_version.type_line}</span>
              </th>
              <td className={styles.costColumn}>
                {card.current_version.mana_cost !== null && <ManaCost cost={card.current_version.mana_cost} />}
              </td>
              <td className={styles.typeColumn}>{card.current_version.type_line}</td>
            </tr>
          ))}
        </tbody>
      ))}
      <tfoot>
        <tr>
          <td className={styles.count}>{DECK.length}</td>
          <th scope="row" colSpan={3}>
            Cards in the deck
          </th>
        </tr>
      </tfoot>
    </table>
  );
}

function CardListSample() {
  const ids = useId();
  return (
    <Screen>
      <h1>List and table sample</h1>
      <p className={screenStyles.summary}>
        The list and table language of the design direction, drawn from the preview fixtures. The Library and Deck
        screens follow it; this page is neither of them.
      </p>
      <section className={styles.sample} aria-labelledby={`${ids}-cards`}>
        <h2 id={`${ids}-cards`}>Saved cards</h2>
        <ul className={styles.cardList}>
          {LIST.map((entry) => (
            <CardRow key={entry.key} entry={entry} />
          ))}
        </ul>
      </section>
      <section className={styles.sample} aria-labelledby={`${ids}-deck`}>
        <h2 id={`${ids}-deck`}>Deck list</h2>
        <DeckTable labelledBy={`${ids}-deck`} />
      </section>
    </Screen>
  );
}

export const directionStates: PreviewState[] = [
  { id: "card-list", name: "Card list and deck table", render: () => <CardListSample /> },
];
