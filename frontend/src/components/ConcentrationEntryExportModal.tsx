import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { ConcentrationEntryExportRequest } from "../types";

interface ConcentrationEntryExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (request: ConcentrationEntryExportRequest) => void;
  title: string;
  loading?: boolean;
  exportFormat: "pdf" | "excel";
}

const ConcentrationEntryExportModal: React.FC<
  ConcentrationEntryExportModalProps
> = ({ isOpen, onClose, onExport, title, loading = false, exportFormat }) => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [exportRequest, setExportRequest] =
    useState<ConcentrationEntryExportRequest>(() => {
      const baseRequest = {
        include_description: true,
        include_calculation_sheet_no: true,
        include_drawing_no: true,
        include_estimated_quantity: true,
        include_quantity_submitted: true,
        include_internal_quantity: true,
        include_approved_by_project_manager: true,
        include_notes: true,
      };
      return baseRequest;
    });

  const handleCheckboxChange = (
    field: keyof ConcentrationEntryExportRequest
  ) => {
    setExportRequest((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const handleSelectAll = () => {
    setExportRequest({
      include_description: true,
      include_calculation_sheet_no: true,
      include_drawing_no: true,
      include_estimated_quantity: true,
      include_quantity_submitted: true,
      include_internal_quantity: true,
      include_approved_by_project_manager: true,
      include_notes: true,
    });
  };

  const handleDeselectAll = () => {
    setExportRequest({
      include_description: false,
      include_calculation_sheet_no: false,
      include_drawing_no: false,
      include_estimated_quantity: false,
      include_quantity_submitted: false,
      include_internal_quantity: false,
      include_approved_by_project_manager: false,
      include_notes: false,
    });
  };

  const handleExport = () => {
    onExport(exportRequest);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div
        className="bg-white rounded-lg p-6 w-full max-w-md mx-4"
        dir={isRTL ? "rtl" : "ltr"}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={loading}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-3">
            {t("concentration.selectColumnsForExport")}
          </p>

          <div className="flex gap-2 mb-3">
            <button
              onClick={handleSelectAll}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
              disabled={loading}
            >
              {t("common.selectAll")}
            </button>
            <button
              onClick={handleDeselectAll}
              className="px-3 py-1 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              disabled={loading}
            >
              {t("common.deselectAll")}
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_description}
                onChange={() => handleCheckboxChange("include_description")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("boq.description")}</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_calculation_sheet_no}
                onChange={() =>
                  handleCheckboxChange("include_calculation_sheet_no")
                }
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">
                {t("concentration.calculationSheetNo")}
              </span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_drawing_no}
                onChange={() => handleCheckboxChange("include_drawing_no")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("concentration.drawingNo")}</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_estimated_quantity}
                onChange={() =>
                  handleCheckboxChange("include_estimated_quantity")
                }
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("boq.estimatedQuantity")}</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_quantity_submitted}
                onChange={() =>
                  handleCheckboxChange("include_quantity_submitted")
                }
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("boq.quantitySubmitted")}</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_internal_quantity}
                onChange={() =>
                  handleCheckboxChange("include_internal_quantity")
                }
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("boq.internalQuantity")}</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_approved_by_project_manager}
                onChange={() =>
                  handleCheckboxChange("include_approved_by_project_manager")
                }
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("boq.approvedQuantity")}</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_notes}
                onChange={() => handleCheckboxChange("include_notes")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">{t("boq.notes")}</span>
            </label>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleExport}
            disabled={loading || Object.values(exportRequest).every((v) => !v)}
            className={`flex-1 px-4 py-2 text-white rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed ${
              exportFormat === "pdf"
                ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
                : "bg-green-600 hover:bg-green-700 focus:ring-green-500"
            }`}
          >
            {loading
              ? t("common.exporting")
              : `${t("common.export")} ${exportFormat.toUpperCase()}`}
          </button>
        </div>

        {Object.values(exportRequest).every((v) => !v) && (
          <p className="text-sm text-red-600 mt-2 text-center">
            {t("concentration.selectAtLeastOneColumn")}
          </p>
        )}
      </div>
    </div>
  );
};

export default ConcentrationEntryExportModal;
