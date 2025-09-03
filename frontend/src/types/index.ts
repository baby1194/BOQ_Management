export interface BOQItem {
  id: number;
  serial_number?: number; // Integer
  structure?: number; // Integer
  system?: string;
  section_number: string;
  description: string;
  unit: string;
  original_contract_quantity: number;
  price: number;
  total_contract_sum: number;
  estimated_quantity: number;
  quantity_submitted: number;
  internal_quantity: number;
  approved_by_project_manager: number;
  total_estimate: number;
  total_submitted: number;
  internal_total: number;
  total_approved_by_project_manager: number;
  approved_signed_quantity: number;
  approved_signed_total: number;
  notes?: string;
  subsection?: string;
  created_at: string;
  updated_at?: string;
}

export interface BOQItemCreate {
  serial_number?: number;
  structure?: number;
  system?: string;
  section_number: string;
  description: string;
  unit: string;
  original_contract_quantity: number;
  price: number;
  total_contract_sum: number;
  estimated_quantity: number;
  quantity_submitted: number;
  internal_quantity: number;
  approved_by_project_manager: number;
  total_estimate: number;
  total_submitted: number;
  internal_total: number;
  total_approved_by_project_manager: number;
  approved_signed_quantity: number;
  approved_signed_total: number;
  notes?: string;
  subsection?: string;
}

export interface BOQItemUpdate {
  serial_number?: number;
  structure?: number;
  system?: string;
  description?: string;
  unit?: string;
  original_contract_quantity?: number;
  price?: number;
  total_contract_sum?: number;
  estimated_quantity?: number;
  quantity_submitted?: number;
  internal_quantity?: number;
  approved_by_project_manager?: number;
  total_estimate?: number;
  total_submitted?: number;
  internal_total?: number;
  total_approved_by_project_manager?: number;
  approved_signed_quantity?: number;
  approved_signed_total?: number;
  notes?: string;
  subsection?: string;
}

export interface ConcentrationSheet {
  id: number;
  boq_item_id: number;
  sheet_name: string;
  project_name?: string;
  contractor_in_charge?: string;
  contract_no?: string;
  developer_name?: string;
  total_estimate: number;
  total_submitted: number;
  total_pnimi: number;
  total_approved: number;
  created_at: string;
  updated_at?: string;
}

export interface ConcentrationEntry {
  id: number;
  concentration_sheet_id: number;
  section_number: string; // Section Number
  description?: string; // Manual Description
  calculation_sheet_no?: string; // Calculation Sheet No
  drawing_no?: string; // Drawing No
  estimated_quantity: number; // Estimated Quantity
  quantity_submitted: number; // Quantity Submitted
  internal_quantity: number; // Internal Quantity
  approved_by_project_manager: number; // Approved by Project Manager
  notes?: string; // Notes
  created_at: string;
  updated_at?: string;
}

export interface SearchResponse {
  items: BOQItem[];
  total_count: number;
  query: string;
}

export interface SubChapterSummary {
  sub_chapter: string;
  description?: string;
  total_estimate: number;
  total_submitted: number;
  total_pnimi: number;
  total_approved: number;
  item_count: number;
}

export interface SummaryResponse {
  summaries: SubChapterSummary[];
  grand_total_estimate: number;
  grand_total_submitted: number;
  grand_total_pnimi: number;
  grand_total_approved: number;
}

export interface ImportResponse {
  success: boolean;
  message: string;
  files_processed: number;
  items_updated: number;
  errors: string[];
}

export interface PDFExportRequest {
  item_codes: string[];
  hide_columns: string[];
  export_all: boolean;
  export_non_empty_only: boolean;
}

export interface PDFExportResponse {
  success: boolean;
  message: string;
  pdf_path?: string;
  sheets_exported: number;
}

export interface ImportLog {
  id: number;
  file_name: string;
  import_date: string;
  status: string;
  error_message?: string;
  items_processed: number;
  items_updated: number;
}

export interface CalculationSheet {
  id: number;
  file_name: string;
  calculation_sheet_no: string;
  drawing_no: string;
  description: string;
  comment?: string;
  import_date: string;
  created_at: string;
  updated_at?: string;
}

export interface CalculationEntry {
  id: number;
  calculation_sheet_id: number;
  section_number: string;
  estimated_quantity: number;
  quantity_submitted: number;
  created_at: string;
  updated_at?: string;
}

export interface CalculationSheetWithEntries extends CalculationSheet {
  entries: CalculationEntry[];
}

export interface CalculationImportResponse {
  success: boolean;
  message: string;
  files_processed: number;
  sheets_imported: number;
  entries_imported: number;
  errors: string[];
}

export interface PopulateConcentrationEntriesResponse {
  success: boolean;
  message: string;
  entries_created: number;
  entries_skipped: number;
  boq_items_updated: number;
  concentration_sheet_id: number;
}

export interface ProjectInfo {
  id: number;
  project_name?: string;
  main_contractor_name?: string;
  subcontractor_name?: string;
  developer_name?: string;
  contract_no?: string;
  created_at: string;
  updated_at?: string;
}

export interface ProjectInfoUpdate {
  project_name?: string;
  main_contractor_name?: string;
  subcontractor_name?: string;
  developer_name?: string;
  contract_no?: string;
}

export interface ContractQuantityUpdate {
  id: number;
  update_index: number;
  update_name: string;
  created_at: string;
}

export interface BOQItemQuantityUpdate {
  id: number;
  boq_item_id: number;
  contract_update_id: number;
  updated_contract_quantity: number;
  updated_contract_sum: number;
  created_at: string;
  updated_at?: string;
}

export interface BOQItemQuantityUpdateUpdate {
  updated_contract_quantity?: number;
  updated_contract_sum?: number;
}

export interface BOQItemWithUpdates extends BOQItem {
  quantity_updates: BOQItemQuantityUpdate[];
}

export interface BOQItemWithLatestContractUpdate extends BOQItem {
  latest_contract_quantity: number;
  latest_contract_sum: number;
  has_contract_updates: boolean;
  latest_update_index?: number;
}

export interface SubsectionSummary {
  subsection: string;
  description: string;
  total_estimate: number;
  total_submitted: number;
  internal_total: number;
  total_approved: number;
  approved_signed_total: number;
  item_count: number;
}

export interface SystemSummary {
  system: string;
  description: string;
  total_estimate: number;
  total_submitted: number;
  internal_total: number;
  total_approved: number;
  approved_signed_total: number;
  item_count: number;
}

export interface StructureSummary {
  structure: number;
  description: string;
  total_estimate: number;
  total_submitted: number;
  internal_total: number;
  total_approved: number;
  approved_signed_total: number;
  item_count: number;
}

export interface SummaryExportRequest {
  include_structure: boolean;
  include_description: boolean;
  include_total_estimate: boolean;
  include_total_submitted: boolean;
  include_internal_total: boolean;
  include_total_approved: boolean;
  include_approved_signed_total: boolean;
  include_item_count: boolean;
}
