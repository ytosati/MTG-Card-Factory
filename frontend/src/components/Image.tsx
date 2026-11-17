// The one image component: it requires a text alternative and reserves the image's space (spec RN-49).
import { cx } from "./classNames";
import styles from "./Image.module.css";

interface ImageProps {
  src: string;
  /** What the image shows; an empty text marks a decorative image. */
  alt: string;
  /** The natural size, so the layout keeps the space while the image loads. */
  width: number;
  height: number;
  className?: string | undefined;
}

/** An image loaded lazily, with its text alternative and reserved size. */
export function Image({ src, alt, width, height, className }: ImageProps) {
  return (
    <img
      className={cx(styles.image, className)}
      src={src}
      alt={alt}
      width={width}
      height={height}
      loading="lazy"
      decoding="async"
    />
  );
}
