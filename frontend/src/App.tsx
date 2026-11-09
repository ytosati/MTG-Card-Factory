// Application shell with a small hash-based screen switch (no router library).
// Details: specs/plan.md, section 13.
import { useEffect, useState } from "react";
import type { ComponentType } from "react";

import { StatusScreen } from "./screens/StatusScreen";

const SCREENS: Record<string, ComponentType> = {
  "#/status": StatusScreen,
};

const DEFAULT_ROUTE = "#/status";

function currentRoute(): string {
  const hash = window.location.hash;
  return hash in SCREENS ? hash : DEFAULT_ROUTE;
}

/** The application: a header and the screen named by the location hash. */
export function App() {
  const [route, setRoute] = useState(currentRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const Screen = SCREENS[route] ?? StatusScreen;

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-name">Card Factory</span>
        <nav aria-label="Screens">
          <a href="#/status" aria-current={route === "#/status" ? "page" : undefined}>
            Status
          </a>
        </nav>
      </header>
      <Screen key={route} />
    </div>
  );
}
