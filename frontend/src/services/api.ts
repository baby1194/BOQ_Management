import axios from "axios";
import {
  BOQItem,
  BOQItemCreate,
  BOQItemUpdate,
  ConcentrationSheet,
  ConcentrationEntry,
  SearchResponse,
  SummaryResponse,
  ImportResponse,
  PDFExportRequest,
  PDFExportResponse,
  ImportLog,
  CalculationSheet,
  CalculationSheetWithEntries,
  CalculationEntry,
  CalculationImportResponse,
  PopulateConcentrationEntriesResponse,
  ProjectInfo,
  ProjectInfoUpdate,
  ContractQuantityUpdate,
  BOQItemQuantityUpdate,
  BOQItemQuantityUpdateUpdate,
  BOQItemWithLatestContractUpdate,
  SubsectionSummary,
} from "../types";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// BOQ API
export const boqApi = {
  getAll: (skip: number = 0, limit: number = 10000) =>
    api
      .get<BOQItem[]>(`/boq?skip=${skip}&limit=${limit}`)
      .then((res) => res.data),

  getById: (id: number) =>
    api.get<BOQItem>(`/boq/${id}`).then((res) => res.data),

  getBySectionNumber: (sectionNumber: string) =>
    api.get<BOQItem>(`/boq/code/${sectionNumber}`).then((res) => res.data),

  create: (item: BOQItemCreate) =>
    api.post<BOQItem>("/boq", item).then((res) => res.data),

  getWithLatestContractUpdate: (id: number) =>
    api
      .get<BOQItemWithLatestContractUpdate>(
        `/boq/${id}/with-latest-contract-update`
      )
      .then((res) => res.data),

  update: (id: number, data: Partial<BOQItem>) =>
    api.put<BOQItem>(`/boq/${id}`, data).then((res) => res.data),

  delete: (id: number) => api.delete(`/boq/${id}`).then((res) => res.data),

  createBulk: (items: BOQItemCreate[]) =>
    api.post<BOQItem[]>("/boq/bulk", items).then((res) => res.data),
};

// Concentration Sheets API
export const concentrationApi = {
  getAll: (skip = 0, limit = 100) =>
    api
      .get<ConcentrationSheet[]>(`/concentration?skip=${skip}&limit=${limit}`)
      .then((res) => res.data),

  getById: (id: number) =>
    api.get<ConcentrationSheet>(`/concentration/${id}`).then((res) => res.data),

  getByBOQItem: (boqItemId: number) =>
    api
      .get<ConcentrationSheet>(`/concentration/item/${boqItemId}`)
      .then((res) => res.data),

  create: (sheet: { boq_item_id: number; sheet_name: string }) =>
    api
      .post<ConcentrationSheet>("/concentration", sheet)
      .then((res) => res.data),

  update: (id: number, updates: Partial<ConcentrationSheet>) =>
    api
      .put<ConcentrationSheet>(`/concentration/${id}`, updates)
      .then((res) => res.data),

  updateProjectInfo: (
    id: number,
    projectInfo: {
      project_name?: string;
      contractor_in_charge?: string;
      contract_no?: string;
      developer_name?: string;
    }
  ) =>
    api
      .put<ConcentrationSheet>(`/concentration/${id}/project-info`, projectInfo)
      .then((res) => res.data),

  delete: (id: number) =>
    api.delete(`/concentration/${id}`).then((res) => res.data),

  // Entries
  getEntries: (sheetId: number) =>
    api
      .get<ConcentrationEntry[]>(`/concentration/${sheetId}/entries`)
      .then((res) => res.data),

  createEntry: (
    sheetId: number,
    entry: Omit<
      ConcentrationEntry,
      "id" | "concentration_sheet_id" | "created_at" | "updated_at"
    >
  ) =>
    api
      .post<ConcentrationEntry>(`/concentration/${sheetId}/entries`, entry)
      .then((res) => res.data),

  updateEntry: (entryId: number, updates: Partial<ConcentrationEntry>) =>
    api
      .put<ConcentrationEntry>(`/concentration/entries/${entryId}`, updates)
      .then((res) => res.data),

  deleteEntry: (entryId: number) =>
    api.delete(`/concentration/entries/${entryId}`).then((res) => res.data),
};

// Calculation Sheets API
export const calculationSheetsApi = {
  getAll: (skip = 0, limit = 100) =>
    api
      .get<CalculationSheet[]>(
        `/calculation-sheets?skip=${skip}&limit=${limit}`
      )
      .then((res) => res.data),

  getById: (id: number) =>
    api
      .get<CalculationSheet>(`/calculation-sheets/${id}`)
      .then((res) => res.data),

  getWithEntries: (id: number) =>
    api
      .get<CalculationSheetWithEntries>(`/calculation-sheets/${id}/entries`)
      .then((res) => res.data),

  delete: (id: number) =>
    api.delete(`/calculation-sheets/${id}`).then((res) => res.data),

  // Entries
  getEntries: (sheetId: number) =>
    api
      .get<CalculationEntry[]>(`/calculation-sheets/${sheetId}/entries`)
      .then((res) => res.data),

  deleteEntry: (entryId: number) =>
    api
      .delete(`/calculation-sheets/entries/${entryId}`)
      .then((res) => res.data),

  populateConcentrationEntries: (sheetId: number) =>
    api
      .post<PopulateConcentrationEntriesResponse>(
        `/calculation-sheets/${sheetId}/populate-concentration-entries`
      )
      .then((res) => res.data),
  populateAllCalculationEntries: () =>
    api
      .post<PopulateConcentrationEntriesResponse>(
        `/calculation-sheets/populate-all`
      )
      .then((res) => res.data),
};

// Search API
export const searchApi = {
  search: (query: string, searchType = "both", skip = 0, limit = 10000) =>
    api
      .get<SearchResponse>(
        `/search?q=${encodeURIComponent(
          query
        )}&search_type=${searchType}&skip=${skip}&limit=${limit}`
      )
      .then((res) => res.data),

  getBySubchapter: (subchapter: string, skip = 0, limit = 10000) =>
    api
      .get<BOQItem[]>(
        `/search/subchapter/${encodeURIComponent(
          subchapter
        )}?skip=${skip}&limit=${limit}`
      )
      .then((res) => res.data),

  getAllSubchapters: () =>
    api.get<string[]>("/search/subchapters").then((res) => res.data),

  filter: (params: {
    section_number?: string;
    description?: string;
    unit?: string;
    subsection?: string;
    min_price?: number;
    max_price?: number;
    min_quantity?: number;
    max_quantity?: number;
    skip?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, value.toString());
    });
    return api
      .get<BOQItem[]>(`/search/filter?${searchParams}`)
      .then((res) => res.data);
  },

  getSummary: () =>
    api.get<SummaryResponse>("/search/summary").then((res) => res.data),
};

// Import API
export const importApi = {
  importBOQ: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api
      .post<ImportResponse>("/file-import/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((res) => res.data);
  },

  importCalculationFiles: (folderPath: string, recursive = true) => {
    const request = {
      folder_path: folderPath,
      recursive: recursive,
    };
    return api
      .post<ImportResponse>("/file-import/import-folder/", request)
      .then((res) => res.data);
  },

  importCalculationSheets: (files: FormData) => {
    return api
      .post<CalculationImportResponse>(
        "/file-import/import-calculation-sheets/",
        files,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      )
      .then((res) => res.data);
  },

  createConcentrationSheets: () =>
    api
      .post<{ success: boolean; message: string; created_count: number }>(
        "/file-import/create-concentration-sheets/"
      )
      .then((res) => res.data),

  getLogs: (skip = 0, limit = 50) =>
    api
      .get<ImportLog[]>(`/file-import/logs/?limit=${limit}`)
      .then((res) => res.data),
};

// Export API
export const exportApi = {
  exportConcentrationSheets: (request: PDFExportRequest) =>
    api
      .post<PDFExportResponse>("/export/concentration-sheets", request)
      .then((res) => res.data),

  exportSingleConcentrationSheetPDF: (sheetId: number) =>
    api
      .post<PDFExportResponse>(`/export/concentration-sheet/${sheetId}`)
      .then((res) => res.data),

  exportSingleConcentrationSheetExcel: (sheetId: number) =>
    api
      .post<PDFExportResponse>(`/export/concentration-sheet/${sheetId}/excel`)
      .then((res) => res.data),

  exportSummary: () =>
    api.post<PDFExportResponse>("/export/summary").then((res) => res.data),

  listPDFs: () => api.get<string[]>("/export/list").then((res) => res.data),

  downloadPDF: (filename: string) =>
    api
      .get<{ file_path: string }>(`/export/download/${filename}`)
      .then((res) => res.data),

  cleanupPDFs: (days = 7) =>
    api.delete(`/export/cleanup?days=${days}`).then((res) => res.data),
};

// Project Info API
export const projectInfoApi = {
  get: () => api.get<ProjectInfo>("/project-info").then((res) => res.data),

  update: (projectInfo: ProjectInfoUpdate) =>
    api.put<ProjectInfo>("/project-info", projectInfo).then((res) => res.data),

  sync: () =>
    api
      .post<{
        success: boolean;
        message: string;
        sheets_updated: number;
        total_sheets: number;
      }>("/project-info/sync")
      .then((res) => res.data),
};

// Contract Updates API
export const contractUpdatesApi = {
  getAll: () =>
    api
      .get<ContractQuantityUpdate[]>("/contract-updates")
      .then((res) => res.data),

  create: () =>
    api
      .post<ContractQuantityUpdate>("/contract-updates")
      .then((res) => res.data),

  getBOQItemUpdates: (updateId: number) =>
    api
      .get<BOQItemQuantityUpdate[]>(`/contract-updates/${updateId}/boq-items`)
      .then((res) => res.data),

  updateBOQItemQuantity: (
    updateId: number,
    boqItemId: number,
    updateData: BOQItemQuantityUpdateUpdate
  ) =>
    api
      .put<BOQItemQuantityUpdate>(
        `/contract-updates/${updateId}/boq-items/${boqItemId}`,
        updateData
      )
      .then((res) => res.data),

  delete: (updateId: number) =>
    api.delete(`/contract-updates/${updateId}`).then((res) => res.data),
};

// Subsections API
export const subsectionsApi = {
  getSummaries: () =>
    api
      .get<SubsectionSummary[]>("/subsections/summaries")
      .then((res) => res.data),

  updateDescription: (subsection: string, description: string) =>
    api
      .put<{
        success: boolean;
        message: string;
        subsection: string;
        description: string;
      }>(`/subsections/${encodeURIComponent(subsection)}/description`, {
        description,
      })
      .then((res) => res.data),
};

export default api;
