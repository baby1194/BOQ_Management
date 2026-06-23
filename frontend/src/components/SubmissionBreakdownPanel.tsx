import React from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronRight } from "lucide-react";
import { SubmissionBreakdown } from "../types";
import { formatNumber } from "../utils/format";

interface SubmissionBreakdownPanelProps {
  breakdown?: SubmissionBreakdown | null;
  quantitySubmitted: number;
  compact?: boolean;
}

const INVALID_PERIODS = new Set(["nan", "none", "<na>", "nat"]);

const getPeriodQuantities = (
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

const sortedPeriodKeys = (periods: Record<string, number>): string[] =>
  Object.keys(periods).sort((a, b) =>
    a.length === b.length ? a.localeCompare(b) : a.length - b.length,
  );

export const SubmissionBreakdownPanel: React.FC<
  SubmissionBreakdownPanelProps
> = ({ breakdown, quantitySubmitted, compact = false }) => {
  const { t } = useTranslation();

  if (!breakdown) {
    return (
      <div className="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600">
        {t("submissionBreakdown.retrackToLoad")}
      </div>
    );
  }

  const periodQuantities = getPeriodQuantities(breakdown);
  const periodKeys = sortedPeriodKeys(periodQuantities);
  const currentPeriod = breakdown.current_drawing_no?.trim() || "";
  const leftSubmitted = breakdown.left_submitted ?? 0;

  return (
    <div
      className={`rounded-md border border-gray-200 bg-gray-50 ${
        compact ? "px-3 py-2" : "px-4 py-3"
      }`}
    >
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {t("submissionBreakdown.title")}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-gray-500">
              <th className="pb-1 pe-4">{t("submissionBreakdown.period")}</th>
              <th className="pb-1">{t("submissionBreakdown.submittedQty")}</th>
            </tr>
          </thead>
          <tbody className="text-gray-800">
            {periodKeys.map((period) => {
              const isCurrent = period === currentPeriod;
              const qty = isCurrent
                ? quantitySubmitted
                : (periodQuantities[period] ?? 0);

              return (
                <tr
                  key={period}
                  className={isCurrent ? "border-t border-gray-200" : undefined}
                >
                  <td
                    className={`py-0.5 pe-4 font-medium ${
                      isCurrent ? "font-semibold text-blue-700" : ""
                    }`}
                  >
                    {isCurrent
                      ? t("submissionBreakdown.currentPeriod", { period })
                      : period}
                  </td>
                  <td
                    className={`py-0.5 ${
                      isCurrent ? "font-semibold text-blue-700" : ""
                    }`}
                  >
                    {formatNumber(qty)}
                  </td>
                </tr>
              );
            })}
            <tr className="border-t border-gray-200">
              <td className="py-0.5 pe-4 font-medium">
                {t("submissionBreakdown.leftSubmitted")}
              </td>
              <td className="py-0.5">{formatNumber(leftSubmitted)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface SubmissionBreakdownToggleProps {
  expanded: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export const SubmissionBreakdownToggle: React.FC<
  SubmissionBreakdownToggleProps
> = ({ expanded, onToggle, disabled = false }) => {
  const { t } = useTranslation();
  const Icon = expanded ? ChevronDown : ChevronRight;

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      onDoubleClick={(e) => e.stopPropagation()}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-800 disabled:opacity-40"
      title={t("submissionBreakdown.toggleDetails")}
      aria-label={t("submissionBreakdown.toggleDetails")}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
};

export default SubmissionBreakdownPanel;
