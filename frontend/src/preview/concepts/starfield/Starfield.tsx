// Concept E "Starfield" (tasks.md T251): the slow field of stars behind every screen. Decorative only.
import { useStarfield, type StarfieldSpeed } from "./useStarfield";

/** The starfield canvas; it fills its box, so the page decides its size and place. */
export function Starfield({ speed = "rest", className }: { speed?: StarfieldSpeed; className?: string }) {
  const ref = useStarfield(speed);
  return <canvas ref={ref} className={className} aria-hidden="true" data-speed={speed} />;
}
