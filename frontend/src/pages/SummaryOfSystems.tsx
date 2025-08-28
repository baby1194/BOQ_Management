import React, { useState, useEffect } from "react";
import { systemsApi, exportApi } from "../services/api";
import { SystemSummary, SummaryExportRequest } from "../types";
import { formatCurrency } from "../utils/format";
import ExportModal from "../components/ExportModal";

const SummaryOfSystems: React.FC = () => {
  const [systemSummaries, setSystemSummaries] = useState<SystemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDescription, setEditingDescription] = useState<string | null>(
    null
  );
  const [editingValue, setEditingValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Fetch system summaries
  const fetchSystemSummaries = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await systemsApi.getSummaries();
      setSystemSummaries(response);
    } catch (err) {
      console.error("Error fetching system summaries:", err);
      setError("Failed to fetch system summaries");
    } finally {
      setLoading(false);
    }
  };

  // Start editing a description
  const startEditingDescription = (
    system: string,
    currentDescription: string
  ) => {
    setEditingDescription(system);
    setEditingValue(currentDescription);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingDescription(null);
    setEditingValue("");
  };

  // Save description changes
  const saveDescription = async (system: string) => {
    try {
      setSaving(true);
      setError(null);

      const response = await systemsApi.updateDescription(system, editingValue);

      // Update local state
      setSystemSummaries((prev) =>
        prev.map((summary) =>
          summary.system === system
            ? { ...summary, description: editingValue }
            : summary
        )
      );

      setEditingDescription(null);
      setEditingValue("");

      // Show success message
      setSuccessMessage(`Description saved for system: ${system}`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error("Error saving description:", err);
      setError("Failed to save description");
    } finally {
      setSaving(false);
    }
  };

  // Handle input change
  const handleInputChange = (value: string) => {
    setEditingValue(value);
  };

  // Handle key press for saving on Enter
  const handleKeyPress = (e: React.KeyboardEvent, system: string) => {
    if (e.key === "Enter") {
      saveDescription(system);
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  // Export functions
  const handleExport = async (
    request: SummaryExportRequest,
    format: "pdf" | "excel"
  ) => {
    try {
      setExporting(true);
      setError(null);

      // Filter the current table data based on the request
      const filteredData = systemSummaries.map((summary) => {
        const filteredSummary: any = {};
        if (request.include_structure) filteredSummary.system = summary.system;
        if (request.include_description)
          filteredSummary.description = summary.description;
        if (request.include_total_estimate)
          filteredSummary.total_estimate = summary.total_estimate;
        if (request.include_total_submitted)
          filteredSummary.total_submitted = summary.total_submitted;
        if (request.include_internal_total)
          filteredSummary.internal_total = summary.internal_total;
        if (request.include_total_approved)
          filteredSummary.total_approved = summary.total_approved;
        if (request.include_approved_signed_total)
          filteredSummary.approved_signed_total = summary.approved_signed_total;
        if (request.include_item_count)
          filteredSummary.item_count = summary.item_count;
        return filteredSummary;
      });

      let response;
      if (format === "pdf") {
        response = await exportApi.exportSystemsSummary(request, filteredData);
      } else {
        response = await exportApi.exportSystemsSummaryExcel(
          request,
          filteredData
        );
      }

      if (response.success && response.pdf_path) {
        // Create download link
        const link = document.createElement("a");
        // The backend returns /export/download/filename, so we need to access it via the API
        const downloadUrl = response.pdf_path.startsWith("/")
          ? `/api${response.pdf_path}`
          : `/api/${response.pdf_path}`;
        link.href = downloadUrl;
        // Extract filename from the path
        const filename =
          response.pdf_path.split("/").pop() ||
          `systems_summary.${format === "pdf" ? "pdf" : "xlsx"}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Show success message
        setSuccessMessage(
          `Successfully exported systems summary as ${format.toUpperCase()}`
        );
        setTimeout(() => setSuccessMessage(null), 5000);
        setShowExportModal(false);
      }
    } catch (err) {
      console.error(`Error exporting systems summary as ${format}:`, err);
      setError(`Failed to export as ${format.toUpperCase()}`);
    } finally {
      setExporting(false);
    }
  };

  // Calculate grand totals
  const grandTotals = systemSummaries.reduce(
    (acc, summary) => ({
      totalEstimate: acc.totalEstimate + summary.total_estimate,
      totalSubmitted: acc.totalSubmitted + summary.total_submitted,
      internalTotal: acc.internalTotal + summary.internal_total,
      totalApproved: acc.totalApproved + summary.total_approved,
      approvedSignedTotal:
        acc.approvedSignedTotal + summary.approved_signed_total,
    }),
    {
      totalEstimate: 0,
      totalSubmitted: 0,
      internalTotal: 0,
      totalApproved: 0,
      approvedSignedTotal: 0,
    }
  );

  // Load data on component mount
  useEffect(() => {
    fetchSystemSummaries();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Summary of Systems
          </h1>
          <p className="mt-2 text-gray-600">
            Summary of BOQ items grouped by system
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Summary of Systems
          </h1>
          <p className="mt-2 text-gray-600">
            Summary of BOQ items grouped by system ({systemSummaries.length}{" "}
            systems)
          </p>
          <p className="mt-1 text-sm text-gray-500">
            This table is automatically updated when BOQ items are imported or
            modified. You can edit system descriptions by clicking on them.
          </p>
        </div>
        <div>
          <button
            onClick={() => setShowExportModal(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Export Summary
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="text-red-600">{error}</div>
          </div>
        </div>
      )}

      {/* Success Message */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex">
            <div className="text-green-600">{successMessage}</div>
          </div>
        </div>
      )}

      {/* Summary Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  System
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  System Description
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Estimate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Submitted
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Internal Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Approved by Project Manager
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Approved Signed Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Item Count
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {systemSummaries.map((summary) => (
                <tr key={summary.system} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {summary.system}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {editingDescription === summary.system ? (
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={editingValue}
                          onChange={(e) => handleInputChange(e.target.value)}
                          onKeyDown={(e) => handleKeyPress(e, summary.system)}
                          className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                          disabled={saving}
                          autoFocus
                        />
                        <button
                          onClick={() => saveDescription(summary.system)}
                          disabled={saving}
                          className="text-green-600 hover:text-green-800 disabled:opacity-50 text-sm px-2 py-1"
                        >
                          {saving ? "Saving..." : "Save"}
                        </button>
                        <button
                          onClick={cancelEditing}
                          disabled={saving}
                          className="text-red-600 hover:text-red-800 disabled:opacity-50 text-sm px-2 py-1"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div
                        className="cursor-pointer hover:bg-blue-50 px-2 py-1 rounded -ml-2"
                        onClick={() =>
                          startEditingDescription(
                            summary.system,
                            summary.description
                          )
                        }
                        title="Click to edit description"
                      >
                        {summary.description || (
                          <span className="text-gray-400 italic">
                            Click to add description
                          </span>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(summary.total_estimate)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(summary.total_submitted)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(summary.internal_total)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(summary.total_approved)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(summary.approved_signed_total)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {summary.item_count}
                  </td>
                </tr>
              ))}
            </tbody>
            {/* Grand Totals Row */}
            <tfoot className="bg-gray-50 border-t-2 border-gray-300">
              <tr>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  GRAND TOTALS
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">-</td>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {formatCurrency(grandTotals.totalEstimate)}
                </td>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {formatCurrency(grandTotals.totalSubmitted)}
                </td>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {formatCurrency(grandTotals.internalTotal)}
                </td>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {formatCurrency(grandTotals.totalApproved)}
                </td>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {formatCurrency(grandTotals.approvedSignedTotal)}
                </td>
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {systemSummaries.reduce(
                    (sum, summary) => sum + summary.item_count,
                    0
                  )}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Empty State */}
      {!loading && systemSummaries.length === 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center text-gray-500">
            <p className="text-lg font-medium">No systems found</p>
            <p className="text-sm mt-1">
              Import BOQ items to see system summaries here
            </p>
          </div>
        </div>
      )}

      {/* Information Panel */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-blue-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              Automatic Updates
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <p>
                This summary table is automatically calculated from your BOQ
                items. When you import new BOQ data or modify existing items,
                the totals will be updated automatically. You can edit system
                descriptions by clicking on them in the table.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Export Modal */}
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        onExport={handleExport}
        title="Export Systems Summary"
        loading={exporting}
      />
    </div>
  );
};

export default SummaryOfSystems;
