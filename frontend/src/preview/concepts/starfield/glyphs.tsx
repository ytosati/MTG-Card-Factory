// Concept E "Starfield" (tasks.md T251): the small drawn marks of the concept: the compass star, section stars and orbits.

/** The wordmark's sign: a compass star inside a thin orbit, with one cyan moon on it. */
export function CompassMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <circle cx="16" cy="16" r="12.5" fill="none" stroke="currentColor" strokeOpacity="0.4" strokeWidth="0.75" />
      <ellipse cx="16" cy="16" rx="15" ry="5.2" fill="none" stroke="currentColor" strokeOpacity="0.28" strokeWidth="0.6" transform="rotate(-28 16 16)" />
      {/* Four long points on the axes, four short ones between them. */}
      <path d="M16 3.5 L17.6 14.4 L28.5 16 L17.6 17.6 L16 28.5 L14.4 17.6 L3.5 16 L14.4 14.4 Z" fill="currentColor" />
      <path d="M16 9.6 L17 15 L22.4 16 L17 17 L16 22.4 L15 17 L9.6 16 L15 15 Z" fill="currentColor" opacity="0.55" transform="rotate(45 16 16)" />
      <circle cx="27.6" cy="7.8" r="1.5" fill="var(--sf-cyan)" />
    </svg>
  );
}

/** A four-pointed star, the marker of sections and the current place. */
export function StarGlyph({ size = 10, className }: { size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 10 10" aria-hidden="true" focusable="false">
      <path d="M5 0 L5.9 4.1 L10 5 L5.9 5.9 L5 10 L4.1 5.9 L0 5 L4.1 4.1 Z" fill="currentColor" />
    </svg>
  );
}

/**
 * The selection mark of a choice: a small body that, when chosen, gains a violet core and a tilted orbit with a
 * cyan moon. Styled by the caller through data-checked.
 */
export function Orbit({ checked, className }: { checked: boolean; className?: string }) {
  return (
    <svg className={className} data-checked={checked ? "true" : "false"} width="26" height="26" viewBox="0 0 26 26" aria-hidden="true" focusable="false">
      <circle cx="13" cy="13" r="5.5" fill="none" stroke="currentColor" strokeWidth="1" data-part="body" />
      <circle cx="13" cy="13" r="3" fill="var(--sf-violet)" data-part="core" />
      <g data-part="ring">
        <ellipse cx="13" cy="13" rx="12" ry="4.6" fill="none" stroke="var(--sf-violet-text)" strokeWidth="0.9" transform="rotate(-24 13 13)" />
        <circle cx="21.6" cy="6.7" r="1.4" fill="var(--sf-cyan)" />
      </g>
    </svg>
  );
}
