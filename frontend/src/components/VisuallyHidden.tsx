// Text read by assistive technology and kept in copied text, but not drawn on screen.
import type { ReactNode } from "react";

import styles from "./VisuallyHidden.module.css";

/** Text that is not drawn on screen. */
export function VisuallyHidden({ children }: { children: ReactNode }) {
  return <span className={styles.hidden}>{children}</span>;
}
