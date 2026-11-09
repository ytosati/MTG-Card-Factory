// Small decorative icons that mark the tone of a message; the text beside them carries the meaning.

/** The tone of a message: a problem to fix, a notice, or a good state. */
export type StatusTone = "danger" | "notice" | "success";

/** A status icon, hidden from assistive technology; it takes the color of its text. */
export function StatusIcon({ tone }: { tone: StatusTone }) {
  return (
    <svg className="status-icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
      {tone === "danger" && (
        <>
          <circle cx="8" cy="8" r="6.75" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="M8 4.5v4.25" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="8" cy="11.25" r="0.9" fill="currentColor" />
        </>
      )}
      {tone === "notice" && (
        <>
          <path d="M8 1.75 14.75 13.75H1.25Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
          <path d="M8 6v3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="8" cy="11.6" r="0.85" fill="currentColor" />
        </>
      )}
      {tone === "success" && (
        <>
          <circle cx="8" cy="8" r="6.75" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <path d="m5 8.25 2 2 4-4.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )}
    </svg>
  );
}
