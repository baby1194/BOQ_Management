import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  boqApi,
  searchApi,
  importApi,
  projectInfoApi,
  contractUpdatesApi,
  exportApi,
} from "../services/api";
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

const BOQItems: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<BOQItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState<"both" | "code" | "description">(
    "both"
  );
  const [selectedSubchapter, setSelectedSubchapter] = useState<string>("");
  const [subchapters, setSubchapters] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingValues, setEditingValues] = useState<Partial<BOQItem>>({});
  const [savingId, setSavingId] = useState<number | null>(null);
  const [navigatingToSheet, setNavigatingToSheet] = useState<number | null>(
    null
  );
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Panel collapse state
  const [panelsCollapsed, setPanelsCollapsed] = useState(false);

  // Project Info state
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [editingProjectInfo, setEditingProjectInfo] = useState(false);
  const [projectInfoDraft, setProjectInfoDraft] = useState<ProjectInfoUpdate>(
    {}
  );
  const [savingProjectInfo, setSavingProjectInfo] = useState(false);
  const [projectInfoError, setProjectInfoError] = useState<string | null>(null);
  const [projectInfoSuccess, setProjectInfoSuccess] = useState<string | null>(
    null
  );

  // Comprehensive filter system
  const [filters, setFilters] = useState({
    // String filters (contains)
    serial_number: "",
    structure: "",
    system: "",
    section_number: "",
    description: "",
    unit: "",
    subsection: "",
    notes: "",

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

    // Contract update filters - will be populated dynamically
    contract_updates: {} as Record<number, { quantity: string; sum: string }>,
  });

  // Dropdown filter states for Structure, System, and Unit columns
  const [dropdownFilters, setDropdownFilters] = useState({
    structure: [] as string[],
    system: [] as string[],
    unit: [] as string[],
  });

  // Dropdown open/close states
  const [dropdownOpen, setDropdownOpen] = useState({
    structure: false,
    system: false,
    unit: false,
  });

  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState({
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
    total_estimate: true,
    total_submitted: true,
    internal_total: true,
    total_approved_by_project_manager: true,
    approved_signed_total: true,
    subsection: true,
    notes: true,
    actions: true,
  });

  // Column visibility settings modal state
  const [showColumnSettings, setShowColumnSettings] = useState(false);

  // Load column visibility preferences from localStorage
  useEffect(() => {
    const savedVisibility = localStorage.getItem("boq-column-visibility");
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
      "boq-column-visibility",
      JSON.stringify(columnVisibility)
    );
  }, [columnVisibility]);

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
      total_estimate: true,
      total_submitted: true,
      internal_total: true,
      total_approved_by_project_manager: true,
      approved_signed_total: true,
      subsection: true,
      notes: true,
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
    []
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

  // Password for BOQ item creation
  // To use environment variables, create a .env file in the frontend directory with:
  // VITE_BOQ_CREATION_PASSWORD=your_secure_password_here
  // Then replace this line with: const BOQ_CREATION_PASSWORD = import.meta.env.VITE_BOQ_CREATION_PASSWORD;
  const BOQ_CREATION_PASSWORD = "password";

  // Password confirmation functions
  const handlePasswordConfirm = () => {
    console.log(
      "Password confirmed, action:",
      passwordAction,
      "itemId:",
      passwordItemId,
      "contractUpdateId:",
      passwordContractUpdateId
    );
    console.log(
      "Entered password:",
      passwordInput,
      "Expected password:",
      BOQ_CREATION_PASSWORD
    );

    if (passwordInput === BOQ_CREATION_PASSWORD) {
      console.log("Password matches, proceeding with action");
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
              passwordContractUpdateId
            );
            handleDeleteContractUpdateAfterPassword(
              passwordItemId || 0,
              passwordContractUpdateId
            );
          } else {
            console.error("No contractUpdateId found for delete action");
          }
          break;
      }
    } else {
      console.log("Password does not match");
      setPasswordError("Incorrect password. Please try again.");
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
    contractUpdateId: number
  ) => {
    setPasswordAction("delete");
    setPasswordItemId(itemId);
    setPasswordContractUpdateId(contractUpdateId);
    setShowPasswordDialog(true);
  };

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
      }),
      {
        total_contract_sum: 0,
        total_estimate: 0,
        total_submitted: 0,
        internal_total: 0,
        total_approved_by_project_manager: 0,
      }
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
    itemValue: number
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

      // Numeric filters
      const matchesOriginalContractQuantity = parseNumericFilter(
        filters.original_contract_quantity,
        item.original_contract_quantity || 0
      );

      const matchesPrice = parseNumericFilter(filters.price, item.price || 0);

      const matchesTotalContractSum = parseNumericFilter(
        filters.total_contract_sum,
        item.total_contract_sum || 0
      );

      const matchesEstimatedQuantity = parseNumericFilter(
        filters.estimated_quantity,
        item.estimated_quantity || 0
      );

      const matchesQuantitySubmitted = parseNumericFilter(
        filters.quantity_submitted,
        item.quantity_submitted || 0
      );

      const matchesInternalQuantity = parseNumericFilter(
        filters.internal_quantity,
        item.internal_quantity || 0
      );

      const matchesApprovedByProjectManager = parseNumericFilter(
        filters.approved_by_project_manager,
        item.approved_by_project_manager || 0
      );

      const matchesTotalEstimate = parseNumericFilter(
        filters.total_estimate,
        item.total_estimate || 0
      );

      const matchesTotalSubmitted = parseNumericFilter(
        filters.total_submitted,
        item.total_submitted || 0
      );

      const matchesInternalTotal = parseNumericFilter(
        filters.internal_total,
        item.internal_total || 0
      );

      const matchesTotalApprovedByProjectManager = parseNumericFilter(
        filters.total_approved_by_project_manager,
        item.total_approved_by_project_manager || 0
      );

      // Contract update filters
      // console.log(Object.entries(filters.contract_updates || {}));
      const matchesContractUpdates = Object.entries(
        filters.contract_updates || {}
      ).every(([updateId, update]) => {
        // console.log("updateId", updateId);
        // console.log("update", update);
        // console.log("!update", !update);
        // console.log("typeof update", typeof update);
        // console.log("!update.quantity", !update.quantity);
        // console.log("!update.sum", !update.sum);
        // Safety check: ensure update object exists and has expected structure
        if (
          !update ||
          typeof update !== "object" ||
          (update.quantity.trim() === "" && update.sum.trim() === "")
        ) {
          return true; // Skip invalid filter entries
        }

        // console.log("OKKKKKKKKKKKK");

        // If no filter values, skip this filter
        if (!update.quantity.trim() && !update.sum.trim()) {
          return true;
        }
        // console.log("_________________");
        // Find the update for this specific BOQ item and contract update
        const currentUpdate = boqItemUpdates.find(
          (u) =>
            u.boq_item_id === item.id &&
            u.contract_update_id === parseInt(updateId)
        );

        // Debug logging
        // console.log(
        //   `Filtering BOQ item ${item.id} for contract update ${updateId}:`,
        //   {
        //     itemId: item.id,
        //     updateId: parseInt(updateId),
        //     filterValues: update,
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
          !update.quantity.trim() ||
          parseNumericFilter(
            update.quantity,
            currentUpdate.updated_contract_quantity || 0
          );

        // Check sum filter
        const matchesSum =
          !update.sum.trim() ||
          parseNumericFilter(
            update.sum,
            currentUpdate.updated_contract_sum || 0
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
            if (update && update.quantity && update.quantity.trim() !== "")
              count++;
            if (update && update.sum && update.sum.trim() !== "") count++;
          });
        }
      } else if (typeof value === "string" && value.trim() !== "") {
        count++;
      }
    });

    // Count dropdown filters
    Object.values(dropdownFilters).forEach((selectedValues) => {
      if (selectedValues.length > 0) count++;
    });

    return count;
  }, [filters, dropdownFilters]);

  // Get unique values for dropdown filters
  const uniqueValues = useMemo(() => {
    const structureValues = [
      ...new Set(
        allItems.map((item) => item.structure?.toString() || "").filter(Boolean)
      ),
    ].sort();
    const systemValues = [
      ...new Set(
        allItems.map((item) => item.system?.toString() || "").filter(Boolean)
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
    selectedValues: string[]
  ) => {
    setDropdownFilters((prev) => ({
      ...prev,
      [column]: selectedValues,
    }));
  };

  const handleClearDropdownFilter = (
    column: "structure" | "system" | "unit"
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
    field: "quantity" | "sum"
  ) => {
    const update = boqItemUpdates.find(
      (update) =>
        update.boq_item_id === boqItemId &&
        update.contract_update_id === updateId
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
        hasValue = Object.values(contractUpdateFilters).some(
          (update) =>
            update &&
            update.quantity &&
            update.sum &&
            (update.quantity.trim() !== "" || update.sum.trim() !== "")
        );
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
          prevItem.id === item.id ? updatedItem : prevItem
        )
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
        `This will also delete all related concentration sheets and entries. This action cannot be undone.`
    );

    if (!confirmDelete) return;

    try {
      setDeletingId(item.id);
      await boqApi.delete(item.id);

      // Remove item from local state
      setItems((prevItems) =>
        prevItems.filter((prevItem) => prevItem.id !== item.id)
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

  // Fetch BOQ items
  const fetchItems = async () => {
    try {
      setLoading(true);
      setError(null);

      if (searchQuery.trim()) {
        // Search functionality - fetch all matching results
        const response = await searchApi.search(
          searchQuery,
          searchType,
          0, // offset
          10000 // large limit to get all results
        );
        console.log("Search API Response:", response);
        console.log("First item system field:", response.items[0]?.system);
        setAllItems(response.items);
      } else if (selectedSubchapter) {
        // Filter by subchapter - fetch all results
        const response = await searchApi.getBySubchapter(
          selectedSubchapter,
          0, // offset
          10000 // large limit to get all results
        );
        // console.log("Subchapter API Response:", response);
        // console.log("First item system field:", response[0]?.system);
        setAllItems(response);
      } else {
        // Get all items without pagination
        const response = await boqApi.getAll(0, 10000); // large limit to get all results
        // console.log("BOQ API Response:", response);
        // console.log("First item system field:", response[0]?.system);
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
        main_contractor_name: response.main_contractor_name || "",
        subcontractor_name: response.subcontractor_name || "",
        developer_name: response.developer_name || "",
        contract_no: response.contract_no || "",
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
            update.id
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
        "New contract quantity update created successfully!"
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
              "quantity"
            );
          }

          if (request[`include_${sumKey}`]) {
            filteredItem[sumKey] = getContractUpdateValue(
              item.id,
              update.id,
              "sum"
            );
          }
        });

        return filteredItem;
      });

      // Choose the appropriate export function based on format
      const response =
        format === "excel"
          ? await exportApi.exportBOQItemsExcel(request, filteredData)
          : await exportApi.exportBOQItemsPDF(request, filteredData);

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
          `Successfully exported BOQ items as ${formatName}`
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
    newQuantity: number
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
            : update
        )
      );
    } catch (err) {
      console.error("Error updating contract quantity:", err);
      setError("Failed to update contract quantity");
    }
  };

  const handleProjectInfoDraftChange = (
    field: keyof ProjectInfoUpdate,
    value: string
  ) => {
    setProjectInfoDraft((prev) => ({ ...prev, [field]: value }));
  };

  const handleEditProjectInfo = () => {
    setEditingProjectInfo(true);
    setProjectInfoError(null);
  };

  const handleCancelProjectInfo = () => {
    setEditingProjectInfo(false);
    setProjectInfoDraft({
      project_name: projectInfo?.project_name || "",
      main_contractor_name: projectInfo?.main_contractor_name || "",
      subcontractor_name: projectInfo?.subcontractor_name || "",
      developer_name: projectInfo?.developer_name || "",
      contract_no: projectInfo?.contract_no || "",
    });
    setProjectInfoError(null);
  };

  const handleSaveProjectInfo = async () => {
    try {
      setSavingProjectInfo(true);
      setProjectInfoError(null);

      const updatedProjectInfo = await projectInfoApi.update(projectInfoDraft);
      setProjectInfo(updatedProjectInfo);
      setEditingProjectInfo(false);
      setError(null);
      setProjectInfoSuccess(
        "Project information updated successfully! All concentration sheets have been updated. Note: You may need to refresh the Concentration Sheets page to see the changes."
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

  useEffect(() => {
    fetchItems();
  }, [searchQuery, searchType, selectedSubchapter]);

  // Update items when filteredItems change
  useEffect(() => {
    setItems(filteredItems);
  }, [filteredItems]);

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
    value: string
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
    setSearchType("both");

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
          `Successfully created ${response.created_count} concentration sheets!`
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
    contractUpdateId: number
  ) => {
    try {
      console.log("Deleting contract update:", { itemId, contractUpdateId });

      // Delete the contract update using the API
      await contractUpdatesApi.delete(contractUpdateId);

      // Remove the contract update from local state
      setContractUpdates((prev) => {
        const filtered = prev.filter(
          (update) => update.id !== contractUpdateId
        );
        console.log("Updated contract updates:", filtered);
        return filtered;
      });

      // Also remove any BOQ item updates associated with this contract update
      setBoqItemUpdates((prev) => {
        const filtered = prev.filter(
          (update) => update.contract_update_id !== contractUpdateId
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
          <h1 className="text-3xl font-bold text-gray-900">BOQ Items</h1>
          <p className="mt-2 text-gray-600">
            Manage your Bill of Quantities items
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">BOQ Items</h1>
          <p className="mt-2 text-gray-600">
            Manage your Bill of Quantities items ({items.length} items)
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
                  ? "Expand all panels"
                  : "Collapse all panels except BOQ table"
              }
            >
              {panelsCollapsed ? "🔓 Expand Panels" : "📦 Collapse Panels"}
            </button>
            <button
              onClick={handleShowAddForm}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              + Add BOQ Item
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
              {creatingUpdate ? "Creating..." : "Update Contract Quantity"}
            </button>
            <button
              onClick={createConcentrationSheets}
              disabled={items.length === 0 || loading}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create Concentration Sheets
            </button>
            <button
              onClick={() => setShowColumnSettings(true)}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              ⚙️ Column Settings
            </button>
            <button
              onClick={() => setShowExportModal(true)}
              disabled={items.length === 0 || loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              📊 Export Table
            </button>
          </div>
        </div>
      </div>

      {/* Contract Updates Info */}
      {!panelsCollapsed && contractUpdates.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-sm font-medium text-blue-900">
                Contract Quantity Updates ({contractUpdates.length} active)
              </h3>
              <p className="text-sm text-blue-700 mt-1">
                Use the "Update Contract Quantity" button to create new contract
                quantity versions. Each update creates editable columns for
                quantities and automatically calculated sums.
              </p>
            </div>
            <button
              onClick={handleCreateContractUpdate}
              disabled={creatingUpdate}
              className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {creatingUpdate ? "Creating..." : "+ New Update"}
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
                    <p className="text-xs text-blue-600">
                      Created:{" "}
                      {new Date(update.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      handleDeleteContractUpdateClick(0, update.id)
                    }
                    className="text-red-600 hover:text-red-800 text-sm px-2 py-1 rounded hover:bg-red-50"
                    title="Delete this contract update"
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
              <h2 className="text-xl font-semibold text-gray-900">
                Project Information
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                This information will be automatically synced to all
                concentration sheets
              </p>
            </div>
            {!editingProjectInfo && (
              <button
                onClick={handleEditProjectInfo}
                className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                Edit
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
                Project Name
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.project_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange("project_name", e.target.value)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter project name"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.project_name || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project Name (Hebrew)
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.project_name_hebrew || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "project_name_hebrew",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="שם הפרויקט"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.project_name_hebrew || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Main Contractor Name
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.main_contractor_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "main_contractor_name",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter main contractor name"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.main_contractor_name || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subcontractor Name
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.subcontractor_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "subcontractor_name",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter subcontractor name"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.subcontractor_name || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Developer Name
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.developer_name || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "developer_name",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter developer name"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.developer_name || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contract No.
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.contract_no || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange("contract_no", e.target.value)
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter contract number"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.contract_no || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Invoice No for Submitted QTY
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.invoice_no_submitted_qty || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "invoice_no_submitted_qty",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter invoice number for submitted qty"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.invoice_no_submitted_qty || "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Invoice Date for Submitted QTY
              </label>
              {editingProjectInfo ? (
                <input
                  type="date"
                  value={projectInfoDraft.invoice_date_submitted_qty || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "invoice_date_submitted_qty",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.invoice_date_submitted_qty
                    ? new Date(
                        projectInfo.invoice_date_submitted_qty
                      ).toLocaleDateString()
                    : "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Invoice No for Approved Signed QTY
              </label>
              {editingProjectInfo ? (
                <input
                  type="text"
                  value={projectInfoDraft.invoice_no_approved_signed_qty || ""}
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "invoice_no_approved_signed_qty",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter invoice number for approved signed qty"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.invoice_no_approved_signed_qty ||
                    "Not specified"}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Invoice Date for Approved Signed QTY
              </label>
              {editingProjectInfo ? (
                <input
                  type="date"
                  value={
                    projectInfoDraft.invoice_date_approved_signed_qty || ""
                  }
                  onChange={(e) =>
                    handleProjectInfoDraftChange(
                      "invoice_date_approved_signed_qty",
                      e.target.value
                    )
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              ) : (
                <div className="px-3 py-2 bg-gray-50 rounded-md text-gray-900 min-h-[40px] flex items-center">
                  {projectInfo?.invoice_date_approved_signed_qty
                    ? new Date(
                        projectInfo.invoice_date_approved_signed_qty
                      ).toLocaleDateString()
                    : "Not specified"}
                </div>
              )}
            </div>
          </div>

          {editingProjectInfo && (
            <div className="flex justify-end space-x-3 mt-4 pt-4 border-t border-gray-200">
              <button
                onClick={handleCancelProjectInfo}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProjectInfo}
                disabled={savingProjectInfo}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {savingProjectInfo ? "Saving..." : "Save Changes"}
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
                Add New BOQ Item
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Manually create a new BOQ item. Subsection will be automatically
                extracted from section number.
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
                Section Number *
              </label>
              <input
                type="text"
                required
                value={newItemForm.section_number}
                onChange={(e) =>
                  handleNewItemFormChange("section_number", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., 01.01.01.0010"
              />
              <p className="text-xs text-gray-500 mt-1">
                Subsection will be:{" "}
                {newItemForm.section_number.split(".").length >= 2
                  ? newItemForm.section_number.split(".").slice(0, 2).join(".")
                  : "Enter section number"}
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
                    parseInt(e.target.value) || 0
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter structure number"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description *
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
                Unit *
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
                Original Contract Quantity *
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={newItemForm.original_contract_quantity}
                onChange={(e) =>
                  handleNewItemFormChange(
                    "original_contract_quantity",
                    parseFloat(e.target.value) || 0
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Price *
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={newItemForm.price}
                onChange={(e) =>
                  handleNewItemFormChange(
                    "price",
                    parseFloat(e.target.value) || 0
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
              Calculated Values:
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Total Contract Sum:</span>
                <span className="ml-2 font-medium text-gray-900">
                  {formatCurrency(
                    newItemForm.original_contract_quantity * newItemForm.price
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
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {passwordAction === "create" && "Confirm BOQ Item Creation"}
                {passwordAction === "update" &&
                  "Confirm Contract Quantity Update"}
                {passwordAction === "delete" &&
                  "Confirm Contract Update Deletion"}
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
                  "Please enter the password to confirm creation of this BOQ item."}
                {passwordAction === "update" &&
                  "Please enter the password to confirm updating the contract quantity for this BOQ item."}
                {passwordAction === "delete" &&
                  "Please enter the password to confirm deletion of this contract update. This action cannot be undone."}
              </p>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
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
                placeholder="Enter password"
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
                Cancel
              </button>
              <button
                onClick={handlePasswordConfirm}
                className={`px-4 py-2 text-white rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                  passwordAction === "delete"
                    ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
                    : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-500"
                }`}
              >
                {passwordAction === "create" && "Confirm"}
                {passwordAction === "update" && "Confirm"}
                {passwordAction === "delete" && "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search and Filter Section */}
      {!panelsCollapsed && (
        <div className="bg-white rounded-lg shadow p-6">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Search
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by code or description..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Search Type
                </label>
                <select
                  value={searchType}
                  onChange={(e) => setSearchType(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="both">Both</option>
                  <option value="code">Code Only</option>
                  <option value="description">Description Only</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subchapter
                </label>
                <select
                  value={selectedSubchapter}
                  onChange={(e) => setSelectedSubchapter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Subchapters</option>
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
            <div className="text-sm text-gray-600 bg-blue-50 px-3 py-2 rounded-md mb-4">
              💡 <strong>Filter Tips:</strong> Column filters are now located
              beneath each column header in the table below. Use{" "}
              <code className="bg-white px-1 rounded">&gt;100</code>,{" "}
              <code className="bg-white px-1 rounded">&lt;50</code>,
              <code className="bg-white px-1 rounded">=25</code> for numeric
              fields. Press Enter in any filter field to apply.
            </div>

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
        <div className="overflow-auto max-h-[70vh]">
          <table className="min-w-full border border-gray-300">
            {/* Frozen Header */}
            <thead className="sticky top-0 z-10 bg-gray-50 shadow-sm border-t-2">
              {/* Column Headers Row */}
              <tr className="border-b border-gray-300 bg-gray-50">
                {columnVisibility.serial_number && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[80px]">
                    Serial
                  </th>
                )}
                {columnVisibility.structure && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[80px]">
                    <div className="flex items-center justify-between">
                      <span>Structure</span>
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
                      <span>System</span>
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
                    Code
                  </th>
                )}
                {columnVisibility.description && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[200px]">
                    Description
                  </th>
                )}
                {columnVisibility.unit && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[80px]">
                    <div className="flex items-center justify-between">
                      <span>Unit</span>
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
                {columnVisibility.original_contract_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px]">
                    Contract Qty
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
                {columnVisibility.price && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px]">
                    Price
                  </th>
                )}
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
                {columnVisibility.total_contract_sum && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px]">
                    Contract Sum
                  </th>
                )}
                {columnVisibility.estimated_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px] bg-red-100">
                    Est. Qty
                  </th>
                )}
                {columnVisibility.quantity_submitted && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-blue-100">
                    Submitted Qty
                  </th>
                )}
                {columnVisibility.internal_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[100px] bg-yellow-100">
                    Internal Qty
                  </th>
                )}
                {columnVisibility.approved_by_project_manager && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-100">
                    Approved Qty
                  </th>
                )}
                {columnVisibility.approved_signed_quantity && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-200">
                    Approved Signed Qty
                  </th>
                )}
                {columnVisibility.total_estimate && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-red-100">
                    Total Est.
                  </th>
                )}
                {columnVisibility.total_submitted && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-blue-100">
                    Total Submitted
                  </th>
                )}
                {columnVisibility.internal_total && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-yellow-100">
                    Internal Total
                  </th>
                )}
                {columnVisibility.total_approved_by_project_manager && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-100">
                    Total Approved
                  </th>
                )}
                {columnVisibility.approved_signed_total && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[120px] bg-green-200">
                    Approved Signed Total
                  </th>
                )}
                {columnVisibility.subsection && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[150px]">
                    Subchapter
                  </th>
                )}
                {columnVisibility.notes && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 min-w-[150px]">
                    Notes
                  </th>
                )}
                {columnVisibility.actions && (
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[120px]">
                    Actions
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
                        "serial_number"
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
                        "structure"
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
                        "system"
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
                        "section_number"
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
                        "description"
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
                        "unit"
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
                          e.target.value
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "original_contract_quantity"
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
                            e.target.value
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
                        "price"
                      )}`}
                    />
                  </th>
                )}
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
                            e.target.value
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
                        "total_contract_sum"
                      )}`}
                    />
                  </th>
                )}
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
                        "estimated_quantity"
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
                        "quantity_submitted"
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
                        "internal_quantity"
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
                          e.target.value
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "approved_by_project_manager"
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
                          e.target.value
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">100, <50, =25..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "approved_signed_quantity"
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
                        "total_estimate"
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
                        "total_submitted"
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
                        "internal_total"
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
                          e.target.value
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "total_approved_by_project_manager"
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
                          e.target.value
                        )
                      }
                      onKeyDown={handleFilterKeyDown}
                      placeholder=">1000, <500, =250..."
                      className={`w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500 ${getFilterInputClass(
                        "approved_signed_total"
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
                        "subsection"
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
                        "notes"
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

                return (
                  <tr
                    key={item.id}
                    className={`hover:bg-gray-100 border-b border-gray-300 ${
                      index % 2 === 0 ? "bg-white" : "bg-gray-50"
                    }`}
                  >
                    {columnVisibility.serial_number && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                                parseInt(e.target.value) || null
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
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                                parseInt(e.target.value) || null
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
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                        {item.section_number}
                      </td>
                    )}
                    {columnVisibility.description && (
                      <td
                        className="px-3 py-4 text-sm text-gray-900 max-w-xs truncate border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                    {columnVisibility.original_contract_quantity && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                                parseFloat(e.target.value) || 0
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
                    {contractUpdates.map((update) => {
                      const qtyKey = `updated_contract_quantity_${update.id}`;
                      return columnVisibility[qtyKey] ? (
                        <td
                          key={update.id}
                          className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
                          onDoubleClick={() => !isEditing && startEditing(item)}
                        >
                          {isEditing ? (
                            <input
                              type="number"
                              step="0.01"
                              value={getContractUpdateValue(
                                item.id,
                                update.id,
                                "quantity"
                              )}
                              onChange={(e) => {
                                const newQuantity =
                                  parseFloat(e.target.value) || 0;
                                handleUpdateContractQuantity(
                                  update.id,
                                  item.id,
                                  newQuantity
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
                                "quantity"
                              )
                            )
                          )}
                        </td>
                      ) : null;
                    })}
                    {columnVisibility.price && (
                      <td
                        className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                                parseFloat(e.target.value) || 0
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
                    {contractUpdates.map((update) => {
                      const sumKey = `updated_contract_sum_${update.id}`;
                      return columnVisibility[sumKey] ? (
                        <td
                          key={update.id}
                          className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
                          onDoubleClick={() => !isEditing && startEditing(item)}
                        >
                          {formatCurrency(
                            getContractUpdateValue(item.id, update.id, "sum")
                          )}
                        </td>
                      ) : null;
                    })}
                    {columnVisibility.total_contract_sum && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_contract_sum
                            : item.total_contract_sum
                        )}
                      </td>
                    )}
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
                                parseFloat(e.target.value) || 0
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
                    {columnVisibility.total_estimate && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-red-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_estimate
                            : item.total_estimate
                        )}
                      </td>
                    )}
                    {columnVisibility.total_submitted && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-blue-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_submitted
                            : item.total_submitted
                        )}
                      </td>
                    )}
                    {columnVisibility.internal_total && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-yellow-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.internal_total
                            : item.internal_total
                        )}
                      </td>
                    )}
                    {columnVisibility.total_approved_by_project_manager && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-green-100">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.total_approved_by_project_manager
                            : item.total_approved_by_project_manager
                        )}
                      </td>
                    )}
                    {columnVisibility.approved_signed_total && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300 bg-green-200">
                        {formatCurrency(
                          isEditing
                            ? derivedValues.approved_signed_total
                            : item.approved_signed_total || 0
                        )}
                      </td>
                    )}

                    {columnVisibility.subsection && (
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 border-r border-gray-300">
                        {item.subsection || "-"}
                      </td>
                    )}
                    {columnVisibility.notes && (
                      <td
                        className="px-3 py-4 text-sm text-gray-500 max-w-xs truncate border-r border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors"
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
                              {navigatingToSheet === item.id
                                ? "Navigating..."
                                : "View Sheet"}
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
                {/* Original Contract Quantity - No total */}
                {columnVisibility.original_contract_quantity && (
                  <td className="px-3 py-4 bg-gray-50"></td>
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
                {/* Price - No total */}
                {columnVisibility.price && (
                  <td className="px-3 py-4 bg-gray-50"></td>
                )}
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
                              u.contract_update_id === update.id
                          );
                          return (
                            sum + (contractUpdate?.updated_contract_sum || 0)
                          );
                        }, 0)
                      )}
                    </td>
                  ) : null;
                })}
                {/* Contract Sum - WITH TOTAL */}
                {columnVisibility.total_contract_sum && (
                  <td className="px-3 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 bg-green-50">
                    {formatCurrency(totals.total_contract_sum)}
                  </td>
                )}
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
                        0
                      )
                    )}
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
          <div className="text-center text-gray-500">
            <p className="text-lg font-medium">No BOQ items found</p>
            <p className="text-sm mt-1">
              {searchQuery || selectedSubchapter
                ? "Try adjusting your search criteria"
                : "Import your BOQ file to see items here"}
            </p>
          </div>
        </div>
      )}

      {/* Column Settings Modal */}
      {showColumnSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Column Visibility Settings
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
                Toggle the visibility of columns in the BOQ table. Your
                preferences will be saved automatically.
              </p>
              {contractUpdates.length > 0 && (
                <p className="text-xs text-gray-500 mb-3">
                  <span className="font-medium">Note:</span> Contract update
                  columns are always visible when contract updates exist and
                  cannot be hidden.
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
                <span className="text-sm text-gray-700">Structure</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.system}
                  onChange={() => toggleColumnVisibility("system")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">System</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.section_number}
                  onChange={() => toggleColumnVisibility("section_number")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  Section Number (Code)
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.description}
                  onChange={() => toggleColumnVisibility("description")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Description</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.unit}
                  onChange={() => toggleColumnVisibility("unit")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Unit</span>
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
                <span className="text-sm text-gray-700">Contract Qty</span>
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
                          qtyKey as keyof typeof columnVisibility
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
                <span className="text-sm text-gray-700">Price</span>
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
                          sumKey as keyof typeof columnVisibility
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
                <span className="text-sm text-gray-700">Contract Sum</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.estimated_quantity}
                  onChange={() => toggleColumnVisibility("estimated_quantity")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Est. Qty</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.quantity_submitted}
                  onChange={() => toggleColumnVisibility("quantity_submitted")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Submitted Qty</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.internal_quantity}
                  onChange={() => toggleColumnVisibility("internal_quantity")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Internal Qty</span>
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
                <span className="text-sm text-gray-700">Approved Qty</span>
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
                  Approved Signed Qty
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_estimate}
                  onChange={() => toggleColumnVisibility("total_estimate")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Total Est.</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.total_submitted}
                  onChange={() => toggleColumnVisibility("total_submitted")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Total Submitted</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.internal_total}
                  onChange={() => toggleColumnVisibility("internal_total")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Internal Total</span>
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
                <span className="text-sm text-gray-700">Total Approved</span>
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
                  Approved Signed Total
                </span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.subsection}
                  onChange={() => toggleColumnVisibility("subsection")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Subchapter</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.notes}
                  onChange={() => toggleColumnVisibility("notes")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Notes</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={columnVisibility.actions}
                  onChange={() => toggleColumnVisibility("actions")}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Actions</span>
              </label>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowColumnSettings(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
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
