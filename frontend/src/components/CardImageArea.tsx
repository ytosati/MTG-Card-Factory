// The card-shaped image area of a card (spec RN-44, CA-50).
import type { CardImage } from "./cardImage";
import styles from "./CardImageArea.module.css";
import { Image } from "./Image";
import { VisuallyHidden } from "./VisuallyHidden";

/** The size requested from image providers (spec RN-44); it reserves the area while the file loads. */
const CARD_IMAGE_WIDTH = 745;
const CARD_IMAGE_HEIGHT = 1040;

interface CardImageAreaProps {
  image: CardImage | null;
  cardName: string;
}

/** The image fitted whole into a card-shaped area, with a link to the stored file; without one, the area says so. */
export function CardImageArea({ image, cardName }: CardImageAreaProps) {
  return (
    <figure className={styles.area} aria-label={`Art of ${cardName}`}>
      <div className={styles.frame}>
        {image === null ? (
          <p className={styles.empty}>No image</p>
        ) : (
          <Image
            className={styles.image}
            src={image.src}
            alt={image.alt}
            width={CARD_IMAGE_WIDTH}
            height={CARD_IMAGE_HEIGHT}
          />
        )}
      </div>
      {image !== null && (
        <figcaption className={styles.caption}>
          <a href={image.src} target="_blank" rel="noopener noreferrer">
            Open full resolution<VisuallyHidden> (opens in a new tab)</VisuallyHidden>
          </a>
        </figcaption>
      )}
    </figure>
  );
}
