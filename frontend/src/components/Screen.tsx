// The main region of a screen and the shared classes of its parts.
import type { ReactNode } from "react";

import styles from "./Screen.module.css";

/** Classes shared by every screen: the summary under the heading, a hint, an action row, an error panel. */
export const screenStyles = {
  summary: styles.summary,
  summaryRow: styles.summaryRow,
  hint: styles.hint,
  actions: styles.actions,
  errorPanel: styles.errorPanel,
};

/** The main region of a screen, on the content axis of the application. */
export function Screen({ children }: { children: ReactNode }) {
  return <main className={styles.screen}>{children}</main>;
}
