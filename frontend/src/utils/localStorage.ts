const ACTIVE_PROJECT_KEY = "active-project-id";

let _activeProjectId: string | null = null;

export function setActiveProjectIdForStorage(id: string | null) {
  _activeProjectId = id;
}

export function getActiveProjectId(): string | null {
  return localStorage.getItem(ACTIVE_PROJECT_KEY);
}

export function setActiveProjectId(id: string) {
  localStorage.setItem(ACTIVE_PROJECT_KEY, id);
  _activeProjectId = id;
}

function scopedKey(key: string): string {
  const projectId = _activeProjectId ?? getActiveProjectId();
  return projectId ? `project:${projectId}:${key}` : key;
}

export function getProjectItem(key: string): string | null {
  return localStorage.getItem(scopedKey(key));
}

export function setProjectItem(key: string, value: string): void {
  localStorage.setItem(scopedKey(key), value);
}

export function removeProjectItem(key: string): void {
  localStorage.removeItem(scopedKey(key));
}

const APP_STORAGE_KEYS = [
  "boq-column-visibility",
  "boq-panels-collapsed",
  "boq-filters",
  "boq-dropdown-filters",
  "boq-search-query",
  "boq-selected-subchapter",
  "boq-selected-row-id",
  "boq-table-scroll-position",
  "systems-column-visibility",
  "structures-column-visibility",
  "subsections-column-visibility",
  "calculation-sheets-search-query",
  "calculation-sheets-filter-sheet-no",
  "calculation-sheets-filter-drawing-no",
  "calculation-selected-sheet-id",
  "concentration-sheets-section-filter",
  "concentration-selected-sheet-id",
  "boq-export-columns",
  "summary-export-columns",
  "concentration-entry-export-columns",
  "dashboard-non-boq-expanded",
];

/**
 * Clear application-related localStorage items for the current project.
 * Language preference is kept globally.
 */
export const clearAppLocalStorage = () => {
  for (const key of APP_STORAGE_KEYS) {
    removeProjectItem(key);
  }
};
