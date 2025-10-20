from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class BOQItem(Base):
    __tablename__ = "boq_items"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Original BOQ.xlsx columns
    serial_number = Column(Integer, nullable=True)
    structure = Column(Integer, nullable=True)
    system = Column(String(100), nullable=True)  # New System column
    section_number = Column(String(50), unique=True, index=True, nullable=False)  # Primary identifier
    description = Column(Text, nullable=False)
    unit = Column(String(20), nullable=False)
    original_contract_quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_contract_sum = Column(Float, nullable=False)
    estimated_quantity = Column(Float, default=0.0)
    quantity_submitted = Column(Float, default=0.0)
    internal_quantity = Column(Float, default=0.0)
    approved_by_project_manager = Column(Float, default=0.0)
    total_estimate = Column(Float, default=0.0)
    total_submitted = Column(Float, default=0.0)
    internal_total = Column(Float, default=0.0)
    total_approved_by_project_manager = Column(Float, default=0.0)
    
    # New Approved Signed columns
    approved_signed_quantity = Column(Float, default=0.0)
    approved_signed_total = Column(Float, default=0.0)
    
    notes = Column(Text, nullable=True)
    
    # Computed fields
    subsection = Column(String(50), nullable=True, index=True)  # Extracted from section_number
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    concentration_sheet = relationship("ConcentrationSheet", back_populates="boq_item", uselist=False)
    quantity_updates = relationship("BOQItemQuantityUpdate", back_populates="boq_item", cascade="all, delete-orphan")


class ConcentrationSheet(Base):
    __tablename__ = "concentration_sheets"
    
    id = Column(Integer, primary_key=True, index=True)
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=False)
    sheet_name = Column(String(200), nullable=False)
    
    # Project information
    project_name = Column(String(200), nullable=True)
    contractor_in_charge = Column(String(200), nullable=True)
    contract_no = Column(String(100), nullable=True)
    developer_name = Column(String(200), nullable=True)
    
    # Totals from concentration sheet
    total_estimate = Column(Float, default=0.0)
    total_submitted = Column(Float, default=0.0)
    total_pnimi = Column(Float, default=0.0)
    total_approved = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    boq_item = relationship("BOQItem", back_populates="concentration_sheet")
    entries = relationship("ConcentrationEntry", back_populates="concentration_sheet", cascade="all, delete-orphan")

class ConcentrationEntry(Base):
    __tablename__ = "concentration_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    concentration_sheet_id = Column(Integer, ForeignKey("concentration_sheets.id"), nullable=False)
    
    # Entry details
    section_number = Column(Text, nullable=False)
    description = Column(Text, nullable=True)  # Manual user input
    calculation_sheet_no = Column(String(100), nullable=True)
    drawing_no = Column(String(100), nullable=True)
    
    # Values
    estimated_quantity = Column(Float, default=0.0)
    quantity_submitted = Column(Float, default=0.0)
    internal_quantity = Column(Float, default=0.0)
    approved_by_project_manager = Column(Float, default=0.0)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Track whether entry was created manually (True) or auto-generated from calculation sheets (False)
    is_manual = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    concentration_sheet = relationship("ConcentrationSheet", back_populates="entries")

class SubChapter(Base):
    __tablename__ = "sub_chapters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ImportLog(Base):
    __tablename__ = "import_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    import_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), nullable=False)  # success, error, partial
    error_message = Column(Text, nullable=True)
    items_processed = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)

class CalculationSheet(Base):
    __tablename__ = "calculation_sheets"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(200), nullable=False)
    calculation_sheet_no = Column(String(100), nullable=False)
    drawing_no = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    comment = Column(Text, nullable=True)  # User-editable comment field
    import_date = Column(DateTime(timezone=True), server_default=func.now())
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique constraint on calculation_sheet_no + drawing_no combination
    __table_args__ = (
        UniqueConstraint('calculation_sheet_no', 'drawing_no', name='uq_calculation_sheet_drawing'),
    )
    
    # Relationships
    entries = relationship("CalculationEntry", back_populates="calculation_sheet", cascade="all, delete-orphan")

class CalculationEntry(Base):
    __tablename__ = "calculation_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    calculation_sheet_id = Column(Integer, ForeignKey("calculation_sheets.id"), nullable=False)
    
    # Entry details
    section_number = Column(String(100), nullable=False)
    estimated_quantity = Column(Float, default=0.0)
    quantity_submitted = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    calculation_sheet = relationship("CalculationSheet", back_populates="entries") 

class ProjectInfo(Base):
    __tablename__ = "project_info"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Project information fields
    project_name = Column(String(200), nullable=True)
    project_name_hebrew = Column(String(200), nullable=True)
    main_contractor_name = Column(String(200), nullable=True)
    subcontractor_name = Column(String(200), nullable=True)
    developer_name = Column(String(200), nullable=True)
    contract_no = Column(String(100), nullable=True)
    
    # Invoice fields for Submitted QTY
    invoice_no_submitted_qty = Column(String(100), nullable=True)
    invoice_date_submitted_qty = Column(DateTime(timezone=True), nullable=True)
    
    # Invoice fields for Approved Signed QTY
    invoice_no_approved_signed_qty = Column(String(100), nullable=True)
    invoice_date_approved_signed_qty = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ContractQuantityUpdate(Base):
    __tablename__ = "contract_quantity_updates"
    
    id = Column(Integer, primary_key=True, index=True)
    update_index = Column(Integer, nullable=False, unique=True)  # 1, 2, 3, etc.
    update_name = Column(String(100), nullable=False)  # "Updated Contract Qty 1", "Updated Contract Qty 2", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    boq_item_updates = relationship("BOQItemQuantityUpdate", back_populates="contract_update", cascade="all, delete-orphan")

class BOQItemQuantityUpdate(Base):
    __tablename__ = "boq_item_quantity_updates"
    
    id = Column(Integer, primary_key=True, index=True)
    boq_item_id = Column(Integer, ForeignKey("boq_items.id"), nullable=False)
    contract_update_id = Column(Integer, ForeignKey("contract_quantity_updates.id"), nullable=False)
    
    # Updated values
    updated_contract_quantity = Column(Float, nullable=False)
    updated_contract_sum = Column(Float, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    boq_item = relationship("BOQItem", back_populates="quantity_updates")
    contract_update = relationship("ContractQuantityUpdate", back_populates="boq_item_updates")
    
    # Unique constraint to ensure one update per BOQ item per contract update
    __table_args__ = (
        UniqueConstraint('boq_item_id', 'contract_update_id', name='uq_boq_item_contract_update'),
    )

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    system_password = Column(String(255), nullable=False)  # Configurable password for BOQ operations
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 