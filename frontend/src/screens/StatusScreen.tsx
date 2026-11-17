// Status screen container: reads the status and hands each state to the view.
// Details: specs/spec.md, RN-01, RN-08, CA-08, CA-77 and "Screens" (Status).
import { useCallback, useEffect, useRef, useState } from "react";

import { getStatus } from "../api/client";
import { statusCopy } from "./status/copy";
import { StatusView } from "./status/StatusView";
import type { StatusViewState } from "./status/StatusView";

function errorState(reason: unknown): StatusViewState {
  if (reason instanceof Error) {
    const setting = "setting" in reason && typeof reason.setting === "string" ? reason.setting : null;
    return { kind: "error", message: reason.message, setting };
  }
  return { kind: "error", message: statusCopy.loadFailed, setting: null };
}

/** The Status screen; it reads GET /api/status each time it opens (spec CA-73). */
export function StatusScreen() {
  const [state, setState] = useState<StatusViewState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusHeadingAfterLoad = useRef(false);

  useEffect(() => {
    let active = true;
    setState({ kind: "loading" });
    getStatus().then(
      (status) => {
        if (active) setState({ kind: "ready", status });
      },
      (reason: unknown) => {
        if (active) setState(errorState(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [attempt]);

  // The button that asked for the reload disappears while loading, so focus returns to the heading.
  useEffect(() => {
    if (state.kind !== "loading" && focusHeadingAfterLoad.current) {
      focusHeadingAfterLoad.current = false;
      headingRef.current?.focus();
    }
  }, [state]);

  const reload = useCallback(() => {
    focusHeadingAfterLoad.current = true;
    setAttempt((value) => value + 1);
  }, []);

  return <StatusView state={state} headingRef={headingRef} onReload={reload} />;
}
