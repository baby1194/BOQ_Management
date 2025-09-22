import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { concentrationApi, boqApi, exportApi } from "../services/api";
import {
  ConcentrationSheet,
  ConcentrationEntry,
  BOQItemWithLatestContractUpdate,
} from "../types";
import { formatCurrency, formatNumber } from "../utils/format";
import { Search, X } from "lucide-react";

interface ConcentrationSheetWithBOQ extends ConcentrationSheet {
  boq_item: BOQItemWithLatestContractUpdate;
}

const ConcentrationSheets: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [sheets, setSheets] = useState<ConcentrationSheetWithBOQ[]>([]);
  const [selectedSheet, setSelectedSheet] =
    useState<ConcentrationSheetWithBOQ | null>(null);
  const [entries, setEntries] = useState<ConcentrationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ConcentrationEntry | null>(
    null
  );
  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingAllPDF, setExportingAllPDF] = useState(false);
  const [exportingAllExcel, setExportingAllExcel] = useState(false);
  const [showNavigationMessage, setShowNavigationMessage] = useState(false);
  const [navigatedFromBOQ, setNavigatedFromBOQ] = useState(false);
  const [sectionNumberFilter, setSectionNumberFilter] = useState("");

  // Project info state - will be loaded from selected sheet
  const [projectInfo, setProjectInfo] = useState({
    projectName: "",
    contractorInCharge: "",
    contractNo: "",
    developerName: "",
  });

  // Load project info from selected sheet
  const loadProjectInfoFromSheet = (sheet: ConcentrationSheetWithBOQ) => {
    console.log("Loading project info from sheet:", {
      id: sheet.id,
      project_name: sheet.project_name,
      contractor_in_charge: sheet.contractor_in_charge,
      contract_no: sheet.contract_no,
      developer_name: sheet.developer_name,
    });

    const info = {
      projectName: sheet.project_name || "",
      contractorInCharge: sheet.contractor_in_charge || "",
      contractNo: sheet.contract_no || "",
      developerName: sheet.developer_name || "",
    };
    setProjectInfo(info);

    console.log("Project info loaded:", info);
  };

  // Export functions
  const handleExportPDF = async () => {
    if (!selectedSheet) {
      setError("No concentration sheet selected for export");
      return;
    }

    try {
      setExportingPDF(true);
      setError(null);

      const response = await exportApi.exportSingleConcentrationSheetPDF(
        selectedSheet.id
      );

      if (response.success && response.pdf_path) {
        // Create download link
        const link = document.createElement("a");
        link.href = `/api${response.pdf_path}`;
        // Extract filename from the path
        const filename =
          response.pdf_path.split("/").pop() ||
          `concentration_sheet_${selectedSheet.id}.pdf`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (err) {
      console.error("Error exporting PDF:", err);
      setError("Failed to export PDF");
    } finally {
      setExportingPDF(false);
    }
  };

  const handleExportExcel = async () => {
    if (!selectedSheet) {
      setError("No concentration sheet selected for export");
      return;
    }

    try {
      setExportingExcel(true);
      setError(null);

      const response = await exportApi.exportSingleConcentrationSheetExcel(
        selectedSheet.id
      );

      if (response.success && response.pdf_path) {
        // Create download link
        const link = document.createElement("a");
        link.href = `/api${response.pdf_path}`;
        // Extract filename from the path
        const filename =
          response.pdf_path.split("/").pop() ||
          `concentration_sheet_${selectedSheet.id}.xlsx`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (err) {
      console.error("Error exporting Excel:", err);
      setError("Failed to export Excel");
    } finally {
      setExportingExcel(false);
    }
  };

  // Export all concentration sheets functions
  const handleExportAllPDF = async () => {
    try {
      setExportingAllPDF(true);
      setError(null);

      const response = await exportApi.exportConcentrationSheets({
        export_all: true,
        export_non_empty_only: false,
      });

      if (response.success && response.pdf_path) {
        // Create download link for the zip file
        const link = document.createElement("a");
        link.href = `/api${response.pdf_path}`;
        link.download = `all_concentration_sheets_individual.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        setError("Export failed: " + response.message);
      }
    } catch (err) {
      console.error("Error exporting all PDFs:", err);
      setError("Failed to export all PDFs");
    } finally {
      setExportingAllPDF(false);
    }
  };

  const handleExportAllExcel = async () => {
    try {
      setExportingAllExcel(true);
      setError(null);

      const response = await exportApi.exportAllConcentrationSheetsExcel({
        export_all: true,
        export_non_empty_only: false,
      });

      if (response.success && response.pdf_path) {
        // Create download link
        const link = document.createElement("a");
        link.href = `/api${response.pdf_path}`;
        link.download = `all_concentration_sheets.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        setError("Export failed: " + response.message);
      }
    } catch (err) {
      console.error("Error exporting all Excel:", err);
      setError("Failed to export all Excel");
    } finally {
      setExportingAllExcel(false);
    }
  };

  // Fetch all concentration sheets with BOQ item data
  const fetchSheets = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log("Fetching concentration sheets...");
      const concentrationSheets = await concentrationApi.getAll(0, 10000);
      console.log("Concentration sheets fetched:", concentrationSheets.length);
      console.log("Sample sheet data:", concentrationSheets[0]);

      // Fetch BOQ item data for each sheet
      const sheetsWithBOQ: ConcentrationSheetWithBOQ[] = [];

      for (const sheet of concentrationSheets) {
        try {
          console.log(
            `Fetching BOQ item with latest contract update for sheet ${sheet.id}, BOQ item ID: ${sheet.boq_item_id}`
          );
          const boqItem = await boqApi.getWithLatestContractUpdate(
            sheet.boq_item_id
          );
          console.log(`BOQ item with latest contract update fetched:`, boqItem);

          const sheetWithBOQ = {
            ...sheet,
            boq_item: boqItem,
          };

          console.log(`Sheet with BOQ data:`, {
            id: sheetWithBOQ.id,
            project_name: sheetWithBOQ.project_name,
            contractor_in_charge: sheetWithBOQ.contractor_in_charge,
            contract_no: sheetWithBOQ.contract_no,
            developer_name: sheetWithBOQ.developer_name,
          });

          sheetsWithBOQ.push(sheetWithBOQ);
        } catch (err) {
          console.error(`Error fetching BOQ item ${sheet.boq_item_id}:`, err);
        }
      }

      console.log("Sheets with BOQ data:", sheetsWithBOQ.length);
      setSheets(sheetsWithBOQ);

      // Check if there's a selected item from URL params
      const selectedItemId = searchParams.get("selectedItem");
      if (selectedItemId) {
        const targetSheet = sheetsWithBOQ.find(
          (sheet) => sheet.boq_item_id === parseInt(selectedItemId)
        );
        if (targetSheet) {
          setSelectedSheet(targetSheet);
          loadProjectInfoFromSheet(targetSheet);
          fetchEntries(targetSheet.id);

          // Show navigation message and set flag
          setShowNavigationMessage(true);
          setNavigatedFromBOQ(true);
          setTimeout(() => setShowNavigationMessage(false), 3000);

          return; // Don't set default selection
        }
      }

      // Select first sheet by default if no specific item was requested
      if (sheetsWithBOQ.length > 0) {
        setSelectedSheet(sheetsWithBOQ[0]);
      }
    } catch (err) {
      console.error("Error fetching concentration sheets:", err);
      setError("Failed to fetch concentration sheets");
    } finally {
      setLoading(false);
    }
  };

  // Fetch entries for selected sheet
  const fetchEntries = async (sheetId: number) => {
    try {
      setEntriesLoading(true);
      const sheetEntries = await concentrationApi.getEntries(sheetId);
      setEntries(sheetEntries);
    } catch (err) {
      console.error("Error fetching entries:", err);
      setEntries([]);
    } finally {
      setEntriesLoading(false);
    }
  };

  // Handle sheet selection
  const handleSheetSelect = (sheet: ConcentrationSheetWithBOQ) => {
    setSelectedSheet(sheet);
    setEditingEntry(null);
    setShowAddForm(false);
    loadProjectInfoFromSheet(sheet);
    fetchEntries(sheet.id);
  };

  // Create new entry
  const createEntry = async (
    entryData: Omit<
      ConcentrationEntry,
      "id" | "created_at" | "updated_at" | "concentration_sheet_id"
    >
  ) => {
    if (!selectedSheet) return;

    try {
      setSaving(true);
      const newEntry = await concentrationApi.createEntry(selectedSheet.id, {
        ...entryData,
      });

      setEntries((prev) => [...prev, newEntry]);
      setShowAddForm(false);
      setError(null);
    } catch (err) {
      console.error("Error creating entry:", err);
      setError("Failed to create entry");
    } finally {
      setSaving(false);
    }
  };

  // Update existing entry
  const updateEntry = async (
    entryId: number,
    entryData: Partial<ConcentrationEntry>
  ) => {
    try {
      setSaving(true);
      const updatedEntry = await concentrationApi.updateEntry(
        entryId,
        entryData
      );

      setEntries((prev) =>
        prev.map((entry) => (entry.id === entryId ? updatedEntry : entry))
      );
      setEditingEntry(null);
      setError(null);
    } catch (err) {
      console.error("Error updating entry:", err);
      setError("Failed to update entry");
    } finally {
      setSaving(false);
    }
  };

  // Start editing entry
  const startEditing = (entry: ConcentrationEntry) => {
    setEditingEntry(entry);
    setShowAddForm(false);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingEntry(null);
    setShowAddForm(false);
  };

  // Filter sheets based on section number
  const filteredSheets = sheets.filter((sheet) => {
    if (!sectionNumberFilter) return true;
    return sheet.boq_item.section_number
      .toLowerCase()
      .includes(sectionNumberFilter.toLowerCase());
  });

  useEffect(() => {
    fetchSheets();
  }, []);

  // Refresh data when page becomes visible (e.g., user navigates back from BOQ Items)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && sheets.length > 0) {
        // Page became visible, refresh data to get latest project info
        fetchSheets();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [sheets.length]);

  useEffect(() => {
    if (selectedSheet) {
      fetchEntries(selectedSheet.id);
    }
  }, [selectedSheet]);

  // Handle URL parameter changes
  useEffect(() => {
    const selectedItemId = searchParams.get("selectedItem");
    if (selectedItemId && sheets.length > 0) {
      const targetSheet = sheets.find(
        (sheet) => sheet.boq_item_id === parseInt(selectedItemId)
      );
      if (targetSheet && targetSheet.id !== selectedSheet?.id) {
        setSelectedSheet(targetSheet);
        loadProjectInfoFromSheet(targetSheet);
        fetchEntries(targetSheet.id);
        setNavigatedFromBOQ(true);

        // Scroll to the selected item in the sidebar
        setTimeout(() => {
          const element = document.getElementById(`sheet-${targetSheet.id}`);
          if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        }, 100);
      }
    }
  }, [searchParams, sheets]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Concentration Sheets
          </h1>
          <p className="mt-2 text-gray-600">
            Manage concentration sheets for BOQ items
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
            Concentration Sheets
          </h1>
          <p className="mt-2 text-gray-600">
            Manage concentration sheets for BOQ items ({sheets.length} sheets)
          </p>
        </div>
        <div className="flex space-x-3 flex-wrap">
          <button
            onClick={fetchSheets}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Refresh concentration sheets data"
          >
            {loading ? "Refreshing..." : "🔄 Refresh"}
          </button>

          {/* Export All Buttons */}
          <div className="flex space-x-2">
            <button
              onClick={handleExportAllPDF}
              disabled={exportingAllPDF || sheets.length === 0}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Export all concentration sheets as individual PDF files (zip)"
            >
              {exportingAllPDF
                ? "Exporting..."
                : "📄 Export All PDF (Individual)"}
            </button>
            <button
              onClick={handleExportAllExcel}
              disabled={exportingAllExcel || sheets.length === 0}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Export all concentration sheets as Excel (separate sheets)"
            >
              {exportingAllExcel ? "Exporting..." : "📊 Export All Excel"}
            </button>
          </div>

          {navigatedFromBOQ && (
            <button
              onClick={() => window.history.back()}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
            >
              ← Back to BOQ Items
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="text-red-600">{error}</div>
          </div>
        </div>
      )}

      {showNavigationMessage && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex">
            <div className="text-green-600">
              ✓ Navigated from BOQ Items - Item automatically selected
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-screen max-h-[calc(100vh-200px)]">
        {/* Left Side - Items List */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow h-full flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">BOQ Items</h2>
              <p className="text-sm text-gray-600">
                Select an item to view its concentration sheet
                {sectionNumberFilter && (
                  <span className="ml-2 text-blue-600">
                    ({filteredSheets.length} of {sheets.length} shown)
                  </span>
                )}
              </p>

              {navigatedFromBOQ && selectedSheet && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <div className="text-sm text-blue-800">
                    <div className="font-medium">Currently viewing:</div>
                    <div className="mt-1">
                      <span className="font-semibold">
                        {selectedSheet.boq_item.section_number}
                      </span>
                      <span className="text-blue-600 ml-2">•</span>
                      <span className="ml-2">
                        {selectedSheet.boq_item.description}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Section Number Filter */}
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Filter by Section Number:
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    value={sectionNumberFilter}
                    onChange={(e) => setSectionNumberFilter(e.target.value)}
                    placeholder="Enter section number..."
                    className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  {sectionNumberFilter && (
                    <button
                      onClick={() => setSectionNumberFilter("")}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {sectionNumberFilter && (
                  <button
                    onClick={() => setSectionNumberFilter("")}
                    className="mt-1 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <X className="h-3 w-3" />
                    Clear filter
                  </button>
                )}
              </div>
            </div>

            <div
              className="flex-1 overflow-y-scroll"
              style={{ minHeight: 0, maxHeight: "calc(100vh - 250px)" }}
            >
              {filteredSheets.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  {sectionNumberFilter ? (
                    <>
                      <p>
                        No concentration sheets found matching "
                        {sectionNumberFilter}"
                      </p>
                      <p className="text-sm mt-1">
                        Try adjusting your filter or{" "}
                        <button
                          onClick={() => setSectionNumberFilter("")}
                          className="text-blue-600 hover:text-blue-800 underline"
                        >
                          clear the filter
                        </button>
                      </p>
                    </>
                  ) : (
                    <>
                      <p>No concentration sheets found</p>
                      <p className="text-sm mt-1">
                        Create concentration sheets from the BOQ Items page
                      </p>
                    </>
                  )}
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {filteredSheets.map((sheet) => (
                    <div
                      key={sheet.id}
                      id={`sheet-${sheet.id}`}
                      className={`p-4 hover:bg-gray-50 transition-colors ${
                        selectedSheet?.id === sheet.id
                          ? navigatedFromBOQ &&
                            searchParams.get("selectedItem") &&
                            sheet.boq_item_id ===
                              parseInt(searchParams.get("selectedItem")!)
                            ? "bg-blue-100 border-r-4 border-blue-600 shadow-sm"
                            : "bg-blue-50 border-r-4 border-blue-500"
                          : ""
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className="flex-1 cursor-pointer"
                          onClick={() => handleSheetSelect(sheet)}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <h3 className="font-medium text-gray-900">
                                  {sheet.boq_item.section_number}
                                </h3>
                                {sheet.boq_item.has_contract_updates && (
                                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    Updated Qty
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                                {sheet.boq_item.description}
                              </p>
                              <div className="mt-2 text-xs text-gray-500">
                                <div>Unit: {sheet.boq_item.unit}</div>
                                <div>
                                  Qty:{" "}
                                  {formatNumber(
                                    sheet.boq_item.latest_contract_quantity
                                  )}
                                  {sheet.boq_item.has_contract_updates && (
                                    <span className="text-blue-600 ml-1">
                                      (Updated{" "}
                                      {sheet.boq_item.latest_update_index})
                                    </span>
                                  )}
                                </div>
                                <div>
                                  Price: {formatCurrency(sheet.boq_item.price)}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side - Concentration Sheet Details */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow h-full flex flex-col">
            {selectedSheet ? (
              <>
                {/* Header Information */}
                <div className="p-6 border-b border-gray-200">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        Concentration Sheet -{" "}
                        {selectedSheet.boq_item.section_number}
                      </h2>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleExportPDF}
                        disabled={exportingPDF}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
                      >
                        {exportingPDF ? "Exporting..." : "Export PDF"}
                      </button>
                      <button
                        onClick={handleExportExcel}
                        disabled={exportingExcel}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      >
                        {exportingExcel ? "Exporting..." : "Export Excel"}
                      </button>
                    </div>
                  </div>

                  {/* Project Information Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Project Name:
                      </label>
                      <p className="text-gray-900">{projectInfo.projectName}</p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Contractor in Charge:
                      </label>
                      <p className="text-gray-900">
                        {projectInfo.contractorInCharge}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-300 font-medium">
                        Contract No:
                      </label>
                      <p className="text-gray-900">{projectInfo.contractNo}</p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Developer Name:
                      </label>
                      <p className="text-gray-900">
                        {projectInfo.developerName}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Section Number:
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.boq_item.section_number}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Contract Quantity:
                      </label>
                      <p className="text-gray-900">
                        {formatNumber(
                          selectedSheet.boq_item.latest_contract_quantity
                        )}{" "}
                        {selectedSheet.boq_item.unit}
                        {selectedSheet.boq_item.has_contract_updates && (
                          <span className="text-blue-600 ml-1">
                            (Updated{" "}
                            {selectedSheet.boq_item.latest_update_index})
                          </span>
                        )}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Unit:
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.boq_item.unit}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Price:
                      </label>
                      <p className="text-gray-900">
                        {formatCurrency(selectedSheet.boq_item.price)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-gray-600 font-medium">
                      Description:
                    </label>
                    <p className="text-gray-900">
                      {selectedSheet.boq_item.description}
                    </p>
                  </div>

                  {/* Contract Update Information */}
                  {selectedSheet.boq_item.has_contract_updates && (
                    <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="block text-blue-800 font-medium text-sm">
                            Contract Quantity Updated
                          </label>
                          <p className="text-blue-700 text-sm mt-1">
                            This item has been updated from the original
                            contract quantity. Current quantity reflects the
                            latest update (Update #
                            {selectedSheet.boq_item.latest_update_index}).
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-blue-600">
                            Original:{" "}
                            {formatNumber(
                              selectedSheet.boq_item.original_contract_quantity
                            )}{" "}
                            {selectedSheet.boq_item.unit}
                          </div>
                          <div className="text-sm font-medium text-blue-800">
                            Current:{" "}
                            {formatNumber(
                              selectedSheet.boq_item.latest_contract_quantity
                            )}{" "}
                            {selectedSheet.boq_item.unit}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Entries Table */}
                <div className="flex-1 p-6 overflow-hidden flex flex-col">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                      Concentration Entries
                    </h3>
                    <button
                      onClick={() => setShowAddForm(true)}
                      disabled={saving}
                      className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                      Add Entry
                    </button>
                  </div>

                  {/* Add/Edit Form */}
                  {(showAddForm || editingEntry) && (
                    <div className="mb-6 p-4 border border-gray-200 rounded-md bg-gray-50">
                      <h4 className="text-md font-medium text-gray-900 mb-4">
                        {editingEntry ? "Edit Entry Notes" : "Add New Entry"}
                      </h4>
                      <EntryForm
                        entry={editingEntry}
                        boqItem={selectedSheet.boq_item}
                        onSave={
                          editingEntry
                            ? (data) => updateEntry(editingEntry.id, data)
                            : createEntry
                        }
                        onCancel={cancelEditing}
                        saving={saving}
                      />
                    </div>
                  )}

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
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Description
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Calc. Sheet No
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Drawing No
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Est. Quantity
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Qty Submitted
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Internal Qty
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Approved Qty
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Notes
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {entries.length === 0 ? (
                              <tr>
                                <td
                                  colSpan={9}
                                  className="px-3 py-8 text-center text-gray-500"
                                >
                                  <p>No entries found</p>
                                  <p className="text-sm mt-1">
                                    Add entries to this concentration sheet
                                  </p>
                                </td>
                              </tr>
                            ) : (
                              entries.map((entry) => (
                                <tr key={entry.id} className="hover:bg-gray-50">
                                  <td className="px-3 py-4 text-sm text-gray-900 max-w-xs">
                                    <div
                                      className="truncate"
                                      title={entry.description || ""}
                                    >
                                      {entry.description || "-"}
                                    </div>
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {entry.calculation_sheet_no || "-"}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {entry.drawing_no || "-"}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.estimated_quantity)}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.quantity_submitted)}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.internal_quantity)}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(
                                      entry.approved_by_project_manager
                                    )}
                                  </td>
                                  <td className="px-3 py-4 text-sm text-gray-500 max-w-xs">
                                    <div
                                      className="truncate"
                                      title={entry.notes || ""}
                                    >
                                      {entry.notes || "-"}
                                    </div>
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    <button
                                      onClick={() => startEditing(entry)}
                                      disabled={saving}
                                      className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                    >
                                      Edit Notes
                                    </button>
                                  </td>
                                </tr>
                              ))
                            )}

                            {/* Totals Row */}
                            {entries.length > 0 && (
                              <tr className="bg-gray-50 border-t-2 border-gray-300">
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  TOTALS
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    entries.reduce(
                                      (sum, entry) =>
                                        sum + entry.estimated_quantity,
                                      0
                                    )
                                  )}
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    entries.reduce(
                                      (sum, entry) =>
                                        sum + entry.quantity_submitted,
                                      0
                                    )
                                  )}
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    entries.reduce(
                                      (sum, entry) =>
                                        sum + entry.internal_quantity,
                                      0
                                    )
                                  )}
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    entries.reduce(
                                      (sum, entry) =>
                                        sum + entry.approved_by_project_manager,
                                      0
                                    )
                                  )}
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                              </tr>
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
                  <p className="text-lg">Select a BOQ item</p>
                  <p className="text-sm mt-1">
                    Choose an item from the list to view its concentration sheet
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

// Entry Form Component
interface EntryFormProps {
  entry?: ConcentrationEntry | null;
  boqItem?: BOQItemWithLatestContractUpdate;
  onSave: (
    data: Omit<
      ConcentrationEntry,
      "id" | "created_at" | "updated_at" | "concentration_sheet_id"
    >
  ) => void;
  onCancel: () => void;
  saving: boolean;
}

const EntryForm: React.FC<EntryFormProps> = ({
  entry,
  boqItem,
  onSave,
  onCancel,
  saving,
}) => {
  const [formData, setFormData] = useState({
    section_number: entry?.section_number || boqItem?.section_number || "",
    description: entry?.description || "",
    calculation_sheet_no: entry?.calculation_sheet_no || "",
    drawing_no: entry?.drawing_no || "",
    estimated_quantity: entry?.estimated_quantity || 0,
    quantity_submitted: entry?.quantity_submitted || 0,
    internal_quantity: entry?.internal_quantity || 0,
    approved_by_project_manager: entry?.approved_by_project_manager || 0,
    notes: entry?.notes || "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <input
            type="text"
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Calculation Sheet No
          </label>
          <input
            type="text"
            value={formData.calculation_sheet_no}
            onChange={(e) =>
              handleChange("calculation_sheet_no", e.target.value)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Drawing No
          </label>
          <input
            type="text"
            value={formData.drawing_no}
            onChange={(e) => handleChange("drawing_no", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Estimated Quantity
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.estimated_quantity}
            onChange={(e) =>
              handleChange(
                "estimated_quantity",
                parseFloat(e.target.value) || 0
              )
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Quantity Submitted
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.quantity_submitted}
            onChange={(e) =>
              handleChange(
                "quantity_submitted",
                parseFloat(e.target.value) || 0
              )
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Internal Quantity
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.internal_quantity}
            onChange={(e) =>
              handleChange("internal_quantity", parseFloat(e.target.value) || 0)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Approved Quantity
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.approved_by_project_manager}
            onChange={(e) =>
              handleChange(
                "approved_by_project_manager",
                parseFloat(e.target.value) || 0
              )
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || !!entry}
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            value={formData.notes}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving}
          />
        </div>
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {saving ? "Saving..." : entry ? "Update Notes" : "Create"}
        </button>
      </div>
    </form>
  );
};

export default ConcentrationSheets;
