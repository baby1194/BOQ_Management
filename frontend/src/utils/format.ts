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
  return value === "" ? 0 : value;
}

/**
 * Format a number with commas and decimal places
 */
export const formatNumber = (value: number, decimals: number = 2): string => {
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
