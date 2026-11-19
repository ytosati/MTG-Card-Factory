// Preview states of concept D (Forge), the refined Nocturne direction. Task T251.
import { approvedCard, cardWithImage, customArtVersion, planeswalkerCard } from "../../fixtures";
import type { PreviewCard } from "../../fixtureTypes";
import type { PreviewState } from "../../types";
import { FxBench } from "./FxBench";
import { GoblinSheet } from "./goblins/GoblinSheet";
import { MachineBench } from "./MachineBench";
import { GeneratingScreen } from "./screens/GeneratingScreen";
import { ReadyScreen } from "./screens/ReadyScreen";
import { RequestScreen } from "./screens/RequestScreen";
import { ResultScreen } from "./screens/ResultScreen";
import { SymbolSheet } from "./SymbolSheet";

/** The fictional planeswalker with its custom art, for the strong reveal. */
const CASUAL_CARD: PreviewCard = {
  ...approvedCard,
  image: cardWithImage.image && { ...cardWithImage.image, alt: `${approvedCard.current_version.name}, card art` },
};

const STRONG_CARD: PreviewCard = {
  ...planeswalkerCard,
  image: { src: customArtVersion.image.src, alt: `${planeswalkerCard.current_version.name}, card art` },
};

export const forgeStates: PreviewState[] = [
  { id: "request", name: "Request", render: () => <RequestScreen /> },
  { id: "generating", name: "Generating", render: () => <GeneratingScreen /> },
  { id: "ready-casual", name: "Ready, casual reveal", render: () => <ReadyScreen tier="casual" entry={CASUAL_CARD} /> },
  { id: "ready-medium", name: "Ready, medium reveal", render: () => <ReadyScreen tier="medium" entry={cardWithImage} /> },
  { id: "ready-strong", name: "Ready, strong reveal", render: () => <ReadyScreen tier="strong" entry={STRONG_CARD} /> },
  { id: "result", name: "Result", render: () => <ResultScreen /> },
  { id: "fx", name: "Pixel effects", render: () => <FxBench /> },
  { id: "goblins", name: "The goblin crew", render: () => <GoblinSheet /> },
  { id: "machine", name: "The forge", render: () => <MachineBench /> },
  { id: "symbols", name: "Mana symbols", render: () => <SymbolSheet /> },
];
