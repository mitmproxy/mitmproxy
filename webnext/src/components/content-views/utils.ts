/**
 * Converts bytes to a human-readable string with appropriate units.
 * @param bytes - Number of bytes.
 * @param decimals - Number of decimal places (default: 1).
 * @param binary - Use binary (1024) or decimal (1000) units (default: binary).
 * @returns Formatted string with appropriate unit.
 */
export function formatBytes(
  bytes: number,
  decimals: number = 1,
  binary: boolean = true,
): string {
  if (bytes === 0) return "0 B";
  if (bytes < 0) return "-" + formatBytes(-bytes, decimals, binary);

  const base = binary ? 1024 : 1000;
  const units = binary
    ? ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    : ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];

  const unitIndex = Math.floor(Math.log(bytes) / Math.log(base));
  const clampedIndex = Math.min(unitIndex, units.length - 1);

  const value = bytes / Math.pow(base, clampedIndex);
  const formattedValue =
    clampedIndex === 0 ? value.toString() : value.toFixed(decimals);

  return `${formattedValue} ${units[clampedIndex]}`;
}
