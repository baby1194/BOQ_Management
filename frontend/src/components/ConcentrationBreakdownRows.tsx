import React from "react";
import { useTranslation } from "react-i18next";
import { FileText, Paperclip } from "lucide-react";
import { ConcentrationEntry } from "../types";
import { formatNumber } from "../utils/format";
import {
  breakdownTotalsForEntry,
  getBreakdownPeriodRows,
  getPeriodDrawingFiles,
} from "../utils/periodDetails";

export type PeriodEditDraft = {
  submission_percentage: number;
  internal_quantity: number;
  approved_by_project_manager: number;
  notes: string;
  supervisor_notes: string;
};

interface ConcentrationBreakdownRowsProps {
  entry: ConcentrationEntry;
  columnCount: number;
  isRTL: boolean;
  saving: boolean;
  periodEdit:
    | {
        entryId: number;
        period: string;
        draft: PeriodEditDraft;
      }
    | null;
  uploadingDrawingKey: string | null;
  expandedDrawingKeys: Set<string>;
  onStartPeriodEdit: (entry: ConcentrationEntry, period: string) => void;
  onPeriodDraftChange: (draft: PeriodEditDraft) => void;
  onSavePeriodEdit: () => void;
  onCancelPeriodEdit: () => void;
  onAttachDrawing: (entryId: number, period: string) => void;
  onOpenDrawing: (entryId: number, path: string) => void;
  onRemoveDrawing: (entryId: number, period: string, path: string) => void;
  onToggleDrawingExpanded: (key: string) => void;
  drawingFileName: (path: string) => string;
}

const TOTAL_ROW_CLASS = "bg-gray-200/80 text-gray-700";

function drawingKey(entryId: number, period: string) {
  return `${entryId}:${period}`;
}

export const ConcentrationBreakdownPastRows: React.FC<
  ConcentrationBreakdownRowsProps
> = ({
  entry,
  columnCount,
  isRTL,
  saving,
  periodEdit,
  uploadingDrawingKey,
  expandedDrawingKeys,
  onStartPeriodEdit,
  onPeriodDraftChange,
  onSavePeriodEdit,
  onCancelPeriodEdit,
  onAttachDrawing,
  onOpenDrawing,
  onRemoveDrawing,
  onToggleDrawingExpanded,
  drawingFileName,
}) => {
  const { t } = useTranslation();
  const rows = getBreakdownPeriodRows(entry).filter((row) => !row.isCurrent);

  if (!entry.submission_breakdown) {
    return (
      <tr className="bg-gray-50/70">
        <td colSpan={columnCount} className="px-3 py-2 text-sm text-gray-600">
          {t("submissionBreakdown.retrackToLoad")}
        </td>
      </tr>
    );
  }

  if (rows.length === 0) {
    return null;
  }

  return (
    <>
      {rows.map((row) => {
        const isEditing =
          periodEdit?.entryId === entry.id && periodEdit.period === row.period;
        const draft = isEditing ? periodEdit.draft : null;
        const drawingFiles = getPeriodDrawingFiles(entry, row.period);
        const key = drawingKey(entry.id, row.period);
        const isUploading = uploadingDrawingKey === key;
        const showToggle = drawingFiles.length > 1;
        const isDrawingExpanded = expandedDrawingKeys.has(key);

        return (
          <tr
            key={`past-${entry.id}-${row.period}`}
            className="bg-gray-50/70"
            onDoubleClick={(e) => {
              const target = e.target as HTMLElement;
              if (target.closest("button, a, input, textarea, select")) return;
              if (saving || isEditing) return;
              onStartPeriodEdit(entry, row.period);
            }}
            title={t("concentration.doubleClickToEdit")}
          >
            <td className="px-2 py-1" />
            <td className="px-3 py-1" />
            <td className="px-3 py-1" />
            <td className="px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap">
              <span className="font-medium text-gray-700">{row.period}</span>
            </td>
            <td className="px-3 py-1 text-sm text-gray-500 align-middle min-w-[10rem] max-w-[14rem]">
              <div className="flex flex-col items-stretch justify-center gap-2 min-h-[2.5rem]">
                {drawingFiles.length === 0 ? (
                  <div className="flex justify-center w-full">
                    <button
                      type="button"
                      onClick={() => onAttachDrawing(entry.id, row.period)}
                      onDoubleClick={(e) => e.stopPropagation()}
                      disabled={isUploading}
                      className="inline-flex items-center justify-center gap-1 bg-indigo-600 text-white px-2 py-1 rounded-md text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
                    >
                      <Paperclip className="h-3.5 w-3.5" />
                      <span>
                        {isUploading
                          ? t("concentration.uploadingDrawings")
                          : t("concentration.attachDrawings")}
                      </span>
                    </button>
                  </div>
                ) : (
                  <>
                    {(isDrawingExpanded ? drawingFiles : drawingFiles.slice(0, 1)).map(
                      (filePath) => (
                        <div
                          key={filePath}
                          className={`flex items-center gap-1 rounded bg-gray-50 border border-gray-200 px-2 py-1 min-w-0 ${
                            isRTL ? "flex-row-reverse" : ""
                          }`}
                        >
                          <FileText className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                          <button
                            type="button"
                            onClick={() => onOpenDrawing(entry.id, filePath)}
                            onDoubleClick={(e) => e.stopPropagation()}
                            className="flex-1 min-w-0 text-blue-600 hover:text-blue-800 hover:underline truncate text-xs text-left"
                            title={filePath}
                          >
                            {drawingFileName(filePath)}
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              onRemoveDrawing(entry.id, row.period, filePath)
                            }
                            onDoubleClick={(e) => e.stopPropagation()}
                            className="shrink-0 text-red-500 hover:text-red-700 text-sm leading-none px-0.5"
                          >
                            ×
                          </button>
                        </div>
                      )
                    )}
                    <div className="flex items-center gap-1">
                      {showToggle && (
                        <button
                          type="button"
                          onClick={() => onToggleDrawingExpanded(key)}
                          onDoubleClick={(e) => e.stopPropagation()}
                          className="shrink-0 text-xs font-medium px-2 py-1 rounded border bg-sky-100 text-sky-800 border-sky-200"
                        >
                          {isDrawingExpanded
                          ? t("concentration.showLessDrawings")
                          : t("concentration.showMoreDrawings")}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => onAttachDrawing(entry.id, row.period)}
                        onDoubleClick={(e) => e.stopPropagation()}
                        disabled={isUploading}
                        className="inline-flex items-center gap-1 text-xs text-indigo-700 hover:text-indigo-900 disabled:opacity-50"
                      >
                        <Paperclip className="h-3.5 w-3.5" />
                        {t("concentration.attachDrawings")}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </td>
            <td className="px-3 py-1" />
            <td className="px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap">
              {isEditing && draft ? (
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    step="0.1"
                    min={0}
                    max={100}
                    value={draft.submission_percentage}
                    onChange={(e) =>
                      onPeriodDraftChange({
                        ...draft,
                        submission_percentage:
                          parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full max-w-[5rem] px-2 py-1 text-sm border border-gray-300 rounded"
                    disabled={saving}
                  />
                  <span>%</span>
                </div>
              ) : (
                `${formatNumber(row.submissionPercentage, 1)}%`
              )}
            </td>
            <td className="px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap">
              {formatNumber(row.qty)}
            </td>
            <td className="px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap">
              {isEditing && draft ? (
                <input
                  type="number"
                  step="0.01"
                  value={draft.internal_quantity}
                  onChange={(e) =>
                    onPeriodDraftChange({
                      ...draft,
                      internal_quantity: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full max-w-[7rem] px-2 py-1 text-sm border border-gray-300 rounded"
                  disabled={saving}
                />
              ) : (
                formatNumber(row.detail.internal_quantity || 0)
              )}
            </td>
            <td className="px-3 py-1 text-sm text-gray-600 align-top whitespace-nowrap">
              {isEditing && draft ? (
                <input
                  type="number"
                  step="0.01"
                  value={draft.approved_by_project_manager}
                  onChange={(e) =>
                    onPeriodDraftChange({
                      ...draft,
                      approved_by_project_manager:
                        parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full max-w-[7rem] px-2 py-1 text-sm border border-gray-300 rounded"
                  disabled={saving}
                />
              ) : (
                formatNumber(row.detail.approved_by_project_manager || 0)
              )}
            </td>
            <td className="px-3 py-1 text-sm text-gray-600 align-top max-w-[10rem]">
              {isEditing && draft ? (
                <textarea
                  value={draft.notes}
                  onChange={(e) =>
                    onPeriodDraftChange({ ...draft, notes: e.target.value })
                  }
                  rows={2}
                  className="w-full min-w-0 px-2 py-1 text-sm border border-gray-300 rounded resize-y"
                  disabled={saving}
                />
              ) : (
                <div className="truncate py-1" title={row.detail.notes || ""}>
                  {row.detail.notes || "-"}
                </div>
              )}
            </td>
            <td className="px-3 py-1 text-sm text-gray-600 align-top max-w-[10rem]">
              {isEditing && draft ? (
                <textarea
                  value={draft.supervisor_notes}
                  onChange={(e) =>
                    onPeriodDraftChange({
                      ...draft,
                      supervisor_notes: e.target.value,
                    })
                  }
                  rows={2}
                  className="w-full min-w-0 px-2 py-1 text-sm border border-gray-300 rounded resize-y"
                  disabled={saving}
                />
              ) : (
                <div
                  className="truncate py-1"
                  title={row.detail.supervisor_notes || ""}
                >
                  {row.detail.supervisor_notes || "-"}
                </div>
              )}
            </td>
            <td className="px-3 py-1 text-sm text-gray-500 align-top whitespace-nowrap">
              {isEditing ? (
                <div
                  className={`flex flex-wrap gap-2 ${
                    isRTL ? "flex-row-reverse" : ""
                  }`}
                >
                  <button
                    type="button"
                    onClick={onSavePeriodEdit}
                    disabled={saving}
                    className="text-green-600 hover:text-green-800 disabled:opacity-50"
                  >
                    {t("common.save")}
                  </button>
                  <button
                    type="button"
                    onClick={onCancelPeriodEdit}
                    disabled={saving}
                    className="text-gray-600 hover:text-gray-800 disabled:opacity-50"
                  >
                    {t("common.cancel")}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => onStartPeriodEdit(entry, row.period)}
                  disabled={saving}
                  className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                >
                  {t("common.edit")}
                </button>
              )}
            </td>
          </tr>
        );
      })}
    </>
  );
};

export const ConcentrationBreakdownTotalRow: React.FC<{
  entry: ConcentrationEntry;
  columnCount: number;
}> = ({ entry, columnCount }) => {
  const { t } = useTranslation();
  if (!entry.submission_breakdown) {
    return null;
  }

  const totals = breakdownTotalsForEntry(entry);
  const estimated = entry.estimated_quantity || 0;
  const percentageLabel =
    estimated > 0
      ? `${formatNumber((totals.submittedTotal / estimated) * 100, 1)}%`
      : `${formatNumber(100, 1)}%`;

  return (
    <tr className={`${TOTAL_ROW_CLASS} border-t border-gray-300`}>
      <td className="px-2 py-1.5" />
      <td className="px-3 py-1.5" />
      <td className="px-3 py-1.5" />
      <td className="px-3 py-1.5 text-sm align-top whitespace-nowrap">
        <span className="font-semibold text-gray-800">{t("common.total")}</span>
      </td>
      <td className="px-3 py-1.5" />
      <td className="px-3 py-1.5" />
      <td className="px-3 py-1.5 text-sm align-top whitespace-nowrap">
        <span className="font-semibold text-gray-800">{percentageLabel}</span>
      </td>
      <td className="px-3 py-1.5 text-sm align-top whitespace-nowrap">
        <span className="font-semibold text-gray-800">
          {formatNumber(totals.submittedTotal)}
        </span>
      </td>
      <td className="px-3 py-1.5 text-sm align-top whitespace-nowrap">
        <span className="font-semibold text-gray-800">
          {formatNumber(totals.internalTotal)}
        </span>
      </td>
      <td className="px-3 py-1.5 text-sm align-top whitespace-nowrap">
        <span className="font-semibold text-gray-800">
          {formatNumber(totals.approvedTotal)}
        </span>
      </td>
      <td className="px-3 py-1.5" />
      <td className="px-3 py-1.5" />
      <td className="px-3 py-1.5" />
    </tr>
  );
};
