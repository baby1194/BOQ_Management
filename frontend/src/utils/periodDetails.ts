import {
  ConcentrationEntry,
  PeriodDetail,
  SubmissionBreakdown,
} from "../types";
import { computeSubmissionPercentage } from "./submissionBreakdown";

export function getPeriodDetailsMap(
  breakdown?: SubmissionBreakdown | null
): Record<string, PeriodDetail> {
  if (!breakdown?.period_details) {
    return {};
  }
  return breakdown.period_details;
}

export function resolveCurrentPeriod(
  entry: ConcentrationEntry,
  breakdown?: SubmissionBreakdown | null
): string {
  return (
    entry.drawing_no?.trim() ||
    breakdown?.current_drawing_no?.trim() ||
    ""
  );
}

export function emptyPeriodDetail(): PeriodDetail {
  return {
    internal_quantity: 0,
    approved_by_project_manager: 0,
    submission_percentage: undefined,
    notes: "",
    supervisor_notes: "",
    drawing_files: [],
  };
}

export function getPeriodDetail(
  breakdown: SubmissionBreakdown | null | undefined,
  period: string
): PeriodDetail {
  if (!period) {
    return emptyPeriodDetail();
  }
  const stored = getPeriodDetailsMap(breakdown)[period];
  return {
    ...emptyPeriodDetail(),
    ...stored,
    drawing_files: stored?.drawing_files ? [...stored.drawing_files] : [],
  };
}

export function periodSubmissionPercentage(
  entry: ConcentrationEntry,
  breakdown: SubmissionBreakdown | null | undefined,
  period: string,
  qty: number
): number {
  const detail = getPeriodDetail(breakdown, period);
  if (detail.submission_percentage != null) {
    return detail.submission_percentage;
  }
  return computeSubmissionPercentage(entry.estimated_quantity || 0, qty);
}

export function entryTotalInternalQuantity(entry: ConcentrationEntry): number {
  const details = getPeriodDetailsMap(entry.submission_breakdown);
  const periods = Object.keys(details);
  if (periods.length > 0) {
    return periods.reduce(
      (sum, period) => sum + (details[period].internal_quantity || 0),
      0
    );
  }
  return entry.internal_quantity || 0;
}

export function entryTotalApprovedQuantity(entry: ConcentrationEntry): number {
  const details = getPeriodDetailsMap(entry.submission_breakdown);
  const periods = Object.keys(details);
  if (periods.length > 0) {
    return periods.reduce(
      (sum, period) =>
        sum + (details[period].approved_by_project_manager || 0),
      0
    );
  }
  return entry.approved_by_project_manager || 0;
}

export function getPeriodDrawingFiles(
  entry: ConcentrationEntry,
  period: string
): string[] {
  const detail = getPeriodDetail(entry.submission_breakdown, period);
  if (detail.drawing_files?.length) {
    return detail.drawing_files;
  }
  if (period === resolveCurrentPeriod(entry, entry.submission_breakdown)) {
    return entry.drawing_files || [];
  }
  return [];
}

export function getCurrentPeriodFields(entry: ConcentrationEntry) {
  const period = resolveCurrentPeriod(entry, entry.submission_breakdown);
  if (!period || !entry.submission_breakdown?.periods) {
    return {
      internal_quantity: entry.internal_quantity ?? 0,
      approved_by_project_manager: entry.approved_by_project_manager ?? 0,
      submission_percentage: entry.submission_percentage ?? 100,
      notes: entry.notes || "",
      supervisor_notes: entry.supervisor_notes || "",
      drawing_files: entry.drawing_files || [],
    };
  }
  const detail = getPeriodDetail(entry.submission_breakdown, period);
  const qty = entry.quantity_submitted || 0;
  return {
    internal_quantity: detail.internal_quantity ?? 0,
    approved_by_project_manager: detail.approved_by_project_manager ?? 0,
    submission_percentage: periodSubmissionPercentage(
      entry,
      entry.submission_breakdown,
      period,
      qty
    ),
    notes: detail.notes || "",
    supervisor_notes: detail.supervisor_notes || "",
    drawing_files: getPeriodDrawingFiles(entry, period),
  };
}

export interface BreakdownPeriodRow {
  period: string;
  qty: number;
  isCurrent: boolean;
  detail: PeriodDetail;
  submissionPercentage: number;
}

export function getBreakdownPeriodRows(
  entry: ConcentrationEntry
): BreakdownPeriodRow[] {
  const breakdown = entry.submission_breakdown;
  if (!breakdown) {
    return [];
  }

  const currentPeriod = resolveCurrentPeriod(entry, breakdown);
  const periods = breakdown.periods || breakdown.past_months || {};
  const periodKeys = Object.keys(periods).sort((a, b) =>
    a.length === b.length ? a.localeCompare(b) : a.length - b.length
  );

  return periodKeys.flatMap((period) => {
    const isCurrent = period === currentPeriod;
    const qty = isCurrent
      ? entry.quantity_submitted || periods[period] || 0
      : periods[period] || 0;
    if (qty === 0 && !isCurrent) {
      return [];
    }
    const detail = getPeriodDetail(breakdown, period);
    return [
      {
        period,
        qty,
        isCurrent,
        detail,
        submissionPercentage: periodSubmissionPercentage(
          entry,
          breakdown,
          period,
          qty
        ),
      },
    ];
  });
}

export function breakdownTotalsForEntry(entry: ConcentrationEntry) {
  const rows = getBreakdownPeriodRows(entry);
  return {
    internalTotal: rows.reduce(
      (sum, row) => sum + (row.detail.internal_quantity || 0),
      0
    ),
    approvedTotal: rows.reduce(
      (sum, row) => sum + (row.detail.approved_by_project_manager || 0),
      0
    ),
    submittedTotal: rows.reduce((sum, row) => sum + row.qty, 0),
  };
}
