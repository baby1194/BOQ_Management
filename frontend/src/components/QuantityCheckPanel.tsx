import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronUp, X } from "lucide-react";
import { useQuantityCheck } from "../contexts/QuantityCheckContext";
import { formatNumber } from "../utils/format";

const QuantityCheckPanel: React.FC = () => {
  const { t } = useTranslation();
  const { mismatches, failed, close } = useQuantityCheck();
  const [collapsed, setCollapsed] = useState(false);
  const [hideManual, setHideManual] = useState(false);
  const [hideNonBoq, setHideNonBoq] = useState(false);

  if (!mismatches && !failed) return null;

  const rows = (mismatches || []).filter((row) => {
    if (hideManual && row.has_manual_entries) return false;
    if (hideNonBoq && row.is_non_boq) return false;
    return true;
  });

  return (
    <div className="fixed bottom-4 inset-x-4 z-40 bg-white rounded-lg shadow-2xl border border-amber-300">
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-amber-200 bg-amber-50 rounded-t-lg">
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
        <div className="p-4 max-h-72 overflow-auto">
          {failed ? (
            <p className="text-sm text-red-600">{t("calculationSheets.quantityCheckFailed")}</p>
          ) : mismatches && mismatches.length === 0 ? (
            <p className="text-sm text-green-700">{t("calculationSheets.quantityCheckOk")}</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-4 mb-3 text-sm text-gray-700">
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
                <p className="text-sm text-gray-600">
                  {t("calculationSheets.quantityCheckFilteredEmpty")}
                </p>
              ) : (
                <table className="min-w-full text-sm">
                  <thead className="text-gray-600">
                    <tr>
                      <th className="px-2 py-1 text-start">{t("boq.sectionNumber")}</th>
                      <th className="px-2 py-1 text-start">{t("calculationSheets.sheetCalculated")}</th>
                      <th className="px-2 py-1 text-start">{t("calculationSheets.systemCalculated")}</th>
                      <th className="px-2 py-1 text-start">{t("calculationSheets.calculatedDiff")}</th>
                      <th className="px-2 py-1 text-start">{t("calculationSheets.sheetSubmitted")}</th>
                      <th className="px-2 py-1 text-start">{t("calculationSheets.systemSubmitted")}</th>
                      <th className="px-2 py-1 text-start">{t("calculationSheets.submittedDiff")}</th>
                      <th className="px-2 py-1 text-start">{t("siteWork.classification")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.section_number} className="border-t border-gray-100">
                        <td className="px-2 py-1">
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
                        <td className="px-2 py-1">{formatNumber(row.sheet_calculated)}</td>
                        <td className="px-2 py-1">{formatNumber(row.system_calculated)}</td>
                        <td className="px-2 py-1">{formatNumber(row.calculated_diff)}</td>
                        <td className="px-2 py-1">{formatNumber(row.sheet_submitted)}</td>
                        <td className="px-2 py-1">{formatNumber(row.system_submitted)}</td>
                        <td className="px-2 py-1">{formatNumber(row.submitted_diff)}</td>
                        <td className="px-2 py-1">{row.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default QuantityCheckPanel;
