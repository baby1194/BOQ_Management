import { getProjectItem, setProjectItem } from "./localStorage";
import type { ConcentrationEntryExportRequest } from "../types";

/** localStorage keys for export / print column selections */
export const EXPORT_PREFS_KEYS = {
  boq: "boq-export-columns",
  summary: "summary-export-columns",
  concentrationEntry: "concentration-entry-export-columns",
} as const;

export const buildDefaultConcentrationEntryExportRequest =
  (): ConcentrationEntryExportRequest => ({
    include_description: true,
    include_calculation_sheet_no: true,
    include_drawing_no: true,
    include_invoice_description: true,
    include_estimated_quantity: true,
    include_submission_percentage: true,
    include_quantity_submitted: true,
    include_past_months_submitted: false,
    include_past_months_submitted_subrows: false,
    include_left_submitted: false,
    include_internal_quantity: true,
    include_approved_by_project_manager: true,
    include_notes: true,
    include_supervisor_notes: true,
  });

/** Saved concentration-sheet PDF/Excel column prefs (same as Export modal). */
export function getConcentrationEntryExportColumns(): ConcentrationEntryExportRequest {
  return loadExportColumnPrefs(
    EXPORT_PREFS_KEYS.concentrationEntry,
    buildDefaultConcentrationEntryExportRequest,
  );
}

/**
 * Load boolean export column preferences, merged onto current defaults.
 * Unknown keys in storage are kept; new default keys use default values.
 */
export function loadExportColumnPrefs<T extends object>(
  storageKey: string,
  buildDefaults: () => T,
): T {
  const defaults = buildDefaults();
  const saved = getProjectItem(storageKey);
  if (!saved) {
    return defaults;
  }
  try {
    const parsed = JSON.parse(saved) as Record<string, boolean>;
    const merged = { ...defaults } as T & Record<string, boolean>;
    for (const key of Object.keys(defaults)) {
      if (typeof parsed[key] === "boolean") {
        merged[key] = parsed[key];
      }
    }
    for (const key of Object.keys(parsed)) {
      if (typeof parsed[key] === "boolean" && !(key in merged)) {
        merged[key] = parsed[key];
      }
    }
    return merged as T;
  } catch {
    return defaults;
  }
}

export function saveExportColumnPrefs<T extends object>(
  storageKey: string,
  prefs: T,
): void {
  setProjectItem(storageKey, JSON.stringify(prefs));
}

/** Add keys for newly created contract-update columns without resetting existing choices */
export function mergeMissingBooleanKeys(
  prev: Record<string, boolean>,
  keys: string[],
  defaultValue = true,
): Record<string, boolean> {
  const next = { ...prev };
  for (const key of keys) {
    if (!(key in next)) {
      next[key] = defaultValue;
    }
  }
  return next;
}
