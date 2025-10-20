from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# BOQ Item Schemas
class BOQItemBase(BaseModel):
    serial_number: Optional[float] = None
    structure: Optional[float] = None
    system: Optional[str] = Field(None, max_length=100)  # Add missing system field
    section_number: str = Field(..., min_length=1, max_length=50)
    description: str = Field("", min_length=0)  # Allow empty descriptions
    unit: str = Field(..., min_length=1, max_length=20)
    original_contract_quantity: float = Field(..., ge=0)
    price: float = Field(..., ge=0)
    total_contract_sum: float = Field(..., ge=0)
    estimated_quantity: float = Field(0.0, ge=0)
    quantity_submitted: float = Field(0.0, ge=0)
    internal_quantity: float = Field(0.0, ge=0)
    approved_by_project_manager: float = Field(0.0, ge=0)
    total_estimate: float = Field(0.0, ge=0)
    total_submitted: float = Field(0.0, ge=0)
    internal_total: float = Field(0.0, ge=0)
    total_approved_by_project_manager: float = Field(0.0, ge=0)
    approved_signed_quantity: float = Field(0.0, ge=0)
    approved_signed_total: float = Field(0.0, ge=0)
    notes: Optional[str] = None
    subsection: Optional[str] = Field(None, max_length=50)

class BOQItemCreate(BaseModel):
    # Only include the essential fields for creation
    structure: Optional[float] = None
    system: Optional[str] = Field(None, max_length=100)
    section_number: str = Field(..., min_length=1, max_length=50)
    description: str = Field("", min_length=0)
    unit: str = Field(..., min_length=1, max_length=20)
    original_contract_quantity: float = Field(..., ge=0)
    price: float = Field(..., ge=0)
    total_contract_sum: float = Field(..., ge=0)
    subsection: Optional[str] = Field(None, max_length=50)

class BOQItemUpdate(BaseModel):
    serial_number: Optional[float] = None
    structure: Optional[float] = None
    system: Optional[str] = Field(None, max_length=100)  # Add missing system field
    description: Optional[str] = Field(None, min_length=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    original_contract_quantity: Optional[float] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    total_contract_sum: Optional[float] = Field(None, ge=0)
    estimated_quantity: Optional[float] = Field(None, ge=0)
    quantity_submitted: Optional[float] = Field(None, ge=0)
    internal_quantity: Optional[float] = Field(None, ge=0)
    approved_by_project_manager: Optional[float] = Field(None, ge=0)
    total_estimate: Optional[float] = Field(None, ge=0)
    total_submitted: Optional[float] = Field(None, ge=0)
    internal_total: Optional[float] = Field(None, ge=0)
    total_approved_by_project_manager: Optional[float] = Field(None, ge=0)
    approved_signed_quantity: Optional[float] = Field(None, ge=0)
    approved_signed_total: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    subsection: Optional[str] = Field(None, max_length=50)

class BOQItem(BOQItemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Concentration Sheet Schemas
class ConcentrationSheetBase(BaseModel):
    sheet_name: str = Field(..., min_length=1, max_length=200)

class ConcentrationSheetCreate(ConcentrationSheetBase):
    boq_item_id: int

class ConcentrationSheetUpdate(BaseModel):
    project_name: Optional[str] = Field(None, max_length=200)
    contractor_in_charge: Optional[str] = Field(None, max_length=200)
    contract_no: Optional[str] = Field(None, max_length=100)
    developer_name: Optional[str] = Field(None, max_length=200)
    total_estimate: Optional[float] = Field(None, ge=0)
    total_submitted: Optional[float] = Field(None, ge=0)
    total_pnimi: Optional[float] = Field(None, ge=0)
    total_approved: Optional[float] = Field(None, ge=0)

class ConcentrationSheet(ConcentrationSheetBase):
    id: int
    boq_item_id: int
    project_name: Optional[str] = None
    contractor_in_charge: Optional[str] = None
    contract_no: Optional[str] = None
    developer_name: Optional[str] = None
    total_estimate: float = 0.0
    total_submitted: float = 0.0
    total_pnimi: float = 0.0
    total_approved: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Concentration Entry Schemas
class ConcentrationEntryBase(BaseModel):
    section_number: str = Field(..., min_length=1)
    description: Optional[str] = None  # Manual user input
    calculation_sheet_no: Optional[str] = Field(None, max_length=100)
    drawing_no: Optional[str] = Field(None, max_length=100)
    estimated_quantity: float = Field(0.0, ge=0)
    quantity_submitted: float = Field(0.0, ge=0)
    internal_quantity: float = Field(0.0, ge=0)
    approved_by_project_manager: float = Field(0.0, ge=0)
    notes: Optional[str] = None
    is_manual: bool = Field(True, description="True if entry was created manually, False if auto-generated from calculation sheets")

class ConcentrationEntryCreate(ConcentrationEntryBase):
    pass

class ConcentrationEntryUpdate(BaseModel):
    section_number: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None  # Manual user input
    calculation_sheet_no: Optional[str] = Field(None, max_length=100)
    drawing_no: Optional[str] = Field(None, max_length=100)
    estimated_quantity: Optional[float] = Field(None, ge=0)
    quantity_submitted: Optional[float] = Field(None, ge=0)
    internal_quantity: Optional[float] = Field(None, ge=0)
    approved_by_project_manager: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None

class ConcentrationEntry(ConcentrationEntryBase):
    id: int
    concentration_sheet_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Concentration Entry Export Request Schema
class ConcentrationEntryExportRequest(BaseModel):
    include_description: bool = True
    include_calculation_sheet_no: bool = True
    include_drawing_no: bool = True
    include_estimated_quantity: bool = True
    include_quantity_submitted: bool = True
    include_internal_quantity: bool = True
    include_approved_by_project_manager: bool = True
    include_notes: bool = True

# Search Schemas
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    search_type: str = Field("both", pattern="^(code|description|both)$")

class SearchResponse(BaseModel):
    items: List[BOQItem]
    total_count: int
    query: str

# Sub-chapter Schemas
class SubChapterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class SubChapterCreate(SubChapterBase):
    pass

class SubChapter(SubChapterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Summary Schemas
class SubChapterSummary(BaseModel):
    sub_chapter: str
    description: Optional[str]
    total_estimate: float
    total_submitted: float
    total_pnimi: float
    total_approved: float
    item_count: int

class SummaryResponse(BaseModel):
    summaries: List[SubChapterSummary]
    grand_total_estimate: float
    grand_total_submitted: float
    grand_total_pnimi: float
    grand_total_approved: float

# Import Schemas
class ImportRequest(BaseModel):
    folder_path: str = Field(..., min_length=1)
    recursive: bool = True

class ImportResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    items_updated: int
    errors: List[str] = []

# PDF Export Schemas
class PDFExportRequest(BaseModel):
    item_codes: List[str] = []
    hide_columns: List[str] = []
    export_all: bool = False
    export_non_empty_only: bool = True
    entry_columns: Optional[ConcentrationEntryExportRequest] = None

class PDFExportResponse(BaseModel):
    success: bool
    message: str
    pdf_path: Optional[str] = None
    sheets_exported: int = 0

# Import Log Schemas
class ImportLog(BaseModel):
    id: int
    file_name: str
    file_path: str
    import_date: datetime
    status: str
    error_message: Optional[str] = None
    items_processed: int
    items_updated: int

    class Config:
        from_attributes = True

# Calculation Sheet Schemas
class CalculationSheetBase(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=200)
    calculation_sheet_no: str = Field(..., min_length=1, max_length=100)
    drawing_no: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    comment: Optional[str] = None

class CalculationSheetCreate(CalculationSheetBase):
    pass

class CalculationSheet(CalculationSheetBase):
    id: int
    import_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CalculationSheetUpdate(BaseModel):
    comment: Optional[str] = None

    class Config:
        from_attributes = True

# Calculation Entry Schemas
class CalculationEntryBase(BaseModel):
    section_number: str = Field(..., min_length=1, max_length=100)
    estimated_quantity: float = Field(0.0, ge=0)
    quantity_submitted: float = Field(0.0, ge=0)
    notes: Optional[str] = None

class CalculationEntryCreate(CalculationEntryBase):
    pass

class CalculationEntryUpdate(BaseModel):
    section_number: Optional[str] = Field(None, min_length=1, max_length=100)
    estimated_quantity: Optional[float] = Field(None, ge=0)
    quantity_submitted: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class CalculationEntry(CalculationEntryBase):
    id: int
    calculation_sheet_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CalculationSheetWithEntries(CalculationSheet):
    entries: List[CalculationEntry] = []

# Calculation Import Response
class CalculationImportResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    sheets_imported: int
    entries_imported: int
    errors: List[str] = []

# Populate Concentration Entries Response
class PopulateConcentrationEntriesResponse(BaseModel):
    success: bool
    message: str
    entries_created: int
    entries_skipped: int
    boq_items_updated: int
    concentration_sheet_id: int

# Project Info Schemas
class ProjectInfoBase(BaseModel):
    project_name: Optional[str] = Field(None, max_length=200)
    project_name_hebrew: Optional[str] = Field(None, max_length=200)
    main_contractor_name: Optional[str] = Field(None, max_length=200)
    subcontractor_name: Optional[str] = Field(None, max_length=200)
    developer_name: Optional[str] = Field(None, max_length=200)
    contract_no: Optional[str] = Field(None, max_length=100)
    # Invoice fields for Submitted QTY
    invoice_no_submitted_qty: Optional[str] = Field(None, max_length=100)
    invoice_date_submitted_qty: Optional[datetime] = None
    # Invoice fields for Approved Signed QTY
    invoice_no_approved_signed_qty: Optional[str] = Field(None, max_length=100)
    invoice_date_approved_signed_qty: Optional[datetime] = None

class ProjectInfoCreate(ProjectInfoBase):
    pass

class ProjectInfoUpdate(ProjectInfoBase):
    pass

class ProjectInfo(ProjectInfoBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Contract Quantity Update Schemas
class ContractQuantityUpdateBase(BaseModel):
    update_index: int = Field(..., ge=1)
    update_name: str = Field(..., min_length=1, max_length=100)

class ContractQuantityUpdateCreate(ContractQuantityUpdateBase):
    pass

class ContractQuantityUpdate(ContractQuantityUpdateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class BOQItemQuantityUpdateBase(BaseModel):
    updated_contract_quantity: float = Field(..., ge=0)
    updated_contract_sum: float = Field(..., ge=0)

class BOQItemQuantityUpdateCreate(BOQItemQuantityUpdateBase):
    boq_item_id: int
    contract_update_id: int

class BOQItemQuantityUpdateUpdate(BaseModel):
    updated_contract_quantity: Optional[float] = Field(None, ge=0)
    updated_contract_sum: Optional[float] = Field(None, ge=0)

class BOQItemQuantityUpdate(BOQItemQuantityUpdateBase):
    id: int
    boq_item_id: int
    contract_update_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Extended BOQ Item with quantity updates
class BOQItemWithUpdates(BOQItem):
    quantity_updates: List[BOQItemQuantityUpdate] = []

# BOQ Item with latest contract update for concentration sheets
class BOQItemWithLatestContractUpdate(BaseModel):
    id: int
    serial_number: Optional[int] = None
    structure: Optional[float] = None
    section_number: str
    description: str
    unit: str
    original_contract_quantity: Optional[float] = None
    price: Optional[float] = None
    total_contract_sum: Optional[float] = None
    estimated_quantity: Optional[float] = None
    quantity_submitted: Optional[float] = None
    internal_quantity: Optional[float] = None
    approved_by_project_manager: Optional[float] = None
    total_estimate: Optional[float] = None
    total_submitted: Optional[float] = None
    internal_total: Optional[float] = None
    total_approved_by_project_manager: Optional[float] = None
    subsection: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Latest contract update fields
    latest_contract_quantity: float
    latest_contract_sum: float
    has_contract_updates: bool
    latest_update_index: Optional[int] = None

    class Config:
        from_attributes = True

class ConcentrationSheetWithBOQData(ConcentrationSheet):
    boq_item: BOQItemWithLatestContractUpdate

    class Config:
        from_attributes = True

# Subsection Summary Schemas
class SubsectionSummary(BaseModel):
    subsection: str
    description: str
    total_contract_sum: float
    contract_update_sums: dict  # Dictionary of {update_id: sum}
    total_estimate: float
    total_submitted: float
    internal_total: float
    total_approved: float
    approved_signed_total: float
    item_count: int

class SystemSummary(BaseModel):
    system: str
    description: str
    total_contract_sum: float
    contract_update_sums: dict  # Dictionary of {update_id: sum}
    total_estimate: float
    total_submitted: float
    internal_total: float
    total_approved: float
    approved_signed_total: float
    item_count: int

class StructureSummary(BaseModel):
    structure: int
    description: str
    total_contract_sum: float
    contract_update_sums: dict  # Dictionary of {update_id: sum}
    total_estimate: float
    total_submitted: float
    internal_total: float
    total_approved: float
    approved_signed_total: float
    item_count: int

class SubsectionDescriptionUpdate(BaseModel):
    description: str = Field(..., min_length=0, max_length=500)

class SystemDescriptionUpdate(BaseModel):
    description: str = Field(..., min_length=0, max_length=500)

class StructureDescriptionUpdate(BaseModel):
    description: str = Field(..., min_length=0, max_length=500)

class SummaryExportRequest(BaseModel):
    include_structure: bool = True
    include_description: bool = True
    include_total_contract_sum: bool = True
    include_total_estimate: bool = True
    include_total_submitted: bool = True
    include_internal_total: bool = True
    include_total_approved: bool = True
    include_approved_signed_total: bool = True
    include_item_count: bool = True
    # Dynamic contract update columns
    include_contract_updates: bool = True  # Include all contract update columns
    data: list = []  # Optional: pass the actual data from frontend

# User Authentication Schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    system_password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    password: Optional[str] = Field(None, min_length=6)
    system_password: Optional[str] = Field(None, min_length=6)

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
