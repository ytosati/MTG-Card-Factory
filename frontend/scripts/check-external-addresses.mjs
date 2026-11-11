// Check of the built frontend: fails when a built file loads an image, font, script or style sheet from
// outside the local application, or when index.html links no local icon. Details: spec RN-33, CA-38, CA-82.
// Run from frontend/ after a build: node scripts/check-external-addresses.mjs [folder] (default: dist).
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative, resolve } from "node:path";
import { pathToFileURL } from "node:url";

/** Attributes that make the browser load what they point to; links the person follows (<a href>) are not loads. */
const LOADING_ATTRIBUTES = new Set(["src", "href", "xlink:href", "srcset", "poster", "data", "background"]);

const NON_LOADING_TAGS = new Set(["a", "area", "base", "form"]);

const SCHEME = /^[a-z][a-z0-9+.-]*:/i;
const LOCAL_SCHEMES = new Set(["data:", "blob:"]);

/** True when a reference leaves the local application: any scheme but data: and blob:, or a //host path. */
export function isExternal(reference) {
  const value = reference.trim().replace(/^['"]|['"]$/g, "").trim();
  if (value === "" || value.startsWith("#")) return false;
  // Browsers read a backslash as a slash, so "\\host" and "/\host" leave the origin too.
  if (/^[/\\]{2}/.test(value)) return true;
  const scheme = SCHEME.exec(value);
  return scheme !== null && !LOCAL_SCHEMES.has(scheme[0].toLowerCase());
}

function cssReferences(css) {
  const found = [];
  for (const match of css.matchAll(/url\(\s*(['"]?)(.*?)\1\s*\)/gi)) found.push(match[2]);
  for (const match of css.matchAll(/@import\s+(['"])(.*?)\1/gi)) found.push(match[2]);
  return found;
}

function markupReferences(markup) {
  const found = [];
  for (const tag of markup.matchAll(/<([a-z][\w:-]*)\b([^>]*)>/gi)) {
    const name = tag[1].toLowerCase();
    for (const attribute of tag[2].matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/g)) {
      const key = attribute[1].toLowerCase();
      const value = attribute[2] ?? attribute[3] ?? attribute[4] ?? "";
      if (key === "style") found.push(...cssReferences(value));
      else if (key === "srcset") found.push(...value.split(",").map((entry) => entry.trim().split(/\s+/)[0] ?? ""));
      else if (LOADING_ATTRIBUTES.has(key) && !NON_LOADING_TAGS.has(name)) found.push(value);
    }
  }
  for (const block of markup.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)) found.push(...cssReferences(block[1]));
  return found;
}

function scriptReferences(script) {
  const found = [];
  const patterns = [
    /\bimport\s*\(\s*(['"`])(.*?)\1/g,
    /\b(?:import|export)\b[^'"`;]*?\bfrom\s*(['"`])(.*?)\1/g,
    /\bimport\s*(['"`])(.*?)\1/g,
    /\bimportScripts\s*\(\s*(['"`])(.*?)\1/g,
    /\bnew\s+(?:Shared)?Worker\s*\(\s*(['"`])(.*?)\1/g,
  ];
  for (const pattern of patterns) for (const match of script.matchAll(pattern)) found.push(match[2]);
  // Style sheets and images built from strings in scripts.
  found.push(...cssReferences(script).filter((reference) => !reference.includes("${")));
  return found;
}

/** The external references in one built file, chosen by its extension; other files are not read as text. */
export function findExternalReferences(fileName, text) {
  const extension = extname(fileName).toLowerCase();
  let references = [];
  if (extension === ".html" || extension === ".svg") references = markupReferences(text);
  else if (extension === ".css") references = cssReferences(text);
  else if (extension === ".js" || extension === ".mjs") references = scriptReferences(text);
  return references.filter(isExternal).map((reference) => ({ file: fileName, reference }));
}

/** The icon index.html links: an /assets/ file of the build or an inlined data: image; null when there is none. */
export function linkedIcon(indexHtml) {
  for (const tag of indexHtml.matchAll(/<link\b([^>]*)>/gi)) {
    const rel = /\brel\s*=\s*["']?([^"'\s>]+)/i.exec(tag[1])?.[1]?.toLowerCase();
    const href = /\bhref\s*=\s*["']([^"']*)["']/i.exec(tag[1])?.[1];
    if (rel === "icon" && href !== undefined) return href;
  }
  return null;
}

const TEXT_EXTENSIONS = new Set([".html", ".svg", ".css", ".js", ".mjs"]);

function builtFiles(folder) {
  const files = [];
  for (const entry of readdirSync(folder)) {
    const path = join(folder, entry);
    if (statSync(path).isDirectory()) files.push(...builtFiles(path));
    else if (TEXT_EXTENSIONS.has(extname(entry).toLowerCase())) files.push(path);
  }
  return files;
}

/** Checks a built folder and returns the problems found, one line each. */
export function checkBuild(folder) {
  const index = join(folder, "index.html");
  if (!existsSync(index)) return [`${index} is missing. Run npm run build first.`];
  const problems = [];
  const files = builtFiles(folder);
  for (const file of files) {
    for (const finding of findExternalReferences(file, readFileSync(file, "utf8"))) {
      problems.push(`${relative(folder, finding.file)} references an address outside the application: ${finding.reference}`);
    }
  }
  const icon = linkedIcon(readFileSync(index, "utf8"));
  if (icon === null) problems.push("index.html links no icon.");
  else if (icon.startsWith("/assets/")) {
    if (!existsSync(join(folder, icon))) problems.push(`index.html links the icon ${icon}, which the build does not contain.`);
  } else if (!icon.startsWith("data:image/")) {
    problems.push(`index.html links the icon ${icon}, which is not served under /assets/ or inlined.`);
  }
  return problems;
}

function main() {
  const folder = resolve(process.argv[2] ?? "dist");
  const problems = checkBuild(folder);
  if (problems.length > 0) {
    for (const problem of problems) console.error(problem);
    process.exit(1);
  }
  console.log(`No external addresses in ${builtFiles(folder).length} built files; the icon is local.`);
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main();
