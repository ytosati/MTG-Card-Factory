// Tests for the built-files check and the application icon (spec RN-33, RN-52; CA-38, CA-82). T139.
// The check itself runs over the build with `npm run check:external` (also the last step of `npm run build`).
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { findExternalReferences, isExternal, linkedIcon } from "../scripts/check-external-addresses.mjs";

const indexHtml = readFileSync("index.html", "utf8");
const iconSvg = readFileSync("src/assets/icon.svg", "utf8");
const tokensCss = readFileSync("src/styles/tokens.css", "utf8");

function references(fileName: string, text: string): string[] {
  return findExternalReferences(fileName, text).map((finding) => finding.reference);
}

describe("built-files check: what counts as outside the application (RN-33, CA-38)", () => {
  it.each(["https://cdn.example/react.js", "http://127.0.0.1:47821/x.png", "//fonts.example/a.woff2", "\\\\host\\x.css", "ftp://x/y"])(
    "CA-38: %s is outside the application",
    (reference) => expect(isExternal(reference)).toBe(true),
  );

  it.each(["/assets/index.js", "./icon.svg", "icon.svg", "data:image/svg+xml,%3Csvg%3E", "blob:abc", "#mark", ""])(
    "CA-38: %s is local",
    (reference) => expect(isExternal(reference)).toBe(false),
  );
});

describe("built-files check: loads found in each kind of file (RN-33, CA-38)", () => {
  it("CA-38: finds scripts, style sheets, icons, images and inline styles loaded from outside in HTML", () => {
    const html = `<script src="https://cdn.example/a.js"></script>
      <link rel="stylesheet" href='//cdn.example/b.css'><link rel="icon" href=https://x.example/i.svg>
      <img srcset="/assets/a.png 1x, https://img.example/b.png 2x" src="/assets/a.png">
      <div style="background: url(https://img.example/c.png)"></div>
      <style>@import "https://fonts.example/d.css";</style>`;
    expect(references("index.html", html)).toEqual([
      "https://cdn.example/a.js",
      "//cdn.example/b.css",
      "https://x.example/i.svg",
      "https://img.example/b.png",
      "https://img.example/c.png",
      "https://fonts.example/d.css",
    ]);
  });

  it("CA-38: a link the person follows and an XML namespace are not loads", () => {
    const html = `<a href="https://github.com/example/releases">Releases</a>
      <svg xmlns="http://www.w3.org/2000/svg"><use href="#mark"/></svg>`;
    expect(references("index.html", html)).toEqual([]);
  });

  it("CA-38: finds fonts, images and imports from outside in CSS", () => {
    const css = `@import url("https://fonts.example/a.css");
      @font-face { src: url(https://fonts.example/b.woff2) format("woff2"), url('/assets/c.woff2'); }
      .x { background: url(data:image/png;base64,AAAA); }`;
    expect(references("assets/index.css", css)).toEqual(["https://fonts.example/a.css", "https://fonts.example/b.woff2"]);
  });

  it("CA-38: finds module imports from outside in scripts, but not addresses that are only text", () => {
    const js = `import{a}from"https://cdn.example/a.js";import"//cdn.example/b.js";
      const c=import("https://cdn.example/c.js");const d=import("./chunk.js");
      throw Error("Minified React error; visit https://react.dev/errors/418");`;
    expect(references("assets/index.js", js)).toEqual([
      "https://cdn.example/c.js",
      "https://cdn.example/a.js",
      "//cdn.example/b.js",
    ]);
  });

  it("CA-38: finds images linked from outside in an SVG file", () => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg"><image href="https://img.example/a.png"/></svg>`;
    expect(references("assets/icon.svg", svg)).toEqual(["https://img.example/a.png"]);
  });
});

describe("application icon (RN-52, CA-82)", () => {
  it("CA-82: index.html links the SVG icon from src/assets, so the build serves it under /assets/", () => {
    expect(linkedIcon(indexHtml)).toBe("/src/assets/icon.svg");
    expect(indexHtml).toMatch(/<link\b[^>]*\btype="image\/svg\+xml"/);
  });

  it("RN-52: the icon is drawn in the accent color of the tokens and loads nothing", () => {
    const accent = /--color-accent\s*:\s*([^;]+);/.exec(tokensCss)?.[1]?.trim().toLowerCase();
    expect(accent).toBeDefined();
    expect(iconSvg.toLowerCase()).toContain(`fill="${accent}"`);
    expect(references("icon.svg", iconSvg)).toEqual([]);
  });

  it("CA-38: index.html loads nothing from outside the application", () => {
    expect(references("index.html", indexHtml)).toEqual([]);
  });
});
