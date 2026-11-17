// Joins CSS Module class names, skipping the absent ones.

/** The class attribute for the given names; false, null and undefined are left out. */
export function cx(...names: (string | false | null | undefined)[]): string {
  return names.filter((name): name is string => typeof name === "string" && name !== "").join(" ");
}
