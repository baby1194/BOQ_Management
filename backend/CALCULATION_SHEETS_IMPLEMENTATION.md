# Calculation Sheets Implementation

## Overview

This document describes the implementation of the calculation sheets functionality in the BOQ Management System backend.

## New Database Models

### CalculationSheet

- `id`: Primary key
- `file_name`: Name of the uploaded Excel file
- `calculation_sheet_no`: Calculation sheet number (from cell C1)
- `drawing_no`: Drawing number (from cell C2)
- `description`: Description (from cell C3)
- `import_date`: When the sheet was imported
- `created_at`, `updated_at`: Timestamps

### CalculationEntry

- `id`: Primary key
- `calculation_sheet_id`: Foreign key to CalculationSheet
- `section_number`: Section number from the calculation sheet
- `estimated_quantity`: Estimated quantity from the calculation sheet
- `quantity_submitted`: Submitted quantity from the calculation sheet
- `created_at`, `updated_at`: Timestamps

## API Endpoints

### POST `/api/file-import/import-calculation-sheets/`

**Purpose**: Import multiple calculation sheet Excel files

**Request**:

- `files`: List of Excel files (.xlsx, .xls)

**Response**: `CalculationImportResponse`

```json
{
  "success": true,
  "message": "Successfully imported X calculation sheets with Y entries",
  "files_processed": 5,
  "sheets_imported": 5,
  "entries_imported": 25,
  "errors": []
}
```

### GET `/api/calculation-sheets/`

**Purpose**: Get all calculation sheets with pagination

**Query Parameters**:

- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

### GET `/api/calculation-sheets/{sheet_id}`

**Purpose**: Get a specific calculation sheet by ID

### GET `/api/calculation-sheets/{sheet_id}/entries`

**Purpose**: Get a calculation sheet with all its entries

### DELETE `/api/calculation-sheets/{sheet_id}`

**Purpose**: Delete a calculation sheet and all its entries

### DELETE `/api/calculation-sheets/entries/{entry_id}`

**Purpose**: Delete a specific calculation entry

### POST `/api/calculation-sheets/{sheet_id}/populate-concentration-entries`

**Purpose**: Populate concentration entries from calculation sheet entries

**Request**: No body required

**Response**:

```json
{
  "success": true,
  "message": "Successfully populated X concentration entries. Y entries skipped (already exist).",
  "entries_created": 5,
  "entries_skipped": 2,
  "concentration_sheet_id": 123
}
```

**How it works**:

1. Finds BOQ items with section numbers matching the calculation entries
2. Locates the corresponding concentration sheet
3. Creates new concentration entries for each calculation entry
4. Skips entries that already exist (by section number)
5. Maps calculation data to concentration entry fields:
   - `section_number` → `job_description`
   - `estimated_quantity` → `estimate_value`
   - `quantity_submitted` → `submitted_value`

## Excel Data Extraction

The system extracts data from specific cells in each Excel file:

- **C1**: Calculation Sheet No
- **C2**: Drawing No
- **C3**: Description
- **J5, K5, L5, ...**: Section Numbers (while valid values exist)
- **J6, K6, L6, ...**: Estimated Quantities
- **J24, K24, L24, ...**: Quantity Submitted

### Data Processing Logic

1. Read Excel file without headers to access specific cell positions
2. Extract header information from cells C1, C2, C3
3. Process columns J, K, L, etc. starting from column 9 (J)
4. For each column, check if section number exists in row 4 (J5, K5, L5, etc.)
5. If section number exists, extract:
   - Estimated quantity from row 5 (J6, K6, L6, etc.)
   - Quantity submitted from row 23 (J24, K24, L24, etc.)
6. Create database records for each valid entry

## Implementation Files

### Models

- `backend/models/models.py` - Database models for CalculationSheet and CalculationEntry

### Schemas

- `backend/schemas/schemas.py` - Pydantic models for API requests/responses

### Services

- `backend/services/excel_service.py` - Excel processing logic with `read_calculation_sheet_data()` method

### Routers

- `backend/routers/file_import.py` - Import endpoint for calculation sheets
- `backend/routers/calculation_sheets.py` - CRUD operations for calculation sheets

### Main Application

- `backend/main.py` - Updated to include calculation sheets router

## Database Migration

To add the new tables to an existing database:

1. **Option 1**: Use the recreate_db.py script (WARNING: This will delete all existing data)

   ```bash
   cd backend
   python recreate_db.py
   ```

2. **Option 2**: Create a migration script to add only the new tables

   ```sql
   -- Add calculation_sheets table
   CREATE TABLE calculation_sheets (
       id SERIAL PRIMARY KEY,
       file_name VARCHAR(200) NOT NULL,
       calculation_sheet_no VARCHAR(100) NOT NULL,
       drawing_no VARCHAR(100) NOT NULL,
       description TEXT NOT NULL,
       import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE
   );

   -- Add calculation_entries table
   CREATE TABLE calculation_entries (
       id SERIAL PRIMARY KEY,
       calculation_sheet_id INTEGER NOT NULL REFERENCES calculation_sheets(id) ON DELETE CASCADE,
       section_number VARCHAR(100) NOT NULL,
       estimated_quantity FLOAT DEFAULT 0.0,
       quantity_submitted FLOAT DEFAULT 0.0,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE
   );

   -- Add indexes
   CREATE INDEX idx_calculation_sheets_file_name ON calculation_sheets(file_name);
   CREATE INDEX idx_calculation_entries_sheet_id ON calculation_entries(calculation_sheet_id);
   CREATE INDEX idx_calculation_entries_section ON calculation_entries(section_number);
   ```

## Testing

A test script is provided to verify the calculation sheet functionality:

```bash
cd backend
python test_calculation_sheets.py
```

This script:

1. Creates a sample Excel file with calculation sheet data
2. Tests the `read_calculation_sheet_data()` method
3. Verifies data extraction from specific cells
4. Cleans up the test file

## Error Handling

The system includes comprehensive error handling:

- **File Validation**: Checks file extensions (.xlsx, .xls)
- **Data Validation**: Ensures required header fields are present
- **Database Transactions**: Uses rollback on errors to maintain data integrity
- **Logging**: Records all import operations and errors
- **Partial Success**: Continues processing other files even if one fails

## Frontend Integration

The frontend can now:

1. Upload multiple calculation sheet files
2. View imported calculation sheets
3. Browse calculation entries
4. Search and filter calculation sheets
5. Delete individual sheets or entries

## Duplicate Detection

The system automatically detects and skips duplicate calculation sheets based on the combination of:

- **Calculation Sheet No** (from cell C1)
- **Drawing No** (from cell C2)

### How It Works

1. **Pre-import Check**: Before importing, the system checks if a calculation sheet with the same Sheet No + Drawing No combination already exists
2. **Skip Logic**: If a duplicate is found, the file is skipped and an informative message is logged
3. **Database Constraint**: A unique constraint at the database level provides additional protection against duplicates
4. **User Feedback**: The import response includes details about skipped files and successful imports

### Example Scenarios

- **File 1**: CS-001, DR-001 → **Imports successfully**
- **File 2**: CS-002, DR-002 → **Imports successfully** (different)
- **File 3**: CS-001, DR-001 → **Skipped** (duplicate of File 1)
- **File 4**: CS-001, DR-003 → **Imports successfully** (same sheet no, different drawing)

### Benefits

- **Prevents Data Duplication**: Ensures each unique calculation sheet is imported only once
- **Maintains Data Integrity**: Keeps the database clean and consistent
- **User-Friendly**: Clear feedback about what was imported vs. skipped
- **Efficient Processing**: Continues with other files even when duplicates are encountered

## Security Considerations

- File upload validation (Excel files only)
- Temporary file processing (files are not permanently stored)
- Database transaction safety
- Input sanitization for database queries
