// Concept E "Starfield" (tasks.md T251): whether motion is off, by the system setting or by an ancestor's switch.
import { useEffect, useRef, useState, type RefObject } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function systemReduced(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(QUERY).matches;
}

/** A ref for the element to check and whether motion is reduced there; follows the gallery switch. */
export function useMotionOff<T extends HTMLElement>(): [RefObject<T | null>, boolean] {
  const ref = useRef<T>(null);
  const [off, setOff] = useState(systemReduced);
  useEffect(() => {
    const next = systemReduced() || ref.current?.closest('[data-reduced-motion="true"]') != null;
    setOff((current) => (current === next ? current : next));
  });
  return [ref, off];
}
