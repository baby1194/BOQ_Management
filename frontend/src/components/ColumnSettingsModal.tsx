import React from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";

interface ColumnVisibility {
  [key: string]: boolean;
}

interface ColumnSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  columnVisibility: ColumnVisibility;
  onToggleColumn: (columnKey: string) => void;
  onResetColumns: () => void;
  title: string;
}

const ColumnSettingsModal: React.FC<ColumnSettingsModalProps> = ({
  isOpen,
  onClose,
  columnVisibility,
  onToggleColumn,
  onResetColumns,
  title,
}) => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div
        className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white"
        dir={isRTL ? "rtl" : "ltr"}
      >
        <div className="mt-3">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {title} - {t("common.columnSettings")}
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
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

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {Object.entries(columnVisibility).map(([key, visible]) => (
              <label
                key={key}
                className="flex items-center space-x-2 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={visible}
                  onChange={() => onToggleColumn(key)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {formatColumnName(key, t)}
                </span>
              </label>
            ))}
          </div>

          <div className="mt-6 flex justify-between">
            <button
              onClick={onResetColumns}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              {t("common.resetAll")}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {t("common.close")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to format column names for display
const formatColumnName = (key: string, t: (key: string) => string): string => {
  const nameMap: { [key: string]: string } = {
    // Basic columns
    structure: t("boq.structure"),
    system: t("boq.system"),
    subsection: t("boq.subchapter"),
    description: t("boq.description"),
    total_contract_sum: t("boq.contractSum"),
    total_estimate: t("boq.totalEstimate"),
    total_submitted: t("boq.totalSubmitted"),
    internal_total: t("boq.internalTotal"),
    total_approved_by_project_manager: t("boq.totalApproved"),
    approved_signed_total: t("boq.approvedSignedTotal"),

    // Contract update columns (dynamic)
    total_updated_contract_sum: t("boq.totalUpdatedContractSum"),
  };

  // Handle dynamic contract update columns
  if (key.startsWith("updated_contract_sum_")) {
    const updateIndex = key.split("_").pop();
    return `${t("boq.totalUpdatedContractSum")} ${updateIndex}`;
  }

  // Handle structure/system/subsection specific columns
  if (key.includes("_description")) {
    const prefix = key.replace("_description", "");
    return `${formatColumnName(prefix, t)} ${t("boq.description")}`;
  }

  return (
    nameMap[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
  );
};

export default ColumnSettingsModal;
