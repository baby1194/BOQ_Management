import { CalculationSheetLocationChange } from "../types";

export function formatLocationChangeLine(
  change: CalculationSheetLocationChange
): string {
  const label = change.drawing_no
    ? `${change.calculation_sheet_no} / ${change.drawing_no}`
    : change.calculation_sheet_no;
  if (change.reason === "moved" && change.new_path) {
    return `${label}: ${change.previous_path || "—"} → ${change.new_path}`;
  }
  return `${label}: ${change.previous_path || "—"}`;
}
