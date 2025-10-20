import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { structuresApi, exportApi, contractUpdatesApi } from "../services/api";
import {
  StructureSummary,
  SummaryExportRequest,
  ContractQuantityUpdate,
} from "../types";
import { formatCurrency } from "../utils/format";
import ExportModal from "../components/ExportModal";
import ColumnSettingsModal from "../components/ColumnSettingsModal";

const SummaryOfStructures: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [structureSummaries, setStructureSummaries] = useState<
    StructureSummary[]
  >([]);
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
  const [contractUpdates, setContractUpdates] = useState<
    ContractQuantityUpdate[]
  >([]);

  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState({
    structure: true,
    structure_description: true,
    total_contract_sum: true,
    total_estimate: true,
    total_submitted: true,
    internal_total: true,
    total_approved_by_project_manager: true,
    approved_signed_total: true,
  });

  // Column settings modal state
  const [showColumnSettings, setShowColumnSettings] = useState(false);

  // Load column visibility preferences from localStorage
  useEffect(() => {
    const savedVisibility = localStorage.getItem(
      "structures-column-visibility"
    );
    if (savedVisibility) {
      try {
        const parsed = JSON.parse(savedVisibility);
        setColumnVisibility((prev) => ({ ...prev, ...parsed }));
      } catch (error) {
        console.error("Error loading column visibility preferences:", error);
      }
    }
  }, []);

  // Save column visibility preferences to localStorage
  useEffect(() => {
    localStorage.setItem(
      "structures-column-visibility",
      JSON.stringify(columnVisibility)
    );
  }, [columnVisibility]);

  // Column visibility functions
  const toggleColumnVisibility = (columnKey: string) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [columnKey]: !prev[columnKey],
    }));
  };

  const resetColumnVisibility = () => {
    const baseVisibility = {
      structure: true,
      structure_description: true,
      total_contract_sum: true,
      total_estimate: true,
      total_submitted: true,
      internal_total: true,
      total_approved_by_project_manager: true,
      approved_signed_total: true,
    };

    // Add contract update columns to reset
    contractUpdates.forEach((update) => {
      baseVisibility[`updated_contract_sum_${update.id}`] = true;
    });

    setColumnVisibility(baseVisibility);
  };

  // Fetch structure summaries
  const fetchStructureSummaries = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await structuresApi.getSummaries();
      setStructureSummaries(response);
    } catch (err) {
      console.error("Error fetching structure summaries:", err);
      setError(t("summary.failedToFetchData"));
    } finally {
      setLoading(false);
    }
  };

  // Start editing a description
  const startEditingDescription = (
    structure: number,
    currentDescription: string
  ) => {
    setEditingDescription(structure.toString());
    setEditingValue(currentDescription);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingDescription(null);
    setEditingValue("");
  };

  // Save description changes
  const saveDescription = async (structure: number) => {
    try {
      setSaving(true);
      setError(null);

      const response = await structuresApi.updateDescription(
        structure,
        editingValue
      );

      // Update local state
      setStructureSummaries((prev) =>
        prev.map((summary) =>
          summary.structure === structure
            ? { ...summary, description: editingValue }
            : summary
        )
      );

      setEditingDescription(null);
      setEditingValue("");

      // Show success message
      setSuccessMessage(t("summary.dataUpdatedSuccessfully"));
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error("Error saving description:", err);
      setError(t("summary.failedToUpdateData"));
    } finally {
      setSaving(false);
    }
  };

  // Handle input change
  const handleInputChange = (value: string) => {
    setEditingValue(value);
  };

  // Handle key press for saving on Enter
  const handleKeyPress = (e: React.KeyboardEvent, structure: number) => {
    if (e.key === "Enter") {
      saveDescription(structure);
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
      const filteredData = structureSummaries.map((summary) => {
        const filteredSummary: any = {};
        if (request.include_structure)
          filteredSummary.structure = summary.structure;
        if (request.include_description)
          filteredSummary.description = summary.description;
        if (request.include_total_contract_sum)
          filteredSummary.total_contract_sum = summary.total_contract_sum;
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
        if (request.include_contract_updates)
          filteredSummary.contract_update_sums = summary.contract_update_sums;
        return filteredSummary;
      });

      // Debug logging
      console.log("Export request:", request);
      console.log("Filtered data:", filteredData);
      console.log(
        "First summary contract_update_sums:",
        filteredData[0]?.contract_update_sums
      );

      let response;
      if (format === "pdf") {
        response = await exportApi.exportStructuresSummary(
          request,
          filteredData
        );
      } else {
        response = await exportApi.exportStructuresSummaryExcel(
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
          `structures_summary.${format === "pdf" ? "pdf" : "xlsx"}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Show success message
        setSuccessMessage(
          `Successfully exported structures summary as ${format.toUpperCase()}`
        );
        setTimeout(() => setSuccessMessage(null), 5000);
        setShowExportModal(false);
      }
    } catch (err) {
      console.error(`Error exporting structures summary as ${format}:`, err);
      setError(`Failed to export as ${format.toUpperCase()}`);
    } finally {
      setExporting(false);
    }
  };

  // Calculate grand totals
  const grandTotals = structureSummaries.reduce(
    (acc, summary) => {
      const newAcc = {
        totalContractSum: acc.totalContractSum + summary.total_contract_sum,
        contractUpdateSums: { ...acc.contractUpdateSums },
        totalEstimate: acc.totalEstimate + summary.total_estimate,
        totalSubmitted: acc.totalSubmitted + summary.total_submitted,
        internalTotal: acc.internalTotal + summary.internal_total,
        totalApproved: acc.totalApproved + summary.total_approved,
        approvedSignedTotal:
          acc.approvedSignedTotal + summary.approved_signed_total,
      };

      // Add contract update sums
      Object.entries(summary.contract_update_sums).forEach(
        ([updateId, sum]) => {
          const id = parseInt(updateId);
          newAcc.contractUpdateSums[id] =
            (newAcc.contractUpdateSums[id] || 0) + sum;
        }
      );

      return newAcc;
    },
    {
      totalContractSum: 0,
      contractUpdateSums: {} as Record<number, number>,
      totalEstimate: 0,
      totalSubmitted: 0,
      internalTotal: 0,
      totalApproved: 0,
      approvedSignedTotal: 0,
    }
  );

  // Fetch contract updates
  const fetchContractUpdates = async () => {
    try {
      const response = await contractUpdatesApi.getAll();
      setContractUpdates(response);

      // Add contract update columns to visibility state
      const newVisibility = { ...columnVisibility };
      response.forEach((update) => {
        newVisibility[`updated_contract_sum_${update.id}`] =
          columnVisibility[`updated_contract_sum_${update.id}`] ?? true;
      });
      setColumnVisibility(newVisibility);
    } catch (err) {
      console.error("Error fetching contract updates:", err);
    }
  };

  // Load data on component mount
  useEffect(() => {
    fetchStructureSummaries();
    fetchContractUpdates();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className={isRTL ? "text-right" : "text-left"}>
          <h1 className="text-3xl font-bold text-gray-900">
            {t("summary.title")} - {t("summary.structure")}
          </h1>
          <p className="mt-2 text-gray-600">{t("summary.subtitle")}</p>
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
        <div className={isRTL ? "text-right" : "text-left"}>
          <h1 className="text-3xl font-bold text-gray-900">
            {t("summary.title")} - {t("summary.structure")}
          </h1>
          <p className="mt-2 text-gray-600">
            {t("summary.subtitle")} ({structureSummaries.length}{" "}
            {t("summary.structure").toLowerCase()})
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {t("summary.tableAutoUpdatedDescription")}
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowColumnSettings(true)}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            {t("summary.columnSettings")}
          </button>
          <button
            onClick={() => setShowExportModal(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {t("summary.export")} {t("summary.title")}
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
                {columnVisibility.structure && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.structure")}
                  </th>
                )}
                {columnVisibility.structure_description && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.structure")} {t("summary.description")}
                  </th>
                )}
                {columnVisibility.total_contract_sum && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.totalContractSum")}
                  </th>
                )}
                {contractUpdates.map((update) =>
                  columnVisibility[`updated_contract_sum_${update.id}`] ? (
                    <th
                      key={update.id}
                      className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {t("summary.totalUpdatedContractSum")}{" "}
                      {update.update_index}
                    </th>
                  ) : null
                )}
                {columnVisibility.total_estimate && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.totalEstimate")}
                  </th>
                )}
                {columnVisibility.total_submitted && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.totalSubmitted")}
                  </th>
                )}
                {columnVisibility.internal_total && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.internalTotal")}
                  </th>
                )}
                {columnVisibility.total_approved_by_project_manager && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.totalApproved")}
                  </th>
                )}
                {columnVisibility.approved_signed_total && (
                  <th
                    className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      isRTL ? "text-right" : "text-left"
                    }`}
                  >
                    {t("summary.approvedSignedTotal")}
                  </th>
                )}
                <th
                  className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${
                    isRTL ? "text-right" : "text-left"
                  }`}
                >
                  {t("common.itemCount")}
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {structureSummaries.map((summary) => (
                <tr key={summary.structure} className="hover:bg-gray-50">
                  {columnVisibility.structure && (
                    <td
                      className={`px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 ${
                        isRTL ? "text-right" : "text-left"
                      }`}
                    >
                      {summary.structure}
                    </td>
                  )}
                  {columnVisibility.structure_description && (
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {editingDescription === summary.structure.toString() ? (
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={editingValue}
                            onChange={(e) => handleInputChange(e.target.value)}
                            onKeyDown={(e) =>
                              handleKeyPress(e, summary.structure)
                            }
                            className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            disabled={saving}
                            autoFocus
                          />
                          <button
                            onClick={() => saveDescription(summary.structure)}
                            disabled={saving}
                            className="text-green-600 hover:text-green-800 disabled:opacity-50 text-sm px-2 py-1"
                          >
                            {saving ? t("summary.saving") : t("summary.save")}
                          </button>
                          <button
                            onClick={cancelEditing}
                            disabled={saving}
                            className="text-red-600 hover:text-red-800 disabled:opacity-50 text-sm px-2 py-1"
                          >
                            {t("summary.cancel")}
                          </button>
                        </div>
                      ) : (
                        <div
                          className="cursor-pointer hover:bg-blue-50 px-2 py-1 rounded -ml-2"
                          onClick={() =>
                            startEditingDescription(
                              summary.structure,
                              summary.description
                            )
                          }
                          title={t("auth.clickToEditDescription")}
                        >
                          {summary.description || (
                            <span className="text-gray-400 italic">
                              {t("auth.clickToAddDescription")}
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                  )}
                  {columnVisibility.total_contract_sum && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(summary.total_contract_sum)}
                    </td>
                  )}
                  {contractUpdates.map((update) =>
                    columnVisibility[`updated_contract_sum_${update.id}`] ? (
                      <td
                        key={update.id}
                        className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                      >
                        {formatCurrency(
                          summary.contract_update_sums[update.id] || 0
                        )}
                      </td>
                    ) : null
                  )}
                  {columnVisibility.total_estimate && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(summary.total_estimate)}
                    </td>
                  )}
                  {columnVisibility.total_submitted && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(summary.total_submitted)}
                    </td>
                  )}
                  {columnVisibility.internal_total && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(summary.internal_total)}
                    </td>
                  )}
                  {columnVisibility.total_approved_by_project_manager && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(summary.total_approved)}
                    </td>
                  )}
                  {columnVisibility.approved_signed_total && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(summary.approved_signed_total)}
                    </td>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {summary.item_count}
                  </td>
                </tr>
              ))}
            </tbody>
            {/* Grand Totals Row */}
            <tfoot className="bg-gray-50 border-t-2 border-gray-300">
              <tr>
                {columnVisibility.structure && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    GRAND TOTALS
                  </td>
                )}
                {columnVisibility.structure_description && (
                  <td className="px-6 py-4 text-sm text-gray-500">-</td>
                )}
                {columnVisibility.total_contract_sum && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {formatCurrency(grandTotals.totalContractSum)}
                  </td>
                )}
                {contractUpdates.map((update) =>
                  columnVisibility[`updated_contract_sum_${update.id}`] ? (
                    <td
                      key={update.id}
                      className="px-6 py-4 text-sm font-bold text-gray-900"
                    >
                      {formatCurrency(
                        grandTotals.contractUpdateSums[update.id] || 0
                      )}
                    </td>
                  ) : null
                )}
                {columnVisibility.total_estimate && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {formatCurrency(grandTotals.totalEstimate)}
                  </td>
                )}
                {columnVisibility.total_submitted && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {formatCurrency(grandTotals.totalSubmitted)}
                  </td>
                )}
                {columnVisibility.internal_total && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {formatCurrency(grandTotals.internalTotal)}
                  </td>
                )}
                {columnVisibility.total_approved_by_project_manager && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {formatCurrency(grandTotals.totalApproved)}
                  </td>
                )}
                {columnVisibility.approved_signed_total && (
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {formatCurrency(grandTotals.approvedSignedTotal)}
                  </td>
                )}
                <td className="px-6 py-4 text-sm font-bold text-gray-900">
                  {structureSummaries.reduce(
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
      {!loading && structureSummaries.length === 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center text-gray-500">
            <p className="text-lg font-medium">No structures found</p>
            <p className="text-sm mt-1">
              Import BOQ items to see structure summaries here
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
                the totals will be updated automatically. You can edit structure
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
        title="Export Structures Summary"
        loading={exporting}
        contractUpdates={contractUpdates}
      />

      {/* Column Settings Modal */}
      <ColumnSettingsModal
        isOpen={showColumnSettings}
        onClose={() => setShowColumnSettings(false)}
        columnVisibility={columnVisibility}
        onToggleColumn={toggleColumnVisibility}
        onResetColumns={resetColumnVisibility}
        title="Summary of Structures"
      />
    </div>
  );
};

export default SummaryOfStructures;
