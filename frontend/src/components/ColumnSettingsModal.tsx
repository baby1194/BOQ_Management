import React from "react";

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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {title} - Column Settings
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
                  {formatColumnName(key)}
                </span>
              </label>
            ))}
          </div>

          <div className="mt-6 flex justify-between">
            <button
              onClick={onResetColumns}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Reset All
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to format column names for display
const formatColumnName = (key: string): string => {
  const nameMap: { [key: string]: string } = {
    // Basic columns
    structure: "Structure",
    system: "System",
    subsection: "Subsection",
    description: "Description",
    total_contract_sum: "Total Contract Sum",
    total_estimate: "Total Estimate",
    total_submitted: "Total Submitted",
    internal_total: "Internal Total",
    total_approved_by_project_manager: "Total Approved by PM",
    approved_signed_total: "Approved Signed Total",

    // Contract update columns (dynamic)
    total_updated_contract_sum: "Total Updated Contract Sum",
  };

  // Handle dynamic contract update columns
  if (key.startsWith("updated_contract_sum_")) {
    const updateIndex = key.split("_").pop();
    return `Total Updated Contract Sum ${updateIndex}`;
  }

  // Handle structure/system/subsection specific columns
  if (key.includes("_description")) {
    const prefix = key.replace("_description", "");
    return `${formatColumnName(prefix)} Description`;
  }

  return (
    nameMap[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
  );
};

export default ColumnSettingsModal;
