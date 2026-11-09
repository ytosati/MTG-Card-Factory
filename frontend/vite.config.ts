// Vite, Vitest and development server configuration.
// Details: specs/plan.md, sections 9.5 and 13.
import { defineConfig } from "vitest/config";

const BACKEND_ORIGIN = "http://127.0.0.1:47821";

export default defineConfig({
  // JSX is compiled by Vite's own esbuild; no React plugin (plan section 13).
  esbuild: { jsx: "automatic" },
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: BACKEND_ORIGIN,
        changeOrigin: true,
        // The backend accepts only its own origin, so development needs no exception to that check.
        headers: { origin: BACKEND_ORIGIN },
      },
    },
  },
  build: { outDir: "dist" },
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
