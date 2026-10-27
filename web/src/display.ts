// Presentation fallbacks never turn absent evidence into a measured zero.
export const numberText = (
  value: unknown,
  digits = 3,
  fallback = "Measurement not recorded",
): string =>
  typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : fallback;

export const valueText = (
  value: unknown,
  fallback = "Not recorded for this event",
): string => {
  if (typeof value === "number")
    return Number.isFinite(value)
      ? value.toLocaleString(undefined, { maximumFractionDigits: 4 })
      : fallback;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (
    typeof value === "string" &&
    value.trim() &&
    !/^[-–—]+$/.test(value.trim())
  )
    return value;
  return fallback;
};
