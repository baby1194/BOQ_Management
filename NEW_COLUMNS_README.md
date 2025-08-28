# New BOQ Columns Implementation

This document describes the new columns added to the BOQ (Bill of Quantities) system.

## New Columns Added

### 1. System Column

- **Location**: Between "Structure" and "Section Number" columns
- **Type**: String (VARCHAR)
- **Purpose**: Stores system information for each BOQ item
- **Import**: Included when importing BOQ Excel files
- **Default**: Empty string

### 2. Approved Signed Quantity Column

- **Location**: After "Total Approved" column
- **Type**: Float (REAL)
- **Purpose**: Stores the approved signed quantity for each BOQ item
- **Import**: NOT included in BOQ Excel files (manual entry only)
- **Default**: 0.0
- **Calculation**: Manual input by users

### 3. Approved Signed Total Column

- **Location**: After "Approved Signed Quantity" column
- **Type**: Float (REAL)
- **Purpose**: Stores the calculated total for approved signed quantities
- **Import**: NOT included in BOQ Excel files (calculated automatically)
- **Default**: 0.0
- **Calculation**: `Approved Signed Quantity × Price`

## Implementation Details

### Backend Changes

1. **Database Models** (`backend/models/models.py`)

   - Added `system` column to BOQItem model
   - Added `approved_signed_quantity` column to BOQItem model
   - Added `approved_signed_total` column to BOQItem model

2. **Excel Service** (`backend/services/excel_service.py`)

   - Updated BOQ file import to include "System" column
   - Added default values for new approved signed columns

3. **Database Migration** (`backend/add_new_columns.py`)
   - Script to add new columns to existing databases
   - Updates existing records with default values

### Frontend Changes

1. **Types** (`frontend/src/types/index.ts`)

   - Updated BOQItem interface with new fields
   - Updated BOQItemCreate and BOQItemUpdate interfaces

2. **BOQItems Component** (`frontend/src/pages/BOQItems.tsx`)
   - Added new columns to table headers
   - Added new columns to table data rows
   - Added filter inputs for new columns
   - Updated new item creation form
   - Added calculated values preview for approved signed total

## How to Apply Changes

### 1. Run Database Migration

```bash
cd backend
python add_new_columns.py
```

### 2. Restart Backend Service

```bash
cd backend
python main.py
```

### 3. Restart Frontend Service

```bash
cd frontend
npm run dev
```

## Usage

### Importing BOQ Files

- The "System" column will be automatically populated from Excel files
- "Approved Signed Quantity" and "Approved Signed Total" will be set to 0 by default

### Manual Entry

- Users can manually enter "Approved Signed Quantity" values
- "Approved Signed Total" is automatically calculated as `quantity × price`
- Both fields are editable in the BOQ Items table

### Filtering

- All new columns support filtering with the same operators as other numeric columns
- String filters for "System" column
- Numeric filters for quantity and total columns

## Notes

- Existing BOQ items will have default values (0.0) for the new approved signed columns
- The "Approved Signed Total" is automatically calculated and updated when editing
- All new columns are included in the comprehensive filtering system
- The new columns maintain the same styling and behavior as existing columns
