import React from "react";
import { useTranslation } from "react-i18next";
import { ChevronRight, ChevronUp } from "lucide-react";
import { SubmissionBreakdown } from "../types";
import { formatNumber } from "../utils/format";
import {
  cumulativeSubmittedQuantity,
  getAllBreakdownPeriodRows,
  getPastPeriodRows,
  resolveCurrentPeriod,
} from "../utils/submissionBreakdown";

interface SubmissionBreakdownPanelProps {
  breakdown?: SubmissionBreakdown | null;
  quantitySubmitted: number;
  compact?: boolean;
  currentInvoiceId?: string | null;
}

interface SubmissionBreakdownTableLayout {
  columnCount: number;
  invoiceColumnIndex: number;
  qtyColumnIndex: number;
  percentageColumnIndex?: number;
}

interface SubmissionBreakdownTableRowsProps
  extends SubmissionBreakdownPanelProps,
    SubmissionBreakdownTableLayout {
  estimatedQuantity?: number;
}

const TOTAL_ROW_CLASS = "bg-gray-200/80 text-gray-700";

function getBreakdownTotals(
  breakdown: SubmissionBreakdown | null | undefined,
  quantitySubmitted: number,
  currentInvoiceId?: string | null,
) {
  if (!breakdown) {
    return null;
  }

  const currentPeriod = resolveCurrentPeriod(breakdown, currentInvoiceId);
  const pastRows = getPastPeriodRows(breakdown, currentPeriod);
  const cumulativeTotal =
    cumulativeSubmittedQuantity(breakdown) ||
    quantitySubmitted + pastRows.reduce((sum, row) => sum + row.qty, 0);

  return { pastRows, cumulativeTotal };
}

function formatSubmissionPercentage(
  estimatedQuantity: number,
  cumulativeSubmitted: number,
): string {
  const estimated = estimatedQuantity || 0;
  const submitted = cumulativeSubmitted || 0;
  if (estimated > 0) {
    return `${formatNumber((submitted / estimated) * 100, 1)}%`;
  }
  return `${formatNumber(100, 1)}%`;
}

const renderBreakdownCells = (
  layout: SubmissionBreakdownTableLayout,
  cells: {
    invoiceCell?: React.ReactNode;
    qtyCell?: React.ReactNode;
    percentageCell?: React.ReactNode;
  },
  cellClassName: string,
) =>
  Array.from({ length: layout.columnCount }, (_, index) => {
    let content: React.ReactNode = "";
    if (index === layout.invoiceColumnIndex) {
      content = cells.invoiceCell ?? "";
    } else if (index === layout.qtyColumnIndex) {
      content = cells.qtyCell ?? "";
    } else if (
      layout.percentageColumnIndex !== undefined &&
      index === layout.percentageColumnIndex
    ) {
      content = cells.percentageCell ?? "";
    }

    return (
      <td key={index} className={cellClassName}>
        {content}
      </td>
    );
  });

export const SubmissionBreakdownPastRows: React.FC<
  SubmissionBreakdownTableRowsProps
> = ({
  breakdown,
  quantitySubmitted,
  currentInvoiceId,
  estimatedQuantity = 0,
  columnCount,
  invoiceColumnIndex,
  qtyColumnIndex,
  percentageColumnIndex,
}) => {
  const { t } = useTranslation();
  const layout = {
    columnCount,
    invoiceColumnIndex,
    qtyColumnIndex,
    percentageColumnIndex,
  };

  if (!breakdown) {
    return (
      <tr className="bg-gray-50/70">
        <td colSpan={columnCount} className="px-3 py-2 text-sm text-gray-600">
          {t("submissionBreakdown.retrackToLoad")}
        </td>
      </tr>
    );
  }

  const totals = getBreakdownTotals(
    breakdown,
    quantitySubmitted,
    currentInvoiceId,
  );
  if (!totals || totals.pastRows.length === 0) {
    return null;
  }

  return (
    <>
      {totals.pastRows.map(({ period, qty }) => (
        <tr key={`past-${period}`} className="bg-gray-50/70">
          {renderBreakdownCells(
            layout,
            {
              invoiceCell: (
                <span className="font-medium text-gray-700">{period}</span>
              ),
              percentageCell: formatSubmissionPercentage(
                estimatedQuantity,
                qty,
              ),
              qtyCell: formatNumber(qty),
            },
            "px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap",
          )}
        </tr>
      ))}
    </>
  );
};

export const SubmissionBreakdownCalcSheetRows: React.FC<
  SubmissionBreakdownTableRowsProps
> = ({
  breakdown,
  quantitySubmitted,
  currentInvoiceId,
  columnCount,
  invoiceColumnIndex,
  qtyColumnIndex,
}) => {
  const { t } = useTranslation();
  const layout = {
    columnCount,
    invoiceColumnIndex,
    qtyColumnIndex,
  };

  if (!breakdown) {
    return (
      <tr className="bg-gray-50/70">
        <td colSpan={columnCount} className="px-3 py-2 text-sm text-gray-600">
          {t("submissionBreakdown.retrackToLoad")}
        </td>
      </tr>
    );
  }

  const currentPeriod = resolveCurrentPeriod(breakdown, currentInvoiceId);
  const periodRows = getAllBreakdownPeriodRows(
    breakdown,
    currentPeriod,
    quantitySubmitted,
  );

  if (periodRows.length === 0) {
    return null;
  }

  return (
    <>
      {periodRows.map(({ period, qty, isCurrent }) => (
        <tr key={`period-${period}`} className="bg-gray-50/70">
          {renderBreakdownCells(
            layout,
            {
              invoiceCell: (
                <span
                  className={`font-medium ${
                    isCurrent ? "font-semibold text-blue-700" : "text-gray-700"
                  }`}
                >
                  {period}
                </span>
              ),
              qtyCell: (
                <span className={isCurrent ? "font-semibold text-blue-700" : ""}>
                  {formatNumber(qty)}
                </span>
              ),
            },
            "px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap",
          )}
        </tr>
      ))}
    </>
  );
};

export const SubmissionBreakdownTotalRow: React.FC<
  SubmissionBreakdownTableRowsProps
> = ({
  breakdown,
  quantitySubmitted,
  currentInvoiceId,
  estimatedQuantity = 0,
  columnCount,
  invoiceColumnIndex,
  qtyColumnIndex,
  percentageColumnIndex,
}) => {
  const { t } = useTranslation();
  const layout = {
    columnCount,
    invoiceColumnIndex,
    qtyColumnIndex,
    percentageColumnIndex,
  };

  if (!breakdown) {
    return null;
  }

  const totals = getBreakdownTotals(
    breakdown,
    quantitySubmitted,
    currentInvoiceId,
  );
  if (!totals) {
    return null;
  }

  const { cumulativeTotal } = totals;
  const percentageLabel = formatSubmissionPercentage(
    estimatedQuantity,
    cumulativeTotal,
  );

  return (
    <tr className={`${TOTAL_ROW_CLASS} border-t border-gray-300`}>
      {renderBreakdownCells(
        layout,
        {
          invoiceCell: (
            <span className="font-semibold text-gray-800">
              {t("common.total")}
            </span>
          ),
          percentageCell: (
            <span className="font-semibold text-gray-800">
              {percentageLabel}
            </span>
          ),
          qtyCell: (
            <span className="font-semibold text-gray-800">
              {formatNumber(cumulativeTotal)}
            </span>
          ),
        },
        "px-3 py-1.5 text-sm align-top whitespace-nowrap",
      )}
    </tr>
  );
};

/** @deprecated Use SubmissionBreakdownPastRows and SubmissionBreakdownTotalRow */
export const SubmissionBreakdownTableRows: React.FC<
  SubmissionBreakdownTableRowsProps
> = (props) => (
  <>
    <SubmissionBreakdownPastRows {...props} />
    <SubmissionBreakdownTotalRow {...props} />
  </>
);

export const SubmissionBreakdownPanel: React.FC<
  SubmissionBreakdownPanelProps
> = ({
  breakdown,
  quantitySubmitted,
  compact = false,
  currentInvoiceId,
}) => {
  const { t } = useTranslation();

  if (!breakdown) {
    return (
      <div className="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600">
        {t("submissionBreakdown.retrackToLoad")}
      </div>
    );
  }

  const totals = getBreakdownTotals(
    breakdown,
    quantitySubmitted,
    currentInvoiceId,
  );
  if (!totals || (totals.pastRows.length === 0 && totals.cumulativeTotal === 0)) {
    return (
      <div
        className={`rounded-md border border-gray-200 bg-gray-50 text-sm text-gray-600 ${
          compact ? "px-3 py-2" : "px-4 py-3"
        }`}
      >
        {t("submissionBreakdown.noNonZeroSubmitted")}
      </div>
    );
  }

  return (
    <div
      className={`rounded-md border border-gray-200 bg-gray-50 ${
        compact ? "px-3 py-2" : "px-4 py-3"
      }`}
    >
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <tbody className="text-gray-800">
            {totals.pastRows.map(({ period, qty }) => (
              <tr key={period}>
                <td className="py-0.5 pe-4 font-medium text-gray-700">
                  {period}
                </td>
                <td className="py-0.5">{formatNumber(qty)}</td>
              </tr>
            ))}
            <tr className={TOTAL_ROW_CLASS}>
              <td className="py-0.5 pe-4 font-semibold text-gray-800">
                {t("common.total")}
              </td>
              <td className="py-0.5 font-semibold text-gray-800">
                {formatNumber(totals.cumulativeTotal)}
              </td>
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
  const Icon = expanded ? ChevronUp : ChevronRight;

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
