import React, { useState, useEffect } from "react";
import { calculationSheetsApi } from "../services/api";
import { CalculationSheet, CalculationEntry } from "../types";
import { formatNumber } from "../utils/format";
import { FileText, Trash2, Eye, Search, Filter } from "lucide-react";

const CalculationSheets: React.FC = () => {
  const [sheets, setSheets] = useState<CalculationSheet[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<CalculationSheet | null>(
    null
  );
  const [entries, setEntries] = useState<CalculationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSheetNo, setFilterSheetNo] = useState("");
  const [filterDrawingNo, setFilterDrawingNo] = useState("");
  const [deletingSheet, setDeletingSheet] = useState(false);
  const [deletingEntry, setDeletingEntry] = useState<number | null>(null);
  const [populatingEntries, setPopulatingEntries] = useState(false);
  const [populatingAllEntries, setPopulatingAllEntries] = useState(false);

  // Fetch all calculation sheets
  const fetchSheets = async () => {
    try {
      setLoading(true);
      setError(null);
      // console.log("Fetching calculation sheets...");
      const response = await calculationSheetsApi.getAll(0, 10000);
      // console.log("Calculation sheets response:", response);
      setSheets(response);
    } catch (err) {
      console.error("Error fetching calculation sheets:", err);
      setError("Failed to fetch calculation sheets");
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
    fetchEntries(sheet.id);
  };

  // Delete calculation sheet
  const handleDeleteSheet = async (sheetId: number) => {
    if (
      !confirm(
        "Are you sure you want to delete this calculation sheet? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      setDeletingSheet(true);
      await calculationSheetsApi.delete(sheetId);

      setSheets((prev) => prev.filter((sheet) => sheet.id !== sheetId));
      if (selectedSheet?.id === sheetId) {
        setSelectedSheet(null);
        setEntries([]);
      }
      setError(null);
    } catch (err) {
      console.error("Error deleting calculation sheet:", err);
      setError("Failed to delete calculation sheet");
    } finally {
      setDeletingSheet(false);
    }
  };

  // Delete entry
  const handleDeleteEntry = async (entryId: number) => {
    if (!confirm("Are you sure you want to delete this entry?")) {
      return;
    }

    try {
      setDeletingEntry(entryId);
      await calculationSheetsApi.deleteEntry(entryId);

      setEntries((prev) => prev.filter((entry) => entry.id !== entryId));
      setError(null);
    } catch (err) {
      console.error("Error deleting entry:", err);
      setError("Failed to delete entry");
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
      let errorMessage = "Failed to populate concentration entries";

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

  // Populate ALL calculation entries from ALL calculation sheets
  const handlePopulateAllCalculationEntries = async () => {
    if (
      !confirm(
        `Are you sure you want to populate concentration entries from ALL calculation sheets in the database? This will process ${sheets.length} sheets and may take some time.`
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
      let errorMessage = "Failed to populate all calculation entries";

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

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Calculation Sheets
          </h1>
          <p className="mt-2 text-gray-600">
            View imported calculation sheet data
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
        <h1 className="text-3xl font-bold text-gray-900">Calculation Sheets</h1>
        <p className="mt-2 text-gray-600">
          View imported calculation sheet data ({sheets.length} sheets)
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
            <p className="text-xs text-gray-500 text-center mt-2 max-w-xs mx-auto">
              Processes all calculation sheets at once. May take time for large
              datasets.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow h-full flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Calculation Sheets
              </h2>
              <p className="text-sm text-gray-600">
                Select a sheet to view its entries
              </p>

              {/* Search */}
              <div className="mt-3">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search sheets..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Filters */}
              <div className="mt-3 grid grid-cols-2 gap-2">
                <input
                  type="text"
                  value={filterSheetNo}
                  onChange={(e) => setFilterSheetNo(e.target.value)}
                  placeholder="Sheet No filter"
                  className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <input
                  type="text"
                  value={filterDrawingNo}
                  onChange={(e) => setFilterDrawingNo(e.target.value)}
                  placeholder="Drawing No filter"
                  className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {filteredSheets.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <p>No calculation sheets found</p>
                  <p className="text-sm mt-1">
                    Import calculation sheets from the File Import page
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {filteredSheets.map((sheet) => (
                    <div
                      key={sheet.id}
                      className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                        selectedSheet?.id === sheet.id
                          ? "bg-blue-50 border-r-4 border-blue-500"
                          : ""
                      }`}
                      onClick={() => handleSheetSelect(sheet)}
                    >
                      <div className="flex justify-between items-start">
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
                            {new Date(sheet.import_date).toLocaleDateString()}
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteSheet(sheet.id);
                          }}
                          disabled={deletingSheet}
                          className="text-red-600 hover:text-red-800 disabled:opacity-50 ml-2"
                          title="Delete sheet"
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
                        Calculation Sheet - {selectedSheet.calculation_sheet_no}
                      </h2>
                      <p className="text-sm text-gray-600 mt-1">
                        {selectedSheet.description}
                      </p>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <button
                        onClick={handlePopulateConcentrationEntries}
                        disabled={populatingEntries || entries.length === 0}
                        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                        title="Populate concentration entries from this calculation sheet"
                      >
                        {populatingEntries ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            <span>Populating...</span>
                          </>
                        ) : (
                          <>
                            <span>📋</span>
                            <span>Populate to Concentration</span>
                          </>
                        )}
                      </button>
                      <p className="text-xs text-gray-500 text-right max-w-xs">
                        Creates concentration entries from calculation entries,
                        matching by section number. Skips if same Calculation
                        Sheet No + Drawing No already exists.
                      </p>
                    </div>
                  </div>

                  {/* Sheet Information Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Calculation Sheet No:
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.calculation_sheet_no}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Drawing No:
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.drawing_no}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        Import Date:
                      </label>
                      <p className="text-gray-900">
                        {new Date(
                          selectedSheet.import_date
                        ).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Entries Table */}
                <div className="flex-1 p-6 overflow-hidden flex flex-col">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                      Calculation Entries ({entries.length})
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
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Section Number
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Estimated Quantity
                              </th>
                              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Quantity Submitted
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
                                  colSpan={4}
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
                                <tr key={entry.id} className="hover:bg-gray-50">
                                  <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                    {entry.section_number}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.estimated_quantity)}
                                  </td>
                                  <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {formatNumber(entry.quantity_submitted)}
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
