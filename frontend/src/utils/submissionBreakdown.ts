import { SubmissionBreakdown } from "../types";

const INVALID_PERIODS = new Set(["nan", "none", "<na>", "nat"]);

export const getPeriodQuantities = (
  breakdown: SubmissionBreakdown,
): Record<string, number> => {
  if (breakdown.periods && Object.keys(breakdown.periods).length > 0) {
    return breakdown.periods;
  }

  const merged: Record<string, number> = { ...(breakdown.past_months ?? {}) };
  const current = breakdown.current_drawing_no?.trim();
  if (current && !(current in merged)) {
    merged[current] = 0;
  }

  Object.keys(merged).forEach((key) => {
    if (INVALID_PERIODS.has(key.toLowerCase())) {
      delete merged[key];
    }
  });

  return merged;
};

export const sortedPeriodKeys = (periods: Record<string, number>): string[] =>
  Object.keys(periods).sort((a, b) =>
    a.length === b.length ? a.localeCompare(b) : a.length - b.length,
  );

export const cumulativeSubmittedQuantity = (
  breakdown?: SubmissionBreakdown | null,
): number => {
  if (!breakdown) {
    return 0;
  }
  const periods = getPeriodQuantities(breakdown);
  return Object.values(periods).reduce((sum, value) => sum + (value ?? 0), 0);
};

export const resolveCurrentPeriod = (
  breakdown?: SubmissionBreakdown | null,
  currentInvoiceId?: string | null,
): string =>
  currentInvoiceId?.trim() ||
  breakdown?.current_drawing_no?.trim() ||
  "";

export const getPastPeriodRows = (
  breakdown: SubmissionBreakdown,
  currentPeriod: string,
): Array<{ period: string; qty: number }> =>
  sortedPeriodKeys(getPeriodQuantities(breakdown)).flatMap((period) => {
    if (period === currentPeriod) {
      return [];
    }
    const qty = getPeriodQuantities(breakdown)[period] ?? 0;
    if (qty === 0) {
      return [];
    }
    return [{ period, qty }];
  });

export const pastSubmittedQuantity = (
  breakdown?: SubmissionBreakdown | null,
  currentInvoiceId?: string | null,
): number => {
  if (!breakdown) {
    return 0;
  }
  const currentPeriod = resolveCurrentPeriod(breakdown, currentInvoiceId);
  return getPastPeriodRows(breakdown, currentPeriod).reduce(
    (sum, row) => sum + row.qty,
    0,
  );
};

interface ConcentrationEntrySubmittedLike {
  id: number;
  quantity_submitted?: number;
  submission_breakdown?: SubmissionBreakdown | null;
  drawing_no?: string;
}

export const concentrationEntriesQuantitySubmittedTotal = (
  entries: ConcentrationEntrySubmittedLike[],
  expandedEntryIds: Set<number>,
): number =>
  entries.reduce((sum, entry) => {
    const currentSubmitted = entry.quantity_submitted || 0;
    if (expandedEntryIds.has(entry.id)) {
      return (
        sum +
        currentSubmitted +
        pastSubmittedQuantity(entry.submission_breakdown, entry.drawing_no)
      );
    }
    return sum + currentSubmitted;
  }, 0);
