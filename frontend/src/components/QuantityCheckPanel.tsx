import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronUp, GripHorizontal, X } from "lucide-react";
import { useQuantityCheck } from "../contexts/QuantityCheckContext";
import { formatNumber } from "../utils/format";
import { getProjectItem, setProjectItem } from "../utils/localStorage";

const HEIGHT_KEY = "quantity-check-panel-height";
const DEFAULT_HEIGHT = 320;
const MIN_HEIGHT = 200;

function clampHeight(value: number): number {
  const max = Math.max(MIN_HEIGHT, window.innerHeight - 48);
  return Math.min(max, Math.max(MIN_HEIGHT, Math.round(value)));
}

function readStoredHeight(): number {
  const raw = getProjectItem(HEIGHT_KEY);
  const parsed = raw ? Number(raw) : DEFAULT_HEIGHT;
  if (!Number.isFinite(parsed)) {
    return DEFAULT_HEIGHT;
  }
  return clampHeight(parsed);
}

const headerCellClass =
  "sticky top-0 z-10 bg-white px-2 py-1 text-start shadow-[inset_0_-1px_0_0_rgb(229,231,235)]";

const QuantityCheckPanel: React.FC = () => {
  const { t } = useTranslation();
  const { mismatches, failed, close } = useQuantityCheck();
  const [collapsed, setCollapsed] = useState(false);
  const [hideManual, setHideManual] = useState(false);
  const [hideNonBoq, setHideNonBoq] = useState(false);
  const [height, setHeight] = useState(readStoredHeight);
  const [resizing, setResizing] = useState(false);

  useEffect(() => {
    setProjectItem(HEIGHT_KEY, String(height));
  }, [height]);

  useEffect(() => {
    if (!resizing) {
      return;
    }

    const handlePointerMove = (event: PointerEvent) => {
      setHeight(clampHeight(window.innerHeight - event.clientY - 16));
    };
    const handlePointerUp = () => {
      setResizing(false);
    };

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [resizing]);

  if (!mismatches && !failed) return null;

  const rows = (mismatches || []).filter((row) => {
    if (hideManual && row.has_manual_entries) return false;
    if (hideNonBoq && row.is_non_boq) return false;
    return true;
  });

  return (
    <div
      className="fixed bottom-4 inset-x-4 z-40 flex flex-col bg-white rounded-lg shadow-2xl border border-amber-300"
      style={collapsed ? undefined : { height }}
    >
      {!collapsed && (
        <div
          role="separator"
          aria-orientation="horizontal"
          aria-label={t("calculationSheets.quantityCheckResize")}
          aria-valuemin={MIN_HEIGHT}
          aria-valuemax={Math.max(MIN_HEIGHT, window.innerHeight - 48)}
          aria-valuenow={height}
          tabIndex={0}
          title={t("calculationSheets.quantityCheckResize")}
          className={`absolute -top-3 inset-x-8 z-10 flex h-6 cursor-row-resize items-center justify-center touch-none select-none rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
            resizing ? "bg-amber-100" : ""
          }`}
          onPointerDown={(event) => {
            event.preventDefault();
            setResizing(true);
          }}
          onKeyDown={(event) => {
            if (event.key !== "ArrowUp" && event.key !== "ArrowDown") {
              return;
            }
            event.preventDefault();
            const step = event.shiftKey ? 40 : 16;
            const direction = event.key === "ArrowUp" ? 1 : -1;
            setHeight((current) => clampHeight(current + direction * step));
          }}
          onDoubleClick={() => setHeight(clampHeight(DEFAULT_HEIGHT))}
        >
          <span
            className={`flex h-5 w-10 items-center justify-center rounded-md border shadow-sm ${
              resizing
                ? "border-amber-500 bg-amber-50 text-amber-700"
                : "border-amber-300 bg-white text-amber-700"
            }`}
          >
            <GripHorizontal className="h-4 w-4" aria-hidden />
          </span>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-amber-200 bg-amber-50 rounded-t-lg shrink-0">
        <span className="font-semibold text-amber-900 text-sm">
          {t("calculationSheets.quantityCheckTitle")}
          {mismatches ? ` (${rows.length}/${mismatches.length})` : ""}
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCollapsed((value) => !value)}
            className="p-1 rounded hover:bg-amber-100 text-amber-900"
            aria-label={
              collapsed
                ? t("calculationSheets.quantityCheckExpand")
                : t("calculationSheets.quantityCheckCollapse")
            }
          >
            {collapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={close}
            className="p-1 rounded hover:bg-amber-100 text-amber-900"
            aria-label={t("common.close")}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="flex min-h-0 flex-1 flex-col">
          {failed ? (
            <p className="p-4 text-sm text-red-600">{t("calculationSheets.quantityCheckFailed")}</p>
          ) : mismatches && mismatches.length === 0 ? (
            <p className="p-4 text-sm text-green-700">{t("calculationSheets.quantityCheckOk")}</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-4 px-4 py-3 text-sm text-gray-700 shrink-0">
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={hideManual}
                    onChange={(event) => setHideManual(event.target.checked)}
                  />
                  {t("calculationSheets.hideManual")}
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={hideNonBoq}
                    onChange={(event) => setHideNonBoq(event.target.checked)}
                  />
                  {t("calculationSheets.hideNonBoq")}
                </label>
              </div>
              {rows.length === 0 ? (
                <p className="px-4 pb-4 text-sm text-gray-600">
                  {t("calculationSheets.quantityCheckFilteredEmpty")}
                </p>
              ) : (
                <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
                  <table className="min-w-full text-sm border-separate border-spacing-0">
                    <thead>
                      <tr>
                        <th className={headerCellClass}>{t("boq.sectionNumber")}</th>
                        <th className={headerCellClass}>{t("calculationSheets.sheetCalculated")}</th>
                        <th className={headerCellClass}>{t("calculationSheets.systemCalculated")}</th>
                        <th className={headerCellClass}>{t("calculationSheets.calculatedDiff")}</th>
                        <th className={headerCellClass}>{t("calculationSheets.sheetSubmitted")}</th>
                        <th className={headerCellClass}>{t("calculationSheets.systemSubmitted")}</th>
                        <th className={headerCellClass}>{t("calculationSheets.submittedDiff")}</th>
                        <th className={headerCellClass}>{t("siteWork.classification")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.section_number}>
                          <td className="px-2 py-1 border-t border-gray-100">
                            <Link
                              to={`/concentration?sectionNumber=${encodeURIComponent(row.section_number)}`}
                              className="text-blue-600 hover:text-blue-800 hover:underline"
                            >
                              {row.section_number}
                            </Link>
                            {row.has_manual_entries && (
                              <span className="ms-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                {t("boq.manualEntry")}
                              </span>
                            )}
                          </td>
                          <td className="px-2 py-1 border-t border-gray-100">{formatNumber(row.sheet_calculated)}</td>
                          <td className="px-2 py-1 border-t border-gray-100">{formatNumber(row.system_calculated)}</td>
                          <td className="px-2 py-1 border-t border-gray-100">{formatNumber(row.calculated_diff)}</td>
                          <td className="px-2 py-1 border-t border-gray-100">{formatNumber(row.sheet_submitted)}</td>
                          <td className="px-2 py-1 border-t border-gray-100">{formatNumber(row.system_submitted)}</td>
                          <td className="px-2 py-1 border-t border-gray-100">{formatNumber(row.submitted_diff)}</td>
                          <td className="px-2 py-1 border-t border-gray-100">{row.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default QuantityCheckPanel;
