// Types of the preview fixtures, shaped like the API contract of plan section 6.
// Contract samples are used where they exist; the image fields are draft types until the art endpoints exist.
import type { CardResponse } from "../api/types";
import type { CardImage } from "../components/cardImage";

/** An image as the screens receive it: its address in the application and its text alternative (draft). */
export type PreviewImage = CardImage;

/** A card response with its current image, or null when it has none (draft of the art milestone). */
export type PreviewCard = CardResponse & { image: PreviewImage | null };

/** A custom art version of a card: its number, where it came from and its image (draft). */
export interface PreviewArtVersion {
  id: string;
  number: number;
  origin: string;
  image: PreviewImage;
}
