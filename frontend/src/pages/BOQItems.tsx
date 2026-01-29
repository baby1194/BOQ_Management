import React, { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";
import {
  boqApi,
  searchApi,
  importApi,
  projectInfoApi,
  contractUpdatesApi,
  exportApi,
  authApi,
} from "../services/api";
import toast from "react-hot-toast";
import {
  BOQItem,
  ProjectInfo,
  ProjectInfoUpdate,
  ContractQuantityUpdate,
  BOQItemQuantityUpdate,
} from "../types";
import { formatCurrency, formatNumber } from "../utils/format";
import BOQExportModal from "../components/BOQExportModal";
import FilterDropdown from "../components/FilterDropdown";

/**
 * Format date as mm/yyyy
 */
const formatDateMMYYYY = (dateString: string): string => {
  if (!dateString) return "";
  const date = new Date(dateString);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${month}/${year}`;
};

const formatDateToMonth = (dateString: string): string => {
  if (!dateString) return "";
  const date = new Date(dateString);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${year}-${month}`;
};

const BOQItems: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const { isRTL } = useLanguage();
  const [items, setItems] = useState<BOQItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Initialize state from localStorage using lazy initialization
  const [searchQuery, setSearchQuery] = useState(() => {
    const saved = localStorage.getItem("boq-search-query");
    return saved !== null ? saved : "";
  });
  const [selectedSubchapter, setSelectedSubchapter] = useState<string>(() => {
    const saved = localStorage.getItem("boq-selected-subchapter");
    return saved !== null ? saved : "";
  });
  const [subchapters, setSubchapters] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingValues, setEditingValues] = useState<Partial<BOQItem>>({});
  const [savingId, setSavingId] = useState<number | null>(null);
  const [navigatingToSheet, setNavigatingToSheet] = useState<number | null>(
    null,
  );
  const [deletingId, setDeletingId] = useState<number | null>(null);
  /** Selected row in BOQ main table – stays highlighted after click (like Concentration Sheets sidebar). Persisted so it survives navigation. */
  const [selectedBoqRowId, setSelectedBoqRowId] = useState<number | null>(
    () => {
      const saved = localStorage.getItem("boq-selected-row-id");
      if (saved === null) return null;
      const n = parseInt(saved, 10);
      return Number.isNaN(n) ? null : n;
    },
  );

  // Panel collapse state - initialize from localStorage
  const [panelsCollapsed, setPanelsCollapsed] = useState(() => {
    const saved = localStorage.getItem("boq-panels-collapsed");
    if (saved !== null) {
      try {
        return JSON.parse(saved);
      } catch {
        return false;
      }
    }
    return false;
  });

  // Project Info state
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [editingProjectInfo, setEditingProjectInfo] = useState(false);
  const [projectInfoDraft, setProjectInfoDraft] = useState<ProjectInfoUpdate>(
    {},
  );
  const [savingProjectInfo, setSavingProjectInfo] = useState(false);
  const [projectInfoError, setProjectInfoError] = useState<string | null>(null);
  const [projectInfoSuccess, setProjectInfoSuccess] = useState<string | null>(
    null,
  );

  // Comprehensive filter system
  const [filters, setFilters] = useState(() => {
    const defaultFilters = {
      // String filters (contains)
      serial_number: "",
      structure: "",
      system: "",
      section_number: "",
      description: "",
      unit: "",
      subsection: "",
      notes: "",
      internal_field_1: "",
      internal_field_2: "",

      // Numeric filters (>, <, =, >=, <=)
      original_contract_quantity: "",
      price: "",
      total_contract_sum: "",
      estimated_quantity: "",
      quantity_submitted: "",
      internal_quantity: "",
      approved_by_project_manager: "",
      total_estimate: "",
      total_submitted: "",
      internal_total: "",
      total_approved_by_project_manager: "",
      approved_signed_quantity: "",
      approved_signed_total: "",
      total_decrease: "",
      total_increase: "",
      quantity_decrease: "",
      quantity_increase: "",

      // Contract update filters - will be populated dynamically
      contract_updates: {} as Record<number, { quantity: string; sum: string }>,
    };

    const saved = localStorage.getItem("boq-filters");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { ...defaultFilters, ...parsed };
      } catch {
        return defaultFilters;
      }
    }
    return defaultFilters;
  });

  // Dropdown filter states for Structure, System, and Unit columns
  const [dropdownFilters, setDropdownFilters] = useState(() => {
    const defaultFilters = {
      structure: [] as string[],
      system: [] as string[],
      unit: [] as string[],
    };

    const saved = localStorage.getItem("boq-dropdown-filters");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { ...defaultFilters, ...parsed };
      } catch {
        return defaultFilters;
      }
    }
    return defaultFilters;
  });

  // Dropdown open/close states
  const [dropdownOpen, setDropdownOpen] = useState({
    structure: false,
    system: false,
    unit: false,
  });

  // Column visibility state - initialize from localStorage
  const [columnVisibility, setColumnVisibility] = useState(() => {
    const defaultVisibility = {
      serial_number: true,
      structure: true,
      system: true,
      section_number: true,
      description: true,
      unit: true,
      original_contract_quantity: true,
      price: true,
      total_contract_sum: true,
      estimated_quantity: true,
      quantity_submitted: true,
      internal_quantity: true,
      approved_by_project_manager: true,
      approved_signed_quantity: true,
      quantity_decrease: true,
      quantity_increase: true,
      total_estimate: true,
      total_submitted: true,
      internal_total: true,
      total_approved_by_project_manager: true,
      approved_signed_total: true,
      total_decrease: true,
      total_increase: true,
      subsection: true,
      notes: true,
      internal_field_1: true,
      internal_field_2: true,
      actions: true,
    };

    const saved = localStorage.getItem("boq-column-visibility");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { ...defaultVisibility, ...parsed };
      } catch {
        return defaultVisibility;
      }
    }
    return defaultVisibility;
  });

  // Column visibility settings modal state
  const [showColumnSettings, setShowColumnSettings] = useState(false);

  // Ref for the scrollable table container
  const tableScrollContainerRef = useRef<HTMLDivElement>(null);
  // Flag to track if scroll position has been restored (only restore once per page load)
  const scrollPositionRestoredRef = useRef(false);

  // Save all display settings to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(
      "boq-column-visibility",
      JSON.stringify(columnVisibility),
    );
  }, [columnVisibility]);

  useEffect(() => {
    localStorage.setItem(
      "boq-panels-collapsed",
      JSON.stringify(panelsCollapsed),
    );
  }, [panelsCollapsed]);

  useEffect(() => {
    const { contract_updates, ...staticFilters } = filters;
    localStorage.setItem("boq-filters", JSON.stringify(staticFilters));
  }, [filters]);

  useEffect(() => {
    localStorage.setItem(
      "boq-dropdown-filters",
      JSON.stringify(dropdownFilters),
    );
  }, [dropdownFilters]);

  useEffect(() => {
    localStorage.setItem("boq-search-query", searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    localStorage.setItem("boq-selected-subchapter", selectedSubchapter);
  }, [selectedSubchapter]);

  useEffect(() => {
    if (selectedBoqRowId === null) {
      localStorage.removeItem("boq-selected-row-id");
    } else {
      localStorage.setItem("boq-selected-row-id", String(selectedBoqRowId));
    }
  }, [selectedBoqRowId]);

  // Clear selection if the saved row id is no longer in the list (e.g. item deleted or data changed)
  useEffect(() => {
    if (
      selectedBoqRowId !== null &&
      items.length > 0 &&
      !items.some((item) => item.id === selectedBoqRowId)
    ) {
      setSelectedBoqRowId(null);
    }
  }, [items, selectedBoqRowId]);

  // Column visibility functions
  const toggleColumnVisibility = (columnKey: keyof typeof columnVisibility) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [columnKey]: !prev[columnKey],
    }));
  };

  const resetColumnVisibility = () => {
    const baseVisibility = {
      serial_number: true,
      structure: true,
      system: true,
      section_number: true,
      description: true,
      unit: true,
      original_contract_quantity: true,
      price: true,
      total_contract_sum: true,
      estimated_quantity: true,
      quantity_submitted: true,
      internal_quantity: true,
      approved_by_project_manager: true,
      approved_signed_quantity: true,
      quantity_decrease: true,
      quantity_increase: true,
      total_estimate: true,
      total_submitted: true,
      internal_total: true,
      total_approved_by_project_manager: true,
      approved_signed_total: true,
      total_decrease: true,
      total_increase: true,
      subsection: true,
      notes: true,
      internal_field_1: true,
      internal_field_2: true,
      actions: true,
    };

    // Add contract update columns to reset
    contractUpdates.forEach((update) => {
      baseVisibility[`updated_contract_quantity_${update.id}`] = true;
      baseVisibility[`updated_contract_sum_${update.id}`] = true;
    });

    setColumnVisibility(baseVisibility);
  };

  const [allItems, setAllItems] = useState<BOQItem[]>([]);

  // Contract Updates state
  const [contractUpdates, setContractUpdates] = useState<
    ContractQuantityUpdate[]
  >([]);
  const [boqItemUpdates, setBoqItemUpdates] = useState<BOQItemQuantityUpdate[]>(
    [],
  );
  const [creatingUpdate, setCreatingUpdate] = useState(false);

  // Update columnVisibility when contractUpdates change
  useEffect(() => {
    if (contractUpdates.length > 0) {
      setColumnVisibility((prev) => {
        const newVisibility = { ...prev };

        contractUpdates.forEach((update) => {
          const qtyKey = `updated_contract_quantity_${update.id}`;
          const sumKey = `updated_contract_sum_${update.id}`;

          // Only add if not already present
          if (!(qtyKey in newVisibility)) {
            newVisibility[qtyKey] = true;
          }
          if (!(sumKey in newVisibility)) {
            newVisibility[sumKey] = true;
          }
        });

        return newVisibility;
      });
    }
  }, [contractUpdates]);

  // Manual BOQ Item Creation state
  const [showAddForm, setShowAddForm] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [passwordInput, setPasswordInput] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordAction, setPasswordAction] = useState<
    "create" | "update" | "delete"
  >("create");

  // Export state
  const [showExportModal, setShowExportModal] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [passwordItemId, setPasswordItemId] = useState<number | null>(null);
  const [passwordContractUpdateId, setPasswordContractUpdateId] = useState<
    number | null
  >(null);
  const [newItemForm, setNewItemForm] = useState({
    section_number: "",
    description: "",
    unit: "",
    original_contract_quantity: 0,
    price: 0,
    system: "",
    structure: 0,
  });
  const [creatingItem, setCreatingItem] = useState(false);

  // Password confirmation functions
  const handlePasswordConfirm = async () => {
    console.log(
      "Password confirmed, action:",
      passwordAction,
      "itemId:",
      passwordItemId,
      "contractUpdateId:",
      passwordContractUpdateId,
    );

    try {
      // Verify system password with backend
      await authApi.verifySystemPassword(passwordInput);
      console.log("System password verified successfully");

      setShowPasswordDialog(false);
      setPasswordInput("");
      setPasswordError("");

      // Execute the appropriate action based on passwordAction
      switch (passwordAction) {
        case "create":
          console.log("Executing create action");
          handleCreateNewItem();
          break;
        case "update":
          console.log("Executing update action");
          if (passwordAction === "update") {
            handleCreateContractUpdate();
          }
          break;
        case "delete":
          console.log("Executing delete action");
          if (passwordContractUpdateId) {
            console.log(
              "Calling handleDeleteContractUpdateAfterPassword with:",
              passwordItemId || 0,
              passwordContractUpdateId,
            );
            handleDeleteContractUpdateAfterPassword(
              passwordItemId || 0,
              passwordContractUpdateId,
            );
          } else {
            console.error("No contractUpdateId found for delete action");
          }
          break;
      }
    } catch (error: any) {
      console.log("System password verification failed:", error);
      setPasswordError(
        error.response?.data?.detail ||
          "Incorrect system password. Please try again.",
      );
    }
  };

  const handlePasswordCancel = () => {
    setShowPasswordDialog(false);
    setPasswordInput("");
    setPasswordError("");
    setPasswordAction("create");
    setPasswordItemId(null);
    setPasswordContractUpdateId(null);
  };

  const handleCreateBOQItemClick = () => {
    setPasswordAction("create");
    setPasswordItemId(null);
    setPasswordContractUpdateId(null);
    setShowPasswordDialog(true);
  };

  const handleUpdateContractQtyClick = (item: BOQItem) => {
    setPasswordAction("update");
    setPasswordItemId(item.id);
    setPasswordContractUpdateId(null);
    setShowPasswordDialog(true);
  };

  const handleDeleteContractUpdateClick = (
    itemId: number,
    contractUpdateId: number,
  ) => {
    setPasswordAction("delete");
    setPasswordItemId(itemId);
    setPasswordContractUpdateId(contractUpdateId);
    setShowPasswordDialog(true);
  };

  const getCurrentContractQuantity = (item: BOQItem): number => {
    const latestUpdate = contractUpdates
      .map((update) => {
        const boqUpdate = boqItemUpdates.find(
          (u) =>
            u.boq_item_id === item.id && u.contract_update_id === update.id,
        );
        return boqUpdate
          ? {
              id: update.id,
              quantity: boqUpdate.updated_contract_quantity || 0,
            }
          : null;
      })
      .filter((u) => u !== null)
      .sort((a, b) => (b?.id || 0) - (a?.id || 0))[0];

    return latestUpdate?.quantity || item.original_contract_quantity || 0;
  };

  const calculateQuantityDecrease = (item: BOQItem): number => {
    const contractQty = getCurrentContractQuantity(item);
    const estimatedQty = item.estimated_quantity || 0;

    if (estimatedQty < contractQty) {
      return contractQty - estimatedQty;
    }
    return 0;
  };

  const calculateQuantityIncrease = (item: BOQItem): number => {
    const contractQty = getCurrentContractQuantity(item);
    const estimatedQty = item.estimated_quantity || 0;

    if (estimatedQty > contractQty) {
      return estimatedQty - contractQty;
    }
    return 0;
  };

  const calculateTotalDecrease = (item: BOQItem): number =>
    calculateQuantityDecrease(item) * (item.price || 0);
  const calculateTotalIncrease = (item: BOQItem): number =>
    calculateQuantityIncrease(item) * (item.price || 0);

  // Calculate totals for all items
  const totals = useMemo(() => {
    return items.reduce(
      (acc, item) => ({
        total_contract_sum:
          acc.total_contract_sum + (item.total_contract_sum || 0),
        total_estimate: acc.total_estimate + (item.total_estimate || 0),
        total_submitted: acc.total_submitted + (item.total_submitted || 0),
        internal_total: acc.internal_total + (item.internal_total || 0),
        total_approved_by_project_manager:
          acc.total_approved_by_project_manager +
          (item.total_approved_by_project_manager || 0),
        total_decrease: acc.total_decrease + calculateTotalDecrease(item),
        total_increase: acc.total_increase + calculateTotalIncrease(item),
      }),
      {
        total_contract_sum: 0,
        total_estimate: 0,
        total_submitted: 0,
        internal_total: 0,
        total_approved_by_project_manager: 0,
        total_decrease: 0,
        total_increase: 0,
      },
    );
  }, [items]);

  // Calculate derived values based on quantity and price
  const calculateDerivedValues = (item: BOQItem, updates: Partial<BOQItem>) => {
    const updatedItem = { ...item, ...updates };
    const price = updatedItem.price || 0;

    return {
      total_contract_sum: (updatedItem.original_contract_quantity || 0) * price,
      total_estimate: (updatedItem.estimated_quantity || 0) * price,
      total_submitted: (updatedItem.quantity_submitted || 0) * price,
      internal_total: (updatedItem.internal_quantity || 0) * price,
      total_approved_by_project_manager:
        (updatedItem.approved_by_project_manager || 0) * price,
      approved_signed_total:
        (updatedItem.approved_signed_quantity || 0) * price,
    };
  };

  // Helper function to parse numeric filters with operators
  const parseNumericFilter = (
    filterValue: string,
    itemValue: number,
  ): boolean => {
    if (!filterValue.trim()) return true;

    const trimmedValue = filterValue.trim();

    // Check for operators
    if (trimmedValue.startsWith(">=")) {
      const value = parseFloat(trimmedValue.substring(2));
      return !isNaN(value) && itemValue >= value;
    } else if (trimmedValue.startsWith("<=")) {
      const value = parseFloat(trimmedValue.substring(2));
      return !isNaN(value) && itemValue <= value;
    } else if (trimmedValue.startsWith(">")) {
      const value = parseFloat(trimmedValue.substring(1));
      return !isNaN(value) && itemValue > value;
    } else if (trimmedValue.startsWith("<")) {
      const value = parseFloat(trimmedValue.substring(1));
      return !isNaN(value) && itemValue < value;
    } else if (trimmedValue.startsWith("=")) {
      const value = parseFloat(trimmedValue.substring(1));
      return !isNaN(value) && itemValue === value;
    } else {
      // No operator, treat as exact match
      const value = parseFloat(trimmedValue);
      return !isNaN(value) && itemValue === value;
    }
  };

  // Apply filters to items
  const applyFilters = (items: BOQItem[]): BOQItem[] => {
    return items.filter((item) => {
      // String filters (case-insensitive contains)
      const matchesSerialNumber =
        !filters.serial_number ||
        (item.serial_number?.toString() || "")
          .toLowerCase()
          .includes(filters.serial_number.toLowerCase());

      const matchesStructure =
        (!filters.structure ||
          (item.structure?.toString() || "")
            .toLowerCase()
            .includes(filters.structure.toLowerCase())) &&
        (dropdownFilters.structure.length === 0 ||
          dropdownFilters.structure.includes(item.structure?.toString() || ""));

      const matchesSystem =
        (!filters.system ||
          (item.system?.toString() || "")
            .toLowerCase()
            .includes(filters.system.toLowerCase())) &&
        (dropdownFilters.system.length === 0 ||
          dropdownFilters.system.includes(item.system?.toString() || ""));

      const matchesSectionNumber =
        !filters.section_number ||
        item.section_number
          .toLowerCase()
          .includes(filters.section_number.toLowerCase());

      const matchesDescription =
        !filters.description ||
        item.description
          .toLowerCase()
          .includes(filters.description.toLowerCase());

      const matchesUnit =
        (!filters.unit ||
          item.unit.toLowerCase().includes(filters.unit.toLowerCase())) &&
        (dropdownFilters.unit.length === 0 ||
          dropdownFilters.unit.includes(item.unit));

      const matchesSubsection =
        !filters.subsection ||
        (item.subsection || "")
          .toLowerCase()
          .includes(filters.subsection.toLowerCase());

      const matchesNotes =
        !filters.notes ||
        (item.notes || "").toLowerCase().includes(filters.notes.toLowerCase());

      const matchesInternalField1 =
        !filters.internal_field_1 ||
        (item.internal_field_1 || "")
          .toLowerCase()
          .includes(filters.internal_field_1.toLowerCase());

      const matchesInternalField2 =
        !filters.internal_field_2 ||
        (item.internal_field_2 || "")
          .toLowerCase()
          .includes(filters.internal_field_2.toLowerCase());

      // Numeric filters
      const matchesOriginalContractQuantity = parseNumericFilter(
        filters.original_contract_quantity,
        item.original_contract_quantity || 0,
      );

      const matchesPrice = parseNumericFilter(filters.price, item.price || 0);

      const matchesTotalContractSum = parseNumericFilter(
        filters.total_contract_sum,
        item.total_contract_sum || 0,
      );

      const matchesEstimatedQuantity = parseNumericFilter(
        filters.estimated_quantity,
        item.estimated_quantity || 0,
      );

      const matchesQuantitySubmitted = parseNumericFilter(
        filters.quantity_submitted,
        item.quantity_submitted || 0,
      );

      const matchesInternalQuantity = parseNumericFilter(
        filters.internal_quantity,
        item.internal_quantity || 0,
      );

      const matchesApprovedByProjectManager = parseNumericFilter(
        filters.approved_by_project_manager,
        item.approved_by_project_manager || 0,
      );

      const matchesTotalEstimate = parseNumericFilter(
        filters.total_estimate,
        item.total_estimate || 0,
      );

      const matchesTotalSubmitted = parseNumericFilter(
        filters.total_submitted,
        item.total_submitted || 0,
      );

      const matchesInternalTotal = parseNumericFilter(
        filters.internal_total,
        item.internal_total || 0,
      );

      const matchesTotalApprovedByProjectManager = parseNumericFilter(
        filters.total_approved_by_project_manager,
        item.total_approved_by_project_manager || 0,
      );

      const quantityDecrease = calculateQuantityDecrease(item);
      const matchesQuantityDecrease = parseNumericFilter(
        filters.quantity_decrease,
        quantityDecrease,
      );

      const quantityIncrease = calculateQuantityIncrease(item);
      const matchesQuantityIncrease = parseNumericFilter(
        filters.quantity_increase,
        quantityIncrease,
      );

      const totalDecrease = calculateTotalDecrease(item);
      const matchesTotalDecrease = parseNumericFilter(
        filters.total_decrease,
        totalDecrease,
      );
      const totalIncrease = calculateTotalIncrease(item);
      const matchesTotalIncrease = parseNumericFilter(
        filters.total_increase,
        totalIncrease,
      );

      // Contract update filters
      // console.log(Object.entries(filters.contract_updates || {}));
      const matchesContractUpdates = Object.entries(
        filters.contract_updates || {},
      ).every(([updateId, update]) => {
        // Type assertion for contract update filter structure
        const updateFilter = update as { quantity: string; sum: string };

        // console.log("updateId", updateId);
        // console.log("update", update);
        // console.log("!update", !update);
        // console.log("typeof update", typeof update);
        // console.log("!update.quantity", !update.quantity);
        // console.log("!update.sum", !update.sum);
        // Safety check: ensure update object exists and has expected structure
        if (
          !updateFilter ||
          typeof updateFilter !== "object" ||
          (updateFilter.quantity.trim() === "" &&
            updateFilter.sum.trim() === "")
        ) {
          return true; // Skip invalid filter entries
        }

        // console.log("OKKKKKKKKKKKK");

        // If no filter values, skip this filter
        if (!updateFilter.quantity.trim() && !updateFilter.sum.trim()) {
          return true;
        }
        // console.log("_________________");
        // Find the update for this specific BOQ item and contract update
        const currentUpdate = boqItemUpdates.find(
          (u) =>
            u.boq_item_id === item.id &&
            u.contract_update_id === parseInt(updateId),
        );

        // Debug logging
        // console.log(
        //   `Filtering BOQ item ${item.id} for contract update ${updateId}:`,
        //   {
        //     itemId: item.id,
        //     updateId: parseInt(updateId),
        //     filterValues: updateFilter,
        //     foundUpdate: currentUpdate,
        //     allUpdates: boqItemUpdates.length,
        //   }
        // );

        // If no update data exists for this item, it doesn't match
        if (!currentUpdate) {
          // console.log(
          //   `No update data found for BOQ item ${item.id} and contract update ${updateId}`
          // );
          return false;
        }

        // Check quantity filter
        const matchesQuantity =
          !updateFilter.quantity.trim() ||
          parseNumericFilter(
            updateFilter.quantity,
            currentUpdate.updated_contract_quantity || 0,
          );

        // Check sum filter
        const matchesSum =
          !updateFilter.sum.trim() ||
          parseNumericFilter(
            updateFilter.sum,
            currentUpdate.updated_contract_sum || 0,
          );

        // console.log(`Filter results for BOQ item ${item.id}:`, {
        //   quantityFilter: update.quantity,
        //   quantityValue: currentUpdate.updated_contract_quantity,
        //   matchesQuantity,
        //   sumFilter: update.sum,
        //   sumValue: currentUpdate.updated_contract_sum,
        //   matchesSum,
        // });

        return matchesQuantity && matchesSum;
      });

      return (
        matchesSerialNumber &&
        matchesStructure &&
        matchesSystem &&
        matchesSectionNumber &&
        matchesDescription &&
        matchesUnit &&
        matchesSubsection &&
        matchesNotes &&
        matchesInternalField1 &&
        matchesInternalField2 &&
        matchesOriginalContractQuantity &&
        matchesPrice &&
        matchesTotalContractSum &&
        matchesEstimatedQuantity &&
        matchesQuantitySubmitted &&
        matchesInternalQuantity &&
        matchesApprovedByProjectManager &&
        matchesTotalEstimate &&
        matchesTotalSubmitted &&
        matchesInternalTotal &&
        matchesTotalApprovedByProjectManager &&
        matchesQuantityDecrease &&
        matchesQuantityIncrease &&
        matchesTotalDecrease &&
        matchesTotalIncrease &&
        matchesContractUpdates
      );
    });
  };

  // Get filtered items
  const filteredItems = useMemo(() => {
    // console.log("Applying filters:", {
    //   filters,
    //   allItemsCount: allItems.length,
    //   boqItemUpdatesCount: boqItemUpdates.length,
    //   contractUpdatesCount: contractUpdates.length,
    // });

    const filtered = applyFilters(allItems);

    // console.log("Filter results:", {
    //   originalCount: allItems.length,
    //   filteredCount: filtered.length,
    // });

    return filtered;
  }, [allItems, filters, dropdownFilters, boqItemUpdates, contractUpdates]);

  // Count active filters
  const activeFiltersCount = useMemo(() => {
    let count = 0;

    // Count string and numeric filters
    Object.entries(filters).forEach(([key, value]) => {
      if (key === "contract_updates") {
        // Count contract update filters
        const contractUpdateFilters = value as Record<
          number,
          { quantity: string; sum: string }
        >;

        // Safety check: ensure contractUpdateFilters exists and is an object
        if (
          contractUpdateFilters &&
          typeof contractUpdateFilters === "object"
        ) {
          Object.values(contractUpdateFilters).forEach((update) => {
            const updateFilter = update as { quantity: string; sum: string };
            if (
              updateFilter &&
              updateFilter.quantity &&
              updateFilter.quantity.trim() !== ""
            )
              count++;
            if (
              updateFilter &&
              updateFilter.sum &&
              updateFilter.sum.trim() !== ""
            )
              count++;
          });
        }
      } else if (typeof value === "string" && value.trim() !== "") {
        count++;
      }
    });

    // Count dropdown filters
    Object.values(dropdownFilters).forEach((selectedValues) => {
      const selectedValuesArray = selectedValues as string[];
      if (selectedValuesArray.length > 0) count++;
    });

    return count;
  }, [filters, dropdownFilters]);

  // Get unique values for dropdown filters
  const uniqueValues = useMemo(() => {
    const structureValues = [
      ...new Set(
        allItems
          .map((item) => item.structure?.toString() || "")
          .filter(Boolean),
      ),
    ].sort();
    const systemValues = [
      ...new Set(
        allItems.map((item) => item.system?.toString() || "").filter(Boolean),
      ),
    ].sort();
    const unitValues = [
      ...new Set(allItems.map((item) => item.unit || "").filter(Boolean)),
    ].sort();

    return {
      structure: structureValues,
      system: systemValues,
      unit: unitValues,
    };
  }, [allItems]);

  // Dropdown filter handlers
  const handleDropdownFilterChange = (
    column: "structure" | "system" | "unit",
    selectedValues: string[],
  ) => {
    setDropdownFilters((prev) => ({
      ...prev,
      [column]: selectedValues,
    }));
  };

  const handleClearDropdownFilter = (
    column: "structure" | "system" | "unit",
  ) => {
    setDropdownFilters((prev) => ({
      ...prev,
      [column]: [],
    }));
  };

  const handleToggleDropdown = (column: "structure" | "system" | "unit") => {
    setDropdownOpen((prev) => ({
      ...prev,
      [column]: !prev[column],
    }));
  };

  const handleCloseDropdown = (column: "structure" | "system" | "unit") => {
    setDropdownOpen((prev) => ({
      ...prev,
      [column]: false,
    }));
  };

  // Helper function to get contract update values for a BOQ item
  const getContractUpdateValue = (
    boqItemId: number,
    updateId: number,
    field: "quantity" | "sum",
  ) => {
    const update = boqItemUpdates.find(
      (update) =>
        update.boq_item_id === boqItemId &&
        update.contract_update_id === updateId,
    );

    if (field === "quantity") {
      return update?.updated_contract_quantity || 0;
    } else {
      return update?.updated_contract_sum || 0;
    }
  };

  // Get filter input CSS class based on whether it has a value
  const getFilterInputClass = (field: keyof typeof filters) => {
    const baseClass =
      "w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm";

    let hasValue = false;
    if (field === "contract_updates") {
      // For contract updates, check if any have values
      const contractUpdateFilters = filters[field] as Record<
        number,
        { quantity: string; sum: string }
      >;

      // Safety check: ensure contractUpdateFilters exists and is an object
      if (contractUpdateFilters && typeof contractUpdateFilters === "object") {
        hasValue = Object.values(contractUpdateFilters).some((update) => {
          const updateFilter = update as { quantity: string; sum: string };
          return (
            updateFilter &&
            updateFilter.quantity &&
            updateFilter.sum &&
            (updateFilter.quantity.trim() !== "" ||
              updateFilter.sum.trim() !== "")
          );
        });
      }
    } else {
      hasValue = (filters[field] as string).trim() !== "";
    }

    if (hasValue) {
      return `${baseClass} border-green-300 bg-green-50`;
    }

    return `${baseClass} border-gray-300`;
  };

  // Start editing an item
  // We start with empty editingValues so that users can clear fields completely
  // and type new values from scratch without interference from original values
  const startEditing = (item: BOQItem) => {
    setEditingId(item.id);
    setEditingValues({});
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingId(null);
    setEditingValues({});
  };

  // Save changes to database
  const saveChanges = async (item: BOQItem) => {
    try {
      setSavingId(item.id);

      // Calculate derived values
      const derivedValues = calculateDerivedValues(item, editingValues);

      // Prepare update data
      const updateData = {
        ...editingValues,
        ...derivedValues,
      };

      // Save to database
      const updatedItem = await boqApi.update(item.id, updateData);

      // Update local state
      setItems((prevItems) =>
        prevItems.map((prevItem) =>
          prevItem.id === item.id ? updatedItem : prevItem,
        ),
      );

      // Exit editing mode
      setEditingId(null);
      setEditingValues({});
    } catch (err) {
      console.error("Error saving changes:", err);
      setError("Failed to save changes");
    } finally {
      setSavingId(null);
    }
  };

  // Handle input change
  const handleInputChange = (field: keyof BOQItem, value: any) => {
    setEditingValues((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  // Handle key press for saving on Enter
  const handleKeyPress = (e: React.KeyboardEvent, item: BOQItem) => {
    if (e.key === "Enter") {
      saveChanges(item);
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  // Navigate to concentration sheet for specific item
  const handleViewConcentrationSheet = async (item: BOQItem) => {
    setNavigatingToSheet(item.id);
    try {
      await navigate(`/concentration?selectedItem=${item.id}`);
    } finally {
      setNavigatingToSheet(null);
    }
  };

  // Delete BOQ item with confirmation
  const handleDeleteItem = async (item: BOQItem) => {
    const confirmDelete = window.confirm(
      `Are you sure you want to delete this BOQ item?\n\n` +
        `Section: ${item.section_number}\n` +
        `Description: ${item.description}\n\n` +
        `This will also delete all related concentration sheets and entries. This action cannot be undone.`,
    );

    if (!confirmDelete) return;

    try {
      setDeletingId(item.id);
      await boqApi.delete(item.id);

      // Remove item from local state
      setItems((prevItems) =>
        prevItems.filter((prevItem) => prevItem.id !== item.id),
      );

      // Clear any editing state if this item was being edited
      if (editingId === item.id) {
        setEditingId(null);
        setEditingValues({});
      }

      console.log(`Successfully deleted BOQ item: ${item.section_number}`);
    } catch (err) {
      console.error("Error deleting BOQ item:", err);
      setError("Failed to delete BOQ item. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  // Fetch BOQ items. Optional overrides allow debounced effect to pass captured query/subchapter.
  const fetchItems = async (
    overrideQuery?: string,
    overrideSubchapter?: string,
  ) => {
    const q = overrideQuery !== undefined ? overrideQuery : searchQuery;
    const sub =
      overrideSubchapter !== undefined
        ? overrideSubchapter
        : selectedSubchapter;
    try {
      setLoading(true);
      setError(null);

      if (q.trim()) {
        const response = await searchApi.search(q, "all", 0, 10000);
        setAllItems(response.items);
      } else if (sub) {
        const response = await searchApi.getBySubchapter(sub, 0, 10000);
        setAllItems(response);
      } else {
        const response = await boqApi.getAll(0, 10000);
        setAllItems(response);
      }
    } catch (err) {
      setError("Failed to fetch BOQ items");
      console.error("Error fetching items:", err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch subchapters for filter
  const fetchSubchapters = async () => {
    try {
      const response = await searchApi.getAllSubchapters();
      setSubchapters(response);
    } catch (err) {
      console.error("Error fetching subchapters:", err);
    }
  };

  // Project Info functions
  const fetchProjectInfo = async () => {
    try {
      const response = await projectInfoApi.get();
      setProjectInfo(response);
      setProjectInfoDraft({
        project_name: response.project_name || "",
        project_name_hebrew: response.project_name_hebrew || "",
        main_contractor_name: response.main_contractor_name || "",
        subcontractor_name: response.subcontractor_name || "",
        developer_name: response.developer_name || "",
        contract_no: response.contract_no || "",
        invoice_no_submitted_qty: response.invoice_no_submitted_qty || "",
        invoice_date_submitted_qty: formatDateToMonth(
          response.invoice_date_submitted_qty || "",
        ),
        invoice_no_approved_signed_qty:
          response.invoice_no_approved_signed_qty || "",
        invoice_date_approved_signed_qty: formatDateToMonth(
          response.invoice_date_approved_signed_qty || "",
        ),
      });
    } catch (err) {
      console.error("Error fetching project info:", err);
      setProjectInfoError("Failed to fetch project info");
    }
  };

  // Contract Updates functions
  const fetchContractUpdates = async () => {
    try {
      const response = await contractUpdatesApi.getAll();
      setContractUpdates(response);
    } catch (err) {
      console.error("Error fetching contract updates:", err);
    }
  };

  const fetchBOQItemUpdates = async () => {
    try {
      if (contractUpdates.length > 0) {
        const allUpdates: BOQItemQuantityUpdate[] = [];
        for (const update of contractUpdates) {
          const response = await contractUpdatesApi.getBOQItemUpdates(
            update.id,
          );
          allUpdates.push(...response);
        }
        setBoqItemUpdates(allUpdates);
      }
    } catch (err) {
      console.error("Error fetching BOQ item updates:", err);
    }
  };

  const handleCreateContractUpdate = async () => {
    try {
      setCreatingUpdate(true);
      const newUpdate = await contractUpdatesApi.create();
      setContractUpdates((prev) => [...prev, newUpdate]);

      // Refresh BOQ item updates
      await fetchBOQItemUpdates();

      setError(null);
      setProjectInfoSuccess(
        "New contract quantity update created successfully!",
      );
      setTimeout(() => setProjectInfoSuccess(null), 5000);
    } catch (err) {
      console.error("Error creating contract update:", err);
      setError("Failed to create contract update");
    } finally {
      setCreatingUpdate(false);
    }
  };

  // Export functions
  const handleExport = async (request: any, format: "excel" | "pdf") => {
    try {
      setExporting(true);
      setError(null);

      // Filter the current table data based on the request
      const filteredData = items.map((item) => {
        const filteredItem: any = {};

        if (request.include_serial_number)
          filteredItem.serial_number = item.serial_number;
        if (request.include_structure) filteredItem.structure = item.structure;
        if (request.include_system) filteredItem.system = item.system;
        if (request.include_section_number)
          filteredItem.section_number = item.section_number;
        if (request.include_description)
          filteredItem.description = item.description;
        if (request.include_unit) filteredItem.unit = item.unit;
        if (request.include_original_contract_quantity)
          filteredItem.original_contract_quantity =
            item.original_contract_quantity;
        if (request.include_price) filteredItem.price = item.price;
        if (request.include_total_contract_sum)
          filteredItem.total_contract_sum = item.total_contract_sum;
        if (request.include_estimated_quantity)
          filteredItem.estimated_quantity = item.estimated_quantity;
        if (request.include_quantity_submitted)
          filteredItem.quantity_submitted = item.quantity_submitted;
        if (request.include_internal_quantity)
          filteredItem.internal_quantity = item.internal_quantity;
        if (request.include_approved_by_project_manager)
          filteredItem.approved_by_project_manager =
            item.approved_by_project_manager;
        if (request.include_approved_signed_quantity)
          filteredItem.approved_signed_quantity = item.approved_signed_quantity;
        if (request.include_quantity_decrease)
          filteredItem.quantity_decrease = calculateQuantityDecrease(item);
        if (request.include_quantity_increase)
          filteredItem.quantity_increase = calculateQuantityIncrease(item);
        if (request.include_total_estimate)
          filteredItem.total_estimate = item.total_estimate;
        if (request.include_total_submitted)
          filteredItem.total_submitted = item.total_submitted;
        if (request.include_internal_total)
          filteredItem.internal_total = item.internal_total;
        if (request.include_total_approved_by_project_manager)
          filteredItem.total_approved_by_project_manager =
            item.total_approved_by_project_manager;
        if (request.include_approved_signed_total)
          filteredItem.approved_signed_total = item.approved_signed_total;
        if (request.include_total_decrease)
          filteredItem.total_decrease = calculateTotalDecrease(item);
        if (request.include_total_increase)
          filteredItem.total_increase = calculateTotalIncrease(item);
        if (request.include_subsection)
          filteredItem.subsection = item.subsection;
        if (request.include_notes) filteredItem.notes = item.notes;

        // Add contract update columns
        contractUpdates.forEach((update) => {
          const qtyKey = `updated_contract_quantity_${update.id}`;
          const sumKey = `updated_contract_sum_${update.id}`;

          if (request[`include_${qtyKey}`]) {
            filteredItem[qtyKey] = getContractUpdateValue(
              item.id,
              update.id,
              "quantity",
            );
          }

          if (request[`include_${sumKey}`]) {
            filteredItem[sumKey] = getContractUpdateValue(
              item.id,
              update.id,
              "sum",
            );
          }
        });

        return filteredItem;
      });

      // Calculate grand totals for Excel export
      let grandTotals: any = null;
      if (format === "excel" && filteredData.length > 0) {
        grandTotals = {
          total_contract_sum: filteredData.reduce(
            (sum, item) => sum + (item.total_contract_sum || 0),
            0,
          ),
          total_estimate: filteredData.reduce(
            (sum, item) => sum + (item.total_estimate || 0),
            0,
          ),
          total_submitted: filteredData.reduce(
            (sum, item) => sum + (item.total_submitted || 0),
            0,
          ),
          internal_total: filteredData.reduce(
            (sum, item) => sum + (item.internal_total || 0),
            0,
          ),
          total_approved_by_project_manager: filteredData.reduce(
            (sum, item) => sum + (item.total_approved_by_project_manager || 0),
            0,
          ),
          approved_signed_total: filteredData.reduce(
            (sum, item) => sum + (item.approved_signed_total || 0),
            0,
          ),
          total_decrease: request.include_total_decrease
            ? filteredData.reduce(
                (sum, item) => sum + (item.total_decrease || 0),
                0,
              )
            : undefined,
          total_increase: request.include_total_increase
            ? filteredData.reduce(
                (sum, item) => sum + (item.total_increase || 0),
                0,
              )
            : undefined,
        };

        // Add contract update sum totals
        contractUpdates.forEach((update) => {
          const sumKey = `updated_contract_sum_${update.id}`;
          if (request[`include_${sumKey}`]) {
            grandTotals[sumKey] = filteredData.reduce(
              (sum, item) => sum + (item[sumKey] || 0),
              0,
            );
          }
        });
      }

      // Choose the appropriate export function based on format
      const response =
        format === "excel"
          ? await exportApi.exportBOQItemsExcel(
              request,
              filteredData,
              grandTotals,
            )
          : await exportApi.exportBOQItemsPDF(
              request,
              filteredData,
              isRTL ? "he" : "en",
            );

      if (response.success && response.pdf_path) {
        // Create download link
        const link = document.createElement("a");
        const downloadUrl = response.pdf_path.startsWith("/")
          ? `/api${response.pdf_path}`
          : `/api/${response.pdf_path}`;
        link.href = downloadUrl;
        const fileExtension = format === "excel" ? "xlsx" : "pdf";
        const filename =
          response.pdf_path.split("/").pop() || `boq_items.${fileExtension}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Show success message
        const formatName = format === "excel" ? "Excel" : "PDF";
        setProjectInfoSuccess(
          `Successfully exported BOQ items as ${formatName}`,
        );
        setTimeout(() => setProjectInfoSuccess(null), 5000);
        setShowExportModal(false);
      }
    } catch (err) {
      const formatName = format === "excel" ? "Excel" : "PDF";
      console.error(`Error exporting BOQ items as ${format}:`, err);
      setError(`Failed to export as ${formatName}`);
    } finally {
      setExporting(false);
    }
  };

  const handleUpdateContractQuantity = async (
    updateId: number,
    boqItemId: number,
    newQuantity: number,
  ) => {
    try {
      await contractUpdatesApi.updateBOQItemQuantity(updateId, boqItemId, {
        updated_contract_quantity: newQuantity,
      });

      // Update local state
      setBoqItemUpdates((prev) =>
        prev.map((update) =>
          update.contract_update_id === updateId &&
          update.boq_item_id === boqItemId
            ? { ...update, updated_contract_quantity: newQuantity }
            : update,
        ),
      );
    } catch (err) {
      console.error("Error updating contract quantity:", err);
      setError("Failed to update contract quantity");
    }
  };

  const handleProjectInfoDraftChange = (
    field: keyof ProjectInfoUpdate,
    value: string,
  ) => {
    setProjectInfoDraft((prev) => ({ ...prev, [field]: value }));
  };

  const handleEditProjectInfo = () => {
    if (projectInfo) {
      setProjectInfoDraft({
        project_name: projectInfo.project_name || "",
        project_name_hebrew: projectInfo.project_name_hebrew || "",
        main_contractor_name: projectInfo.main_contractor_name || "",
        subcontractor_name: projectInfo.subcontractor_name || "",
        developer_name: projectInfo.developer_name || "",
        contract_no: projectInfo.contract_no || "",
        invoice_no_submitted_qty: projectInfo.invoice_no_submitted_qty || "",
        invoice_date_submitted_qty: formatDateToMonth(
          projectInfo.invoice_date_submitted_qty || "",
        ),
        invoice_no_approved_signed_qty:
          projectInfo.invoice_no_approved_signed_qty || "",
        invoice_date_approved_signed_qty: formatDateToMonth(
          projectInfo.invoice_date_approved_signed_qty || "",
        ),
      });
    }
    setEditingProjectInfo(true);
    setProjectInfoError(null);
  };

  const handleCancelProjectInfo = () => {
    setEditingProjectInfo(false);
    setProjectInfoDraft({
      project_name: projectInfo?.project_name || "",
      project_name_hebrew: projectInfo?.project_name_hebrew || "",
      main_contractor_name: projectInfo?.main_contractor_name || "",
      subcontractor_name: projectInfo?.subcontractor_name || "",
      developer_name: projectInfo?.developer_name || "",
      contract_no: projectInfo?.contract_no || "",
      invoice_no_submitted_qty: projectInfo?.invoice_no_submitted_qty || "",
      invoice_date_submitted_qty: formatDateToMonth(
        projectInfo?.invoice_date_submitted_qty || "",
      ),
      invoice_no_approved_signed_qty:
        projectInfo?.invoice_no_approved_signed_qty || "",
      invoice_date_approved_signed_qty: formatDateToMonth(
        projectInfo?.invoice_date_approved_signed_qty || "",
      ),
    });
    setProjectInfoError(null);
  };

  const handleSaveProjectInfo = async () => {
    try {
      setSavingProjectInfo(true);
      setProjectInfoError(null);

      // Convert month strings to datetime format for backend
      const draftToSend = { ...projectInfoDraft };

      if (draftToSend.invoice_date_submitted_qty) {
        // Convert "YYYY-MM" to "YYYY-MM-01T00:00:00"
        draftToSend.invoice_date_submitted_qty = `${draftToSend.invoice_date_submitted_qty}-01T00:00:00`;
      }

      if (draftToSend.invoice_date_approved_signed_qty) {
        // Convert "YYYY-MM" to "YYYY-MM-01T00:00:00"
        draftToSend.invoice_date_approved_signed_qty = `${draftToSend.invoice_date_approved_signed_qty}-01T00:00:00`;
      }

      const updatedProjectInfo = await projectInfoApi.update(draftToSend);
      setProjectInfo(updatedProjectInfo);
      setEditingProjectInfo(false);
      setError(null);
      setProjectInfoSuccess(
        "Project information updated successfully! All concentration sheets have been updated. Note: You may need to refresh the Concentration Sheets page to see the changes.",
      );

      // Clear success message after 5 seconds
      setTimeout(() => setProjectInfoSuccess(null), 5000);
    } catch (err) {
      console.error("Error saving project info:", err);
      setProjectInfoError("Failed to save project info");
    } finally {
      setSavingProjectInfo(false);
    }
  };

  useEffect(() => {
    fetchSubchapters();
    fetchProjectInfo();
    fetchContractUpdates();
  }, []);

  // Fetch BOQ item updates when contract updates change
  useEffect(() => {
    if (contractUpdates.length > 0) {
      fetchBOQItemUpdates();

      // Initialize contract update filters
      const newContractUpdateFilters: Record<
        number,
        { quantity: string; sum: string }
      > = {};
      contractUpdates.forEach((update) => {
        newContractUpdateFilters[update.id] = { quantity: "", sum: "" };
      });

      // console.log("Initializing contract update filters:", {
      //   contractUpdates: contractUpdates.map((u) => ({
      //     id: u.id,
      //     name: u.update_name,
      //   })),
      //   newFilters: newContractUpdateFilters,
      // });

      setFilters((prev) => ({
        ...prev,
        contract_updates: newContractUpdateFilters,
      }));
    }
  }, [contractUpdates]);

  // Debounce search so typing doesn't trigger fetch on every keystroke (avoids focus loss and extra requests)
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstSearchRun = useRef(true);
  useEffect(() => {
    if (isFirstSearchRun.current) {
      isFirstSearchRun.current = false;
      fetchItems(searchQuery, selectedSubchapter);
      return;
    }
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      searchDebounceRef.current = null;
      fetchItems(searchQuery, selectedSubchapter);
    }, 400);
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, [searchQuery, selectedSubchapter]);

  // Update items when filteredItems change
  useEffect(() => {
    setItems(filteredItems);
  }, [filteredItems]);

  // Save scroll position to localStorage
  useEffect(() => {
    const scrollContainer = tableScrollContainerRef.current;

    if (!scrollContainer) {
      return;
    }

    const handleScroll = () => {
      const scrollTop = scrollContainer.scrollTop;
      const scrollHeight = scrollContainer.scrollHeight;
      const clientHeight = scrollContainer.clientHeight;
      const maxScroll = scrollHeight - clientHeight;
      const scrollPercentage =
        maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;

      localStorage.setItem("boq-table-scroll-position", scrollTop.toString());
    };

    scrollContainer.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      scrollContainer.removeEventListener("scroll", handleScroll);
    };
  }, [items.length]); // Re-attach when items change to ensure container is ready

  // Reset restoration flag when navigating to this page and restore scroll position
  useEffect(() => {
    // Reset flag when pathname changes (user navigated to/back to this page)
    scrollPositionRestoredRef.current = false;

    // If we're on the BOQ page and items are loaded, try to restore scroll
    if (
      location.pathname === "/boq" &&
      !loading &&
      items.length > 0 &&
      tableScrollContainerRef.current &&
      !scrollPositionRestoredRef.current
    ) {
      const savedScrollPosition = localStorage.getItem(
        "boq-table-scroll-position",
      );

      if (savedScrollPosition) {
        const scrollTop = parseInt(savedScrollPosition, 10);
        // Function to restore scroll position
        const restoreScroll = () => {
          const container = tableScrollContainerRef.current;
          if (!container) {
            return false;
          }

          // Check if table has content rendered (check for actual table rows)
          const tableRows = container.querySelectorAll("tbody tr");
          const scrollHeight = container.scrollHeight;
          const clientHeight = container.clientHeight;
          const maxScroll = scrollHeight - clientHeight;
          const scrollPercentage =
            maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;
          const hasContent = scrollHeight > 0 && tableRows.length > 0;

          if (hasContent) {
            // Set scroll position
            container.scrollTop = scrollTop;
            scrollPositionRestoredRef.current = true;

            const actualScrollTop = container.scrollTop;
            const actualPercentage =
              maxScroll > 0 ? (actualScrollTop / maxScroll) * 100 : 0;

            return true; // Success
          }

          return false; // Not ready yet
        };

        // Try immediately
        if (!restoreScroll()) {
          // If not ready, try with delays
          let attempts = 0;
          const maxAttempts = 30; // Try up to 30 times (1.5 seconds total)

          const tryRestore = () => {
            attempts++;
            if (restoreScroll() || attempts >= maxAttempts) {
              if (attempts >= maxAttempts) {
                scrollPositionRestoredRef.current = true;
              }
              return;
            }
            setTimeout(tryRestore, 50);
          };

          // Start retry loop after initial delay
          setTimeout(tryRestore, 100);
        }
      } else {
        // No saved position, mark as restored
        scrollPositionRestoredRef.current = true;
      }
    }
  }, [location.pathname, loading, items.length]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
  };

  const handleFilterChange = (field: keyof typeof filters, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  // Handle contract update filter changes
  const handleContractUpdateFilterChange = (
    updateId: number,
    field: "quantity" | "sum",
    value: string,
  ) => {
    console.log("Contract update filter change:", {
      updateId,
      field,
      value,
      currentFilters: filters.contract_updates,
    });

    setFilters((prev) => {
      // Ensure contract_updates object exists
      const currentContractUpdates = prev.contract_updates || {};

      return {
        ...prev,
        contract_updates: {
          ...currentContractUpdates,
          [updateId]: {
            ...currentContractUpdates[updateId],
            [field]: value,
          },
        },
      };
    });
  };

  const handleFilterKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      // Trigger a re-render by updating a dummy state
      setFilters((prev) => ({ ...prev }));
    }
  };

  const handleClearFilters = () => {
    setSearchQuery("");
    setSelectedSubchapter("");

    // Clear all filters including contract updates
    const clearedContractUpdates: Record<
      number,
      { quantity: string; sum: string }
    > = {};
    contractUpdates.forEach((update) => {
      clearedContractUpdates[update.id] = { quantity: "", sum: "" };
    });

    setFilters({
      serial_number: "",
      structure: "",
      system: "",
      section_number: "",
      description: "",
      unit: "",
      subsection: "",
      notes: "",
      internal_field_1: "",
      internal_field_2: "",
      original_contract_quantity: "",
      price: "",
      total_contract_sum: "",
      estimated_quantity: "",
      quantity_submitted: "",
      internal_quantity: "",
      approved_by_project_manager: "",
      total_estimate: "",
      total_submitted: "",
      internal_total: "",
      total_approved_by_project_manager: "",
      approved_signed_quantity: "",
      approved_signed_total: "",
      total_decrease: "",
      total_increase: "",
      quantity_decrease: "",
      quantity_increase: "",
      contract_updates: clearedContractUpdates,
    });
  };

  // Create concentration sheets for all BOQ items
  const createConcentrationSheets = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await importApi.createConcentrationSheets();

      if (response.success) {
        setError(null);
        // Show success message
        alert(
          `Successfully created ${response.created_count} concentration sheets!`,
        );
      } else {
        setError(response.message || "Failed to create concentration sheets");
      }
    } catch (err) {
      console.error("Error creating concentration sheets:", err);
      setError("Failed to create concentration sheets");
    } finally {
      setLoading(false);
    }
  };

  // Manual BOQ Item Creation functions
  const handleNewItemFormChange = (field: string, value: any) => {
    setNewItemForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleShowAddForm = () => {
    setShowAddForm(true);
    setError(null);
    setProjectInfoSuccess(null);
  };

  const handleCancelAddForm = () => {
    setShowAddForm(false);
    setNewItemForm({
      section_number: "",
      description: "",
      unit: "",
      original_contract_quantity: 0,
      price: 0,
      system: "",
      structure: 0,
    });
    setError(null);
  };

  const handleCreateNewItem = async () => {
    try {
      setCreatingItem(true);
      setError(null);

      // Extract subsection from section number (e.g., "01.02.01" -> "01.02")
      const sectionParts = newItemForm.section_number.split(".");
      const subsection =
        sectionParts.length >= 3
          ? sectionParts.slice(0, 3).join(".")
          : newItemForm.section_number;

      // Calculate derived values
      const total_contract_sum =
        newItemForm.original_contract_quantity * newItemForm.price;

      // Create new BOQ item
      const newItem = await boqApi.create({
        section_number: newItemForm.section_number,
        description: newItemForm.description,
        unit: newItemForm.unit,
        original_contract_quantity: newItemForm.original_contract_quantity,
        price: newItemForm.price,
        total_contract_sum: total_contract_sum,
        subsection: subsection,
        system: newItemForm.system,
        structure: newItemForm.structure,
      });

      // Add to local state
      setAllItems((prev) => [...prev, newItem]);

      // Close form and show success message
      handleCancelAddForm();
      setProjectInfoSuccess("New BOQ item created successfully!");
      setTimeout(() => setProjectInfoSuccess(null), 5000);

      // Show notification about concentration sheets
      toast.success(
        "New BOQ item created successfully! Don't forget to create concentration sheets.",
        {
          duration: 8000,
        },
      );
    } catch (err) {
      console.error("Error creating new BOQ item:", err);
      setError("Failed to create new BOQ item");
    } finally {
      setCreatingItem(false);
    }
  };

  // Toggle panel collapse
  const togglePanels = () => {
    setPanelsCollapsed(!panelsCollapsed);
  };

  // Helper functions to execute actions after password confirmation
  const handleSaveChangesAfterPassword = (item: BOQItem) => {
    // Find the current editing state and save changes
    if (editingId === item.id) {
      saveChanges(item);
    }
  };

  const handleDeleteContractUpdateAfterPassword = async (
    itemId: number,
    contractUpdateId: number,
  ) => {
    try {
      console.log("Deleting contract update:", { itemId, contractUpdateId });

      // Delete the contract update using the API
      await contractUpdatesApi.delete(contractUpdateId);

      // Remove the contract update from local state
      setContractUpdates((prev) => {
        const filtered = prev.filter(
          (update) => update.id !== contractUpdateId,
        );
        console.log("Updated contract updates:", filtered);
        return filtered;
      });

      // Also remove any BOQ item updates associated with this contract update
      setBoqItemUpdates((prev) => {
        const filtered = prev.filter(
          (update) => update.contract_update_id !== contractUpdateId,
        );
        console.log("Updated BOQ item updates:", filtered);
        return filtered;
      });

      // Refresh the contract updates to ensure consistency
      await fetchContractUpdates();

      setProjectInfoSuccess("Contract update deleted successfully!");
      setTimeout(() => setProjectInfoSuccess(null), 5000);
    } catch (err) {
      console.error("Error deleting contract update:", err);
      setError("Failed to delete contract update");
    }
  };

  if (loading && items.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className={`text-3xl font-bold text-gray-900`}>
            {t("boq.title")}
          </h1>
          <p className={`mt-2 text-gray-600`}>{t("boq.subtitle")}</p>
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className={`text-3xl font-bold text-gray-900`}>
            {t("boq.title")}
          </h1>
          <p className={`mt-2 text-gray-600`}>
            {t("boq.subtitle")} ({items.length} {t("common.items", "items")})
          </p>
        </div>
        <div>
          <div className="flex space-x-3">
            <button
              onClick={togglePanels}
              className={`px-4 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                panelsCollapsed
                  ? "bg-green-600 text-white hover:bg-green-700 shadow-md"
                  : "bg-orange-600 text-white hover:bg-orange-700 shadow-md"
              }`}
              title={
                panelsCollapsed
                  ? t("boq.expandPanels")
                  : t("boq.collapsePanels")
              }
            >
              {panelsCollapsed
                ? t("boq.expandPanelsBtn")
                : t("boq.collapsePanelsBtn")}
            </button>
            <button
              onClick={handleShowAddForm}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {t("boq.addBOQItem")}
            </button>
            <button
              onClick={() => {
                setPasswordAction("update");
                setPasswordItemId(null);
                setPasswordContractUpdateId(null);
                setShowPasswordDialog(true);
              }}
              disabled={creatingUpdate}
              className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creatingUpdate
                ? t("boq.creating")
                : t("boq.updateContractQuantity")}
            </button>
            <button
              onClick={createConcentrationSheets}
              disabled={items.length === 0 || loading}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("boq.createConcentrationSheets")}
            </button>
            <button
              onClick={() => setShowColumnSettings(true)}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              {t("boq.columnSettings")}
            </button>
            <button
              onClick={() => setShowExportModal(true)}
              disabled={items.length === 0 || loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("boq.exportTable")}
            </button>
          </div>
        </div>
      </div>

      {/* Contract Updates Info */}
      {!panelsCollapsed && contractUpdates.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className={`text-sm font-medium text-blue-900`}>
                {t("boq.contractQuantityUpdates")} ({contractUpdates.length}{" "}
                {t("boq.activeUpdates")})
              </h3>
              <p className={`text-sm text-blue-700 mt-1`}>
                {t("boq.contractUpdatesDescription")}
              </p>
            </div>
            <button
              onClick={handleCreateContractUpdate}
              disabled={creatingUpdate}
              className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {creatingUpdate ? t("boq.creating") : t("boq.newUpdate")}
            </button>
          </div>

          {/* List of active updates */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
            {contractUpdates.map((update) => (
              <div
                key={update.id}
                className="bg-white rounded-md p-3 border border-blue-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-blue-900">
                      {update.update_name}
                    </h4>
                    <p className={`text-xs text-blue-600`}>
                      {t("boq.created")}{" "}
                      {new Date(update.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      handleDeleteContractUpdateClick(0, update.id)
                    }
                    className="text-red-600 hover:text-red-800 text-sm px-2 py-1 rounded hover:bg-red-50"
                    title={t("boq.deleteThisUpdate")}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Project Information Panel */}
      {!panelsCollapsed && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className={`text-xl font-semibold text-gray-900`}>
                {t("projectInfo.title")}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {t("boq.projectInformationSync")}
              </p>
            </div>
            {!editingProjectInfo && (
              <button
                onClick={handleEditProjectInfo}
                className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                {t("projectInfo.edit")}
              </button>
            )}
          </div>

          {projectInfoError && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-3">
              <div className="text-red-600 text-sm">{projectInfoError}</div>
            </div>
          )}

          {projectInfoSuccess && (
            <div className="mb-4 bg-green-50 border border-green-200 rounded-md p-3">
              <div className="text-green-600 text-sm">{projectInfoSuccess}</div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfo.projectName")}
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.project_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange("project_name", e.target.value)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t("boq.projectNamePlaceholder")}
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.project_name || t("boq.notSpecified")}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfo.projectNameHebrew")}
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.project_name_hebrew || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "project_name_hebrew",
                      e.target.value,
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t("projectInfo.projectNameHebrew")}
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.project_name_hebrew || t("boq.notSpecified")}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfo.mainContractorName")}
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.main_contractor_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "main_contractor_name",
                      e.target.value,
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t("projectInfo.mainContractorName")}
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.main_contractor_name || t("boq.notSpecified")}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfo.subcontractorName")}
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.subcontractor_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "subcontractor_name",
                      e.target.value,
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t("projectInfo.subcontractorName")}
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.subcontractor_name || t("boq.notSpecified")}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfo.developerName")}
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.developer_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "developer_name",
                      e.target.value,
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t("projectInfo.developerName")}
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.developer_name || t("boq.notSpecified")}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("projectInfo.contractNumber")}
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.contract_no || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange("contract_no", e.target.value)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t("projectInfo.contractNumber")}
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.contract_no || t("boq.notSpecified")}
                </div>
              )}
            </div>

            {/* Invoice fields grouped in pairs */}
            <div className="md:col-span-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("projectInfo.invoiceNoSubmitted")}
                  </label>
                  {editingProjectInfo ? (
                    <input
                      type="text"
                      value={projectInfoDraft.invoice_no_submitted_qty || ""}
                      onChange={(e) =>
                        handleProjectInfoDraftChange(
                          "invoice_no_submitted_qty",
                          e.target.value,
                        )
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t("projectInfo.invoiceNoSubmitted")}
                    />
                  ) : (
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                      {projectInfo?.invoice_no_submitted_qty ||
                        t("boq.notSpecified")}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("projectInfo.invoiceDateSubmitted")}
                  </label>
                  {editingProjectInfo ? (
                    <input
                      type="month"
                      value={projectInfoDraft.invoice_date_submitted_qty || ""}
                      onChange={(e) =>
                        handleProjectInfoDraftChange(
                          "invoice_date_submitted_qty",
                          e.target.value,
                        )
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                      {projectInfo?.invoice_date_submitted_qty
                        ? formatDateMMYYYY(
                            projectInfo.invoice_date_submitted_qty,
                          )
                        : t("boq.notSpecified")}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="md:col-span-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("projectInfo.invoiceNoApproved")}
                  </label>
                  {editingProjectInfo ? (
                    <input
                      type="text"
                      value={
                        projectInfoDraft.invoice_no_approved_signed_qty || ""
                      }
                      onChange={(e) =>
                        handleProjectInfoDraftChange(
                          "invoice_no_approved_signed_qty",
                          e.target.value,
                        )
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t("projectInfo.invoiceNoApproved")}
                    />
                  ) : (
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                      {projectInfo?.invoice_no_approved_signed_qty ||
                        t("boq.notSpecified")}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("projectInfo.invoiceDateApproved")}
                  </label>
                  {editingProjectInfo ? (
                    <input
                      type="month"
                      value={
                        projectInfoDraft.invoice_date_approved_signed_qty || ""
                      }
                      onChange={(e) =>
                        handleProjectInfoDraftChange(
                          "invoice_date_approved_signed_qty",
                          e.target.value,
                        )
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                      {projectInfo?.invoice_date_approved_signed_qty
                        ? formatDateMMYYYY(
                            projectInfo.invoice_date_approved_signed_qty,
                          )
                        : t("boq.notSpecified")}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {editingProjectInfo && (
            <div className="flex justify-end space-x-3 mt-4 pt-4 border-t border-gray-200">
              <button
                onClick={handleCancelProjectInfo}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={handleSaveProjectInfo}
                disabled={savingProjectInfo}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t(savingProjectInfo ? "boq.saving" : "boq.saveChanges")}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Manual BOQ Item Creation Form */}
      {!panelsCollapsed && showAddForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {t("boq.addNewItem")}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {t("boq.manuallyCreateDescription")}
              </p>
            </div>
            <button
              onClick={handleCancelAddForm}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("boq.sectionNumber")} *
              </label>
              <input
                type="text"
                required
                value={newItemForm.section_number}
                onChange={(e) =>
                  handleNewItemFormChange("section_number", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t("boq.sectionNumberPlaceholder")}
              />
              <p className="text-xs text-gray-500 mt-1">
                {t("boq.subsectionWillBe")}{" "}
                {newItemForm.section_number.split(".").length >= 2
                  ? newItemForm.section_number.split(".").slice(0, 2).join(".")
                  : t("boq.enterSectionNumber")}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                System
              </label>
              <input
                type="text"
                value={newItemForm.system || ""}
                onChange={(e) =>
                  handleNewItemFormChange("system", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter system name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Structure
              </label>
              <input
                type="number"
                value={newItemForm.structure || ""}
                onChange={(e) =>
                  handleNewItemFormChange(
                    "structure",
                    parseInt(e.target.value) || 0,
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter structure number"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("boq.description")} *
              </label>
              <input
                type="text"
                required
                value={newItemForm.description}
                onChange={(e) =>
                  handleNewItemFormChange("description", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter item description"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("boq.unit")} *
              </label>
              <input
                type="text"
                required
                value={newItemForm.unit}
                onChange={(e) =>
                  handleNewItemFormChange("unit", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., m, m², m³, kg"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("boq.contractQty")} *
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={newItemForm.original_contract_quantity}
                onChange={(e) =>
                  handleNewItemFormChange(
                    "original_contract_quantity",
                    parseFloat(e.target.value) || 0,
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("boq.price")} *
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={newItemForm.price}
                onChange={(e) =>
                  handleNewItemFormChange(
                    "price",
                    parseFloat(e.target.value) || 0,
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Calculated Values Preview */}
          <div className="mt-4 p-4 bg-gray-50 rounded-md">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              {t("boq.calculatedValues")}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="text-left">
                <span className="text-gray-600">
                  {t("boq.totalContractSum")}:
                </span>
                <span className="ml-2 font-medium text-gray-900">
                  {formatCurrency(
                    newItemForm.original_contract_quantity * newItemForm.price,
                  )}
                </span>
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={handleCancelAddForm}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateBOQItemClick}
              disabled={
                creatingItem ||
                !newItemForm.section_number ||
                !newItemForm.description ||
                !newItemForm.unit
              }
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creatingItem ? "Creating..." : "Create BOQ Item"}
            </button>
          </div>
        </div>
      )}

      {/* Password Confirmation Dialog */}
      {showPasswordDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <div
              className={`flex items-center justify-between mb-4 ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <h3 className="text-lg font-semibold text-gray-900">
                {passwordAction === "create" && t("boq.confirmBOQItemCreation")}
                {passwordAction === "update" &&
                  t("boq.confirmContractQuantityUpdate")}
                {passwordAction === "delete" &&
                  t("boq.confirmContractUpdateDeletion")}
              </h3>
              <button
                onClick={handlePasswordCancel}
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

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-3">
                {passwordAction === "create" &&
                  t("auth.confirmPasswordForCreate")}
                {passwordAction === "update" &&
                  t("auth.confirmPasswordForUpdate")}
                {passwordAction === "delete" &&
                  t("auth.confirmPasswordForDelete")}
              </p>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t("auth.systemPassword")}
              </label>
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handlePasswordConfirm();
                  } else if (e.key === "Escape") {
                    handlePasswordCancel();
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t("auth.enterSystemPassword")}
                autoFocus
              />
              {passwordError && (
                <p className="text-red-600 text-sm mt-1">{passwordError}</p>
              )}
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={handlePasswordCancel}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={handlePasswordConfirm}
                className={`px-4 py-2 text-white rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                  passwordAction === "delete"
                    ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
                    : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500"
                }`}
              >
                {passwordAction === "create" && t("auth.confirmButton")}
                {passwordAction === "update" && t("auth.confirmButton")}
                {passwordAction === "delete" && t("common.delete")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search and Filter Section */}
      {!panelsCollapsed && (
        <div className="bg-white rounded-lg shadow p-6">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("common.search")}
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={
                    t("auth.searchAllFields") || "Search all fields..."
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("auth.subchapter")}
                </label>
                <select
                  value={selectedSubchapter}
                  onChange={(e) => setSelectedSubchapter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">
                    {t("common.all")} {t("auth.subchapter")}
                  </option>
                  {subchapters.map((subchapter) => (
                    <option key={subchapter} value={subchapter}>
                      {subchapter}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Search
                </button>
              </div>
            </div>

            {/* Column Filters */}

            <div className="flex justify-between items-center">
              <button
                type="button"
                onClick={handleClearFilters}
                className="text-gray-600 hover:text-gray-800 text-sm"
              >
                Clear All Filters
              </button>
              <div className="text-sm text-gray-600">
                Showing {items.length} of {allItems.length} items
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="text-red-600">{error}</div>
          </div>
        </div>
      )}

      {/* Collapsed Panels Info */}
      {panelsCollapsed && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-blue-600">📦</span>
              <span className="text-sm text-blue-700">
                <strong>Panels collapsed.</strong> Click "🔓 Expand Panels" to
                show Project Information, Search & Filters, and other panels.
              </span>
            </div>
            <button
              onClick={togglePanels}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              Expand Now
            </button>
          </div>
        </div>
      )}

      {/* Items Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {activeFiltersCount > 0 && (
          <div className="px-4 py-2 bg-green-50 border-b border-green-200">
            <span className="text-sm text-green-700">
              🔍 <strong>{activeFiltersCount} active filter(s)</strong> -
              Results are being filtered
            </span>
          </div>
        )}

        {/* Table Container with Vertical Scrolling */}
        <div
          ref={tableScrollContainerRef}
          className="overflow-auto max-h-[70vh]"
        >
          <table className="min-w-full border border-gray-300">
            {/* Frozen Header */}
            <thead className="sticky top-0 z-10 bg-gray-50 shadow-sm border-t-2">
              {/* Column Headers Row */}
              <tr className="border-b border-gray-300 bg-gray-50">
                {columnVisibility.serial_number && (
                  <th className="px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[80px]">
                    {t("boq.serialNumber")}
                  </th>
                )}
                {columnVisibility.structure && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[80px]">
                    <div className="flex items-center justify-between">
                      <span>{t("boq.structure")}</span>
                      <FilterDropdown
                        columnName="Structure"
                        values={uniqueValues.structure}
                        selectedValues={dropdownFilters.structure}
                        onSelectionChange={(values) =>
                          handleDropdownFilterChange("structure", values)
                        }
                        onClearFilter={() =>
                          handleClearDropdownFilter("structure")
                        }
                        isOpen={dropdownOpen.structure}
                        onToggle={() => handleToggleDropdown("structure")}
                        onClose={() => handleCloseDropdown("structure")}
                      />
                    </div>
                  </th>
                )}
                {columnVisibility.system && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px]">
                    <div className="flex items-center justify-between">
                      <span>{t("boq.system")}</span>
                      <FilterDropdown
                        columnName="System"
                        values={uniqueValues.system}
                        selectedValues={dropdownFilters.system}
                        onSelectionChange={(values) =>
                          handleDropdownFilterChange("system", values)
                        }
                        onClearFilter={() =>
                          handleClearDropdownFilter("system")
                        }
                        isOpen={dropdownOpen.system}
                        onToggle={() => handleToggleDropdown("system")}
                        onClose={() => handleCloseDropdown("system")}
                      />
                    </div>
                  </th>
                )}
                {columnVisibility.section_number && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px]">
                    {t("boq.sectionNumber")}
                  </th>
                )}
                {columnVisibility.description && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[200px]">
                    {t("boq.description")}
                  </th>
                )}
                {columnVisibility.unit && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[80px]">
                    <div className="flex items-center justify-between">
                      <span>{t("boq.unit")}</span>
                      <FilterDropdown
                        columnName="Unit"
                        values={uniqueValues.unit}
                        selectedValues={dropdownFilters.unit}
                        onSelectionChange={(values) =>
                          handleDropdownFilterChange("unit", values)
                        }
                        onClearFilter={() => handleClearDropdownFilter("unit")}
                        isOpen={dropdownOpen.unit}
                        onToggle={() => handleToggleDropdown("unit")}
                        onClose={() => handleCloseDropdown("unit")}
                      />
                    </div>
                  </th>
                )}
                {columnVisibility.price && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px]">
                    {t("boq.price")}
                  </th>
                )}
                {columnVisibility.original_contract_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px]">
                    {t("boq.contractQty")}
                  </th>
                )}
                {columnVisibility.total_contract_sum && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px]">
                    {t("boq.contractSum")}
                  </th>
                )}
                {/* Dynamic Contract Update Columns */}
                {contractUpdates.map((update) => {
                  const qtyKey = `updated_contract_quantity_${update.id}`;
                  return columnVisibility[qtyKey] ? (
                    <th
                      key={update.id}
                      className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px]"
                    >
                      {update.update_name}
                    </th>
                  ) : null;
                })}
                {/* Dynamic Contract Sum Columns */}
                {contractUpdates.map((update) => {
                  const sumKey = `updated_contract_sum_${update.id}`;
                  return columnVisibility[sumKey] ? (
                    <th
                      key={update.id}
                      className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px]"
                    >
                      {update.update_name.replace("Qty", "Sum")}
                    </th>
                  ) : null;
                })}
                {columnVisibility.estimated_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px] bg-red-100">
                    {t("boq.estimatedQuantity")}
                  </th>
                )}
                {columnVisibility.quantity_submitted && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-blue-100">
                    {t("boq.quantitySubmitted")}
                  </th>
                )}
                {columnVisibility.internal_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px] bg-yellow-100">
                    {t("boq.internalQuantity")}
                  </th>
                )}
                {columnVisibility.approved_by_project_manager && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-100">
                    {t("boq.approvedQuantity")}
                  </th>
                )}
                {columnVisibility.approved_signed_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-200">
                    {t("boq.approvedSignedQuantity")}
                  </th>
                )}
                {columnVisibility.quantity_decrease && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-orange-100">
                    {t("boq.quantityDecrease")}
                  </th>
                )}
                {columnVisibility.quantity_increase && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-blue-100">
                    {t("boq.quantityIncrease")}
                  </th>
                )}
                {columnVisibility.total_estimate && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-red-100">
                    {t("boq.totalEstimate")}
                  </th>
                )}
                {columnVisibility.total_submitted && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-blue-100">
                    {t("boq.totalSubmitted")}
                  </th>
                )}
                {columnVisibility.internal_total && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-yellow-100">
                    {t("boq.internalTotal")}
                  </th>
                )}
                {columnVisibility.total_approved_by_project_manager && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-100">
                    {t("boq.totalApproved")}
                  </th>
                )}
                {columnVisibility.approved_signed_total && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-200">
                    {t("boq.approvedSignedTotal")}
                  </th>
                )}
                {columnVisibility.total_decrease && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-orange-100">
                    {t("boq.totalDecrease")}
                  </th>
                )}
                {columnVisibility.total_increase && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-blue-100">
                    {t("boq.totalIncrease")}
                  </th>
                )}
                {columnVisibility.subsection && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[150px]">
                    {t("boq.subchapter")}
                  </th>
                )}
                {columnVisibility.notes && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[150px]">
                    {t("boq.notes")}
                  </th>
                )}
                {columnVisibility.internal_field_1 && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[150px]">
                    Internal Field 1
                  </th>
                )}
                {columnVisibility.internal_field_2 && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[150px]">
                    Internal Field 2
                  </th>
                )}
                {columnVisibility.actions && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[120px]">
                    {t("boq.actions")}
                  </th>
                )}
              </tr>

              {/* Filter Inputs Row */}
              <tr className="border-b border-gray-300 bg-gray-100">
                {columnVisibility.serial_number && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.serial_number}
                      onChange={(e) =>
                        handleFilterChange("serial_number", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "serial_number",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.structure && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.structure}
                      onChange={(e) =>
                        handleFilterChange("structure", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "structure",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.system && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.system}
                      onChange={(e) =>
                        handleFilterChange("system", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "system",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.section_number && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.section_number}
                      onChange={(e) =>
                        handleFilterChange("section_number", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "section_number",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.description && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.description}
                      onChange={(e) =>
                        handleFilterChange("description", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "description",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.unit && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.unit}
                      onChange={(e) =>
                        handleFilterChange("unit", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "unit",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.price && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.price}
                      onChange={(e) =>
                        handleFilterChange("price", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "price",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.original_contract_quantity && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.original_contract_quantity}
                      onChange={(e) =>
                        handleFilterChange(
                          "original_contract_quantity",
                          e.target.value,
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "original_contract_quantity",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.total_contract_sum && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.total_contract_sum}
                      onChange={(e) =>
                        handleFilterChange("total_contract_sum", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_contract_sum",
                      )}`}
                    />
                  </th>
                )}
                {/* Dynamic Contract Update Filter Columns */}
                {contractUpdates.map((update) => {
                  const qtyKey = `updated_contract_quantity_${update.id}`;
                  return columnVisibility[qtyKey] ? (
                    <th
                      key={update.id}
                      className="px-2 py-2 border-r border-gray-300"
                    >
                      <input
                        type="text"
                        value={(
                          filters.contract_updates[update.id]?.quantity || ""
                        ).toString()}
                        onChange={(e) =>
                          handleContractUpdateFilterChange(
                            update.id,
                            "quantity",
                            e.target.value,
                          )
                        }
                        onKeyDown={handleFilterKeyDown}
                        placeholder=">100, <50, =25..."
                        className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                          (
                            filters.contract_updates[update.id]?.quantity || ""
                          ).trim() !== ""
                            ? "border-green-300 bg-green-50"
                            : "border-gray-300"
                        }`}
                      />
                    </th>
                  ) : null;
                })}
                {/* Dynamic Contract Sum Filter Columns */}
                {contractUpdates.map((update) => {
                  const sumKey = `updated_contract_sum_${update.id}`;
                  return columnVisibility[sumKey] ? (
                    <th
                      key={update.id}
                      className="px-2 py-2 border-r border-gray-300"
                    >
                      <input
                        type="text"
                        value={(
                          filters.contract_updates[update.id]?.sum || ""
                        ).toString()}
                        onChange={(e) =>
                          handleContractUpdateFilterChange(
                            update.id,
                            "sum",
                            e.target.value,
                          )
                        }
                        onKeyDown={handleFilterKeyDown}
                        placeholder=">1000, <500, =250..."
                        className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                          (
                            filters.contract_updates[update.id]?.sum || ""
                          ).trim() !== ""
                            ? "border-green-300 bg-green-50"
                            : "border-gray-300"
                        }`}
                      />
                    </th>
                  ) : null;
                })}
                {columnVisibility.estimated_quantity && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.estimated_quantity}
                      onChange={(e) =>
                        handleFilterChange("estimated_quantity", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "estimated_quantity",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.quantity_submitted && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.quantity_submitted}
                      onChange={(e) =>
                        handleFilterChange("quantity_submitted", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "quantity_submitted",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.internal_quantity && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.internal_quantity}
                      onChange={(e) =>
                        handleFilterChange("internal_quantity", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "internal_quantity",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.approved_by_project_manager && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.approved_by_project_manager}
                      onChange={(e) =>
                        handleFilterChange(
                          "approved_by_project_manager",
                          e.target.value,
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "approved_by_project_manager",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.approved_signed_quantity && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.approved_signed_quantity}
                      onChange={(e) =>
                        handleFilterChange(
                          "approved_signed_quantity",
                          e.target.value,
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "approved_signed_quantity",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.quantity_decrease && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.quantity_decrease}
                      onChange={(e) =>
                        handleFilterChange("quantity_decrease", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "quantity_decrease",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.quantity_increase && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.quantity_increase}
                      onChange={(e) =>
                        handleFilterChange("quantity_increase", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "quantity_increase",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.total_estimate && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.total_estimate}
                      onChange={(e) =>
                        handleFilterChange("total_estimate", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_estimate",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.total_submitted && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.total_submitted}
                      onChange={(e) =>
                        handleFilterChange("total_submitted", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_submitted",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.internal_total && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.internal_total}
                      onChange={(e) =>
                        handleFilterChange("internal_total", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "internal_total",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.total_approved_by_project_manager && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.total_approved_by_project_manager}
                      onChange={(e) =>
                        handleFilterChange(
                          "total_approved_by_project_manager",
                          e.target.value,
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_approved_by_project_manager",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.approved_signed_total && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.approved_signed_total}
                      onChange={(e) =>
                        handleFilterChange(
                          "approved_signed_total",
                          e.target.value,
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "approved_signed_total",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.total_decrease && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.total_decrease}
                      onChange={(e) =>
                        handleFilterChange("total_decrease", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_decrease",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.total_increase && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.total_increase}
                      onChange={(e) =>
                        handleFilterChange("total_increase", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_increase",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.subsection && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.subsection}
                      onChange={(e) =>
                        handleFilterChange("subsection", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "subsection",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.notes && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.notes}
                      onChange={(e) =>
                        handleFilterChange("notes", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "notes",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.internal_field_1 && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.internal_field_1}
                      onChange={(e) =>
                        handleFilterChange("internal_field_1", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "internal_field_1",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.internal_field_2 && (
                  <th className="px-2 py-2 border-r border-gray-300">
                    <input
                      type="text"
                      value={filters.internal_field_2}
                      onChange={(e) =>
                        handleFilterChange("internal_field_2", e.target.value)
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder="Filter..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "internal_field_2",
                      )}`}
                    />
                  </th>
                )}
                {columnVisibility.actions && (
                  <th className="px-2 py-2">
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => setFilters((prev) => ({ ...prev }))}
                        className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-1 focus:ring-green-500"
                        title="Apply all filters"
                      >
                        🔍
                      </button>
                      <button
                        type="button"
                        onClick={handleClearFilters}
                        className="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-500"
                        title="Clear all filters"
                      >
                        ✕
                      </button>
                    </div>
                  </th>
                )}
              </tr>
            </thead>

            {/* Table Body */}
            <tbody className="bg-gray-50">
              {items.map((item, index) => {
                const isEditing = editingId === item.id;
                const isSaving = savingId === item.id;
                const currentValues = isEditing ? editingValues : {};
                const derivedValues = isEditing
                  ? calculateDerivedValues(item, currentValues)
                  : {
                      total_contract_sum: item.total_contract_sum,
                      total_estimate: item.total_estimate,
                      total_submitted: item.total_submitted,
                      internal_total: item.internal_total,
                      total_approved_by_project_manager:
                        item.total_approved_by_project_manager,
                      approved_signed_total: item.approved_signed_total,
                    };

                const isSelected = selectedBoqRowId === item.id;
                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedBoqRowId(item.id)}
                    className={`table-row-hover border-b border-gray-300 cursor-pointer ${
                      isSelected
                        ? "!bg-blue-200 !border-l-4 !border-l-blue-600"
                        : index % 2 === 0
                          ? "bg-white"
                          : "bg-gray-50"
                    }`}
                  >
                    {columnVisibility.serial_number && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="number"
                            value={
                              currentValues.serial_number !== undefined &&
                              currentValues.serial_number !== null
                                ? currentValues.serial_number
                                : item.serial_number || ""
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "serial_number",
                                parseInt(e.target.value) || null,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.serial_number || "-"
                        )}
                      </td>
                    )}
                    {columnVisibility.structure && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="number"
                            value={
                              currentValues.structure !== undefined &&
                              currentValues.structure !== null
                                ? currentValues.structure
                                : item.structure || ""
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "structure",
                                parseInt(e.target.value) || null,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.structure || "-"
                        )}
                      </td>
                    )}
                    {columnVisibility.system && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            value={
                              currentValues.system !== undefined &&
                              currentValues.system !== null
                                ? currentValues.system
                                : item.system || ""
                            }
                            onChange={(e) =>
                              handleInputChange("system", e.target.value)
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.system || "-"
                        )}
                      </td>
                    )}
                    {columnVisibility.section_number && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900 border-r border-gray-300">
                        <div className="flex items-center gap-2">
                          <span>{item.section_number}</span>
                          {item.has_manual_entries && (
                            <span
                              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
                              title={t("boq.hasManualEntries")}
                            >
                              {t("boq.manualEntry")}
                            </span>
                          )}
                        </div>
                      </td>
                    )}
                    {columnVisibility.description && (
                      <td
                        className="px-3 py-4 text-sm text-gray-900 max-w-xs break-words border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            value={
                              currentValues.description !== undefined &&
                              currentValues.description !== null
                                ? currentValues.description
                                : item.description || ""
                            }
                            onChange={(e) =>
                              handleInputChange("description", e.target.value)
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.description
                        )}
                      </td>
                    )}
                    {columnVisibility.unit && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300">
                        {item.unit}
                      </td>
                    )}
                    {columnVisibility.price && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.01"
                            value={
                              currentValues.price !== undefined &&
                              currentValues.price !== null
                                ? currentValues.price
                                : item.price || 0
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "price",
                                parseFloat(e.target.value) || 0,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          formatCurrency(item.price || 0)
                        )}
                      </td>
                    )}
                    {columnVisibility.original_contract_quantity && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.01"
                            value={
                              currentValues.original_contract_quantity !==
                                undefined &&
                              currentValues.original_contract_quantity !== null
                                ? currentValues.original_contract_quantity
                                : item.original_contract_quantity || 0
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "original_contract_quantity",
                                parseFloat(e.target.value) || 0,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          formatNumber(item.original_contract_quantity || 0)
                        )}
                      </td>
                    )}
                    {columnVisibility.total_contract_sum && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_contract_sum
                            : item.total_contract_sum,
                        )}
                      </td>
                    )}
                    {/* Dynamic Contract Update Quantity Columns */}
                    {contractUpdates.map((update) => {
                      const qtyKey = `updated_contract_quantity_${update.id}`;
                      return columnVisibility[qtyKey] ? (
                        <td
                          key={update.id}
                          className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                          onDoubleClick={() => !isEditing && startEditing(item)}
                        >
                          {isEditing ? (
                            <input
                              type="number"
                              step="0.01"
                              value={getContractUpdateValue(
                                item.id,
                                update.id,
                                "quantity",
                              )}
                              onChange={(e) => {
                                const newQuantity =
                                  parseFloat(e.target.value) || 0;
                                handleUpdateContractQuantity(
                                  update.id,
                                  item.id,
                                  newQuantity,
                                );
                              }}
                              className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                              disabled={isSaving}
                            />
                          ) : (
                            formatNumber(
                              getContractUpdateValue(
                                item.id,
                                update.id,
                                "quantity",
                              ),
                            )
                          )}
                        </td>
                      ) : null;
                    })}
                    {/* Dynamic Contract Update Sum Columns */}
                    {contractUpdates.map((update) => {
                      const sumKey = `updated_contract_sum_${update.id}`;
                      return columnVisibility[sumKey] ? (
                        <td
                          key={update.id}
                          className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer transition-colors"
                          onDoubleClick={() => !isEditing && startEditing(item)}
                        >
                          {formatCurrency(
                            getContractUpdateValue(item.id, update.id, "sum"),
                          )}
                        </td>
                      ) : null;
                    })}
                    {columnVisibility.estimated_quantity && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-red-50"
                        title="Read-only field"
                      >
                        {formatNumber(item.estimated_quantity || 0)}
                      </td>
                    )}
                    {columnVisibility.quantity_submitted && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-blue-50"
                        title="Read-only field"
                      >
                        {formatNumber(item.quantity_submitted || 0)}
                      </td>
                    )}
                    {columnVisibility.internal_quantity && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-yellow-50"
                        title="Read-only field"
                      >
                        {formatNumber(item.internal_quantity || 0)}
                      </td>
                    )}
                    {columnVisibility.approved_by_project_manager && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-green-50"
                        title="Read-only field"
                      >
                        {formatNumber(item.approved_by_project_manager || 0)}
                      </td>
                    )}
                    {columnVisibility.approved_signed_quantity && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-green-100 cursor-pointer hover:bg-green-200 transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.01"
                            value={
                              currentValues.approved_signed_quantity !==
                                undefined &&
                              currentValues.approved_signed_quantity !== null
                                ? currentValues.approved_signed_quantity
                                : item.approved_signed_quantity || 0
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "approved_signed_quantity",
                                parseFloat(e.target.value) || 0,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          formatNumber(item.approved_signed_quantity || 0)
                        )}
                      </td>
                    )}
                    {columnVisibility.quantity_decrease && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-orange-50">
                        {formatNumber(calculateQuantityDecrease(item))}
                      </td>
                    )}
                    {columnVisibility.quantity_increase && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-blue-50">
                        {formatNumber(calculateQuantityIncrease(item))}
                      </td>
                    )}
                    {columnVisibility.total_estimate && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-red-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_estimate
                            : item.total_estimate,
                        )}
                      </td>
                    )}
                    {columnVisibility.total_submitted && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-blue-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_submitted
                            : item.total_submitted,
                        )}
                      </td>
                    )}
                    {columnVisibility.internal_total && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-yellow-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.internal_total
                            : item.internal_total,
                        )}
                      </td>
                    )}
                    {columnVisibility.total_approved_by_project_manager && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-green-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_approved_by_project_manager
                            : item.total_approved_by_project_manager,
                        )}
                      </td>
                    )}
                    {columnVisibility.approved_signed_total && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-green-200">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.approved_signed_total
                            : item.approved_signed_total || 0,
                        )}
                      </td>
                    )}
                    {columnVisibility.total_decrease && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-orange-50">
                        {formatCurrency(calculateTotalDecrease(item))}
                      </td>
                    )}
                    {columnVisibility.total_increase && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-blue-50">
                        {formatCurrency(calculateTotalIncrease(item))}
                      </td>
                    )}

                    {columnVisibility.subsection && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300">
                        {item.subsection || "-"}
                      </td>
                    )}
                    {columnVisibility.notes && (
                      <td
                        className="px-3 py-4 text-sm text-gray-500 max-w-xs break-words border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            value={
                              currentValues.notes !== undefined &&
                              currentValues.notes !== null
                                ? currentValues.notes
                                : item.notes || ""
                            }
                            onChange={(e) =>
                              handleInputChange("notes", e.target.value)
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.notes || "-"
                        )}
                      </td>
                    )}
                    {columnVisibility.internal_field_1 && (
                      <td
                        className="px-3 py-4 text-sm text-gray-500 max-w-xs break-words border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            value={
                              currentValues.internal_field_1 !== undefined &&
                              currentValues.internal_field_1 !== null
                                ? currentValues.internal_field_1
                                : item.internal_field_1 || ""
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "internal_field_1",
                                e.target.value,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.internal_field_1 || "-"
                        )}
                      </td>
                    )}
                    {columnVisibility.internal_field_2 && (
                      <td
                        className="px-3 py-4 text-sm text-gray-500 max-w-xs break-words border-r border-gray-300 cursor-pointer transition-colors"
                        onDoubleClick={() => !isEditing && startEditing(item)}
                        title="Double-click to edit"
                      >
                        {isEditing ? (
                          <input
                            type="text"
                            value={
                              currentValues.internal_field_2 !== undefined &&
                              currentValues.internal_field_2 !== null
                                ? currentValues.internal_field_2
                                : item.internal_field_2 || ""
                            }
                            onChange={(e) =>
                              handleInputChange(
                                "internal_field_2",
                                e.target.value,
                              )
                            }
                            onKeyDown={(e) => handleKeyPress(e, item)}
                            className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                            disabled={isSaving}
                          />
                        ) : (
                          item.internal_field_2 || "-"
                        )}
                      </td>
                    )}
                    {columnVisibility.actions && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                        {isEditing ? (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => saveChanges(item)}
                              disabled={isSaving}
                              className="text-green-600 hover:text-green-800 disabled:opacity-50"
                            >
                              {isSaving ? "Saving..." : "Save"}
                            </button>
                            <button
                              onClick={cancelEditing}
                              disabled={isSaving}
                              className="text-red-600 hover:text-red-800 disabled:opacity-50"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleViewConcentrationSheet(item)}
                              disabled={navigatingToSheet === item.id}
                              className="text-purple-600 hover:text-purple-800 px-2 py-1 rounded text-sm hover:bg-purple-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title={`View concentration sheet for ${item.section_number}: ${item.description}`}
                            >
                              {t(
                                navigatingToSheet === item.id
                                  ? "common.navigating"
                                  : "concentration.viewSheet",
                              )}
                            </button>
                            <button
                              onClick={() => handleDeleteItem(item)}
                              disabled={deletingId === item.id}
                              className="text-red-600 hover:text-red-800 px-2 py-1 rounded text-sm hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title={`Delete BOQ item: ${item.section_number}`}
                            >
                              {deletingId === item.id
                                ? "Deleting..."
                                : "Delete"}
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>

            {/* Frozen Footer with Totals */}
            <tfoot className="sticky bottom-0 z-10 bg-gray-100 border-t-2 border-gray-300 shadow-sm">
              <tr>
                {/* Serial Number - No total */}
                {columnVisibility.serial_number && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Structure - No total */}
                {columnVisibility.structure && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* System - No total */}
                {columnVisibility.system && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Code - No total */}
                {columnVisibility.section_number && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Description - No total */}
                {columnVisibility.description && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Unit - No total */}
                {columnVisibility.unit && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Price - No total */}
                {columnVisibility.price && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Original Contract Quantity - No total */}
                {columnVisibility.original_contract_quantity && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Contract Sum - WITH TOTAL */}
                {columnVisibility.total_contract_sum && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-green-50">
                    {formatCurrency(totals.total_contract_sum)}
                  </td>
                )}
                {/* Dynamic Contract Update Quantity Columns - No totals */}
                {contractUpdates.map((update) => {
                  const qtyKey = `updated_contract_quantity_${update.id}`;
                  return columnVisibility[qtyKey] ? (
                    <td
                      key={`qty-${update.id}`}
                      className="px-3 py-4 bg-gray-50"
                    ></td>
                  ) : null;
                })}
                {/* Dynamic Contract Update Sum Columns - WITH TOTALS */}
                {contractUpdates.map((update) => {
                  const sumKey = `updated_contract_sum_${update.id}`;
                  return columnVisibility[sumKey] ? (
                    <td
                      key={`sum-${update.id}`}
                      className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-green-50"
                    >
                      {/* Calculate total for this contract update based on filtered items */}
                      {formatCurrency(
                        items.reduce((sum, item) => {
                          const contractUpdate = boqItemUpdates.find(
                            (u) =>
                              u.boq_item_id === item.id &&
                              u.contract_update_id === update.id,
                          );
                          return (
                            sum + (contractUpdate?.updated_contract_sum || 0)
                          );
                        }, 0),
                      )}
                    </td>
                  ) : null;
                })}
                {/* Estimated Quantity - No total */}
                {columnVisibility.estimated_quantity && (
                  <td className="px-3 py-4 bg-red-50"></td>
                )}
                {/* Quantity Submitted - No total */}
                {columnVisibility.quantity_submitted && (
                  <td className="px-3 py-4 bg-blue-50"></td>
                )}
                {/* Internal Quantity - No total */}
                {columnVisibility.internal_quantity && (
                  <td className="px-3 py-4 bg-yellow-50"></td>
                )}
                {/* Approved by Project Manager - No total */}
                {columnVisibility.approved_by_project_manager && (
                  <td className="px-3 py-4 bg-green-50"></td>
                )}
                {/* Approved Signed Quantity - No total */}
                {columnVisibility.approved_signed_quantity && (
                  <td className="px-3 py-4 bg-green-100"></td>
                )}
                {/* Quantity Decrease - No total */}
                {columnVisibility.quantity_decrease && (
                  <td className="px-3 py-4 bg-orange-50"></td>
                )}
                {/* Quantity Increase - No total */}
                {columnVisibility.quantity_increase && (
                  <td className="px-3 py-4 bg-blue-50"></td>
                )}
                {/* Total Estimate - WITH TOTAL */}
                {columnVisibility.total_estimate && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-red-100">
                    {formatCurrency(totals.total_estimate)}
                  </td>
                )}
                {/* Total Submitted - WITH TOTAL */}
                {columnVisibility.total_submitted && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-blue-100">
                    {formatCurrency(totals.total_submitted)}
                  </td>
                )}
                {/* Internal Total - WITH TOTAL */}
                {columnVisibility.internal_total && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-yellow-100">
                    {formatCurrency(totals.internal_total)}
                  </td>
                )}
                {/* Total Approved by Project Manager - WITH TOTAL */}
                {columnVisibility.total_approved_by_project_manager && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-green-100">
                    {formatCurrency(totals.total_approved_by_project_manager)}
                  </td>
                )}
                {/* Approved Signed Total - WITH TOTAL */}
                {columnVisibility.approved_signed_total && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-green-200">
                    {formatCurrency(
                      items.reduce(
                        (sum, item) => sum + (item.approved_signed_total || 0),
                        0,
                      ),
                    )}
                  </td>
                )}
                {/* Total Decrease - WITH TOTAL */}
                {columnVisibility.total_decrease && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-orange-100">
                    {formatCurrency(totals.total_decrease)}
                  </td>
                )}
                {/* Total Increase - WITH TOTAL */}
                {columnVisibility.total_increase && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-blue-100">
                    {formatCurrency(totals.total_increase)}
                  </td>
                )}
                {/* Subchapter - No total */}
                {columnVisibility.subsection && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Notes - No total */}
                {columnVisibility.notes && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Internal Field 1 - No total */}
                {columnVisibility.internal_field_1 && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Internal Field 2 - No total */}
                {columnVisibility.internal_field_2 && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
                {/* Actions - No total */}
                {columnVisibility.actions && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Empty State */}
      {!loading && items.length === 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-gray-500">
            <p className="text-lg font-medium">{t("boq.noItemsFound")}</p>
            <p className="text-sm mt-1">
              {searchQuery || selectedSubchapter
                ? t("boq.tryAdjustingSearchCriteria")
                : t("boq.importBOQFileToSeeItems")}
            </p>
          </div>
        </div>
      )}

      {/* Column Settings Modal */}
      {showColumnSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div
              className={`flex justify-between items-center mb-4 ${
                isRTL ? "flex-row-reverse" : ""
              }`}
            >
              <h3 className="text-lg font-semibold text-gray-900">
                {t("boq.columnSettings")}
              </h3>
              <button
                onClick={() => setShowColumnSettings(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="sr-only">Close</span>
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
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
                {t("boq.toggleColumnVisibilityDescription")}
              </p>
              {contractUpdates.length > 0 && (
                <p className="text-xs text-gray-500 mb-3">
                  <span className="font-medium">{t("common.note")}:</span>{" "}
                  {t("boq.contractUpdateColumnsNote")}
                </p>
              )}
              <button
                onClick={resetColumnVisibility}
                className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded hover:bg-blue-200"
              >
                Reset to Default
              </button>
            </div>

            <div className="grid grid-cols-1 gap-2">
              {/* Static columns in BOQ table order */}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.serial_number}
                  onChange={() => toggleColumnVisibility("serial_number")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Serial Number</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.structure}
                  onChange={() => toggleColumnVisibility("structure")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.structure")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.system}
                  onChange={() => toggleColumnVisibility("system")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{t("boq.system")}</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.section_number}
                  onChange={() => toggleColumnVisibility("section_number")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.sectionNumber")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.description}
                  onChange={() => toggleColumnVisibility("description")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.description")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.unit}
                  onChange={() => toggleColumnVisibility("unit")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{t("boq.unit")}</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.original_contract_quantity}
                  onChange={() =>
                    toggleColumnVisibility("original_contract_quantity")
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.contractQty")}
                </span>
              </label>

              {/* Contract Update Quantity Columns */}
              {contractUpdates.map((update) => {
                const qtyKey = `updated_contract_quantity_${update.id}`;
                return (
                  <label
                    key={`qty-${update.id}`}
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={columnVisibility[qtyKey] || false}
                      onChange={() =>
                        toggleColumnVisibility(
                          qtyKey as keyof typeof columnVisibility,
                        )
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">
                      {update.update_name}
                    </span>
                  </label>
                );
              })}

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.price}
                  onChange={() => toggleColumnVisibility("price")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{t("boq.price")}</span>
              </label>

              {/* Contract Update Sum Columns */}
              {contractUpdates.map((update) => {
                const sumKey = `updated_contract_sum_${update.id}`;
                return (
                  <label
                    key={`sum-${update.id}`}
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={columnVisibility[sumKey] || false}
                      onChange={() =>
                        toggleColumnVisibility(
                          sumKey as keyof typeof columnVisibility,
                        )
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">
                      {update.update_name.replace("Qty", "Sum")}
                    </span>
                  </label>
                );
              })}

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_contract_sum}
                  onChange={() => toggleColumnVisibility("total_contract_sum")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.contractSum")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.estimated_quantity}
                  onChange={() => toggleColumnVisibility("estimated_quantity")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.estimatedQuantity")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.quantity_submitted}
                  onChange={() => toggleColumnVisibility("quantity_submitted")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.quantitySubmitted")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.internal_quantity}
                  onChange={() => toggleColumnVisibility("internal_quantity")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.internalQuantity")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.approved_by_project_manager}
                  onChange={() =>
                    toggleColumnVisibility("approved_by_project_manager")
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.approvedQuantity")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.approved_signed_quantity}
                  onChange={() =>
                    toggleColumnVisibility("approved_signed_quantity")
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.approvedSignedQuantity")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.quantity_decrease}
                  onChange={() => toggleColumnVisibility("quantity_decrease")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.quantityDecrease")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.quantity_increase}
                  onChange={() => toggleColumnVisibility("quantity_increase")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.quantityIncrease")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_estimate}
                  onChange={() => toggleColumnVisibility("total_estimate")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.totalEstimate")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_submitted}
                  onChange={() => toggleColumnVisibility("total_submitted")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.totalSubmitted")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.internal_total}
                  onChange={() => toggleColumnVisibility("internal_total")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.internalTotal")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_approved_by_project_manager}
                  onChange={() =>
                    toggleColumnVisibility("total_approved_by_project_manager")
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.totalApproved")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.approved_signed_total}
                  onChange={() =>
                    toggleColumnVisibility("approved_signed_total")
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.approvedSignedTotal")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_decrease}
                  onChange={() => toggleColumnVisibility("total_decrease")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.totalDecrease")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_increase}
                  onChange={() => toggleColumnVisibility("total_increase")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.totalIncrease")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.subsection}
                  onChange={() => toggleColumnVisibility("subsection")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.subchapter")}
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.notes}
                  onChange={() => toggleColumnVisibility("notes")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{t("boq.notes")}</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.internal_field_1}
                  onChange={() => toggleColumnVisibility("internal_field_1")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Internal Field 1</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.internal_field_2}
                  onChange={() => toggleColumnVisibility("internal_field_2")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Internal Field 2</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.actions}
                  onChange={() => toggleColumnVisibility("actions")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  {t("boq.actions")}
                </span>
              </label>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowColumnSettings(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                {t("common.close")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {/* ============ MARKER: Line 4425 - Export loading prop ============ */}
      <BOQExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        onExport={handleExport}
        loading={exporting}
        title="Export BOQ Items Table"
        contractUpdates={contractUpdates}
      />
    </div>
  );
};

export default BOQItems;
