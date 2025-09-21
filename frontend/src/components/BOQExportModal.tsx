import React, { useState } from "react";
import { ContractQuantityUpdate } from "../types";

interface BOQExportRequest {
  include_serial_number: boolean;
  include_structure: boolean;
  include_system: boolean;
  include_section_number: boolean;
  include_description: boolean;
  include_unit: boolean;
  include_original_contract_quantity: boolean;
  include_price: boolean;
  include_total_contract_sum: boolean;
  include_estimated_quantity: boolean;
  include_quantity_submitted: boolean;
  include_internal_quantity: boolean;
  include_approved_by_project_manager: boolean;
  include_approved_signed_quantity: boolean;
  include_total_estimate: boolean;
  include_total_submitted: boolean;
  include_internal_total: boolean;
  include_total_approved_by_project_manager: boolean;
  include_approved_signed_total: boolean;
  include_subsection: boolean;
  include_notes: boolean;
  // Dynamic contract update columns
  [key: string]: boolean;
}

interface BOQExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (request: BOQExportRequest, format: "excel" | "pdf") => void;
  title: string;
  loading?: boolean;
  contractUpdates?: ContractQuantityUpdate[];
}

const BOQExportModal: React.FC<BOQExportModalProps> = ({
  isOpen,
  onClose,
  onExport,
  title,
  loading = false,
  contractUpdates = [],
}) => {
  const [exportRequest, setExportRequest] = useState<BOQExportRequest>(() => {
    const baseRequest = {
      include_serial_number: true,
      include_structure: true,
      include_system: true,
      include_section_number: true,
      include_description: true,
      include_unit: true,
      include_original_contract_quantity: true,
      include_price: true,
      include_total_contract_sum: true,
      include_estimated_quantity: true,
      include_quantity_submitted: true,
      include_internal_quantity: true,
      include_approved_by_project_manager: true,
      include_approved_signed_quantity: true,
      include_total_estimate: true,
      include_total_submitted: true,
      include_internal_total: true,
      include_total_approved_by_project_manager: true,
      include_approved_signed_total: true,
      include_subsection: true,
      include_notes: true,
    };

    // Add contract update columns
    contractUpdates.forEach((update) => {
      baseRequest[`include_updated_contract_quantity_${update.id}`] = true;
      baseRequest[`include_updated_contract_sum_${update.id}`] = true;
    });

    return baseRequest;
  });

  const handleCheckboxChange = (field: keyof BOQExportRequest) => {
    setExportRequest((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const handleSelectAll = () => {
    const baseRequest = {
      include_serial_number: true,
      include_structure: true,
      include_system: true,
      include_section_number: true,
      include_description: true,
      include_unit: true,
      include_original_contract_quantity: true,
      include_price: true,
      include_total_contract_sum: true,
      include_estimated_quantity: true,
      include_quantity_submitted: true,
      include_internal_quantity: true,
      include_approved_by_project_manager: true,
      include_approved_signed_quantity: true,
      include_total_estimate: true,
      include_total_submitted: true,
      include_internal_total: true,
      include_total_approved_by_project_manager: true,
      include_approved_signed_total: true,
      include_subsection: true,
      include_notes: true,
    };

    // Add contract update columns
    contractUpdates.forEach((update) => {
      baseRequest[`include_updated_contract_quantity_${update.id}`] = true;
      baseRequest[`include_updated_contract_sum_${update.id}`] = true;
    });

    setExportRequest(baseRequest);
  };

  const handleDeselectAll = () => {
    const baseRequest = {
      include_serial_number: false,
      include_structure: false,
      include_system: false,
      include_section_number: false,
      include_description: false,
      include_unit: false,
      include_original_contract_quantity: false,
      include_price: false,
      include_total_contract_sum: false,
      include_estimated_quantity: false,
      include_quantity_submitted: false,
      include_internal_quantity: false,
      include_approved_by_project_manager: false,
      include_approved_signed_quantity: false,
      include_total_estimate: false,
      include_total_submitted: false,
      include_internal_total: false,
      include_total_approved_by_project_manager: false,
      include_approved_signed_total: false,
      include_subsection: false,
      include_notes: false,
    };

    // Add contract update columns
    contractUpdates.forEach((update) => {
      baseRequest[`include_updated_contract_quantity_${update.id}`] = false;
      baseRequest[`include_updated_contract_sum_${update.id}`] = false;
    });

    setExportRequest(baseRequest);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
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
            Select the columns you want to include in your export:
          </p>

          <div className="flex gap-2 mb-3">
            <button
              onClick={handleSelectAll}
              className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
            >
              Select All
            </button>
            <button
              onClick={handleDeselectAll}
              className="px-3 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-700"
            >
              Deselect All
            </button>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {/* Columns ordered according to BOQ table display order */}
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_serial_number}
                onChange={() => handleCheckboxChange("include_serial_number")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Serial Number</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_structure}
                onChange={() => handleCheckboxChange("include_structure")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Structure</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_system}
                onChange={() => handleCheckboxChange("include_system")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">System</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_section_number}
                onChange={() => handleCheckboxChange("include_section_number")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">
                Section Number (Code)
              </span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_description}
                onChange={() => handleCheckboxChange("include_description")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Description</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_unit}
                onChange={() => handleCheckboxChange("include_unit")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Unit</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_original_contract_quantity}
                onChange={() =>
                  handleCheckboxChange("include_original_contract_quantity")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Contract Qty</span>
            </label>

            {/* Contract Update Quantity Columns */}
            {contractUpdates.map((update) => (
              <label
                key={`qty-${update.id}`}
                className="flex items-center space-x-2"
              >
                <input
                  type="checkbox"
                  checked={
                    exportRequest[
                      `include_updated_contract_quantity_${update.id}`
                    ] || false
                  }
                  onChange={() =>
                    handleCheckboxChange(
                      `include_updated_contract_quantity_${update.id}`
                    )
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {update.update_name}
                </span>
              </label>
            ))}

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_price}
                onChange={() => handleCheckboxChange("include_price")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Price</span>
            </label>

            {/* Contract Update Sum Columns */}
            {contractUpdates.map((update) => (
              <label
                key={`sum-${update.id}`}
                className="flex items-center space-x-2"
              >
                <input
                  type="checkbox"
                  checked={
                    exportRequest[
                      `include_updated_contract_sum_${update.id}`
                    ] || false
                  }
                  onChange={() =>
                    handleCheckboxChange(
                      `include_updated_contract_sum_${update.id}`
                    )
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {update.update_name.replace("Qty", "Sum")}
                </span>
              </label>
            ))}

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_total_contract_sum}
                onChange={() =>
                  handleCheckboxChange("include_total_contract_sum")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Contract Sum</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_estimated_quantity}
                onChange={() =>
                  handleCheckboxChange("include_estimated_quantity")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Est. Qty</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_quantity_submitted}
                onChange={() =>
                  handleCheckboxChange("include_quantity_submitted")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Submitted Qty</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_internal_quantity}
                onChange={() =>
                  handleCheckboxChange("include_internal_quantity")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Internal Qty</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_approved_by_project_manager}
                onChange={() =>
                  handleCheckboxChange("include_approved_by_project_manager")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Approved Qty</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_approved_signed_quantity}
                onChange={() =>
                  handleCheckboxChange("include_approved_signed_quantity")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Approved Signed Qty</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_total_estimate}
                onChange={() => handleCheckboxChange("include_total_estimate")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Total Est.</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_total_submitted}
                onChange={() => handleCheckboxChange("include_total_submitted")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Total Submitted</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_internal_total}
                onChange={() => handleCheckboxChange("include_internal_total")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Internal Total</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={
                  exportRequest.include_total_approved_by_project_manager
                }
                onChange={() =>
                  handleCheckboxChange(
                    "include_total_approved_by_project_manager"
                  )
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Total Approved</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_approved_signed_total}
                onChange={() =>
                  handleCheckboxChange("include_approved_signed_total")
                }
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">
                Approved Signed Total
              </span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_subsection}
                onChange={() => handleCheckboxChange("include_subsection")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Subchapter</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportRequest.include_notes}
                onChange={() => handleCheckboxChange("include_notes")}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Notes</span>
            </label>
          </div>
        </div>

        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={() => onExport(exportRequest, "excel")}
            disabled={loading || Object.values(exportRequest).every((v) => !v)}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Exporting..." : "Export to Excel"}
          </button>
          <button
            onClick={() => onExport(exportRequest, "pdf")}
            disabled={loading || Object.values(exportRequest).every((v) => !v)}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Exporting..." : "Export to PDF"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default BOQExportModal;
