// A message in the danger, notice or success tone (spec RN-49): danger is an alert, the others a status.
import type { ReactNode } from "react";

import { cx } from "./classNames";
import styles from "./Notice.module.css";
import { StatusIcon, toneStyles } from "./StatusIcon";
import type { StatusTone } from "./StatusIcon";

interface NoticeProps {
  tone: StatusTone;
  title?: string | undefined;
  children: ReactNode;
}

const TONE_CLASSES: Record<StatusTone, string | undefined> = {
  danger: styles.danger,
  notice: styles.notice,
  success: styles.success,
};

/** A message with its icon; danger interrupts as an alert, notice and success are announced politely. */
export function Notice({ tone, title, children }: NoticeProps) {
  return (
    <div className={cx(styles.box, TONE_CLASSES[tone], toneStyles.tone)} role={tone === "danger" ? "alert" : "status"}>
      <StatusIcon tone={tone} />
      <div className={cx(toneStyles.toneBody, styles.body)}>
        {title !== undefined && <p className={styles.title}>{title}</p>}
        {children}
      </div>
    </div>
  );
}
