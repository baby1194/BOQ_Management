import { useCallback, useMemo, useState } from "react";

export function sortUniqueValues(values: string[]): string[] {
  return Array.from(new Set(values)).sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
  );
}

export function filterCellValue(
  value: string | number | null | undefined
): string {
  if (value == null) return "";
  return String(value);
}

export function matchesSelectedFilter(
  value: string,
  selected: string[]
): boolean {
  return selected.length === 0 || selected.includes(value);
}

export function createEmptyFilterMap<K extends string>(
  keys: readonly K[]
): Record<K, string[]> {
  return Object.fromEntries(keys.map((key) => [key, [] as string[]])) as Record<
    K,
    string[]
  >;
}

export function createEmptyOpenMap<K extends string>(
  keys: readonly K[]
): Record<K, boolean> {
  return Object.fromEntries(keys.map((key) => [key, false])) as Record<
    K,
    boolean
  >;
}

export function useColumnDropdownFilters<K extends string>(
  keys: readonly K[]
) {
  const [selected, setSelected] = useState(() => createEmptyFilterMap(keys));
  const [open, setOpen] = useState(() => createEmptyOpenMap(keys));

  const handleSelectionChange = useCallback((key: K, values: string[]) => {
    setSelected((prev) => ({ ...prev, [key]: values }));
  }, []);

  const handleClear = useCallback((key: K) => {
    setSelected((prev) => ({ ...prev, [key]: [] }));
  }, []);

  const handleClearAll = useCallback(() => {
    setSelected(createEmptyFilterMap(keys));
    setOpen(createEmptyOpenMap(keys));
  }, [keys]);

  const handleToggle = useCallback((key: K) => {
    setOpen((prev) => {
      const next = createEmptyOpenMap(keys);
      next[key] = !prev[key];
      return next;
    });
  }, [keys]);

  const handleClose = useCallback((key: K) => {
    setOpen((prev) => ({ ...prev, [key]: false }));
  }, []);

  const activeFilterCount = useMemo(
    () => Object.values(selected).filter((vals) => (vals as string[]).length > 0).length,
    [selected]
  );

  return {
    selected,
    open,
    activeFilterCount,
    handleSelectionChange,
    handleClear,
    handleClearAll,
    handleToggle,
    handleClose,
  };
}
