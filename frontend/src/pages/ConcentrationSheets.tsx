import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import {
  concentrationApi,
  exportApi,
  calculationSheetsApi,
  boqApi,
} from "../services/api";
import {
  ConcentrationSheet,
  ConcentrationSheetWithBOQData,
  ConcentrationEntry,
  ConcentrationEntryExportRequest,
  BOQItemWithLatestContractUpdate,
  BOQItem,
} from "../types";
import { formatCurrency, formatNumber } from "../utils/format";
import {
  Search,
  X,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import ConcentrationEntryExportModal from "../components/ConcentrationEntryExportModal";
import PopulateConcentrationEntryModal from "../components/PopulateConcentrationEntryModal";
import ConcentrationDrawingFilesCell from "../components/ConcentrationDrawingFilesCell";
import {
  ConcentrationBreakdownPastRows,
  ConcentrationBreakdownTotalRow,
  PeriodEditDraft,
} from "../components/ConcentrationBreakdownRows";
import { SubmissionBreakdownToggle } from "../components/SubmissionBreakdownPanel";
import { concentrationEntriesQuantitySubmittedTotal } from "../utils/submissionBreakdown";
import {
  entryTotalApprovedQuantity,
  entryTotalInternalQuantity,
  getCurrentPeriodFields,
  getPeriodDetail,
  getPeriodDrawingFiles,
  resolveCurrentPeriod,
} from "../utils/periodDetails";
import { getProjectItem, setProjectItem } from "../utils/localStorage";

/** Draft state for inline row editing (mirrors EntryForm fields). */
type ConcentrationEntryEditDraft = {
  section_number: string;
  description: string;
  calculation_sheet_no: string;
  drawing_no: string;
  invoice_description: string;
  estimated_quantity: number;
  submission_percentage: number;
  quantity_submitted: number;
  internal_quantity: number;
  approved_by_project_manager: number;
  notes: string;
  supervisor_notes: string;
  is_manual: boolean;
};

function computeQuantitySubmitted(
  estimatedQuantity: number,
  submissionPercentage: number
): number {
  return estimatedQuantity * (submissionPercentage / 100);
}

function drawingFileName(path: string): string {
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
}

function expandedBreakdownIdsForEntries(
  entryList: ConcentrationEntry[]
): Set<number> {
  return new Set(
    entryList
      .filter((entry) => (entry.estimated_quantity ?? 0) !== 0)
      .map((entry) => entry.id)
  );
}

function concentrationEntryToEditDraft(
  entry: ConcentrationEntry
): ConcentrationEntryEditDraft {
  const currentFields = getCurrentPeriodFields(entry);
  const estimatedQuantity = entry.estimated_quantity ?? 0;
  return {
    section_number: entry.section_number || "",
    description: entry.description || "",
    calculation_sheet_no: entry.calculation_sheet_no || "",
    drawing_no: entry.drawing_no || "",
    invoice_description: entry.invoice_description || "",
    estimated_quantity: estimatedQuantity,
    submission_percentage: currentFields.submission_percentage,
    quantity_submitted: entry.quantity_submitted ?? computeQuantitySubmitted(
      estimatedQuantity,
      currentFields.submission_percentage
    ),
    internal_quantity: currentFields.internal_quantity,
    approved_by_project_manager: currentFields.approved_by_project_manager,
    notes: currentFields.notes,
    supervisor_notes: currentFields.supervisor_notes,
    is_manual: entry.is_manual,
  };
}

const ConcentrationSheets: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [sheets, setSheets] = useState<ConcentrationSheetWithBOQData[]>([]);
  const [selectedSheet, setSelectedSheet] =
    useState<ConcentrationSheetWithBOQData | null>(null);
  const [entries, setEntries] = useState<ConcentrationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debug: Log error state changes
  useEffect(() => {
    if (error) {
      console.log("Error state set to:", error);
    }
  }, [error]);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ConcentrationEntry | null>(
    null
  );
  const [editDraft, setEditDraft] =
    useState<ConcentrationEntryEditDraft | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingAllPDF, setExportingAllPDF] = useState(false);
  const [exportingAllExcel, setExportingAllExcel] = useState(false);
  const [trackingCalculationSheets, setTrackingCalculationSheets] =
    useState(false);
  const [showNavigationMessage, setShowNavigationMessage] = useState(false);
  const [navigatedFromBOQ, setNavigatedFromBOQ] = useState(false);
  // Initialize filter from localStorage
  const [sectionNumberFilter, setSectionNumberFilter] = useState(() => {
    const saved = getProjectItem("concentration-sheets-section-filter");
    return saved !== null ? saved : "";
  });
  const [showEntryColumnModal, setShowEntryColumnModal] = useState(false);
  const [pendingExportAction, setPendingExportAction] = useState<{
    type: "single" | "all";
    format: "pdf" | "excel";
    title: string;
  } | null>(null);

  const [populateEntrySource, setPopulateEntrySource] =
    useState<ConcentrationEntry | null>(null);
  const [populateBoqItems, setPopulateBoqItems] = useState<BOQItem[]>([]);
  const [populateListLoading, setPopulateListLoading] = useState(false);
  const [populateSubmitting, setPopulateSubmitting] = useState(false);
  const drawingFileInputRef = useRef<HTMLInputElement>(null);
  const [attachTarget, setAttachTarget] = useState<{
    entryId: number;
    invoiceNo?: string;
  } | null>(null);
  const [uploadingDrawingKey, setUploadingDrawingKey] = useState<
    string | null
  >(null);
  const [expandedDrawingKeys, setExpandedDrawingKeys] = useState<Set<string>>(
    new Set()
  );
  const [deletingAllDrawingKey, setDeletingAllDrawingKey] = useState<
    string | null
  >(null);
  const [periodEdit, setPeriodEdit] = useState<{
    entryId: number;
    period: string;
    draft: PeriodEditDraft;
  } | null>(null);
  const [expandedBreakdownEntryIds, setExpandedBreakdownEntryIds] = useState<
    Set<number>
  >(new Set());
  const visibleEntries = useMemo(
    () => entries.filter((entry) => (entry.estimated_quantity ?? 0) !== 0),
    [entries]
  );
  const visibleEntriesSubmittedTotal = useMemo(
    () =>
      concentrationEntriesQuantitySubmittedTotal(
        visibleEntries,
        expandedBreakdownEntryIds,
      ),
    [visibleEntries, expandedBreakdownEntryIds],
  );
  const allBreakdownsExpanded = useMemo(
    () =>
      visibleEntries.length > 0 &&
      visibleEntries.every((entry) => expandedBreakdownEntryIds.has(entry.id)),
    [visibleEntries, expandedBreakdownEntryIds],
  );

  // Project info state - will be loaded from selected sheet
  const [projectInfo, setProjectInfo] = useState({
    projectName: "",
    contractorInCharge: "",
    contractNo: "",
    developerName: "",
  });

  // Load project info from selected sheet
  const loadProjectInfoFromSheet = (sheet: ConcentrationSheetWithBOQData) => {
    const info = {
      projectName: sheet.project_name || "",
      contractorInCharge: sheet.contractor_in_charge || "",
      contractNo: sheet.contract_no || "",
      developerName: sheet.developer_name || "",
    };
    setProjectInfo(info);
  };

  // Export functions with column selection modal
  const showExportModal = (
    type: "single" | "all",
    format: "pdf" | "excel",
    title: string
  ) => {
    setPendingExportAction({ type, format, title });
    setShowEntryColumnModal(true);
  };

  const handleExportModalSubmit = async (
    entryColumnRequest: ConcentrationEntryExportRequest
  ) => {
    if (!pendingExportAction) return;

    setShowEntryColumnModal(false);

    const actualFormat = pendingExportAction.format;

    if (pendingExportAction.type === "single") {
      await executeSingleSheetExport(actualFormat, entryColumnRequest);
    } else {
      await executeAllSheetsExport(actualFormat, entryColumnRequest);
    }

    setPendingExportAction(null);
  };

  const handleOpenCalculationSheet = async (calculationSheetNo: string) => {
    try {
      const normalizedNo = calculationSheetNo.trim();
      if (!normalizedNo) {
        setError("Calculation sheet number is required");
        return;
      }

      await calculationSheetsApi.openSourceFileByNo(normalizedNo);
    } catch (err: any) {
      console.error("Error opening calculation sheet:", err);
      setError(
        err.response?.data?.detail || "Failed to open calculation sheet"
      );
    }
  };

  const handleAttachDrawingFiles = async (
    entryId: number,
    fileList: FileList | null,
    invoiceNo?: string
  ) => {
    if (!fileList?.length) return;
    const key = `${entryId}:${invoiceNo || "current"}`;
    try {
      setUploadingDrawingKey(key);
      setError(null);
      const updated = await concentrationApi.uploadDrawingFiles(
        entryId,
        Array.from(fileList),
        invoiceNo
      );
      setEntries((prev) => prev.map((e) => (e.id === entryId ? updated : e)));
    } catch (err: any) {
      console.error("Error attaching drawing files:", err);
      setError(
        err.response?.data?.detail || t("concentration.failedToAttachDrawings")
      );
    } finally {
      setUploadingDrawingKey(null);
      setAttachTarget(null);
    }
  };

  const handleOpenDrawingFile = async (entryId: number, path: string) => {
    try {
      setError(null);
      await concentrationApi.openDrawingFile(entryId, path);
    } catch (err: any) {
      console.error("Error opening drawing file:", err);
      setError(
        err.response?.data?.detail || t("concentration.failedToOpenDrawing")
      );
    }
  };

  const handleRemoveDrawingFile = async (
    entryId: number,
    path: string,
    invoiceNo?: string
  ) => {
    if (!confirm(t("concentration.confirmRemoveDrawing"))) return;
    try {
      setError(null);
      const updated = await concentrationApi.removeDrawingFile(
        entryId,
        path,
        invoiceNo
      );
      setEntries((prev) => prev.map((e) => (e.id === entryId ? updated : e)));
    } catch (err: any) {
      console.error("Error removing drawing file:", err);
      setError(
        err.response?.data?.detail || t("concentration.failedToRemoveDrawing")
      );
    }
  };

  const handleRemoveAllDrawingFiles = async (
    entryId: number,
    invoiceNo?: string
  ) => {
    if (!confirm(t("concentration.confirmDeleteAllDrawings"))) return;
    const key = `${entryId}:${invoiceNo || "current"}`;
    try {
      setDeletingAllDrawingKey(key);
      setError(null);
      const updated = await concentrationApi.removeAllDrawingFiles(
        entryId,
        invoiceNo
      );
      setEntries((prev) => prev.map((e) => (e.id === entryId ? updated : e)));
    } catch (err: any) {
      console.error("Error removing all drawing files:", err);
      setError(
        err.response?.data?.detail ||
          t("concentration.failedToDeleteAllDrawings")
      );
    } finally {
      setDeletingAllDrawingKey(null);
    }
  };

  const toggleDrawingFilesExpanded = (key: string) => {
    setExpandedDrawingKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleBreakdownExpanded = (entryId: number) => {
    setExpandedBreakdownEntryIds((prev) => {
      const next = new Set(prev);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
  };

  const toggleAllBreakdownsExpanded = () => {
    if (allBreakdownsExpanded) {
      setExpandedBreakdownEntryIds(new Set());
    } else {
      setExpandedBreakdownEntryIds(expandedBreakdownIdsForEntries(visibleEntries));
    }
  };

  const triggerAttachDrawings = (entryId: number, invoiceNo?: string) => {
    setAttachTarget({ entryId, invoiceNo });
    drawingFileInputRef.current?.click();
  };

  const executeSingleSheetExport = async (
    format: "pdf" | "excel",
    entryColumnRequest: ConcentrationEntryExportRequest
  ) => {
    console.log("executeSingleSheetExport called with format:", format);

    if (!selectedSheet) {
      setError(t("auth.noSheetSelectedForExport"));
      return;
    }

    try {
      console.log("Starting export, setting loading state...");
      if (format === "pdf") {
        setExportingPDF(true);
      } else {
        setExportingExcel(true);
      }
      setError(null);
      console.log("Loading state set, making API call...");

      let response;
      try {
        response =
          format === "pdf"
            ? await exportApi.exportSingleConcentrationSheetPDF(
                selectedSheet.id,
                entryColumnRequest,
                isRTL ? "he" : "en"
              )
            : await exportApi.exportSingleConcentrationSheetExcel(
                selectedSheet.id,
                entryColumnRequest
              );
        console.log("API call completed, response received:", response);
      } catch (apiError: any) {
        console.error("API call threw an error:", apiError);
        console.error("Error response:", apiError?.response);
        console.error("Error data:", apiError?.response?.data);
        // If the API call itself fails, handle it
        throw apiError;
      }

      console.log("Export response:", response);
      console.log("Response type:", typeof response);
      console.log("Response.success:", response?.success);
      console.log("Response.message:", response?.message);
      console.log(
        "Response keys:",
        response ? Object.keys(response) : "response is null/undefined"
      );

      // Check for error first - be very explicit
      const isSuccess = response && response.success === true;
      console.log("isSuccess check:", isSuccess);

      if (!isSuccess) {
        console.log("Export was NOT successful, handling error...");
        const errorMessage =
          (response && response.message) ||
          t("concentration.exportFailed") + " " + format.toUpperCase();
        console.error(
          `Export failed - setting error: ${errorMessage}`,
          "Full response:",
          response
        );
        console.log("About to call setError with:", errorMessage);

        // Force a synchronous check
        const currentError = error;
        console.log("Current error state before setError:", currentError);

        setError(errorMessage);

        // Use setTimeout to check state after React updates
        setTimeout(() => {
          console.log(
            "Error state after setError (delayed check):",
            errorMessage
          );
        }, 100);

        console.log("setError called, error state should be:", errorMessage);
        return;
      }

      console.log("Export was successful, proceeding with download...");

      // For Excel exports, files are saved server-side to C:/Fatina/{section_number}/
      // For PDF exports, download the file
      if (format === "excel") {
        // Excel files are saved server-side, just show success message
        // The response.message already contains the success message
        console.log("Excel file saved server-side:", response.message);
      } else if (response.pdf_path) {
        // PDF export - download the file
        const link = document.createElement("a");
        link.href = `/api${response.pdf_path}`;
        // Extract filename from the path
        const filename =
          response.pdf_path.split("/").pop() || `${selectedSheet.id}.pdf`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        // Success but no pdf_path for PDF - this shouldn't happen but handle it
        const errorMessage =
          response?.message ||
          t("concentration.exportFailed") + " " + format.toUpperCase();
        console.error(
          `Export succeeded but no file path - setting error: ${errorMessage}`,
          response
        );
        setError(errorMessage);
      }
    } catch (err: any) {
      console.error(`Error exporting ${format}:`, err);
      console.error("Error object:", err);
      console.error("Error response:", err?.response);
      console.error("Error response data:", err?.response?.data);

      // Extract error message from axios error response
      let errorMessage =
        t("concentration.exportFailed") + " " + format.toUpperCase();

      // Check if error has response data (axios error)
      if (err?.response?.data) {
        // If response.data has a message, use it
        if (err.response.data.message) {
          errorMessage = err.response.data.message;
        } else if (err.response.data.detail) {
          errorMessage = err.response.data.detail;
        }
      } else if (err?.message) {
        errorMessage = err.message;
      }

      console.log("Setting error message:", errorMessage);
      setError(errorMessage);
      console.log("Error set, current error state should be:", errorMessage);
    } finally {
      if (format === "pdf") {
        setExportingPDF(false);
      } else {
        setExportingExcel(false);
      }
    }
  };

  const executeAllSheetsExport = async (
    format: "pdf" | "excel",
    entryColumnRequest: ConcentrationEntryExportRequest
  ) => {
    try {
      if (format === "pdf") {
        setExportingAllPDF(true);
      } else {
        setExportingAllExcel(true);
      }
      setError(null);

      const exportNonEmptyOnly =
        entryColumnRequest.export_non_empty_only ?? false;
      const exportNonZeroPsqOnly =
        entryColumnRequest.export_non_zero_psq_only ?? false;
      const exportEstimatedGtContractOnly =
        entryColumnRequest.export_estimated_gt_contract_only ?? false;
      const skipFullyApprovedCalcSheetFolders =
        entryColumnRequest.skip_fully_approved_calc_sheet_folders ?? false;

      const response =
        format === "pdf"
          ? await exportApi.exportConcentrationSheets(
              {
                item_codes: [],
                hide_columns: [],
                export_all: true,
                export_non_empty_only: exportNonEmptyOnly,
                export_non_zero_psq_only: exportNonZeroPsqOnly,
                export_estimated_gt_contract_only: exportEstimatedGtContractOnly,
                skip_fully_approved_calc_sheet_folders:
                  skipFullyApprovedCalcSheetFolders,
              },
              entryColumnRequest,
              isRTL ? "he" : "en"
            )
          : await exportApi.exportAllConcentrationSheetsExcel(
              {
                item_codes: [],
                hide_columns: [],
                export_all: true,
                export_non_empty_only: exportNonEmptyOnly,
                export_non_zero_psq_only: exportNonZeroPsqOnly,
                export_estimated_gt_contract_only: exportEstimatedGtContractOnly,
                skip_fully_approved_calc_sheet_folders:
                  skipFullyApprovedCalcSheetFolders,
              },
              entryColumnRequest
            );

      console.log("Bulk export response:", response);

      // Check for error first
      if (!response || !response.success) {
        const errorMessage =
          response?.message ||
          t("concentration.exportFailed") + " " + format.toUpperCase();
        console.error(
          `Bulk export failed - setting error: ${errorMessage}`,
          "Full response:",
          response
        );
        console.log("About to call setError with:", errorMessage);
        setError(errorMessage);
        console.log("setError called, error state should be:", errorMessage);
        return;
      }

      // Bulk exports are saved server-side (Excel -> C:/Fatina, PDF zip -> Downloads)
      console.log(
        `${format.toUpperCase()} files saved server-side:`,
        response.message
      );
    } catch (err: any) {
      console.error(`Error exporting all ${format}s:`, err);
      // Extract error message from axios error response
      let errorMessage =
        t("concentration.exportFailed") +
        " " +
        t("concentration.exportAllSheetsPDF");
      if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      if (format === "pdf") {
        setExportingAllPDF(false);
      } else {
        setExportingAllExcel(false);
      }
    }
  };

  const handleTrackCalculationSheets = async () => {
    if (!selectedSheet) return;

    try {
      setTrackingCalculationSheets(true);
      setError(null);
      const response = await concentrationApi.trackCalculationSheets(
        selectedSheet.id,
        isRTL ? "he" : "en"
      );

      if (response.success) {
        await fetchEntries(selectedSheet.id);
        alert(`✅ ${response.message}`);
      } else {
        const errorMessage =
          response.errors[0] ||
          response.message ||
          t("concentration.failedToTrack");
        setError(errorMessage);
        alert(`Error: ${errorMessage}`);
      }
    } catch (err: any) {
      console.error("Error tracking calculation sheets:", err);
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        t("concentration.failedToTrack");
      setError(errorMessage);
      alert(`Error: ${errorMessage}`);
    } finally {
      setTrackingCalculationSheets(false);
    }
  };

  const handleExportPDF = () => {
    if (!selectedSheet) {
      setError(t("concentration.noSheetSelected"));
      return;
    }
    showExportModal("single", "pdf", t("concentration.exportSingleSheetPDF"));
  };

  const handleExportExcel = () => {
    if (!selectedSheet) {
      setError(t("concentration.noSheetSelected"));
      return;
    }
    showExportModal(
      "single",
      "excel",
      t("concentration.exportSingleSheetExcel")
    );
  };

  // Export all concentration sheets functions
  const handleExportAllPDF = () => {
    showExportModal("all", "pdf", t("concentration.exportAllSheetsPDF"));
  };

  const handleExportAllExcel = () => {
    showExportModal("all", "excel", t("concentration.exportAllSheetsExcel"));
  };

  // Fetch all concentration sheets with BOQ item data
  const fetchSheets = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log("Fetching concentration sheets with BOQ data...");
      const sheetsWithBOQ = await concentrationApi.getAllWithBOQData(0, 10000);
      console.log(
        "Concentration sheets with BOQ data fetched:",
        sheetsWithBOQ.length
      );

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

          // Save selected sheet ID to localStorage
          setProjectItem(
            "concentration-selected-sheet-id",
            targetSheet.id.toString()
          );

          return; // Don't set default selection
        }
      }

      // Restore previously selected sheet from localStorage
      const savedSheetId = getProjectItem("concentration-selected-sheet-id");
      if (savedSheetId) {
        const savedSheet = sheetsWithBOQ.find(
          (sheet) => sheet.id === parseInt(savedSheetId)
        );
        if (savedSheet) {
          setSelectedSheet(savedSheet);
          loadProjectInfoFromSheet(savedSheet);
          fetchEntries(savedSheet.id);

          // Scroll to the selected sheet in the sidebar
          setTimeout(() => {
            const element = document.getElementById(`sheet-${savedSheet.id}`);
            if (element) {
              element.scrollIntoView({ behavior: "smooth", block: "center" });
            }
          }, 100);
          return;
        }
      }

      // Don't automatically select first sheet - let user choose
    } catch (err) {
      console.error("Error fetching concentration sheets:", err);
      setError(t("concentration.failedToFetchSheets"));
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
      setExpandedBreakdownEntryIds(
        expandedBreakdownIdsForEntries(sheetEntries)
      );
    } catch (err) {
      console.error("Error fetching entries:", err);
      setEntries([]);
    } finally {
      setEntriesLoading(false);
    }
  };

  // Handle sheet selection
  const handleSheetSelect = (sheet: ConcentrationSheetWithBOQData) => {
    setSelectedSheet(sheet);
    setEditingEntry(null);
    setEditDraft(null);
    setShowAddForm(false);
    loadProjectInfoFromSheet(sheet);
    fetchEntries(sheet.id);
    // Save selected sheet ID to localStorage
    setProjectItem("concentration-selected-sheet-id", sheet.id.toString());
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
      setError(t("auth.failedToCreateEntry"));
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
      setEditDraft(null);
      setError(null);
    } catch (err) {
      console.error("Error updating entry:", err);
      setError(t("auth.failedToUpdateEntry"));
    } finally {
      setSaving(false);
    }
  };

  // Delete entry
  const deleteEntry = async (entryId: number) => {
    try {
      setSaving(true);
      await concentrationApi.deleteEntry(entryId);

      setEntries((prev) => prev.filter((entry) => entry.id !== entryId));
      if (editingEntry?.id === entryId) {
        setEditingEntry(null);
        setEditDraft(null);
      }
      setError(null);
    } catch (err) {
      console.error("Error deleting entry:", err);
      setError(t("auth.failedToDeleteEntry"));
    } finally {
      setSaving(false);
    }
  };

  // Start editing entry
  const startEditing = (entry: ConcentrationEntry) => {
    setPeriodEdit(null);
    setEditingEntry(entry);
    setEditDraft(concentrationEntryToEditDraft(entry));
    setShowAddForm(false);
  };

  const startPeriodEditing = (entry: ConcentrationEntry, period: string) => {
    setEditingEntry(null);
    setEditDraft(null);
    const breakdown = entry.submission_breakdown;
    const periods = breakdown?.periods || breakdown?.past_months || {};
    const qty =
      period === resolveCurrentPeriod(entry, breakdown)
        ? entry.quantity_submitted || 0
        : periods[period] || 0;
    const detail = getPeriodDetail(breakdown, period);
    setPeriodEdit({
      entryId: entry.id,
      period,
      draft: {
        submission_percentage:
          detail.submission_percentage ??
          (entry.estimated_quantity
            ? (qty / entry.estimated_quantity) * 100
            : 100),
        internal_quantity: detail.internal_quantity ?? 0,
        approved_by_project_manager: detail.approved_by_project_manager ?? 0,
        notes: detail.notes || "",
        supervisor_notes: detail.supervisor_notes || "",
      },
    });
  };

  const cancelPeriodEdit = useCallback(() => {
    setPeriodEdit(null);
  }, []);

  const savePeriodEdit = async () => {
    if (!periodEdit) return;
    try {
      setSaving(true);
      const updatedEntry = await concentrationApi.updateEntry(periodEdit.entryId, {
        invoice_no: periodEdit.period,
        submission_percentage: periodEdit.draft.submission_percentage,
        internal_quantity: periodEdit.draft.internal_quantity,
        approved_by_project_manager: periodEdit.draft.approved_by_project_manager,
        notes: periodEdit.draft.notes,
        supervisor_notes: periodEdit.draft.supervisor_notes,
      });
      setEntries((prev) =>
        prev.map((entry) =>
          entry.id === periodEdit.entryId ? updatedEntry : entry
        )
      );
      setPeriodEdit(null);
      setError(null);
    } catch (err) {
      console.error("Error updating period entry:", err);
      setError(t("auth.failedToUpdateEntry"));
    } finally {
      setSaving(false);
    }
  };

  const cancelInlineEdit = useCallback(() => {
    setEditingEntry(null);
    setEditDraft(null);
    setPeriodEdit(null);
  }, []);

  const saveInlineEdit = async () => {
    if (!editingEntry || !editDraft) return;
    const invoiceNo = resolveCurrentPeriod(
      editingEntry,
      editingEntry.submission_breakdown
    );
    const periodFields = {
      invoice_no: invoiceNo || undefined,
      submission_percentage: editDraft.submission_percentage,
      internal_quantity: editDraft.internal_quantity,
      approved_by_project_manager: editDraft.approved_by_project_manager,
      notes: editDraft.notes,
      supervisor_notes: editDraft.supervisor_notes,
    };
    if (editDraft.is_manual) {
      await updateEntry(editingEntry.id, {
        section_number: editDraft.section_number,
        description: editDraft.description,
        calculation_sheet_no: editDraft.calculation_sheet_no,
        drawing_no: editDraft.drawing_no,
        invoice_description: editDraft.invoice_description,
        estimated_quantity: editDraft.estimated_quantity,
        ...periodFields,
        is_manual: true,
      });
    } else {
      await updateEntry(editingEntry.id, periodFields);
    }
  };

  const saveInlineEditRef = useRef(saveInlineEdit);
  saveInlineEditRef.current = saveInlineEdit;

  useEffect(() => {
    if (!editingEntry) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (saving) return;

      if (e.key === "Escape") {
        e.preventDefault();
        cancelInlineEdit();
        return;
      }
      if (e.key !== "Enter") return;

      const target = e.target as HTMLElement;
      if (target.tagName === "TEXTAREA") {
        if (!e.ctrlKey && !e.metaKey) return;
      }

      e.preventDefault();
      void saveInlineEditRef.current();
    };

    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [editingEntry, cancelInlineEdit, saving]);

  const handleRowDoubleClick = (
    entry: ConcentrationEntry,
    e: React.MouseEvent<HTMLTableRowElement>
  ) => {
    const target = e.target as HTMLElement;
    if (target.closest("button, a, input, textarea, select")) return;
    if (saving || populateSubmitting) return;
    if (editingEntry?.id === entry.id) return;
    setPeriodEdit(null);
    startEditing(entry);
  };

  const openPopulateModal = async (entry: ConcentrationEntry) => {
    setPopulateEntrySource(entry);
    setPopulateListLoading(true);
    setPopulateBoqItems([]);
    try {
      const items = await boqApi.getAll(0, 10000);
      setPopulateBoqItems(items);
    } catch (err) {
      console.error("Error loading BOQ items for populate:", err);
      setError(t("concentration.populateLoadBoqFailed"));
      setPopulateEntrySource(null);
    } finally {
      setPopulateListLoading(false);
    }
  };

  const handlePopulateConfirm = async (boqItemIds: number[]) => {
    if (!populateEntrySource) return;
    try {
      setPopulateSubmitting(true);
      setError(null);
      await concentrationApi.copyEntryToBoqItems(populateEntrySource.id, {
        boq_item_ids: boqItemIds,
      });
      setPopulateEntrySource(null);
    } catch (err: any) {
      console.error("Error copying concentration entry:", err);
      const detail = err.response?.data?.detail;
      let msg: string = t("concentration.populateFailed");
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail) && detail[0]?.msg)
        msg = detail
          .map((x: { msg?: string }) => x.msg)
          .filter(Boolean)
          .join(", ");
      else if (err.response?.data?.message)
        msg = String(err.response.data.message);
      setError(msg);
    } finally {
      setPopulateSubmitting(false);
    }
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

  // Save section number filter to localStorage
  useEffect(() => {
    setProjectItem("concentration-sheets-section-filter", sectionNumberFilter);
  }, [sectionNumberFilter]);

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
            {t("concentration.title")}
          </h1>
          <p className="mt-2 text-gray-600">{t("concentration.subtitle")}</p>
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
      <input
        ref={drawingFileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          if (attachTarget !== null) {
            void handleAttachDrawingFiles(
              attachTarget.entryId,
              e.target.files,
              attachTarget.invoiceNo
            );
          }
          e.target.value = "";
        }}
      />
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {t("concentration.title")}
          </h1>
          <p className="mt-2 text-gray-600">
            {t("concentration.subtitle")} ({sheets.length}{" "}
            {t("concentration.sheetsCount")})
          </p>
        </div>
        <div className="flex space-x-3 flex-wrap">
          <button
            onClick={fetchSheets}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title={t("auth.refreshConcentrationSheetsData")}
          >
            {loading ? t("auth.refreshing") : `🔄 ${t("auth.refresh")}`}
          </button>

          {/* Export All Buttons */}
          <div className="flex space-x-2">
            <button
              onClick={handleExportAllPDF}
              disabled={exportingAllPDF || sheets.length === 0}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={t("concentration.exportAllPDFTitle")}
            >
              {exportingAllPDF
                ? t("concentration.exporting")
                : t("concentration.exportAllPDFIndividual")}
            </button>
            <button
              onClick={handleExportAllExcel}
              disabled={exportingAllExcel || sheets.length === 0}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={t("concentration.exportAllExcelTitle")}
            >
              {exportingAllExcel
                ? t("concentration.exporting")
                : t("concentration.exportAllExcel")}
            </button>
          </div>

          {navigatedFromBOQ && (
            <button
              onClick={() => window.history.back()}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
            >
              {t("concentration.backToBOQItems")}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div
          className="bg-red-50 border-2 border-red-300 rounded-md p-4 mb-4 shadow-md"
          style={{ display: "block", visibility: "visible" }}
        >
          <div className="flex items-center justify-between">
            <div className="text-red-700 font-medium flex-1">
              {error || "Error message is empty"}
            </div>
            <button
              onClick={() => {
                console.log("Closing error message, current error:", error);
                setError(null);
              }}
              className="ml-4 text-red-600 hover:text-red-800 focus:outline-none transition-colors"
              aria-label="Close error"
            >
              <X size={20} />
            </button>
          </div>
        </div>
      )}

      {showNavigationMessage && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex">
            <div className="text-green-600">
              {t("concentration.navigatedFromBOQ")}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-screen max-h-[calc(100vh-200px)]">
        {/* Left Side - Items List */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow h-full flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {t("concentration.boqItems")}
              </h2>
              <p className="text-sm text-gray-600">
                {t("concentration.selectItemToViewSheet")}
                {sectionNumberFilter && (
                  <span className={`${isRTL ? "mr-2" : "ml-2"} text-blue-600`}>
                    ({filteredSheets.length} {t("common.of", "of")}{" "}
                    {sheets.length} {t("concentration.filteredCount")})
                  </span>
                )}
              </p>

              {navigatedFromBOQ && selectedSheet && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <div className="text-sm text-blue-800">
                    <div className="font-medium">
                      {t("concentration.currentlyViewing")}
                    </div>
                    <div className="mt-1">
                      <span className="font-semibold">
                        {selectedSheet.boq_item.section_number}
                      </span>
                      <span
                        className={`text-blue-600 ${isRTL ? "mr-2" : "ml-2"}`}
                      >
                        •
                      </span>
                      <span className={isRTL ? "mr-2" : "ml-2"}>
                        {selectedSheet.boq_item.description}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Section Number Filter */}
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("concentration.filterBySectionNumber")}
                </label>
                <div className="relative">
                  <div
                    className={`absolute inset-y-0 ${
                      isRTL ? "right-0 pr-3" : "left-0 pl-3"
                    } flex items-center pointer-events-none`}
                  >
                    <Search className="h-4 w-4 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    value={sectionNumberFilter}
                    onChange={(e) => setSectionNumberFilter(e.target.value)}
                    placeholder={t("concentration.enterSectionNumber")}
                    className={`w-full py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm ${
                      isRTL ? "pr-10 pl-3" : "pl-10 pr-10"
                    }`}
                  />
                  {sectionNumberFilter && (
                    <button
                      onClick={() => setSectionNumberFilter("")}
                      className={`absolute inset-y-0 ${
                        isRTL ? "left-0 pl-3" : "right-0 pr-3"
                      } flex items-center text-gray-400 hover:text-gray-600`}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {sectionNumberFilter && (
                  <button
                    onClick={() => setSectionNumberFilter("")}
                    className={`mt-1 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 ${
                      isRTL ? "flex-row-reverse" : ""
                    }`}
                  >
                    <X className="h-3 w-3" />
                    {t("concentration.clearFilter")}
                  </button>
                )}
              </div>
            </div>

            <div
              className="flex-1 overflow-y-scroll"
              style={{ minHeight: 0, maxHeight: "calc(100vh - 250px)" }}
            >
              {filteredSheets.length === 0 ? (
                <div
                  className={`p-4 text-gray-500 ${
                    isRTL ? "text-right" : "text-center"
                  }`}
                >
                  {sectionNumberFilter ? (
                    <>
                      <p>
                        {t("concentration.noSheetsFoundMatching")} "
                        {sectionNumberFilter}"
                      </p>
                      <p className="text-sm mt-1">
                        {t("concentration.tryAdjustingFilter")}{" "}
                        <button
                          onClick={() => setSectionNumberFilter("")}
                          className="text-blue-600 hover:text-blue-800 underline"
                        >
                          {t("concentration.clearTheFilter")}
                        </button>
                      </p>
                    </>
                  ) : (
                    <>
                      <p>{t("concentration.noConcentrationSheetsFound")}</p>
                      <p className="text-sm mt-1">
                        {t("concentration.createSheetsFromBOQ")}
                      </p>
                    </>
                  )}
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {filteredSheets.map((sheet) => {
                    const submittedQty =
                      sheet.boq_item.quantity_submitted ?? 0;
                    const approvedQty =
                      sheet.boq_item.approved_by_project_manager ?? 0;
                    const roundedSubmitted =
                      Math.round(submittedQty * 100) / 100;
                    const roundedApproved =
                      Math.round(approvedQty * 100) / 100;
                    const bothZero =
                      roundedSubmitted === 0 && roundedApproved === 0;
                    const qtyMismatch =
                      !bothZero && roundedSubmitted !== roundedApproved;

                    return (
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
                            : bothZero
                              ? "bg-gray-100"
                              : qtyMismatch
                                ? "bg-yellow-100"
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
                                      {t("concentration.updatedQty")}
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                                  {sheet.boq_item.description}
                                </p>
                                <div className="mt-2 text-xs text-gray-500">
                                  <div>
                                    {t("concentration.unit")}{" "}
                                    {sheet.boq_item.unit}
                                  </div>
                                  <div>
                                    {t("concentration.qtyLabel")}{" "}
                                    {formatNumber(
                                      sheet.boq_item.latest_contract_quantity
                                    )}
                                    {sheet.boq_item.has_contract_updates && (
                                      <span
                                        className={`text-blue-600 ${
                                          isRTL ? "mr-1" : "ml-1"
                                        }`}
                                      >
                                        ({t("concentration.updated")}{" "}
                                        {sheet.boq_item.latest_update_index})
                                      </span>
                                    )}
                                  </div>
                                  <div>
                                    {t("concentration.priceLabel")}{" "}
                                    {formatCurrency(sheet.boq_item.price)}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
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
                  <div
                    className={`flex justify-between items-start mb-4 ${
                      isRTL ? "flex-row-reverse" : ""
                    }`}
                  >
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {t("concentration.concentrationSheet")}{" "}
                        {selectedSheet.boq_item.section_number}
                      </h2>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleTrackCalculationSheets}
                        disabled={trackingCalculationSheets}
                        className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                        title={t("concentration.trackTooltip")}
                      >
                        {trackingCalculationSheets ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            <span>{t("calculationSheets.tracking")}</span>
                          </>
                        ) : (
                          <>
                            <RefreshCw className="h-4 w-4" />
                            <span>{t("calculationSheets.track")}</span>
                          </>
                        )}
                      </button>
                      <button
                        onClick={handleExportPDF}
                        disabled={exportingPDF}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
                      >
                        {exportingPDF
                          ? t("auth.exportingPdf")
                          : t("auth.exportPdf")}
                      </button>
                      <button
                        onClick={handleExportExcel}
                        disabled={exportingExcel}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      >
                        {exportingExcel
                          ? t("auth.exportingExcel")
                          : t("auth.exportExcel")}
                      </button>
                    </div>
                  </div>

                  {/* Project Information Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.projectName")}
                      </label>
                      <p className="text-gray-900">{projectInfo.projectName}</p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.contractorInCharge")}
                      </label>
                      <p className="text-gray-900">
                        {projectInfo.contractorInCharge}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-300 font-medium">
                        {t("concentration.contractNo")}
                      </label>
                      <p className="text-gray-900">{projectInfo.contractNo}</p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.developerName")}
                      </label>
                      <p className="text-gray-900">
                        {projectInfo.developerName}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.sectionNumberLabel")}
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.boq_item.section_number}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.contractQuantity")}
                      </label>
                      <p className="text-gray-900">
                        {formatNumber(
                          selectedSheet.boq_item.latest_contract_quantity
                        )}{" "}
                        {selectedSheet.boq_item.unit}
                        {selectedSheet.boq_item.has_contract_updates && (
                          <span
                            className={`text-blue-600 ${
                              isRTL ? "mr-1" : "ml-1"
                            }`}
                          >
                            ({t("concentration.updated")}{" "}
                            {selectedSheet.boq_item.latest_update_index})
                          </span>
                        )}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.unit")}
                      </label>
                      <p className="text-gray-900">
                        {selectedSheet.boq_item.unit}
                      </p>
                    </div>
                    <div>
                      <label className="block text-gray-600 font-medium">
                        {t("concentration.priceLabel")}
                      </label>
                      <p className="text-gray-900">
                        {formatCurrency(selectedSheet.boq_item.price)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-gray-600 font-medium">
                      {t("concentration.descriptionLabel")}
                    </label>
                    <p className="text-gray-900">
                      {selectedSheet.boq_item.description}
                    </p>
                  </div>

                  {/* Contract Update Information */}
                  {selectedSheet.boq_item.has_contract_updates && (
                    <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                      <div
                        className={`flex items-center justify-between ${
                          isRTL ? "flex-row-reverse" : ""
                        }`}
                      >
                        <div>
                          <label className="block text-blue-800 font-medium text-sm">
                            {t("concentration.contractQuantityUpdated")}
                          </label>
                          <p className="text-blue-700 text-sm mt-1">
                            {t("concentration.hasBeenUpdated")}
                            {selectedSheet.boq_item.latest_update_index}).
                          </p>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-blue-600">
                            {t("concentration.original")}{" "}
                            {formatNumber(
                              selectedSheet.boq_item.original_contract_quantity
                            )}{" "}
                            {selectedSheet.boq_item.unit}
                          </div>
                          <div className="text-sm font-medium text-blue-800">
                            {t("concentration.current")}{" "}
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
                  <div
                    className={`flex justify-between items-center mb-4 ${
                      isRTL ? "flex-row-reverse" : ""
                    }`}
                  >
                    <h3 className="text-lg font-medium text-gray-900">
                      {t("concentration.concentrationEntries")}
                    </h3>
                    <div
                      className={`flex items-center gap-2 ${
                        isRTL ? "flex-row-reverse" : ""
                      }`}
                    >
                      {visibleEntries.length > 0 && (
                        <button
                          type="button"
                          onClick={toggleAllBreakdownsExpanded}
                          disabled={entriesLoading || saving}
                          className="bg-gray-100 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400 disabled:opacity-50"
                          title={
                            allBreakdownsExpanded
                              ? t("submissionBreakdown.collapseAllBreakdowns")
                              : t("submissionBreakdown.expandAllBreakdowns")
                          }
                        >
                          {allBreakdownsExpanded
                            ? t("submissionBreakdown.collapseAllBreakdowns")
                            : t("submissionBreakdown.expandAllBreakdowns")}
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setEditingEntry(null);
                          setEditDraft(null);
                          setShowAddForm(true);
                        }}
                        disabled={saving}
                        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                      >
                        {t("auth.addEntry")}
                      </button>
                    </div>
                  </div>

                  {/* Add new entry form (edit is inline in the table) */}
                  {showAddForm && (
                    <div className="mb-6 p-4 border border-gray-200 rounded-md bg-gray-50">
                      <h4 className="text-md font-medium text-gray-900 mb-4">
                        {t("auth.addNewEntry")}
                      </h4>
                      <EntryForm
                        key="add-entry"
                        entry={null}
                        boqItem={selectedSheet.boq_item}
                        onSave={createEntry}
                        onCancel={() => setShowAddForm(false)}
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
                              <th className="px-2 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-10">
                                <span className="sr-only">
                                  {t("submissionBreakdown.toggleDetails")}
                                </span>
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.descriptionLabel")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.calcSheetNo")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.drawingNoLabel")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.invoiceDescriptionLabel")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.drawings")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.estQuantity")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.submissionPercentage")}
                              </th>
                              <th
                                className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider"
                                title={t(
                                  "submissionBreakdown.currentMonthHint"
                                )}
                              >
                                {t("concentration.qtySubmitted")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.internalQty")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.approvedQty")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("boq.notes")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.supervisorNotes")}
                              </th>
                              <th className="px-3 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {t("concentration.actions")}
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {visibleEntries.length === 0 ? (
                              <tr>
                                <td
                                  colSpan={14}
                                  className={`px-3 py-8 text-gray-500 ${
                                    isRTL ? "text-right" : "text-center"
                                  }`}
                                >
                                  <p>{t("concentration.noEntriesFound")}</p>
                                  <p className="text-sm mt-1">
                                    {t("concentration.addEntriesToSheet")}
                                  </p>
                                </td>
                              </tr>
                            ) : (
                              visibleEntries.map((entry) => {
                                const isEditingRow =
                                  editingEntry !== null &&
                                  editDraft !== null &&
                                  editingEntry.id === entry.id;
                                const manualEditable =
                                  isEditingRow && editDraft.is_manual;

                                const isBreakdownExpanded =
                                  expandedBreakdownEntryIds.has(entry.id);
                                const currentFields = getCurrentPeriodFields(entry);
                                const currentPeriod = resolveCurrentPeriod(
                                  entry,
                                  entry.submission_breakdown
                                );
                                const currentDrawingKey = `${entry.id}:${
                                  currentPeriod || "current"
                                }`;

                                return (
                                  <React.Fragment key={entry.id}>
                                    {isBreakdownExpanded && (
                                      <ConcentrationBreakdownPastRows
                                        entry={entry}
                                        columnCount={14}
                                        isRTL={isRTL}
                                        saving={saving}
                                        periodEdit={periodEdit}
                                        uploadingDrawingKey={uploadingDrawingKey}
                                        expandedDrawingKeys={expandedDrawingKeys}
                                        onStartPeriodEdit={startPeriodEditing}
                                        onPeriodDraftChange={(draft) =>
                                          setPeriodEdit((current) =>
                                            current
                                              ? { ...current, draft }
                                              : null
                                          )
                                        }
                                        onSavePeriodEdit={() =>
                                          void savePeriodEdit()
                                        }
                                        onCancelPeriodEdit={cancelPeriodEdit}
                                        onAttachDrawing={triggerAttachDrawings}
                                        onOpenDrawing={handleOpenDrawingFile}
                                        onRemoveDrawing={handleRemoveDrawingFile}
                                        onRemoveAllDrawings={
                                          handleRemoveAllDrawingFiles
                                        }
                                        onToggleDrawingExpanded={
                                          toggleDrawingFilesExpanded
                                        }
                                        deletingAllDrawingKey={
                                          deletingAllDrawingKey
                                        }
                                        drawingFileName={drawingFileName}
                                      />
                                    )}
                                    <tr
                                      onDoubleClick={(e) =>
                                        handleRowDoubleClick(entry, e)
                                      }
                                      title={t(
                                        "concentration.doubleClickToEdit"
                                      )}
                                      className={`table-row-hover ${
                                        isEditingRow ? "bg-blue-50/80" : ""
                                      }`}
                                    >
                                      <td className="px-2 py-2 whitespace-nowrap align-top">
                                        <SubmissionBreakdownToggle
                                          expanded={isBreakdownExpanded}
                                          onToggle={() =>
                                            toggleBreakdownExpanded(entry.id)
                                          }
                                        />
                                      </td>
                                      <td className="px-3 py-2 text-sm text-gray-900 max-w-[14rem] align-top">
                                        {manualEditable ? (
                                          <input
                                            type="text"
                                            value={editDraft.description}
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      description:
                                                        e.target.value,
                                                    }
                                                  : null
                                              )
                                            }
                                            className="w-full min-w-0 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={saving}
                                          />
                                        ) : (
                                          <div
                                            className="truncate py-1"
                                            title={entry.description || ""}
                                          >
                                            {entry.description || "-"}
                                          </div>
                                        )}
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top min-w-[7rem]">
                                        {manualEditable ? (
                                          <div className="flex items-start gap-1">
                                            <input
                                              type="text"
                                              value={
                                                editDraft.calculation_sheet_no
                                              }
                                              onChange={(e) =>
                                                setEditDraft((d) =>
                                                  d
                                                    ? {
                                                        ...d,
                                                        calculation_sheet_no:
                                                          e.target.value,
                                                      }
                                                    : null
                                                )
                                              }
                                              className="min-w-0 flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                              disabled={saving}
                                            />
                                            {editDraft.calculation_sheet_no ? (
                                              <button
                                                type="button"
                                                onClick={() =>
                                                  handleOpenCalculationSheet(
                                                    editDraft.calculation_sheet_no
                                                  )
                                                }
                                                onDoubleClick={(e) =>
                                                  e.stopPropagation()
                                                }
                                                className="shrink-0 p-1 text-blue-600 hover:text-blue-800 rounded"
                                                title="Open calculation sheet file"
                                                aria-label="Open calculation sheet file"
                                              >
                                                <ExternalLink className="h-4 w-4" />
                                              </button>
                                            ) : null}
                                          </div>
                                        ) : entry.calculation_sheet_no ? (
                                          <button
                                            type="button"
                                            onClick={() =>
                                              handleOpenCalculationSheet(
                                                entry.calculation_sheet_no!
                                              )
                                            }
                                            onDoubleClick={(e) =>
                                              e.stopPropagation()
                                            }
                                            className="text-blue-600 hover:text-blue-800 hover:underline"
                                            title="Open calculation sheet file"
                                          >
                                            {entry.calculation_sheet_no}
                                          </button>
                                        ) : (
                                          "-"
                                        )}
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top">
                                        {manualEditable ? (
                                          <input
                                            type="text"
                                            value={editDraft.drawing_no}
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      drawing_no:
                                                        e.target.value,
                                                    }
                                                  : null
                                              )
                                            }
                                            className="w-full min-w-[5rem] px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={saving}
                                          />
                                        ) : (
                                          entry.drawing_no || "-"
                                        )}
                                      </td>
                                      <td className="px-3 py-2 text-sm text-gray-500 align-top max-w-[14rem]">
                                        {manualEditable ? (
                                          <input
                                            type="text"
                                            value={editDraft.invoice_description}
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      invoice_description:
                                                        e.target.value,
                                                    }
                                                  : null
                                              )
                                            }
                                            className="w-full min-w-0 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={saving}
                                          />
                                        ) : (
                                          <div
                                            className="truncate py-1"
                                            title={
                                              entry.invoice_description || ""
                                            }
                                          >
                                            {entry.invoice_description || "-"}
                                          </div>
                                        )}
                                      </td>
                                      <td className="px-3 py-2 text-sm text-gray-500 align-middle min-w-[10rem] max-w-[14rem]">
                                        <ConcentrationDrawingFilesCell
                                          drawingFiles={getPeriodDrawingFiles(
                                            entry,
                                            currentPeriod
                                          )}
                                          isRTL={isRTL}
                                          isUploading={
                                            uploadingDrawingKey ===
                                            currentDrawingKey
                                          }
                                          isExpanded={
                                            expandedDrawingKeys.has(
                                              currentDrawingKey
                                            ) &&
                                            getPeriodDrawingFiles(
                                              entry,
                                              currentPeriod
                                            ).length > 1
                                          }
                                          onAttach={() =>
                                            triggerAttachDrawings(
                                              entry.id,
                                              currentPeriod || undefined
                                            )
                                          }
                                          onOpen={(path) =>
                                            handleOpenDrawingFile(
                                              entry.id,
                                              path
                                            )
                                          }
                                          onRemove={(path) =>
                                            handleRemoveDrawingFile(
                                              entry.id,
                                              path,
                                              currentPeriod || undefined
                                            )
                                          }
                                          onRemoveAll={() =>
                                            handleRemoveAllDrawingFiles(
                                              entry.id,
                                              currentPeriod || undefined
                                            )
                                          }
                                          isDeletingAll={
                                            deletingAllDrawingKey ===
                                            currentDrawingKey
                                          }
                                          onToggleExpanded={() =>
                                            toggleDrawingFilesExpanded(
                                              currentDrawingKey
                                            )
                                          }
                                          drawingFileName={drawingFileName}
                                        />
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top">
                                        {manualEditable ? (
                                          <input
                                            type="number"
                                            step="0.01"
                                            value={editDraft.estimated_quantity}
                                            onChange={(e) => {
                                              const estimated =
                                                parseFloat(e.target.value) || 0;
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      estimated_quantity:
                                                        estimated,
                                                      quantity_submitted:
                                                        computeQuantitySubmitted(
                                                          estimated,
                                                          d.submission_percentage
                                                        ),
                                                    }
                                                  : null
                                              );
                                            }}
                                            className="w-full max-w-[7rem] px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={saving}
                                          />
                                        ) : (
                                          formatNumber(entry.estimated_quantity)
                                        )}
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top">
                                        {isEditingRow ? (
                                          <div className="flex items-center gap-1">
                                            <input
                                              type="number"
                                              step="0.1"
                                              min="0"
                                              max="100"
                                              value={
                                                editDraft.submission_percentage
                                              }
                                              onChange={(e) => {
                                                const percentage = Math.min(
                                                  100,
                                                  Math.max(
                                                    0,
                                                    parseFloat(
                                                      e.target.value
                                                    ) || 0
                                                  )
                                                );
                                                setEditDraft((d) =>
                                                  d
                                                    ? {
                                                        ...d,
                                                        submission_percentage:
                                                          percentage,
                                                        quantity_submitted:
                                                          computeQuantitySubmitted(
                                                            d.estimated_quantity,
                                                            percentage
                                                          ),
                                                      }
                                                    : null
                                                );
                                              }}
                                              className="w-full max-w-[5rem] px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                              disabled={saving}
                                            />
                                            <span>%</span>
                                          </div>
                                        ) : (
                                          `${formatNumber(
                                            currentFields.submission_percentage
                                          )}%`
                                        )}
                                      </td>
                                      <td
                                        className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top"
                                        title={t(
                                          "submissionBreakdown.currentMonthHint"
                                        )}
                                      >
                                        {formatNumber(
                                          isEditingRow
                                            ? editDraft.quantity_submitted
                                            : entry.quantity_submitted
                                        )}
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top">
                                        {isEditingRow ? (
                                          <input
                                            type="number"
                                            step="0.01"
                                            value={editDraft.internal_quantity}
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      internal_quantity:
                                                        parseFloat(
                                                          e.target.value
                                                        ) || 0,
                                                    }
                                                  : null
                                              )
                                            }
                                            className="w-full max-w-[7rem] px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={saving}
                                          />
                                        ) : (
                                          formatNumber(currentFields.internal_quantity)
                                        )}
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top">
                                        {isEditingRow ? (
                                          <input
                                            type="number"
                                            step="0.01"
                                            value={
                                              editDraft.approved_by_project_manager
                                            }
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      approved_by_project_manager:
                                                        parseFloat(
                                                          e.target.value
                                                        ) || 0,
                                                    }
                                                  : null
                                              )
                                            }
                                            className="w-full max-w-[7rem] px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={saving}
                                          />
                                        ) : (
                                          formatNumber(
                                            currentFields.approved_by_project_manager
                                          )
                                        )}
                                      </td>
                                      <td className="px-3 py-2 text-sm text-gray-500 max-w-[10rem] align-top">
                                        {isEditingRow ? (
                                          <textarea
                                            value={editDraft.notes}
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      notes: e.target.value,
                                                    }
                                                  : null
                                              )
                                            }
                                            rows={2}
                                            className="w-full min-w-0 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                                            disabled={saving}
                                          />
                                        ) : (
                                          <div
                                            className="truncate py-1"
                                            title={currentFields.notes || ""}
                                          >
                                            {currentFields.notes || "-"}
                                          </div>
                                        )}
                                      </td>
                                      <td className="px-3 py-2 text-sm text-gray-500 max-w-[10rem] align-top">
                                        {isEditingRow ? (
                                          <textarea
                                            value={editDraft.supervisor_notes}
                                            onChange={(e) =>
                                              setEditDraft((d) =>
                                                d
                                                  ? {
                                                      ...d,
                                                      supervisor_notes:
                                                        e.target.value,
                                                    }
                                                  : null
                                              )
                                            }
                                            rows={2}
                                            className="w-full min-w-0 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                                            disabled={saving}
                                          />
                                        ) : (
                                          <div
                                            className="truncate py-1"
                                            title={currentFields.supervisor_notes || ""}
                                          >
                                            {currentFields.supervisor_notes || "-"}
                                          </div>
                                        )}
                                      </td>
                                      <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500 align-top">
                                        {isEditingRow ? (
                                          <div
                                            className={`flex flex-wrap gap-2 ${
                                              isRTL ? "flex-row-reverse" : ""
                                            }`}
                                          >
                                            <button
                                              type="button"
                                              onClick={() => saveInlineEdit()}
                                              disabled={saving}
                                              className="text-blue-700 font-medium hover:text-blue-900 disabled:opacity-50"
                                            >
                                              {saving
                                                ? t("boq.saving")
                                                : t("common.update")}
                                            </button>
                                            <button
                                              type="button"
                                              onClick={cancelInlineEdit}
                                              disabled={saving}
                                              className="text-gray-600 hover:text-gray-800 disabled:opacity-50"
                                            >
                                              {t("common.cancel")}
                                            </button>
                                          </div>
                                        ) : entry.is_manual ? (
                                          <div
                                            className={`flex flex-wrap gap-2 ${
                                              isRTL ? "flex-row-reverse" : ""
                                            }`}
                                          >
                                            <button
                                              type="button"
                                              onClick={() =>
                                                startEditing(entry)
                                              }
                                              disabled={
                                                saving || populateSubmitting
                                              }
                                              className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                            >
                                              {t("common.edit")}
                                            </button>
                                            <button
                                              type="button"
                                              onClick={() =>
                                                openPopulateModal(entry)
                                              }
                                              disabled={
                                                saving ||
                                                populateSubmitting ||
                                                populateListLoading ||
                                                populateEntrySource !== null
                                              }
                                              className="text-emerald-700 hover:text-emerald-900 disabled:opacity-50"
                                            >
                                              {t("concentration.populate")}
                                            </button>
                                            <button
                                              type="button"
                                              onClick={() =>
                                                deleteEntry(entry.id)
                                              }
                                              disabled={
                                                saving || populateSubmitting
                                              }
                                              className="text-red-600 hover:text-red-800 disabled:opacity-50"
                                            >
                                              {t("common.delete")}
                                            </button>
                                          </div>
                                        ) : (
                                          <button
                                            type="button"
                                            onClick={() => startEditing(entry)}
                                            disabled={saving}
                                            className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                          >
                                            {t("common.edit")}
                                          </button>
                                        )}
                                      </td>
                                    </tr>
                                    {isBreakdownExpanded && (
                                      <ConcentrationBreakdownTotalRow
                                        entry={entry}
                                        columnCount={14}
                                      />
                                    )}
                                  </React.Fragment>
                                );
                              })
                            )}

                            {/* Totals Row */}
                            {visibleEntries.length > 0 && (
                              <tr className="bg-gray-50 border-t-2 border-gray-300">
                                <td className="px-2 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {t("concentration.totals")}
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    visibleEntries.reduce(
                                      (sum, entry) =>
                                        sum + entry.estimated_quantity,
                                      0
                                    )
                                  )}
                                </td>
                                <td className="px-3 py-3 text-sm text-gray-500">
                                  -
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(visibleEntriesSubmittedTotal)}
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    visibleEntries.reduce(
                                      (sum, entry) =>
                                        sum + entryTotalInternalQuantity(entry),
                                      0
                                    )
                                  )}
                                </td>
                                <td className="px-3 py-3 text-sm font-bold text-gray-900">
                                  {formatNumber(
                                    visibleEntries.reduce(
                                      (sum, entry) =>
                                        sum +
                                        entryTotalApprovedQuantity(entry),
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
            ) : null}
          </div>
        </div>
      </div>

      {/* Concentration Entry Column Selection Modal */}
      <ConcentrationEntryExportModal
        isOpen={showEntryColumnModal}
        onClose={() => {
          setShowEntryColumnModal(false);
          setPendingExportAction(null);
        }}
        onExport={handleExportModalSubmit}
        title={pendingExportAction?.title || t("concentration.selectColumns")}
        loading={
          exportingPDF || exportingExcel || exportingAllPDF || exportingAllExcel
        }
        exportFormat={pendingExportAction?.format || "pdf"}
        exportScope={pendingExportAction?.type}
      />

      <PopulateConcentrationEntryModal
        isOpen={populateEntrySource !== null}
        onClose={() => {
          if (!populateSubmitting) setPopulateEntrySource(null);
        }}
        onConfirm={handlePopulateConfirm}
        boqItems={populateBoqItems}
        currentBoqItemId={selectedSheet?.boq_item_id ?? 0}
        listLoading={populateListLoading}
        submitLoading={populateSubmitting}
      />
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
  const { t } = useTranslation();
  const fieldsLockedForAuto = !!entry && !entry.is_manual;
  const [formData, setFormData] = useState({
    section_number: entry?.section_number || boqItem?.section_number || "",
    description: entry?.description || "",
    calculation_sheet_no: entry?.calculation_sheet_no || "",
    drawing_no: entry?.drawing_no || "",
    invoice_description: entry?.invoice_description || "",
    estimated_quantity: entry?.estimated_quantity || 0,
    submission_percentage: entry?.submission_percentage ?? 100,
    quantity_submitted: computeQuantitySubmitted(
      entry?.estimated_quantity || 0,
      entry?.submission_percentage ?? 100
    ),
    internal_quantity: entry?.internal_quantity || 0,
    approved_by_project_manager: entry?.approved_by_project_manager || 0,
    notes: entry?.notes || "",
    supervisor_notes: entry?.supervisor_notes || "",
    is_manual: entry?.is_manual ?? true, // Default to true for manual entries
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => {
      const next = {
        ...prev,
        [field]: value,
      };
      if (field === "estimated_quantity" || field === "submission_percentage") {
        next.quantity_submitted = computeQuantitySubmitted(
          field === "estimated_quantity" ? value : prev.estimated_quantity,
          field === "submission_percentage" ? value : prev.submission_percentage
        );
      }
      return next;
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("boq.description")}
          </label>
          <input
            type="text"
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || fieldsLockedForAuto}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("auth.calculationSheetNo")}
          </label>
          <input
            type="text"
            value={formData.calculation_sheet_no}
            onChange={(e) =>
              handleChange("calculation_sheet_no", e.target.value)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || fieldsLockedForAuto}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("auth.drawingNo")}
          </label>
          <input
            type="text"
            value={formData.drawing_no}
            onChange={(e) => handleChange("drawing_no", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || fieldsLockedForAuto}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("concentration.invoiceDescription")}
          </label>
          <input
            type="text"
            value={formData.invoice_description}
            onChange={(e) =>
              handleChange("invoice_description", e.target.value)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving || fieldsLockedForAuto}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("auth.estimatedQuantity")}
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
            disabled={saving || fieldsLockedForAuto}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("concentration.submissionPercentage")}
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={formData.submission_percentage}
              onChange={(e) =>
                handleChange(
                  "submission_percentage",
                  Math.min(100, Math.max(0, parseFloat(e.target.value) || 0))
                )
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={saving}
            />
            <span className="text-sm text-gray-500">%</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("auth.quantitySubmitted")}
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.quantity_submitted}
            readOnly
            className="w-full px-3 py-2 border border-gray-200 rounded-md bg-gray-50 text-gray-700"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("auth.internalQuantity")}
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.internal_quantity}
            onChange={(e) =>
              handleChange("internal_quantity", parseFloat(e.target.value) || 0)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("auth.approvedQuantity")}
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
            disabled={saving}
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("boq.notes")}
          </label>
          <textarea
            value={formData.notes}
            onChange={(e) => handleChange("notes", e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={saving}
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t("concentration.supervisorNotes")}
          </label>
          <textarea
            value={formData.supervisor_notes}
            onChange={(e) => handleChange("supervisor_notes", e.target.value)}
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
          {t("common.cancel")}
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {saving
            ? t("boq.saving")
            : entry
            ? t("common.update")
            : t("common.create")}
        </button>
      </div>
    </form>
  );
};

export default ConcentrationSheets;
