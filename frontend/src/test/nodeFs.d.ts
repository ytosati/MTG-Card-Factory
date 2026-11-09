// Minimal typing of the Node file reader used by tests that check stylesheets (no @types/node in v1).
declare module "node:fs" {
  export function readFileSync(path: string, encoding: "utf8"): string;
}
