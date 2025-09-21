import pandas as pd
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from datetime import datetime
from models import models
import os

logger = logging.getLogger(__name__)

class ExcelService:
    def __init__(self):
        self.supported_extensions = ['.xlsx', '.xls']
        self.exports_dir = Path("exports")
        self.exports_dir.mkdir(exist_ok=True)
    
    def read_boq_file(self, file_path: str) -> List[Dict]:
        """Read BOQ items from Excel file"""
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Clean column names by stripping whitespace
            df.columns = df.columns.str.strip()
            # print("_____Cleaned column names_____", list(df.columns))
            
            items = []
            
            for _, row in df.iterrows():
                # print("_____row_____", row)
                # print("_____row types_____", row.dtypes)
                # print("_____Serial Number raw_____", row.get('Serial Number'), "Type:", type(row.get('Serial Number')))
                # print("_____Description raw_____", row.get('Description'), "Type:", type(row.get('Description')))
                
                # Check if we have the minimum required data
                if pd.notna(row.get('Section Number', '')) and pd.notna(row.get('Description', '')):
                    section_number = str(row.get('Section Number', '')).strip()
                    parts = section_number.split('.')
                    subsection = '.'.join(parts[:3]) if len(parts) >= 3 else section_number
                    
                    # Extract all values with proper null handling
                    serial_number = row.get('Serial Number')
                    structure = row.get('Structure')
                    system = row.get('System')
                    description = row.get('Description')
                    unit = row.get('Unit')
                    original_contract_quantity = row.get('Original Contract Quantity')
                    price = row.get('Price')
                    total_contract_sum = row.get('Total Contract Sum')
                    estimated_quantity = row.get('Estimated Quantity')
                    quantity_submitted = row.get('Quantity Submitted')
                    internal_quantity = row.get('Internal Quantity')
                    approved_by_project_manager = row.get('Approved by Project Manager')
                    total_estimate = row.get('Total Estimate')
                    total_submitted = row.get('Total Submitted')
                    internal_total = row.get('Internal Total')
                    total_approved_by_project_manager = row.get('Total Approved by Project Manager')
                    notes = row.get('NOTES')
                    
                    # print("_____Extracted values_____")
                    # print("serial_number:", serial_number, "pd.notna:", pd.notna(serial_number))
                    # print("description:", description, "pd.notna:", pd.notna(description))
                    
                    # More robust null checking
                    def safe_float(value):
                        if pd.isna(value) or value == '' or value is None:
                            return None
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return None
                    
                    def safe_int(value):
                        if pd.isna(value) or value == '' or value is None:
                            return None
                        try:
                            return int(float(value))  # Convert float to int for cases like 59.0 -> 59
                        except (ValueError, TypeError):
                            return None
                    
                    def safe_str(value):
                        if pd.isna(value) or value is None:
                            return ''
                        return str(value).strip()
                    
                    item = {
                        'serial_number': safe_int(serial_number),
                        'structure': safe_int(structure),
                        'system': safe_str(system),
                        'section_number': section_number,
                        'description': safe_str(description),
                        'unit': safe_str(unit),
                        'original_contract_quantity': safe_float(original_contract_quantity) or 0,
                        'price': safe_float(price) or 0,
                        'total_contract_sum': safe_float(total_contract_sum) or 0,
                        'estimated_quantity': safe_float(estimated_quantity) or 0,
                        'quantity_submitted': safe_float(quantity_submitted) or 0,
                        'internal_quantity': safe_float(internal_quantity) or 0,
                        'approved_by_project_manager': safe_float(approved_by_project_manager) or 0,
                        'total_estimate': safe_float(total_estimate) or 0,
                        'total_submitted': safe_float(total_submitted) or 0,
                        'internal_total': safe_float(internal_total) or 0,
                        'total_approved_by_project_manager': safe_float(total_approved_by_project_manager) or 0,
                        'approved_signed_quantity': 0.0,  # Default value for new column
                        'approved_signed_total': 0.0,  # Default value for new column
                        'notes': safe_str(notes),
                        'subsection': subsection
                    }
                    # print("_____item_____", item)
                    items.append(item)
            
            logger.info(f"Successfully read {len(items)} items from BOQ file")
            return items
            
        except Exception as e:
            logger.error(f"Error reading BOQ file: {str(e)}")
            raise
    

    def read_calculation_sheet_data(self, file_path: str) -> Dict:
        """
        Read calculation sheet data from Excel file based on specific cell locations
        Returns: {
            'calculation_sheet_no': str,
            'drawing_no': str,
            'description': str,
            'entries': [
                {
                    'section_number': str,
                    'estimated_quantity': float,
                    'quantity_submitted': float
                }
            ]
        }
        """
        try:
            print("_____ok_____")
            # Read Excel file without headers to access specific cells

            # if os.path.exists(file_path):
            #     print("_____file exists_____")
            # else:
            #     print("_____file does not exist_____")

            df = pd.read_excel(file_path, sheet_name="Calculation", header=None)
            df.to_csv("output.csv", index=False, header=False)
            # print(df)
            
            # Extract header information from specific cells
            calculation_sheet_no = str(df.iloc[0, 2]).strip() if pd.notna(df.iloc[0, 2]) else ""  # C1
            drawing_no = str(df.iloc[1, 2]).strip() if pd.notna(df.iloc[1, 2]) else ""  # C2
            description = str(df.iloc[2, 2]).strip() if pd.notna(df.iloc[2, 2]) else ""  # C3
            
            # Validate required fields
            if not calculation_sheet_no or not drawing_no or not description:
                raise ValueError(f"Missing required header information in {file_path}")
            
            entries = []
            
            col_index = 4
            
            while col_index < df.shape[1]:
                # Check if section number exists in row 4 (J5, K5, L5, etc.)
                section_number = df.iloc[4, col_index]
                
                if pd.notna(section_number) and str(section_number).strip():
                    section_number = str(section_number).strip()
                    
                    # Get estimated quantity from row 5 (J6, K6, L6, etc.)
                    estimated_quantity = df.iloc[5, col_index]
                    estimated_quantity = float(estimated_quantity) if pd.notna(estimated_quantity) else 0.0
                    
                    # Get quantity submitted from row 23 (J24, K24, L24, etc.)
                    quantity_submitted = df.iloc[23, col_index]
                    quantity_submitted = float(quantity_submitted) if pd.notna(quantity_submitted) else 0.0
                    
                    entry = {
                        'section_number': section_number,
                        'estimated_quantity': estimated_quantity,
                        'quantity_submitted': quantity_submitted
                    }
                    entries.append(entry)
                
                col_index += 1
            
            if not entries:
                logger.warning(f"No valid entries found in {file_path}")
            
            result = {
                'calculation_sheet_no': calculation_sheet_no,
                'drawing_no': drawing_no,
                'description': description,
                'entries': entries
            }
            
            logger.info(f"Successfully read calculation sheet data from {file_path}: {len(entries)} entries")
            return result
            
        except Exception as e:
            logger.error(f"Error reading calculation sheet data from {file_path}: {str(e)}")
            raise
    
    def process_excel_file(self, file_path: Path) -> Tuple[List[Dict], List[str]]:
        """
        Process an Excel file and return items and errors
        Returns: (items, errors)
        """
        items = []
        errors = []
        
        try:
            # Try to process as BOQ file first
            try:
                items = self.read_boq_file(str(file_path))
                logger.info(f"Successfully processed {len(items)} BOQ items from {file_path.name}")
                return items, errors
            except Exception as e:
                logger.warning(f"Failed to process {file_path.name} as BOQ file: {str(e)}")
                errors.append(f"Failed to process as BOQ file: {str(e)}")
            
            # If BOQ processing failed, try as calculation file
            try:
                calculation_entries = self.read_calculation_file(str(file_path))
                # For calculation files, we need to create BOQ items from the entries
                # This is a simplified approach - you might need to adjust based on your needs
                if calculation_entries:
                    # Create a single BOQ item from the calculation file
                    item = {
                        'serial_number': None,
                        'structure': None,
                        'section_number': f"CALC_{file_path.stem}",
                        'description': f"Calculation entries from {file_path.name}",
                        'unit': 'N/A',
                        'original_contract_quantity': 0,
                        'price': 0,
                        'total_contract_sum': 0,
                        'estimated_quantity': sum(entry.get('estimated_quantity', 0) for entry in calculation_entries),
                        'quantity_submitted': sum(entry.get('quantity_submitted', 0) for entry in calculation_entries),
                        'internal_quantity': sum(entry.get('internal_quantity', 0) for entry in calculation_entries),
                        'approved_by_project_manager': sum(entry.get('approved_by_project_manager', 0) for entry in calculation_entries),
                        'total_estimate': sum(entry.get('estimated_quantity', 0) for entry in calculation_entries),
                        'total_submitted': sum(entry.get('quantity_submitted', 0) for entry in calculation_entries),
                        'internal_total': sum(entry.get('internal_quantity', 0) for entry in calculation_entries),
                        'total_approved_by_project_manager': sum(entry.get('approved_by_project_manager', 0) for entry in calculation_entries),
                        'notes': f"Processed from calculation file: {file_path.name}",
                        'subsection': 'CALCULATIONS'
                    }
                    items = [item]
                    logger.info(f"Successfully processed calculation file {file_path.name} into {len(items)} BOQ items")
                    return items, errors
            except Exception as e:
                logger.warning(f"Failed to process {file_path.name} as calculation file: {str(e)}")
                errors.append(f"Failed to process as calculation file: {str(e)}")
            
            # If both failed, return empty items with errors
            if not items:
                errors.append(f"Could not process {file_path.name} as either BOQ or calculation file")
            
            return items, errors
            
        except Exception as e:
            error_msg = f"Unexpected error processing {file_path.name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            return items, errors 

    def export_single_concentration_sheet(self, sheet, boq_item, entries):
        """Export a single concentration sheet to Excel matching PDF format on single sheet"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concentration_sheet_{sheet.id}_{timestamp}.xlsx"
            filepath = self.exports_dir / filename
            
            # Create Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # Single sheet with all content
                sheet_name = 'Concentration Sheet'
                
                # Project Information Table (like first image)
                project_data = [
                    ['Contractor in Charge', 'Project Name', 'Developer Name'],
                    [sheet.contractor_in_charge or 'N/A', sheet.project_name or 'N/A', sheet.developer_name or 'N/A'],
                    ['Contract No.', '', ''],
                    [sheet.contract_no or 'N/A', '', '']
                ]
                
                df_project = pd.DataFrame(project_data)
                df_project.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=0)
                
                # Add spacing after project info
                spacing_rows = 2
                
                # Concentration Entries Table
                if entries:
                    entries_data = []
                    for entry in entries:
                        entries_data.append([
                            entry.notes or '',
                            f"{entry.approved_by_project_manager:,.2f}",
                            f"{entry.internal_quantity:,.2f}",
                            f"{entry.quantity_submitted:,.2f}",
                            f"{entry.estimated_quantity:,.2f}",
                            entry.drawing_no or '',
                            entry.calculation_sheet_no or '',
                            entry.description[:30] + '...' if entry.description and len(entry.description) > 30 else (entry.description or '')
                        ])
                    
                    # Add totals row
                    total_estimate = sum(entry.estimated_quantity for entry in entries)
                    total_submitted = sum(entry.quantity_submitted for entry in entries)
                    total_pnimi = sum(entry.internal_quantity for entry in entries)
                    total_approved = sum(entry.approved_by_project_manager for entry in entries)
                    
                    entries_data.append([
                        '',
                        f"{total_approved:,.2f}",
                        f"{total_pnimi:,.2f}",
                        f"{total_submitted:,.2f}",
                        f"{total_estimate:,.2f}",
                        '',
                        '',
                        'TOTALS'
                    ])
                    
                    # Create DataFrame with reversed column order
                    columns = ['Notes', 'Approved', 'Int Qty', 'Sub Qty', 'Est Qty', 'Drawing', 'Calc Sheet', 'Description']
                    df_entries = pd.DataFrame(entries_data, columns=columns)
                    df_entries.to_excel(writer, sheet_name=sheet_name, index=False, startrow=len(project_data) + spacing_rows)
                
                # Apply formatting to the single sheet
                workbook = writer.book
                worksheet = workbook[sheet_name]
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Style header row and apply right alignment for RTL
                from openpyxl.styles import Font, PatternFill, Alignment
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="right", vertical="center")
                data_alignment = Alignment(horizontal="right", vertical="center")
                
                # Apply right alignment to all cells for RTL layout
                for row in worksheet.iter_rows():
                    for cell in row:
                        cell.alignment = data_alignment
                
                # Style Project Info header row (first row)
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Style Concentration Entries header row
                if entries:
                    entries_header_row = len(project_data) + spacing_rows + 1
                    for cell in worksheet[entries_header_row]:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                    
                    # Style totals row
                    totals_row = len(project_data) + spacing_rows + len(entries_data)
                    for cell in worksheet[totals_row]:
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(start_color="87CEEB", end_color="87CEEB", fill_type="solid")
                
                # Merge cells for Project Info sheet (Contract No. spanning)
                worksheet.merge_cells('A3:B3')  # Contract No. header
                worksheet.merge_cells('A4:B4')  # Contract No. value
            
            logger.info(f"Generated concentration sheet Excel with single sheet RTL layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating concentration sheet Excel: {str(e)}")
            raise

    def export_all_concentration_sheets(self, sheets_data):
        """Export all concentration sheets to a single Excel file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"all_concentration_sheets_{timestamp}.xlsx"
            filepath = self.exports_dir / filename
            
            # Create Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # Sheet 1: Overview
                overview_data = []
                for sheet_info in sheets_data:
                    sheet = sheet_info['sheet']
                    boq_item = sheet_info['boq_item']
                    entries = sheet_info['entries']
                    
                    total_estimated = sum(entry.estimated_quantity for entry in entries) if entries else 0
                    total_submitted = sum(entry.quantity_submitted for entry in entries) if entries else 0
                    total_internal = sum(entry.internal_quantity for entry in entries) if entries else 0
                    total_approved = sum(entry.approved_by_project_manager for entry in entries) if entries else 0
                    
                    overview_data.append({
                        'Sheet ID': sheet.id,
                        'Sheet Name': sheet.sheet_name,
                        'BOQ Section': boq_item.section_number,
                        'BOQ Description': boq_item.description,
                        'Project Name': sheet.project_name or 'N/A',
                        'Contractor': sheet.contractor_in_charge or 'N/A',
                        'Total Entries': len(entries) if entries else 0,
                        'Total Est Qty': total_estimated,
                        'Total Sub Qty': total_submitted,
                        'Total Int Qty': total_internal,
                        'Total Approved Qty': total_approved,
                        'Contract Qty': boq_item.original_contract_quantity,
                        'Contract Value': boq_item.total_contract_sum,
                        'Est Value': total_estimated * boq_item.price,
                        'Sub Value': total_submitted * boq_item.price,
                        'Int Value': total_internal * boq_item.price,
                        'Approved Value': total_approved * boq_item.price,
                        'Variance (Sub-Contract)': (total_submitted * boq_item.price) - boq_item.total_contract_sum,
                        'Variance (Approved-Contract)': (total_approved * boq_item.price) - boq_item.total_contract_sum
                    })
                
                if overview_data:
                    df_overview = pd.DataFrame(overview_data)
                    df_overview.to_excel(writer, sheet_name='Overview', index=False)
                    
                    # Add grand totals row
                    grand_totals = {
                        'Sheet ID': 'GRAND TOTALS',
                        'Sheet Name': '',
                        'BOQ Section': '',
                        'BOQ Description': '',
                        'Project Name': '',
                        'Contractor': '',
                        'Total Entries': sum(row['Total Entries'] for row in overview_data),
                        'Total Est Qty': sum(row['Total Est Qty'] for row in overview_data),
                        'Total Sub Qty': sum(row['Total Sub Qty'] for row in overview_data),
                        'Total Int Qty': sum(row['Total Int Qty'] for row in overview_data),
                        'Total Approved Qty': sum(row['Total Approved Qty'] for row in overview_data),
                        'Contract Qty': sum(row['Contract Qty'] for row in overview_data),
                        'Contract Value': sum(row['Contract Value'] for row in overview_data),
                        'Est Value': sum(row['Est Value'] for row in overview_data),
                        'Sub Value': sum(row['Sub Value'] for row in overview_data),
                        'Int Value': sum(row['Int Value'] for row in overview_data),
                        'Approved Value': sum(row['Approved Value'] for row in overview_data),
                        'Variance (Sub-Contract)': sum(row['Variance (Sub-Contract)'] for row in overview_data),
                        'Variance (Approved-Contract)': sum(row['Variance (Approved-Contract)'] for row in overview_data)
                    }
                    
                    df_totals = pd.DataFrame([grand_totals])
                    df_totals.to_excel(writer, sheet_name='Overview', 
                                     startrow=len(overview_data) + 2, index=False, header=False)
                
                # Individual sheets for each concentration sheet
                for i, sheet_info in enumerate(sheets_data):
                    sheet = sheet_info['sheet']
                    boq_item = sheet_info['boq_item']
                    entries = sheet_info['entries']
                    
                    sheet_name = f"Sheet_{sheet.id}_{boq_item.section_number[:20]}"
                    if len(sheet_name) > 31:  # Excel sheet name limit
                        sheet_name = f"Sheet_{sheet.id}_{i+1}"
                    
                    # Project info for this sheet
                    project_data = {
                        'Field': [
                            'Project Name',
                            'Contractor in Charge', 
                            'Contract No',
                            'Developer Name',
                            'Section Number',
                            'Description',
                            'Unit',
                            'Contract Quantity',
                            'Price',
                            'Total Contract Sum',
                            'Sheet Name',
                            'Created Date',
                            'Last Updated'
                        ],
                        'Value': [
                            sheet.project_name or 'N/A',
                            sheet.contractor_in_charge or 'N/A',
                            sheet.contract_no or 'N/A',
                            sheet.developer_name or 'N/A',
                            boq_item.section_number,
                            boq_item.description,
                            boq_item.unit,
                            f"{boq_item.original_contract_quantity:,.2f}",
                            f"${boq_item.price:,.2f}",
                            f"${boq_item.total_contract_sum:,.2f}",
                            sheet.sheet_name,
                            sheet.created_at.strftime("%Y-%m-%d %H:%M:%S") if sheet.created_at else 'N/A',
                            sheet.updated_at.strftime("%Y-%m-%d %H:%M:%S") if sheet.updated_at else 'N/A'
                        ]
                    }
                    
                    df_project = pd.DataFrame(project_data)
                    df_project.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)
                    
                    # Entries for this sheet
                    if entries:
                        entries_data = []
                        for entry in entries:
                            entries_data.append({
                                'ID': entry.id,
                                'Section Number': entry.section_number,
                                'Description': entry.description or '',
                                'Calculation Sheet No': entry.calculation_sheet_no or '',
                                'Drawing No': entry.drawing_no or '',
                                'Estimated Quantity': entry.estimated_quantity,
                                'Quantity Submitted': entry.quantity_submitted,
                                'Internal Quantity': entry.internal_quantity,
                                'Approved by Project': entry.approved_by_project_manager,
                                'Notes': entry.notes or '',
                                'Created Date': entry.created_at.strftime("%Y-%m-%d %H:%M:%S") if entry.created_at else '',
                                'Last Updated': entry.updated_at.strftime("%Y-%m-%d %H:%M:%S") if entry.updated_at else ''
                            })
                        
                        df_entries = pd.DataFrame(entries_data)
                        df_entries.to_excel(writer, sheet_name=sheet_name, index=False, startrow=len(project_data) + 3)
                        
                        # Add totals row
                        total_estimated = sum(entry.estimated_quantity for entry in entries)
                        total_submitted = sum(entry.quantity_submitted for entry in entries)
                        total_internal = sum(entry.internal_quantity for entry in entries)
                        total_approved = sum(entry.approved_by_project_manager for entry in entries)
                        
                        totals_data = {
                            'ID': 'TOTALS',
                            'Section Number': '',
                            'Description': '',
                            'Calculation Sheet No': '',
                            'Drawing No': '',
                            'Estimated Quantity': total_estimated,
                            'Quantity Submitted': total_submitted,
                            'Internal Quantity': total_internal,
                            'Approved by Project': total_approved,
                            'Notes': '',
                            'Created Date': '',
                            'Last Updated': ''
                        }
                        
                        df_totals = pd.DataFrame([totals_data])
                        df_totals.to_excel(writer, sheet_name=sheet_name, 
                                         startrow=len(project_data) + len(entries_data) + 5, index=False, header=False)
                
                # Apply formatting
                workbook = writer.book
                for sheet_name in workbook.sheetnames:
                    worksheet = workbook[sheet_name]
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                    
                    # Style header row
                    from openpyxl.styles import Font, PatternFill, Alignment
                    header_font = Font(bold=True, color="FFFFFF")
                    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                    header_alignment = Alignment(horizontal="center", vertical="center")
                    
                    for cell in worksheet[1]:
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                    
                    # Style totals row if it exists
                    if sheet_name != 'Overview':
                        # Find totals row (look for row with 'TOTALS' in first column)
                        for row_num in range(1, worksheet.max_row + 1):
                            if worksheet.cell(row=row_num, column=1).value == 'TOTALS':
                                totals_font = Font(bold=True, color="FFFFFF")
                                totals_fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
                                totals_alignment = Alignment(horizontal="center", vertical="center")
                                
                                for col in range(1, worksheet.max_column + 1):
                                    cell = worksheet.cell(row=row_num, column=col)
                                    cell.font = totals_font
                                    cell.fill = totals_fill
                                    cell.alignment = totals_alignment
                                break
                    else:
                        # Style grand totals row for Overview sheet
                        totals_row = len(overview_data) + 3
                        totals_font = Font(bold=True, color="FFFFFF")
                        totals_fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
                        totals_alignment = Alignment(horizontal="center", vertical="center")
                        
                        for col in range(1, worksheet.max_column + 1):
                            cell = worksheet.cell(row=totals_row, column=col)
                            cell.font = totals_font
                            cell.fill = totals_fill
                            cell.alignment = totals_alignment
            
            logger.info(f"Generated comprehensive all concentration sheets Excel: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating all concentration sheets Excel: {str(e)}")
            raise

    def export_structures_summary(self, summaries):
        """Export structures summary to Excel"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"structures_summary_{timestamp}.xlsx"
            filepath = self.exports_dir / filename
            
            if not summaries:
                raise ValueError("No data to export")
            
            # Convert to DataFrame
            df = pd.DataFrame(summaries)
            
            # Format numeric columns
            numeric_columns = ['total_estimate', 'total_submitted', 'internal_total', 'total_approved', 'approved_signed_total']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
            
            # Add grand totals row
            totals_row = {}
            for col in df.columns:
                if col in numeric_columns and col in df.columns:
                    # Extract numeric values for calculation
                    numeric_values = [float(str(val).replace('$', '').replace(',', '')) for val in df[col] if pd.notna(val) and str(val).startswith('$')]
                    totals_row[col] = f"${sum(numeric_values):,.2f}" if numeric_values else "$0.00"
                elif col == 'structure':
                    totals_row[col] = "GRAND TOTAL"
                elif col == 'description':
                    totals_row[col] = ""
                else:
                    totals_row[col] = ""
            
            df_totals = pd.DataFrame([totals_row])
            df_final = pd.concat([df, df_totals], ignore_index=True)
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='Structures Summary', index=False)
                
                # Apply formatting
                workbook = writer.book
                worksheet = writer.sheets['Structures Summary']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Style header row
                from openpyxl.styles import Font, PatternFill, Alignment
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Style totals row
                totals_row_num = len(df_final) + 1
                totals_font = Font(bold=True, color="FFFFFF")
                totals_fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
                totals_alignment = Alignment(horizontal="center", vertical="center")
                
                for col in range(1, worksheet.max_column + 1):
                    cell = worksheet.cell(row=totals_row_num, column=col)
                    cell.font = totals_font
                    cell.fill = totals_fill
                    cell.alignment = totals_alignment
            
            logger.info(f"Generated structures summary Excel: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating structures summary Excel: {str(e)}")
            raise

    def export_systems_summary(self, summaries):
        """Export systems summary to Excel"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"systems_summary_{timestamp}.xlsx"
            filepath = self.exports_dir / filename
            
            if not summaries:
                raise ValueError("No data to export")
            
            # Convert to DataFrame
            df = pd.DataFrame(summaries)
            
            # Format numeric columns
            numeric_columns = ['total_estimate', 'total_submitted', 'internal_total', 'total_approved', 'approved_signed_total']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
            
            # Add grand totals row
            totals_row = {}
            for col in df.columns:
                if col in numeric_columns and col in df.columns:
                    # Extract numeric values for calculation
                    numeric_values = [float(str(val).replace('$', '').replace(',', '')) for val in df[col] if pd.notna(val) and str(val).startswith('$')]
                    totals_row[col] = f"${sum(numeric_values):,.2f}" if numeric_values else "$0.00"
                elif col == 'system':
                    totals_row[col] = "GRAND TOTAL"
                elif col == 'description':
                    totals_row[col] = ""
                else:
                    totals_row[col] = ""
            
            df_totals = pd.DataFrame([totals_row])
            df_final = pd.concat([df, df_totals], ignore_index=True)
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='Systems Summary', index=False)
                
                # Apply formatting
                workbook = writer.book
                worksheet = writer.sheets['Systems Summary']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Style header row
                from openpyxl.styles import Font, PatternFill, Alignment
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Style totals row
                totals_row_num = len(df_final) + 1
                totals_font = Font(bold=True, color="FFFFFF")
                totals_fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
                totals_alignment = Alignment(horizontal="center", vertical="center")
                
                for col in range(1, worksheet.max_column + 1):
                    cell = worksheet.cell(row=totals_row_num, column=col)
                    cell.font = totals_font
                    cell.fill = totals_fill
                    cell.alignment = totals_alignment
            
            logger.info(f"Generated systems summary Excel: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating systems summary Excel: {str(e)}")
            raise

    def export_subsections_summary(self, summaries):
        """Export subsections summary to Excel"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"subsections_summary_{timestamp}.xlsx"
            filepath = self.exports_dir / filename
            
            if not summaries:
                raise ValueError("No data to export")
            
            # Convert to DataFrame
            df = pd.DataFrame(summaries)
            
            # Format numeric columns
            numeric_columns = ['total_estimate', 'total_submitted', 'internal_total', 'total_approved', 'approved_signed_total']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
            
            # Add grand totals row
            totals_row = {}
            for col in df.columns:
                if col in numeric_columns and col in df.columns:
                    # Extract numeric values for calculation
                    numeric_values = [float(str(val).replace('$', '').replace(',', '')) for val in df[col] if pd.notna(val) and str(val).startswith('$')]
                    totals_row[col] = f"${sum(numeric_values):,.2f}" if numeric_values else "$0.00"
                elif col == 'subsection':
                    totals_row[col] = "GRAND TOTAL"
                elif col == 'description':
                    totals_row[col] = ""
                else:
                    totals_row[col] = ""
            
            df_totals = pd.DataFrame([totals_row])
            df_final = pd.concat([df, df_totals], ignore_index=True)
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='Subsections Summary', index=False)
                
                # Apply formatting
                workbook = writer.book
                worksheet = writer.sheets['Subsections Summary']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Style header row
                from openpyxl.styles import Font, PatternFill, Alignment
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Style totals row
                totals_row_num = len(df_final) + 1
                totals_font = Font(bold=True, color="FFFFFF")
                totals_fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
                totals_alignment = Alignment(horizontal="center", vertical="center")
                
                for col in range(1, worksheet.max_column + 1):
                    cell = worksheet.cell(row=totals_row_num, column=col)
                    cell.font = totals_font
                    cell.fill = totals_fill
                    cell.alignment = totals_alignment
            
            logger.info(f"Generated subsections summary Excel: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating subsections summary Excel: {str(e)}")
            raise

    def export_boq_items(self, items):
        """Export BOQ items to Excel"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"boq_items_{timestamp}.xlsx"
            filepath = self.exports_dir / filename
            
            if not items:
                raise ValueError("No data to export")
            
            # Define column order to match BOQ table order
            all_possible_headers = [
                'serial_number', 'structure', 'system', 'section_number', 'description', 'unit',
                'original_contract_quantity'
            ]
            
            # Add contract update quantity columns in order
            for key in items[0].keys():
                if key.startswith('updated_contract_quantity_'):
                    all_possible_headers.append(key)
            
            all_possible_headers.append('price')
            
            # Add contract update sum columns in order
            for key in items[0].keys():
                if key.startswith('updated_contract_sum_'):
                    all_possible_headers.append(key)
            
            all_possible_headers.extend([
                'total_contract_sum', 'estimated_quantity', 'quantity_submitted', 'internal_quantity',
                'approved_by_project_manager', 'approved_signed_quantity', 'total_estimate',
                'total_submitted', 'internal_total', 'total_approved_by_project_manager',
                'approved_signed_total', 'subsection', 'notes'
            ])
            
            # Only include headers that exist in the data
            ordered_headers = [h for h in all_possible_headers if h in items[0].keys()]
            
            # Create DataFrame with ordered columns
            df = pd.DataFrame(items)[ordered_headers]
            
            # Format only price and sum/total columns (not quantity columns)
            for col in df.columns:
                if col in df.columns and df[col].dtype in ['float64', 'int64']:
                    # Only apply $ formatting to price and sum/total columns, not quantity columns
                    if ('total' in col.lower() or 'sum' in col.lower() or 'price' in col.lower()) and 'quantity' not in col.lower():
                        df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else "$0.00")
                    else:
                        # Format quantity columns without $ symbol
                        df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) and x != int(x) else str(int(x)) if pd.notna(x) and isinstance(x, (int, float)) else "0")
            
            # Add grand totals row
            totals_row = {}
            for col in df.columns:
                if df[col].dtype in ['float64', 'int64']:
                    # Calculate totals from original numeric data
                    total_value = sum([float(str(val).replace('$', '').replace(',', '')) for val in df[col] if pd.notna(val) and str(val) not in ['', 'nan']])
                    
                    # Apply same formatting logic as data rows
                    if ('total' in col.lower() or 'sum' in col.lower() or 'price' in col.lower()) and 'quantity' not in col.lower():
                        totals_row[col] = f"${total_value:,.2f}"
                    else:
                        totals_row[col] = f"{total_value:,.2f}" if total_value != int(total_value) else str(int(total_value))
                elif col == 'section_number':
                    totals_row[col] = "GRAND TOTAL"
                else:
                    totals_row[col] = ""
            
            df_totals = pd.DataFrame([totals_row])
            df_final = pd.concat([df, df_totals], ignore_index=True)
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='BOQ Items', index=False)
                
                # Apply formatting
                workbook = writer.book
                worksheet = writer.sheets['BOQ Items']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Style header row
                from openpyxl.styles import Font, PatternFill, Alignment
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Style totals row
                totals_row_num = len(df_final) + 1
                totals_font = Font(bold=True, color="FFFFFF")
                totals_fill = PatternFill(start_color="C0504D", end_color="C0504D", fill_type="solid")
                totals_alignment = Alignment(horizontal="center", vertical="center")
                
                for col in range(1, worksheet.max_column + 1):
                    cell = worksheet.cell(row=totals_row_num, column=col)
                    cell.font = totals_font
                    cell.fill = totals_fill
                    cell.alignment = totals_alignment
            
            logger.info(f"Generated BOQ items Excel: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating BOQ items Excel: {str(e)}")
            raise 