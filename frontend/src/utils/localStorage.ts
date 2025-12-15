/**
 * Clear all application-related localStorage items
 * This should be called on logout or session expiration
 */
export const clearAppLocalStorage = () => {
  // BOQ Items page settings
  localStorage.removeItem("boq-column-visibility");
  localStorage.removeItem("boq-panels-collapsed");
  localStorage.removeItem("boq-filters");
  localStorage.removeItem("boq-dropdown-filters");
  localStorage.removeItem("boq-search-query");
  localStorage.removeItem("boq-selected-subchapter");

  // Summary pages column visibility
  localStorage.removeItem("systems-column-visibility");
  localStorage.removeItem("structures-column-visibility");
  localStorage.removeItem("subsections-column-visibility");

  // Calculation Sheets filters
  localStorage.removeItem("calculation-sheets-search-query");
  localStorage.removeItem("calculation-sheets-filter-sheet-no");
  localStorage.removeItem("calculation-sheets-filter-drawing-no");

  // Concentration Sheets filters
  localStorage.removeItem("concentration-sheets-section-filter");

  // Note: We intentionally keep "language" as it's a user preference
  // that should persist across sessions
};

