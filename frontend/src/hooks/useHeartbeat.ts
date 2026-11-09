// Tab heartbeat that keeps the local application running while a tab is open.
// Details: spec RN-41; specs/plan.md, section 9.4 (step 8).
import { useEffect, useState } from "react";

import { sendHeartbeat } from "../api/client";

const HEARTBEAT_INTERVAL_MS = 15_000;

/** Sends heartbeats while mounted; `stopped` is true while the last heartbeat failed. */
export function useHeartbeat(): { stopped: boolean } {
  const [stopped, setStopped] = useState(false);

  useEffect(() => {
    let active = true;
    let latest = 0;

    const beat = () => {
      latest += 1;
      const sequence = latest;
      // Only the newest heartbeat decides, so a slow earlier answer cannot override a later one.
      const settle = (failed: boolean) => {
        if (active && sequence === latest) setStopped(failed);
      };
      sendHeartbeat().then(
        () => settle(false),
        () => settle(true),
      );
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") beat();
    };

    beat();
    const timer = window.setInterval(beat, HEARTBEAT_INTERVAL_MS);
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pagehide", beat);

    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("pagehide", beat);
    };
  }, []);

  return { stopped };
}
