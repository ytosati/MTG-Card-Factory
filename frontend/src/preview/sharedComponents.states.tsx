// Preview states of the shared card components, with the fictional fixtures.
import { CardImageArea } from "../components/CardImageArea";
import { CardText } from "../components/CardText";
import { Notice } from "../components/Notice";
import { Screen } from "../components/Screen";
import { StepIndicator } from "../components/StepIndicator";
import {
  approvedCard,
  cardWithImage,
  cardWithoutImage,
  customArtVersion,
  designNotesCard,
  planeswalkerCard,
  rejectedCard,
} from "./fixtures";
import type { PreviewCard } from "./fixtureTypes";
import styles from "./sharedComponents.module.css";
import type { PreviewState } from "./types";

const GENERATION_STEPS = ["Write the card", "Check the rules", "Revise the card", "Assess the power"];

function cardText(card: PreviewCard) {
  return () => (
    <Screen>
      <h1>Card text</h1>
      <CardText version={card.current_version} />
    </Screen>
  );
}

export const sharedComponentStates: PreviewState[] = [
  { id: "card-text-approved", name: "Card text: approved card", render: cardText(approvedCard) },
  { id: "card-text-rejected", name: "Card text: rejected card", render: cardText(rejectedCard) },
  { id: "card-text-planeswalker", name: "Card text: planeswalker", render: cardText(planeswalkerCard) },
  { id: "card-text-design-notes", name: "Card text: card with design notes", render: cardText(designNotesCard) },
  {
    id: "card-image",
    name: "Card image: with an image",
    render: () => (
      <Screen>
        <h1>Card image</h1>
        <CardImageArea image={cardWithImage.image} cardName={cardWithImage.current_version.name} />
      </Screen>
    ),
  },
  {
    id: "card-image-art-version",
    name: "Card image: custom art version",
    render: () => (
      <Screen>
        <h1>Card image</h1>
        <CardImageArea image={customArtVersion.image} cardName={planeswalkerCard.current_version.name} />
      </Screen>
    ),
  },
  {
    id: "card-image-none",
    name: "Card image: no image",
    render: () => (
      <Screen>
        <h1>Card image</h1>
        <CardImageArea image={cardWithoutImage.image} cardName={cardWithoutImage.current_version.name} />
      </Screen>
    ),
  },
  {
    id: "steps",
    name: "Step indicator: second step running",
    render: () => (
      <Screen>
        <h1>Step indicator</h1>
        <StepIndicator label="Generation steps" steps={GENERATION_STEPS} current={1} />
      </Screen>
    ),
  },
  {
    id: "notices",
    name: "Notices: danger, notice and success",
    render: () => (
      <Screen>
        <h1>Notices</h1>
        <div className={styles.stack}>
          <Notice tone="danger" title="The card could not be saved.">
            <p>The data folder is not writable. Check its permissions, then try again.</p>
          </Notice>
          <Notice tone="notice">
            <p>The automatic revision did not complete. The card is shown as it was checked.</p>
          </Notice>
          <Notice tone="success">
            <p>The card passed every check.</p>
          </Notice>
        </div>
      </Screen>
    ),
  },
];
