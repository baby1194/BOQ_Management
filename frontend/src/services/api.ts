import axios from "axios";
import {
  BOQItem,
  BOQItemCreate,
  BOQItemUpdate,
  ConcentrationSheet,
  ConcentrationSheetWithBOQData,
  ConcentrationEntry,
  SearchResponse,
  SummaryResponse,
  ImportResponse,
  PDFExportRequest,
  PDFExportResponse,
  SummaryExportRequest,
  ConcentrationEntryExportRequest,
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
  SystemSummary,
  StructureSummary,
  User,
  UserCreate,
  UserLogin,
  UserUpdate,
  Token,
  AuthStatus,
  SignupAllowed,
} from "../types";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // This ensures cookies are sent with all requests
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

  getAllWithBOQData: (skip = 0, limit = 100) =>
    api
      .get<ConcentrationSheetWithBOQData[]>(
        `/concentration/with-boq-data?skip=${skip}&limit=${limit}`
      )
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

  updateComment: (id: number, comment: string) =>
    api
      .put<CalculationSheet>(`/calculation-sheets/${id}/comment`, { comment })
      .then((res) => res.data),

  // Entries
  getEntries: (sheetId: number) =>
    api
      .get<CalculationEntry[]>(`/calculation-sheets/${sheetId}/entries`)
      .then((res) => res.data),

  deleteEntry: (entryId: number) =>
    api
      .delete(`/calculation-sheets/entries/${entryId}`)
      .then((res) => res.data),

  updateEntry: (entryId: number, entryData: any) =>
    api
      .put<CalculationEntry>(
        `/calculation-sheets/entries/${entryId}`,
        entryData
      )
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

  syncAll: () =>
    api
      .post<{ success: boolean; message: string; details: any }>(
        `/calculation-sheets/sync-all`
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
  exportConcentrationSheets: (
    request: PDFExportRequest,
    entryColumnRequest?: ConcentrationEntryExportRequest
  ) =>
    api
      .post<PDFExportResponse>("/export/concentration-sheets", {
        ...request,
        entry_columns: entryColumnRequest,
      })
      .then((res) => res.data),

  exportAllConcentrationSheetsExcel: (
    request: PDFExportRequest,
    entryColumnRequest?: ConcentrationEntryExportRequest
  ) =>
    api
      .post<PDFExportResponse>("/export/concentration-sheets/excel", {
        ...request,
        entry_columns: entryColumnRequest,
      })
      .then((res) => res.data),

  exportSingleConcentrationSheetPDF: (
    sheetId: number,
    entryColumnRequest?: ConcentrationEntryExportRequest
  ) =>
    api
      .post<PDFExportResponse>(`/export/concentration-sheet/${sheetId}`, {
        entry_columns: entryColumnRequest,
      })
      .then((res) => res.data),

  exportSingleConcentrationSheetExcel: (
    sheetId: number,
    entryColumnRequest?: ConcentrationEntryExportRequest
  ) =>
    api
      .post<PDFExportResponse>(`/export/concentration-sheet/${sheetId}/excel`, {
        entry_columns: entryColumnRequest,
      })
      .then((res) => res.data),

  exportSummary: () =>
    api.post<PDFExportResponse>("/export/summary").then((res) => res.data),

  // Summary export endpoints
  exportStructuresSummary: (request: SummaryExportRequest, data?: any[]) =>
    api
      .post<PDFExportResponse>("/export/structures-summary", {
        ...request,
        data,
      })
      .then((res) => res.data),

  exportSystemsSummary: (request: SummaryExportRequest, data?: any[]) =>
    api
      .post<PDFExportResponse>("/export/systems-summary", { ...request, data })
      .then((res) => res.data),

  exportSubsectionsSummary: (request: SummaryExportRequest, data?: any[]) =>
    api
      .post<PDFExportResponse>("/export/subsections-summary", {
        ...request,
        data,
      })
      .then((res) => res.data),

  exportStructuresSummaryExcel: (request: SummaryExportRequest, data?: any[]) =>
    api
      .post<PDFExportResponse>("/export/structures-summary/excel", {
        ...request,
        data,
      })
      .then((res) => res.data),

  exportSystemsSummaryExcel: (request: SummaryExportRequest, data?: any[]) =>
    api
      .post<PDFExportResponse>("/export/systems-summary/excel", {
        ...request,
        data,
      })
      .then((res) => res.data),

  exportSubsectionsSummaryExcel: (
    request: SummaryExportRequest,
    data?: any[]
  ) =>
    api
      .post<PDFExportResponse>("/export/subsections-summary/excel", {
        ...request,
        data,
      })
      .then((res) => res.data),

  // BOQ Items export endpoints
  exportBOQItemsExcel: (request: any, data?: any[], grandTotals?: any) =>
    api
      .post<PDFExportResponse>("/export/boq-items/excel", {
        ...request,
        data,
        grand_totals: grandTotals,
      })
      .then((res) => res.data),

  exportBOQItemsPDF: (request: any, data?: any[]) =>
    api
      .post<PDFExportResponse>("/export/boq-items/pdf", {
        ...request,
        data,
      })
      .then((res) => res.data),

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

// Subsection API
export const subsectionsApi = {
  getSummaries: () =>
    api
      .get<SubsectionSummary[]>("/subsections/summaries")
      .then((res) => res.data),
  updateDescription: (subsection: string, description: string) =>
    api
      .put(`/subsections/${encodeURIComponent(subsection)}/description`, {
        description,
      })
      .then((res) => res.data),
};

// Systems API
export const systemsApi = {
  getSummaries: () =>
    api.get<SystemSummary[]>("/systems/summaries").then((res) => res.data),
  updateDescription: (system: string, description: string) =>
    api
      .put(`/systems/${encodeURIComponent(system)}/description`, {
        description,
      })
      .then((res) => res.data),
};

// Structures API
export const structuresApi = {
  getSummaries: () =>
    api
      .get<StructureSummary[]>("/structures/summaries")
      .then((res) => res.data),
  updateDescription: (structure: number, description: string) =>
    api
      .put(`/structures/${structure}/description`, {
        description,
      })
      .then((res) => res.data),
};

// Authentication API
export const authApi = {
  signup: (userData: UserCreate) =>
    api.post<User>("/auth/signup", userData).then((res) => res.data),

  signin: (userData: UserLogin) =>
    api
      .post<Token>("/auth/signin", userData, {
        withCredentials: true,
      })
      .then((res) => res.data),

  signout: () =>
    api
      .post(
        "/auth/signout",
        {},
        {
          withCredentials: true,
        }
      )
      .then((res) => res.data),

  getCurrentUser: () =>
    api
      .get<User>("/auth/me", {
        withCredentials: true,
      })
      .then((res) => res.data),

  checkAuthStatus: () =>
    api
      .get<AuthStatus>("/auth/check-auth", {
        withCredentials: true,
      })
      .then((res) => res.data),

  checkSignupAllowed: () =>
    api
      .get<SignupAllowed>("/auth/check-signup-allowed")
      .then((res) => res.data),

  updateProfile: (userData: UserUpdate) =>
    api
      .put<User>("/auth/profile", userData, {
        withCredentials: true,
      })
      .then((res) => res.data),

  verifySystemPassword: (systemPassword: string) =>
    api
      .post<{ verified: boolean }>(
        "/auth/verify-system-password",
        {
          system_password: systemPassword,
        },
        {
          withCredentials: true,
        }
      )
      .then((res) => res.data),
};

export default api;
