import React, { useState, useEffect } from "react";
import { subsectionsApi } from "../services/api";
import { SubsectionSummary } from "../types";
import { formatCurrency } from "../utils/format";

const SummaryOfSubsections: React.FC = () => {
  const [subsectionSummaries, setSubsectionSummaries] = useState<
    SubsectionSummary[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingDescription, setEditingDescription] = useState<string | null>(
    null
  );
  const [editingValue, setEditingValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch subsection summaries
  const fetchSubsectionSummaries = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await subsectionsApi.getSummaries();
      setSubsectionSummaries(response);
    } catch (err) {
      console.error("Error fetching subsection summaries:", err);
      setError("Failed to fetch subsection summaries");
    } finally {
      setLoading(false);
    }
  };

  // Start editing a description
  const startEditingDescription = (
    subsection: string,
    currentDescription: string
  ) => {
    setEditingDescription(subsection);
    setEditingValue(currentDescription);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingDescription(null);
    setEditingValue("");
  };

  // Save description changes
  const saveDescription = async (subsection: string) => {
    try {
      setSaving(true);
      setError(null);

      const response = await subsectionsApi.updateDescription(
        subsection,
        editingValue
      );

      // Update local state
      setSubsectionSummaries((prev) =>
        prev.map((summary) =>
          summary.subsection === subsection
            ? { ...summary, description: editingValue }
            : summary
        )
      );

      setEditingDescription(null);
      setEditingValue("");

      // Show success message
      setSuccessMessage(`Description saved for subsection: ${subsection}`);
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
  const handleKeyPress = (e: React.KeyboardEvent, subsection: string) => {
    if (e.key === "Enter") {
      saveDescription(subsection);
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  // Calculate grand totals
  const grandTotals = subsectionSummaries.reduce(
    (acc, summary) => ({
      totalEstimate: acc.totalEstimate + summary.total_estimate,
      totalSubmitted: acc.totalSubmitted + summary.total_submitted,
      internalTotal: acc.internalTotal + summary.internal_total,
      totalApproved: acc.totalApproved + summary.total_approved,
    }),
    {
      totalEstimate: 0,
      totalSubmitted: 0,
      internalTotal: 0,
      totalApproved: 0,
    }
  );

  // Load data on component mount
  useEffect(() => {
    fetchSubsectionSummaries();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Summary of Subsections
          </h1>
          <p className="mt-2 text-gray-600">
            Summary of BOQ items grouped by subsection
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
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Summary of Subsections
        </h1>
        <p className="mt-2 text-gray-600">
          Summary of BOQ items grouped by subsection (
          {subsectionSummaries.length} subsections)
        </p>
        <p className="mt-1 text-sm text-gray-500">
          This table is automatically updated when BOQ items are imported or
          modified. You can edit subsection descriptions by clicking on them.
        </p>
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
                  Subsection
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subsection Description
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
                  Item Count
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {subsectionSummaries.map((summary) => (
                <tr key={summary.subsection} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {summary.subsection}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {editingDescription === summary.subsection ? (
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={editingValue}
                          onChange={(e) => handleInputChange(e.target.value)}
                          onKeyDown={(e) =>
                            handleKeyPress(e, summary.subsection)
                          }
                          className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                          disabled={saving}
                          autoFocus
                        />
                        <button
                          onClick={() => saveDescription(summary.subsection)}
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
                            summary.subsection,
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
                  {subsectionSummaries.reduce(
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
      {!loading && subsectionSummaries.length === 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center text-gray-500">
            <p className="text-lg font-medium">No subsections found</p>
            <p className="text-sm mt-1">
              Import BOQ items to see subsection summaries here
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
                the totals will be updated automatically. You can edit
                subsection descriptions by clicking on them in the table.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SummaryOfSubsections;
