// Byte counts for people, in binary units.

const UNITS = ["B", "KB", "MB", "GB", "TB", "PB"];
const STEP = 1024;

/** A byte count in binary units with at most one decimal, for example "77.5 KB"; null when it is not a size. */
export function formatSize(bytes: number): string | null {
  if (!Number.isFinite(bytes) || bytes < 0) return null;
  let value = bytes;
  let unit = 0;
  while (value >= STEP && unit < UNITS.length - 1) {
    value /= STEP;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  // Rounding can reach the next unit (1048575 bytes is "1024 KB"), so promote it.
  if (Number(value.toFixed(digits)) >= STEP && unit < UNITS.length - 1) {
    value /= STEP;
    unit += 1;
  }
  const text = value.toFixed(unit === 0 || value >= 100 ? 0 : 1).replace(/\.0$/, "");
  return `${text} ${UNITS[unit]}`;
}
