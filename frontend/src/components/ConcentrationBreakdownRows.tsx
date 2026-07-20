import React from "react";
import { useTranslation } from "react-i18next";
import { ConcentrationEntry } from "../types";
import { formatNumber } from "../utils/format";
import ConcentrationDrawingFilesCell from "./ConcentrationDrawingFilesCell";
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
  onRemoveDrawing: (
    entryId: number,
    path: string,
    invoiceNo?: string
  ) => void;
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

  if (!entry.submission_breakdown || rows.length === 0) {
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
            <td className="px-3 py-1 text-sm text-gray-600 align-top max-w-[14rem]">
              <div
                className="truncate py-1"
                title={row.detail.invoice_description || ""}
              >
                {row.detail.invoice_description || "-"}
              </div>
            </td>
            <td className="px-3 py-1 text-sm text-gray-500 align-middle min-w-[10rem] max-w-[14rem]">
              <ConcentrationDrawingFilesCell
                drawingFiles={drawingFiles}
                isRTL={isRTL}
                isUploading={isUploading}
                isExpanded={
                  isDrawingExpanded && drawingFiles.length > 1
                }
                onAttach={() => onAttachDrawing(entry.id, row.period)}
                onOpen={(path) => onOpenDrawing(entry.id, path)}
                onRemove={(path) =>
                  onRemoveDrawing(entry.id, path, row.period)
                }
                onToggleExpanded={() => onToggleDrawingExpanded(key)}
                drawingFileName={drawingFileName}
              />
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
