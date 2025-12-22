import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import { calculationSheetsApi } from "../services/api";
import { CalculationSheet, CalculationEntry } from "../types";
import { formatNumber } from "../utils/format";
import {
  FileText,
  Trash2,
  Eye,
  Search,
  Filter,
  FolderOpen,
} from "lucide-react";

const CalculationSheets: React.FC = () => {
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [sheets, setSheets] = useState<CalculationSheet[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<CalculationSheet | null>(
    null
  );
  const [entries, setEntries] = useState<CalculationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entriesLoading, setEntriesLoading] = useState(false);
  // Initialize filters from localStorage
  const [searchQuery, setSearchQuery] = useState(() => {
    const saved = localStorage.getItem("calculation-sheets-search-query");
    return saved !== null ? saved : "";
  });
  const [filterSheetNo, setFilterSheetNo] = useState(() => {
    const saved = localStorage.getItem("calculation-sheets-filter-sheet-no");
    return saved !== null ? saved : "";
  });
  const [filterDrawingNo, setFilterDrawingNo] = useState(() => {
    const saved = localStorage.getItem("calculation-sheets-filter-drawing-no");
    return saved !== null ? saved : "";
  });
  const [deletingSheet, setDeletingSheet] = useState(false);
  const [deletingEntry, setDeletingEntry] = useState<number | null>(null);
  const [populatingEntries, setPopulatingEntries] = useState(false);
  const [populatingAllEntries, setPopulatingAllEntries] = useState(false);
  const [editingComment, setEditingComment] = useState(false);
  const [commentValue, setCommentValue] = useState("");
  const [updatingComment, setUpdatingComment] = useState(false);
  const [syncingAll, setSyncingAll] = useState(false);
  const [openingFile, setOpeningFile] = useState(false);
  const [selectedSheetIds, setSelectedSheetIds] = useState<Set<number>>(
    new Set()
  );
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Fetch all calculation sheets
  const fetchSheets = async () => {
    try {
      setLoading(true);
      setError(null);
      // console.log("Fetching calculation sheets...");
      const response = await calculationSheetsApi.getAll(0, 10000);
      // console.log("Calculation sheets response:", response);
      setSheets(response);

      // Restore previously selected sheet from localStorage
      const savedSheetId = localStorage.getItem(
        "calculation-selected-sheet-id"
      );
      if (savedSheetId && response.length > 0) {
        const savedSheet = response.find(
          (sheet) => sheet.id === parseInt(savedSheetId)
        );
        if (savedSheet) {
          setSelectedSheet(savedSheet);
          setCommentValue(savedSheet.comment || "");
          setEditingComment(false);
          fetchEntries(savedSheet.id);

          // Scroll to the selected sheet in the sidebar
          setTimeout(() => {
            const element = document.getElementById(`sheet-${savedSheet.id}`);
            if (element) {
              element.scrollIntoView({ behavior: "smooth", block: "center" });
            }
          }, 100);
        }
      }
    } catch (err) {
      console.error("Error fetching calculation sheets:", err);
      setError(t("auth.failedToFetchCalculationSheets"));
    } finally {
      setLoading(false);
    }
  };

  // Fetch entries for selected sheet
  const fetchEntries = async (sheetId: number) => {
    try {
      setEntriesLoading(true);
      // console.log("Fetching entries for sheet:", sheetId);
      const response = await calculationSheetsApi.getWithEntries(sheetId);
      // console.log("Entries response:", response);
      setEntries(response.entries);
    } catch (err) {
      console.error("Error fetching entries:", err);
      setEntries([]);
    } finally {
      setEntriesLoading(false);
    }
  };

  // Handle sheet selection
  const handleSheetSelect = (sheet: CalculationSheet) => {
    setSelectedSheet(sheet);
    setCommentValue(sheet.comment || "");
    setEditingComment(false);
    fetchEntries(sheet.id);
    // Save selected sheet ID to localStorage
    localStorage.setItem("calculation-selected-sheet-id", sheet.id.toString());
  };

  // Handle comment update
  const handleCommentUpdate = async () => {
    if (!selectedSheet) return;

    try {
      setUpdatingComment(true);
      const updatedSheet = await calculationSheetsApi.updateComment(
        selectedSheet.id,
        commentValue
      );

      // Update the selected sheet with the new comment
      setSelectedSheet(updatedSheet);

      // Update the sheet in the sheets list
      setSheets((prev) =>
        prev.map((sheet) =>
          sheet.id === selectedSheet.id
            ? { ...sheet, comment: updatedSheet.comment }
            : sheet
        )
      );

      setEditingComment(false);
      setError(null);
    } catch (err) {
      console.error("Error updating comment:", err);
      setError(t("auth.failedToUpdateComment"));
    } finally {
      setUpdatingComment(false);
    }
  };

  // Handle comment edit start
  const handleCommentEditStart = () => {
    setEditingComment(true);
  };

  // Handle comment edit cancel
  const handleCommentEditCancel = () => {
    setCommentValue(selectedSheet?.comment || "");
    setEditingComment(false);
  };

  // Delete calculation sheet
  const handleDeleteSheet = async (sheetId: number) => {
    if (
      !confirm(
        "Are you sure you want to delete this calculation sheet? This will also delete related concentration entries and update BOQ items. This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      setDeletingSheet(true);
      const response = await calculationSheetsApi.delete(sheetId);

      setSheets((prev) => prev.filter((sheet) => sheet.id !== sheetId));
      if (selectedSheet?.id === sheetId) {
        setSelectedSheet(null);
        setEntries([]);
      }

      // Remove from selected if it was selected
      setSelectedSheetIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(sheetId);
        return newSet;
      });

      // Show synchronization message if available
      if (response.sync_result && response.sync_result.success) {
        const syncMsg = `Synchronized: ${response.sync_result.entries_deleted} concentration entries deleted, ${response.sync_result.boq_items_updated} BOQ items updated`;
        setError(null);
        // You could show a success message here instead of error
        console.log("Sync result:", syncMsg);
      }

      setError(null);
    } catch (err) {
      console.error("Error deleting calculation sheet:", err);
      setError(t("auth.failedToDeleteCalculationSheet"));
    } finally {
      setDeletingSheet(false);
    }
  };

  // Bulk delete calculation sheets
  const handleBulkDeleteSheets = async () => {
    if (selectedSheetIds.size === 0) {
      alert("Please select at least one calculation sheet to delete.");
      return;
    }

    const selectedCount = selectedSheetIds.size;
    const sheetNumbers = Array.from(selectedSheetIds)
      .map((id) => sheets.find((s) => s.id === id)?.calculation_sheet_no || id)
      .join(", ");

    if (
      !confirm(
        `Are you sure you want to delete ${selectedCount} calculation sheet(s)?\n\nSelected sheets: ${sheetNumbers}\n\nThis will also delete related concentration entries and update BOQ items. This action cannot be undone.`
      )
    ) {
      return;
    }

    try {
      setBulkDeleting(true);
      setError(null);

      const sheetIdsArray = Array.from(selectedSheetIds);
      const response = await calculationSheetsApi.bulkDelete(sheetIdsArray);

      // Remove deleted sheets from state
      setSheets((prev) =>
        prev.filter((sheet) => !selectedSheetIds.has(sheet.id))
      );

      // Clear selection if selected sheet was deleted
      if (selectedSheet && selectedSheetIds.has(selectedSheet.id)) {
        setSelectedSheet(null);
        setEntries([]);
      }

      // Clear selected sheet IDs
      setSelectedSheetIds(new Set());

      // Show success message
      let successMsg = response.message;
      if (response.errors && response.errors.length > 0) {
        successMsg += `\n\nErrors:\n${response.errors.join("\n")}`;
      }

      alert(successMsg);
      setError(null);

      // Refresh sheets list
      await fetchSheets();
    } catch (err: any) {
      console.error("Error bulk deleting calculation sheets:", err);
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        t("auth.failedToDeleteCalculationSheet");
      setError(errorMessage);
      alert(`Error: ${errorMessage}`);
    } finally {
      setBulkDeleting(false);
    }
  };

  // Toggle sheet selection
  const handleToggleSheetSelection = (sheetId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedSheetIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sheetId)) {
        newSet.delete(sheetId);
      } else {
        newSet.add(sheetId);
      }
      return newSet;
    });
  };

  // Toggle select all
  const handleToggleSelectAll = () => {
    if (selectedSheetIds.size === filteredSheets.length) {
      setSelectedSheetIds(new Set());
    } else {
      setSelectedSheetIds(new Set(filteredSheets.map((sheet) => sheet.id)));
    }
  };

  // Delete entry
  const handleDeleteEntry = async (entryId: number) => {
    if (
      !confirm(
        "Are you sure you want to delete this entry? This will also delete related concentration entries and update BOQ items."
      )
    ) {
      return;
    }

    try {
      setDeletingEntry(entryId);
      const response = await calculationSheetsApi.deleteEntry(entryId);

      setEntries((prev) => prev.filter((entry) => entry.id !== entryId));

      // Show synchronization message if available
      if (response.sync_result && response.sync_result.success) {
        const syncMsg = `Synchronized: ${response.sync_result.entries_deleted} concentration entries deleted, ${response.sync_result.boq_items_updated} BOQ items updated`;
        console.log("Sync result:", syncMsg);
      }

      setError(null);
    } catch (err) {
      console.error("Error deleting entry:", err);
      setError(t("auth.failedToDeleteEntry"));
    } finally {
      setDeletingEntry(null);
    }
  };

  // Populate concentration entries from calculation entries
  const handlePopulateConcentrationEntries = async () => {
    if (!selectedSheet) return;

    if (
      !confirm(
        `Are you sure you want to populate concentration entries from calculation sheet "${selectedSheet.calculation_sheet_no}"? This will add new entries to the matching concentration sheet.`
      )
    ) {
      return;
    }

    try {
      setPopulatingEntries(true);
      setError(null);

      const response = await calculationSheetsApi.populateConcentrationEntries(
        selectedSheet.id
      );

      // Show success message
      alert(
        `✅ ${response.message}\n\nEntries Created: ${
          response.entries_created
        }\nEntries Skipped: ${response.entries_skipped}\nBOQ Items Updated: ${
          response.boq_items_updated || 0
        }`
      );

      // Clear any previous errors
      setError(null);
    } catch (err: any) {
      console.error("Error populating concentration entries:", err);

      // Extract detailed error message
      let errorMessage = t("auth.failedToPopulateEntries");

      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);

      // Show error in console for debugging
      console.error("Detailed error:", {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message,
      });
    } finally {
      setPopulatingEntries(false);
    }
  };

  // Open source Excel file
  const handleOpenSourceFile = async () => {
    if (!selectedSheet) return;

    if (!selectedSheet.source_file_path) {
      alert(
        "Source file path is not set for this calculation sheet. Please set it first."
      );
      return;
    }

    try {
      setOpeningFile(true);
      setError(null);
      const response = await calculationSheetsApi.openSourceFile(
        selectedSheet.id
      );
      if (response.success) {
        // File opening is handled by the backend
        console.log(response.message);
      }
    } catch (err: any) {
      console.error("Error opening source file:", err);
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        "Failed to open source file";
      setError(errorMessage);
      alert(`Error: ${errorMessage}`);
    } finally {
      setOpeningFile(false);
    }
  };

  // Populate ALL calculation entries from ALL calculation sheets
  const handlePopulateAllCalculationEntries = async () => {
    if (
      !confirm(
        `Are you sure you want to populate concentration entries from ALL calculation sheets? This will DELETE auto-generated concentration entries and recreate them from ${sheets.length} calculation sheets. Manual entries will be preserved. This action cannot be undone and may take some time.`
      )
    ) {
      return;
    }

    try {
      setPopulatingAllEntries(true);
      setError(null);

      const response =
        await calculationSheetsApi.populateAllCalculationEntries();

      // Show success message
      alert(
        `✅ ${response.message}\n\nTotal Entries Created: ${
          response.entries_created
        }\nTotal Entries Skipped: ${
          response.entries_skipped
        }\nTotal BOQ Items Updated: ${response.boq_items_updated || 0}`
      );

      // Clear any previous errors
      setError(null);
    } catch (err: any) {
      console.error("Error populating all calculation entries:", err);

      // Extract detailed error message
      let errorMessage = t("auth.failedToPopulateAllEntries");

      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);

      // Show error in console for debugging
      console.error("Detailed error:", {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message,
      });
    } finally {
      setPopulatingAllEntries(false);
    }
  };

  // Sync all calculation sheets with concentration sheets and BOQ items
  const handleSyncAll = async () => {
    if (
      !confirm(
        "Are you sure you want to synchronize all calculation sheets? This will update concentration entries and BOQ items to match calculation sheet data."
      )
    ) {
      return;
    }

    try {
      setSyncingAll(true);
      setError(null);
      const response = await calculationSheetsApi.syncAll();

      if (response.success) {
        setError(null);
        alert(
          `✅ ${response.message}\n\nSheets Processed: ${response.details.sheets_processed}\nEntries Updated: ${response.details.entries_updated}\nBOQ Items Updated: ${response.details.boq_items_updated}`
        );
        // Refresh data to show updated values
        await fetchSheets();
        if (selectedSheet) {
          await fetchEntries(selectedSheet.id);
        }
      } else {
        setError(response.message || t("auth.failedToSyncSheets"));
      }
    } catch (err) {
      console.error("Error syncing all calculation sheets:", err);
      setError(t("auth.failedToSyncSheets"));
    } finally {
      setSyncingAll(false);
    }
  };

  // Filter sheets based on search and filters
  const filteredSheets = sheets.filter((sheet) => {
    const matchesSearch =
      searchQuery === "" ||
      sheet.calculation_sheet_no
        .toLowerCase()
        .includes(searchQuery.toLowerCase()) ||
      sheet.drawing_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sheet.description.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSheetNo =
      filterSheetNo === "" ||
      sheet.calculation_sheet_no
        .toLowerCase()
        .includes(filterSheetNo.toLowerCase());

    const matchesDrawingNo =
      filterDrawingNo === "" ||
      sheet.drawing_no.toLowerCase().includes(filterDrawingNo.toLowerCase());

    return matchesSearch && matchesSheetNo && matchesDrawingNo;
  });

  useEffect(() => {
    fetchSheets();
  }, []);

  // Save filter values to localStorage
  useEffect(() => {
    localStorage.setItem("calculation-sheets-search-query", searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    localStorage.setItem("calculation-sheets-filter-sheet-no", filterSheetNo);
  }, [filterSheetNo]);

  useEffect(() => {
    localStorage.setItem(
      "calculation-sheets-filter-drawing-no",
      filterDrawingNo
    );
  }, [filterDrawingNo]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {t("calculationSheets.title")}
          </h1>
          <p className="mt-2 text-gray-600">
            {t("calculationSheets.subtitle")}
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
          {t("calculationSheets.title")}
        </h1>
        <p className="mt-2 text-gray-600">
          {t("calculationSheets.subtitle")} ({sheets.length}{" "}
          {t("calculationSheets.sheets")})
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="text-red-600">{error}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-screen max-h-[calc(100vh-200px)]">
        {/* Left Side - Sheets List */}
        <div className="lg:col-span-1">
          {/* Bulk Populate Button */}
          <div className="mb-4">
            <button
              onClick={handlePopulateAllCalculationEntries}
              disabled={populatingAllEntries || sheets.length === 0}
              className="w-full bg-blue-600 text-white px-4 py-3 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              title="Populate concentration entries from ALL calculation sheets"
            >
              {populatingAllEntries ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Populating All...</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>Populate ALL Sheets</span>
                </>
              )}
            </button>
          </div>

          {/* Sync All Button */}
          <div className="mb-4">
            <button
              onClick={handleSyncAll}
              disabled={syncingAll || sheets.length === 0}
              className="w-full bg-green-600 text-white px-4 py-3 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              title="Synchronize all calculation sheets with concentration sheets and BOQ items"
            >
              {syncingAll ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Syncing All...</span>
                </>
              ) : (
                <>
                  <span>🔄</span>
                  <span>Sync All Sheets</span>
                </>
              )}
            </button>
          </div>

          {/* Bulk Delete Button */}
          {selectedSheetIds.size > 0 && (
            <div className="mb-4">
              <button
                onClick={handleBulkDeleteSheets}
                disabled={bulkDeleting}
                className="w-full bg-red-600 text-white px-4 py-3 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                title={`Delete ${selectedSheetIds.size} selected calculation sheet(s)`}
              >
                {bulkDeleting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    <span>Delete Selected ({selectedSheetIds.size})</span>
                  </>
                )}
              </button>
            </div>
          )}
          <div className="bg-white rounded-lg shadow h-full flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {t("calculationSheets.title")}
              </h2>
              <p className="text-sm text-gray-600">
                {t("calculationSheets.selectSheetToViewEntries")}
              </p>

              {/* Search */}
              <div className="mt-3">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t("calculationSheets.searchSheets")}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Filters */}
              <div className="mt-3 grid grid-cols-2 gap-2">
                <input
                  type="text"
                  value={filterSheetNo}
                  onChange={(e) => setFilterSheetNo(e.target.value)}
                  placeholder={t("calculationSheets.filterBySheetNo")}
                  className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <input
                  type="text"
                  value={filterDrawingNo}
                  onChange={(e) => setFilterDrawingNo(e.target.value)}
                  placeholder={t("calculationSheets.filterByDrawingNo")}
                  className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div
              className="flex-1 overflow-y-scroll"
              style={{ minHeight: 0, maxHeight: "calc(100vh - 250px)" }}
            >
              {filteredSheets.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <p>{t("calculationSheets.noSheetsFound")}</p>
                  <p className="text-sm mt-1">
                    {t("calculationSheets.importFromFileImportPage")}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {/* Select All Checkbox */}
                  <div className="p-3 bg-gray-50 border-b border-gray-200 flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={
                        filteredSheets.length > 0 &&
                        selectedSheetIds.size === filteredSheets.length
                      }
                      onChange={handleToggleSelectAll}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                      onClick={(e) => e.stopPropagation()}
                    />
                    <label
                      className="text-sm font-medium text-gray-700 cursor-pointer"
                      onClick={handleToggleSelectAll}
                    >
                      Select All ({filteredSheets.length})
                    </label>
                  </div>

                  {filteredSheets.map((sheet) => (
                    <div
                      key={sheet.id}
                      id={`sheet-${sheet.id}`}
                      className={`p-4 hover:bg-gray-50 transition-colors ${
                        selectedSheet?.id === sheet.id
                          ? "bg-blue-50 border-r-4 border-blue-500"
                          : ""
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div
                          className="flex-1 cursor-pointer"
                          onClick={() => handleSheetSelect(sheet)}
                        >
                          <div className="flex items-start space-x-3">
                            <input
                              type="checkbox"
                              checked={selectedSheetIds.has(sheet.id)}
                              onChange={() => {}}
                              onClick={(e) =>
                                handleToggleSheetSelection(sheet.id, e)
                              }
                              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer flex-shrink-0"
                            />
                            <div className="flex-1">
                              <h3 className="font-medium text-gray-900">
                                {sheet.calculation_sheet_no}
                              </h3>
                              <p className="text-sm text-gray-600 mt-1">
                                {sheet.drawing_no}
                              </p>
                              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                                {sheet.description}
                              </p>
                              <div className="mt-2 text-xs text-gray-400">
                                {new Date(
                                  sheet.import_date
                                ).toLocaleDateString()}
                              </div>
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteSheet(sheet.id);
                          }}
                          disabled={deletingSheet || bulkDeleting}
                          className="text-red-600 hover:text-red-800 disabled:opacity-50 ml-2"
                          title={t("calculationSheets.delete")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side - Sheet Details */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow h-full flex flex-col">
            {selectedSheet ? (
              <>
                {/* Header Information */}
                <div className="p-6 border-b border-gray-200">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {t("calculationSheets.title")} -{" "}
                        {selectedSheet.calculation_sheet_no}
                      </h2>
                      <p className="text-sm text-gray-600 mt-1">
                        {selectedSheet.description}
                      </p>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <div className="flex space-x-2">
                        {selectedSheet.source_file_path && (
                          <button
                            onClick={handleOpenSourceFile}
                            disabled={openingFile}
                            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                            title="Open source Excel file"
                          >
                            {openingFile ? (
                              <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                <span>Opening...</span>
                              </>
                            ) : (
                              <>
                                <FolderOpen className="h-4 w-4" />
                                <span>Open Source File</span>
                              </>
                            )}
                          </button>
                        )}
                        <button
                          onClick={handlePopulateConcentrationEntries}
                          disabled={populatingEntries || entries.length === 0}
                          className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                          title={t("calculationSheets.populateEntries")}
                        >
                          {populatingEntries ? (
                            <>
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                              <span>{t("calculationSheets.populating")}</span>
                            </>
                          ) : (
                            <>
                              <span>📋</span>
                              <span>
                                {t("calculationSheets.populateEntries")}
                              </span>
                            </>
                          )}
                        </button>
                      </div>
                      {selectedSheet.source_file_path && (
                        <p
                          className={`text-xs text-gray-500 max-w-xs ${
                            isRTL ? "text-left" : "text-right"
                          }`}
                        >
                          Source: {selectedSheet.source_file_path}
                        </p>
                      )}
                      {/* <p
                        className={`text-xs text-gray-500 max-w-xs ${
                          isRTL ? "text-left" : "text-right"
                        }`}
                      >
                        {t("calculationSheets.populateEntriesDescription")}
                      </p> */}
                    </div>
                  </div>

                  {/* Sheet Information Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("calculationSheets.sheetNumber")}:
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.calculation_sheet_no}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("calculationSheets.drawingNumber")}:
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.drawing_no}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("common.importDate")}:
                      </label>
                      <p className="text-gray-900">
                        {new Date(
                          selectedSheet.import_date
                        ).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {/* Comment Field */}
                  <div className="mt-4">
                    <label className="block text-gray-600 font-medium mb-2">
                      {t("calculationSheets.comment")}:
                    </label>
                    {editingComment ? (
                      <div className="space-y-2">
                        <textarea
                          value={commentValue}
                          onChange={(e) => setCommentValue(e.target.value)}
                          placeholder={t("calculationSheets.enterCommentHere")}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          rows={3}
                        />
                        <div className="flex space-x-2">
                          <button
                            onClick={handleCommentUpdate}
                            disabled={updatingComment}
                            className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                          >
                            {updatingComment
                              ? t("calculationSheets.saving")
                              : t("calculationSheets.saveComment")}
                          </button>
                          <button
                            onClick={handleCommentEditCancel}
                            disabled={updatingComment}
                            className="bg-gray-300 text-gray-700 px-3 py-1 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                          >
                            {t("calculationSheets.cancel")}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start space-x-2">
                        <div className="flex-1">
                          {selectedSheet.comment ? (
                            <p className="text-gray-900 bg-gray-50 p-3 rounded-md border">
                              {selectedSheet.comment}
                            </p>
                          ) : (
                            <p className="text-gray-500 italic bg-gray-50 p-3 rounded-md border">
                              {t("calculationSheets.noCommentAddedYet")}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={handleCommentEditStart}
                          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                        >
                          {t("calculationSheets.editComment")}
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Entries Table */}
                <div className="flex-1 p-6 overflow-hidden flex flex-col">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                      {t("calculationSheets.entries")} ({entries.length})
                    </h3>
                  </div>

                  {entriesLoading ? (
                    <div className="flex justify-center items-center flex-1">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                  ) : (
                    <div className="flex-1 overflow-hidden">
                      <div className="overflow-x-auto h-full">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50 sticky top-0">
                            <tr>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("common.sectionNumber")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("common.estimatedQuantity")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("common.quantitySubmitted")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("common.notes")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("calculationSheets.actions")}
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {entries.length === 0 ? (
                              <tr>
                                <td
                                  colSpan={5}
                                  className="px-3 py-8 text-center text-gray-500"
                                >
                                  <p>No entries found</p>
                                  <p className="text-sm mt-1">
                                    This calculation sheet has no entries
                                  </p>
                                </td>
                              </tr>
                            ) : (
                              entries.map((entry) => (
                                <tr key={entry.id} className="table-row-hover">
                                  <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                    {entry.section_number}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.estimated_quantity)}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.quantity_submitted)}
                                  </td>
                                  <td className="px-3 py-4 text-sm text-gray-900 max-w-xs">
                                    <div
                                      className="truncate"
                                      title={entry.notes || ""}
                                    >
                                      {entry.notes || "-"}
                                    </div>
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    <button
                                      onClick={() =>
                                        handleDeleteEntry(entry.id)
                                      }
                                      disabled={deletingEntry === entry.id}
                                      className="text-red-600 hover:text-red-800 disabled:opacity-50"
                                      title="Delete entry"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </button>
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg">Select a calculation sheet</p>
                  <p className="text-sm mt-1">
                    Choose a sheet from the list to view its entries
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalculationSheets;
