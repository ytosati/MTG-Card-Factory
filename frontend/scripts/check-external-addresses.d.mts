// Types of the built-files check, so Vitest tests can import its scanner.

/** True when a reference leaves the local application. */
export function isExternal(reference: string): boolean;

/** The external references in one built file, chosen by its extension. */
export function findExternalReferences(fileName: string, text: string): { file: string; reference: string }[];

/** The icon index.html links, or null when there is none. */
export function linkedIcon(indexHtml: string): string | null;

/** Checks a built folder and returns the problems found, one line each. */
export function checkBuild(folder: string): string[];
