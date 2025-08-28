import React, { useState } from "react";
import { SummaryExportRequest } from "../types";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (request: SummaryExportRequest, format: "pdf" | "excel") => void;
  title: string;
  loading?: boolean;
}

const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  onExport,
  title,
  loading = false,
}) => {
  const [exportRequest, setExportRequest] = useState<SummaryExportRequest>({
    include_structure: true,
    include_description: true,
    include_total_estimate: true,
    include_total_submitted: true,
    include_internal_total: true,
    include_total_approved: true,
    include_approved_signed_total: true,
    include_item_count: true,
  });

  const handleCheckboxChange = (field: keyof SummaryExportRequest) => {
    setExportRequest((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const handleSelectAll = () => {
    setExportRequest({
      include_structure: true,
      include_description: true,
      include_total_estimate: true,
      include_total_submitted: true,
      include_internal_total: true,
      include_total_approved: true,
      include_approved_signed_total: true,
      include_item_count: true,
    });
  };

  const handleDeselectAll = () => {
    setExportRequest({
      include_structure: false,
      include_description: false,
      include_total_estimate: false,
      include_total_submitted: false,
      include_internal_total: false,
      include_total_approved: false,
      include_approved_signed_total: false,
      include_item_count: false,
    });
  };

  const handleExport = (format: "pdf" | "excel") => {
    onExport(exportRequest, format);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
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
            Select the columns you want to include in the export:
          </p>

          <div className="flex gap-2 mb-3">
            <button
              onClick={handleSelectAll}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
              disabled={loading}
            >
              Select All
            </button>
            <button
              onClick={handleDeselectAll}
              className="px-3 py-1 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              disabled={loading}
            >
              Deselect All
            </button>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_structure}
                onChange={() => handleCheckboxChange("include_structure")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Structure/System/Subsection</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_description}
                onChange={() => handleCheckboxChange("include_description")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Description</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_total_estimate}
                onChange={() => handleCheckboxChange("include_total_estimate")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Total Estimate</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_total_submitted}
                onChange={() => handleCheckboxChange("include_total_submitted")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Total Submitted</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_internal_total}
                onChange={() => handleCheckboxChange("include_internal_total")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Internal Total</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_total_approved}
                onChange={() => handleCheckboxChange("include_total_approved")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Total Approved</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_approved_signed_total}
                onChange={() =>
                  handleCheckboxChange("include_approved_signed_total")
                }
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Approved Signed Total</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                checked={exportRequest.include_item_count}
                onChange={() => handleCheckboxChange("include_item_count")}
                className="mr-2"
                disabled={loading}
              />
              <span className="text-sm">Item Count</span>
            </label>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => handleExport("pdf")}
            disabled={loading || Object.values(exportRequest).every((v) => !v)}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Exporting..." : "Export PDF"}
          </button>

          <button
            onClick={() => handleExport("excel")}
            disabled={loading || Object.values(exportRequest).every((v) => !v)}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Exporting..." : "Export Excel"}
          </button>
        </div>

        {Object.values(exportRequest).every((v) => !v) && (
          <p className="text-sm text-red-600 mt-2 text-center">
            Please select at least one column to export
          </p>
        )}
      </div>
    </div>
  );
};

export default ExportModal;
