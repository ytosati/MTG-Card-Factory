// Setup screen: opens first while the reference database is not ready.
// Details: specs/spec.md, RN-28 and "Screens" (First-run setup).

interface SetupScreenProps {
  /** Called once the database is ready, so the shell moves to the normal screens. */
  onReady: () => void;
}

/** The Setup screen. */
export function SetupScreen(_props: SetupScreenProps) {
  return (
    <main className="screen">
      <h1>Setup</h1>
      <p className="summary">The reference database of cards must be built before the other screens open.</p>
    </main>
  );
}
