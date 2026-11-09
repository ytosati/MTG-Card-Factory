// The Card Factory symbol shown beside the name in the header.

/** The wordmark symbol of Card Factory: a card outline with a spark, hidden from assistive technology. */
export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
      <rect x="3.75" y="1.75" width="12.5" height="16.5" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 6.25 11.1 8.9 13.75 10 11.1 11.1 10 13.75 8.9 11.1 6.25 10 8.9 8.9Z" fill="currentColor" />
    </svg>
  );
}
