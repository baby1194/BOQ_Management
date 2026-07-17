import { useCallback, useEffect, useMemo, useState } from "react";
import { getProjectItem, setProjectItem } from "./localStorage";

export type SummaryNumericFilterKey =
  | "total_decreases"
  | "total_increases"
  | "total_contract_sum"
  | "total_estimate"
  | "total_submitted"
  | "internal_total"
  | "total_approved"
  | "approved_signed_total"
  | "partial_submitted_total"
  | "item_count";

export type SummaryTableFiltersState = {
  key: string;
  description: string;
  total_decreases: string;
  total_increases: string;
  total_contract_sum: string;
  total_estimate: string;
  total_submitted: string;
  internal_total: string;
  total_approved: string;
  approved_signed_total: string;
  partial_submitted_total: string;
  item_count: string;
  contract_updates: Record<number, string>;
};

export type SummaryRowLike = {
  description: string;
  total_contract_sum: number;
  contract_update_sums: Record<number, number>;
  total_estimate: number;
  total_submitted: number;
  internal_total: number;
  total_approved: number;
  approved_signed_total: number;
  partial_submitted_total: number;
  item_count: number;
};

const EMPTY_FILTERS: SummaryTableFiltersState = {
  key: "",
  description: "",
  total_decreases: "",
  total_increases: "",
  total_contract_sum: "",
  total_estimate: "",
  total_submitted: "",
  internal_total: "",
  total_approved: "",
  approved_signed_total: "",
  partial_submitted_total: "",
  item_count: "",
  contract_updates: {},
};

export function parseNumericFilter(
  filterValue: string,
  itemValue: number
): boolean {
  if (!filterValue.trim()) return true;

  const trimmedValue = filterValue.trim();

  if (trimmedValue.startsWith(">=")) {
    const value = parseFloat(trimmedValue.substring(2));
    return !isNaN(value) && itemValue >= value;
  }
  if (trimmedValue.startsWith("<=")) {
    const value = parseFloat(trimmedValue.substring(2));
    return !isNaN(value) && itemValue <= value;
  }
  if (trimmedValue.startsWith(">")) {
    const value = parseFloat(trimmedValue.substring(1));
    return !isNaN(value) && itemValue > value;
  }
  if (trimmedValue.startsWith("<")) {
    const value = parseFloat(trimmedValue.substring(1));
    return !isNaN(value) && itemValue < value;
  }
  if (trimmedValue.startsWith("=")) {
    const value = parseFloat(trimmedValue.substring(1));
    return !isNaN(value) && itemValue === value;
  }

  const value = parseFloat(trimmedValue);
  return !isNaN(value) && itemValue === value;
}

export function summaryDecreases(row: SummaryRowLike): number {
  return row.total_estimate < row.total_contract_sum
    ? row.total_contract_sum - row.total_estimate
    : 0;
}

export function summaryIncreases(row: SummaryRowLike): number {
  return row.total_estimate > row.total_contract_sum
    ? row.total_estimate - row.total_contract_sum
    : 0;
}

function loadFilters(storageKey: string): SummaryTableFiltersState {
  const saved = getProjectItem(storageKey);
  if (!saved) return { ...EMPTY_FILTERS, contract_updates: {} };
  try {
    const parsed = JSON.parse(saved);
    return {
      ...EMPTY_FILTERS,
      ...parsed,
      contract_updates: parsed.contract_updates || {},
    };
  } catch {
    return { ...EMPTY_FILTERS, contract_updates: {} };
  }
}

function loadDropdown(storageKey: string): string[] {
  const saved = getProjectItem(storageKey);
  if (!saved) return [];
  try {
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function getSummaryFilterInputClass(value: string): string {
  const base =
    "w-full px-2 py-1 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-blue-500";
  return value.trim()
    ? `${base} border-green-300 bg-green-50`
    : `${base} border-gray-300`;
}

export function useSummaryTableFilters<T extends SummaryRowLike>(
  storageKeyPrefix: string,
  rows: T[],
  getKey: (row: T) => string
) {
  const filtersKey = `${storageKeyPrefix}-filters`;
  const dropdownKey = `${storageKeyPrefix}-dropdown-filters`;

  const [filters, setFilters] = useState<SummaryTableFiltersState>(() =>
    loadFilters(filtersKey)
  );
  const [dropdownSelected, setDropdownSelected] = useState<string[]>(() =>
    loadDropdown(dropdownKey)
  );
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    setProjectItem(filtersKey, JSON.stringify(filters));
  }, [filters, filtersKey]);

  useEffect(() => {
    setProjectItem(dropdownKey, JSON.stringify(dropdownSelected));
  }, [dropdownSelected, dropdownKey]);

  const uniqueKeys = useMemo(() => {
    const values = Array.from(new Set(rows.map((row) => getKey(row)))).filter(
      Boolean
    );
    return values.sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
    );
  }, [rows, getKey]);

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const key = getKey(row);
      const matchesKeyText =
        !filters.key ||
        key.toLowerCase().includes(filters.key.toLowerCase());
      const matchesKeyDropdown =
        dropdownSelected.length === 0 || dropdownSelected.includes(key);
      const matchesDescription =
        !filters.description ||
        (row.description || "")
          .toLowerCase()
          .includes(filters.description.toLowerCase());

      const numericChecks: Array<[string, number]> = [
        [filters.total_decreases, summaryDecreases(row)],
        [filters.total_increases, summaryIncreases(row)],
        [filters.total_contract_sum, row.total_contract_sum || 0],
        [filters.total_estimate, row.total_estimate || 0],
        [filters.total_submitted, row.total_submitted || 0],
        [filters.internal_total, row.internal_total || 0],
        [filters.total_approved, row.total_approved || 0],
        [filters.approved_signed_total, row.approved_signed_total || 0],
        [filters.partial_submitted_total, row.partial_submitted_total || 0],
        [filters.item_count, row.item_count || 0],
      ];

      const matchesNumeric = numericChecks.every(([filterValue, itemValue]) =>
        parseNumericFilter(filterValue, itemValue)
      );

      const matchesContractUpdates = Object.entries(
        filters.contract_updates || {}
      ).every(([updateId, filterValue]) => {
        if (!filterValue?.trim()) return true;
        const sum = row.contract_update_sums[parseInt(updateId, 10)] || 0;
        return parseNumericFilter(filterValue, sum);
      });

      return (
        matchesKeyText &&
        matchesKeyDropdown &&
        matchesDescription &&
        matchesNumeric &&
        matchesContractUpdates
      );
    });
  }, [rows, filters, dropdownSelected, getKey]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    Object.entries(filters).forEach(([key, value]) => {
      if (key === "contract_updates") {
        Object.values(value as Record<number, string>).forEach((v) => {
          if (v?.trim()) count += 1;
        });
      } else if (typeof value === "string" && value.trim()) {
        count += 1;
      }
    });
    if (dropdownSelected.length > 0) count += 1;
    return count;
  }, [filters, dropdownSelected]);

  const handleFilterChange = useCallback(
    (field: Exclude<keyof SummaryTableFiltersState, "contract_updates">, value: string) => {
      setFilters((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  const handleContractUpdateFilterChange = useCallback(
    (updateId: number, value: string) => {
      setFilters((prev) => ({
        ...prev,
        contract_updates: {
          ...prev.contract_updates,
          [updateId]: value,
        },
      }));
    },
    []
  );

  const handleClearFilters = useCallback(() => {
    setFilters({ ...EMPTY_FILTERS, contract_updates: {} });
    setDropdownSelected([]);
    setDropdownOpen(false);
  }, []);

  const handleDropdownSelectionChange = useCallback((values: string[]) => {
    setDropdownSelected(values);
  }, []);

  const handleClearDropdownFilter = useCallback(() => {
    setDropdownSelected([]);
  }, []);

  const handleToggleDropdown = useCallback(() => {
    setDropdownOpen((open) => !open);
  }, []);

  const handleCloseDropdown = useCallback(() => {
    setDropdownOpen(false);
  }, []);

  return {
    filters,
    filteredRows,
    uniqueKeys,
    dropdownSelected,
    dropdownOpen,
    activeFiltersCount,
    handleFilterChange,
    handleContractUpdateFilterChange,
    handleClearFilters,
    handleDropdownSelectionChange,
    handleClearDropdownFilter,
    handleToggleDropdown,
    handleCloseDropdown,
  };
}
