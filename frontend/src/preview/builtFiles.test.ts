// Built-file check: no preview code and no fixture reaches the production build (tasks.md T167 "Done
// when"; plan section 14 "Screen previews").
//
// Form chosen: the test runs the real production build in memory (Vite's build API with write: false, the
// project's vite.config.ts, mode "production") and searches every emitted chunk, style sheet and asset
// for sentinels taken from the preview module itself: the fixture card names, the gallery heading and
// the preview address. Cost: a few seconds, no files written, no dependency, and it does not need
// `frontend/dist` to exist.
// Limits: it proves the absence of those sentinels, not of every preview byte; a preview module that
// shares no text with them could slip through, so a new preview module with its own text adds a sentinel
// here. The sentinels are read from the fixtures module, so the check cannot pass by being out of date.
import { build } from "vite";
import { describe, expect, it } from "vitest";

import { approvedCard, designNotesCard, planeswalkerCard, rejectedCard } from "./fixtures";

type Output = { fileName: string; code?: string; source?: string | Uint8Array };

async function productionBuild(): Promise<Output[]> {
  const result = await build({ logLevel: "silent", mode: "production", build: { write: false } });
  const runs = Array.isArray(result) ? result : [result];
  return runs.flatMap((run) => ("output" in run ? (run.output as Output[]) : []));
}

function textOf(file: Output): string {
  if (typeof file.code === "string") return file.code;
  if (typeof file.source === "string") return file.source;
  return file.source === undefined ? "" : new TextDecoder().decode(file.source);
}

describe("production build excludes the preview (T167)", () => {
  it(
    "no emitted file holds the gallery text, a fixture name or the preview address",
    async () => {
      const sentinels = [
        "Preview gallery",
        "List and table sample",
        approvedCard.current_version.name,
        rejectedCard.current_version.name,
        planeswalkerCard.current_version.name,
        designNotesCard.current_version.name,
        "#/preview",
      ];
      for (const sentinel of sentinels) expect(sentinel.length).toBeGreaterThan(3);

      const files = await productionBuild();
      expect(files.length).toBeGreaterThan(0);
      // The application itself is in the build, so an empty or wrong build cannot pass.
      expect(files.some((file) => textOf(file).includes("Card Factory"))).toBe(true);

      for (const file of files) {
        const text = textOf(file);
        for (const sentinel of sentinels) {
          expect(text.includes(sentinel), `${file.fileName} contains "${sentinel}"`).toBe(false);
        }
      }
    },
    120_000,
  );
});
