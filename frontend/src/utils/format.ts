/**
 * Format a number as currency
 */
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat("he-IL", {
    style: "currency",
    currency: "ILS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

/** Number input draft: blank instead of a pre-filled 0. */
export type NumberDraft = number | "";

/** Open a number cell empty when the stored value is 0/absent. */
export function toNumberDraft(
  value: number | null | undefined
): NumberDraft {
  if (value == null || value === 0) return "";
  return value;
}

export function parseNumberDraft(raw: string): NumberDraft {
  if (raw === "") return "";
  const parsed = parseFloat(raw);
  return Number.isNaN(parsed) ? "" : parsed;
}

export function numberDraftToValue(value: NumberDraft): number {
  return value === "" ? 0 : roundQuantity(value);
}

/** Standard qty precision (calc sheets, concentration, BOQ quantities). */
export const QUANTITY_DECIMALS = 2;

export function roundQuantity(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const negative = value < 0;
  // toFixed(8) turns the binary value Excel stores for 0.835
  // (0.8349999999999999) into "0.83500000". Round the third decimal
  // first, then to two places, so a sheet value shown as 0.835 becomes 0.84.
  const [whole, frac = ""] = Math.abs(value).toFixed(8).split(".");
  const digits = (frac + "00000000").slice(0, 8);
  let milli = Number(whole) * 1000 + Number(digits.slice(0, 3));
  if (digits[3] >= "5") milli += 1;
  let cents = Math.floor(milli / 10);
  if (milli % 10 >= 5) cents += 1;
  const rounded = cents / 100;
  return negative ? -rounded : rounded;
}

/**
 * Format a number with commas and decimal places
 */
export const formatNumber = (value: number, decimals: number = QUANTITY_DECIMALS): string => {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

/**
 * Format a percentage
 */
export const formatPercentage = (value: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value / 100);
};

/**
 * Format a date
 */
export const formatDate = (date: string | Date): string => {
  const dateObj = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(dateObj);
};

/**
 * Format a date and time
 */
export const formatDateTime = (date: string | Date): string => {
  const dateObj = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(dateObj);
};
