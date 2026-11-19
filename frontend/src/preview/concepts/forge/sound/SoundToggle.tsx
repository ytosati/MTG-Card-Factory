// Concept D "Forge" (tasks.md T251): the button that turns the concept's sounds on and off.
import { setMuted, useSoundMuted } from "./forgeAudio";
import styles from "./SoundToggle.module.css";

/** A small speaker button; pressed means sound is on. */
export function SoundToggle({ className }: { className?: string }) {
  const muted = useSoundMuted();
  return (
    <button
      type="button"
      className={[styles.toggle, className].filter(Boolean).join(" ")}
      aria-label="Sound"
      aria-pressed={!muted}
      title={muted ? "Sound off" : "Sound on"}
      onClick={() => setMuted(!muted)}
    >
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
        <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" fill="currentColor" />
        {muted ? (
          <path d="M16 9.5l5 5M21 9.5l-5 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        ) : (
          <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        )}
      </svg>
    </button>
  );
}
