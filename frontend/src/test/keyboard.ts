// Test helpers for keyboard navigation in jsdom, which has no layout and no native Tab handling.
// Details: spec RN-49, CA-59.

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]",
].join(",");

/** Elements reached with the Tab key, in document order (positive tabindex is not modeled; tests forbid it). */
export function tabbableElements(root: ParentNode = document): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (element) => element.tabIndex >= 0 && element.closest("[hidden], [inert], [aria-hidden='true']") === null,
  );
}

/** Moves focus as the Tab key would, from the focused element to the next tabbable one, and returns it. */
export function pressTab(): HTMLElement | null {
  const order = tabbableElements();
  const current = document.activeElement;
  const index = current instanceof HTMLElement ? order.indexOf(current) : -1;
  const next = order[index + 1] ?? null;
  next?.focus();
  return next;
}
