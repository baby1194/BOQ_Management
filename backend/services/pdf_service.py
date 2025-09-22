from reportlab.lib.pagesizes import A3, letter, A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        self.exports_dir = Path("exports")
        self.exports_dir.mkdir(exist_ok=True)
        self._register_fonts()
    
    def _register_fonts(self):
        """Register fonts including Hebrew-compatible fonts"""
        import platform
        import os
        
        # Initialize with fallback fonts
        self.hebrew_font = 'Helvetica'
        self.hebrew_font_bold = 'Helvetica-Bold'
        
        try:
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            
            # Font paths to try based on operating system
            font_paths = []
            system = platform.system().lower()
            
            if system == 'windows':
                font_paths = [
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/arialuni.ttf'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/ARIALUNI.TTF'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/arial.ttf'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/ARIAL.TTF'),
                ]
            elif system == 'linux':
                font_paths = [
                    ('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                    ('DejaVuSans', '/usr/share/fonts/TTF/DejaVuSans.ttf'),
                    ('NotoSansHebrew', '/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf'),
                    ('NotoSansHebrew', '/usr/share/fonts/opentype/noto/NotoSansHebrew-Regular.otf'),
                ]
            elif system == 'darwin':  # macOS
                font_paths = [
                    ('ArialUnicodeMS', '/System/Library/Fonts/Arial Unicode MS.ttf'),
                    ('ArialUnicodeMS', '/Library/Fonts/Arial Unicode MS.ttf'),
                    ('HelveticaNeue', '/System/Library/Fonts/HelveticaNeue.ttc'),
                ]
            
            # Try to register fonts
            font_registered = False
            for font_name, font_path in font_paths:
                try:
                    if os.path.exists(font_path):
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        
                        # Try to register bold version if it exists
                        bold_path = font_path.replace('.ttf', '-Bold.ttf').replace('.otf', '-Bold.otf')
                        bold_name = f"{font_name}-Bold"
                        
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                            registerFontFamily(font_name, normal=font_name, bold=bold_name)
                            self.hebrew_font = font_name
                            self.hebrew_font_bold = bold_name
                        else:
                            self.hebrew_font = font_name
                            self.hebrew_font_bold = font_name
                        
                        logger.info(f"Successfully registered {font_name} font for Hebrew support from {font_path}")
                        font_registered = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to register font {font_name} from {font_path}: {e}")
                    continue
            
            if not font_registered:
                logger.warning("Could not register any Hebrew-compatible fonts. Hebrew text may not display correctly.")
                
        except Exception as e:
            logger.warning(f"Font registration failed: {e}. Hebrew text may not display correctly.")
    
    def _detect_rtl(self, text):
        """Detect if text contains RTL characters (Hebrew, Arabic, etc.)"""
        if not text:
            return False
        # Check for Hebrew, Arabic, and other RTL characters
        rtl_pattern = re.compile(r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]')
        return bool(rtl_pattern.search(text))
    
    def _create_hebrew_aware_table_style(self, data, headers, column_widths):
        """Create table style that uses Hebrew fonts for Hebrew text in cells"""
        # Start with basic table style
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]
        
        # Add Hebrew font styling for individual cells
        for row_idx, row in enumerate(data):
            for col_idx, cell_value in enumerate(row):
                if cell_value and self._detect_rtl(str(cell_value)):
                    # Use Hebrew font for this cell
                    table_style.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), self.hebrew_font))
        
        return table_style
    
    def _get_project_names(self, db_session=None, sheet_data=None):
        """Get project names (English and Hebrew) from various sources"""
        project_name = ""
        project_name_hebrew = ""
        
        # Try to get from sheet data first (for concentration sheets)
        if sheet_data and hasattr(sheet_data, 'project_name') and sheet_data.project_name:
            project_name = sheet_data.project_name
            if hasattr(sheet_data, 'project_name_hebrew') and sheet_data.project_name_hebrew:
                project_name_hebrew = sheet_data.project_name_hebrew
        elif sheet_data and isinstance(sheet_data, dict) and sheet_data.get('project_name'):
            project_name = sheet_data['project_name']
            project_name_hebrew = sheet_data.get('project_name_hebrew', '')
        elif sheet_data and isinstance(sheet_data, list) and len(sheet_data) > 0:
            # For lists, try to get from first item
            first_item = sheet_data[0]
            if hasattr(first_item, 'project_name') and first_item.project_name:
                project_name = first_item.project_name
                if hasattr(first_item, 'project_name_hebrew') and first_item.project_name_hebrew:
                    project_name_hebrew = first_item.project_name_hebrew
            elif isinstance(first_item, dict) and first_item.get('project_name'):
                project_name = first_item['project_name']
                project_name_hebrew = first_item.get('project_name_hebrew', '')
        
        # If not found in data, try database
        if not project_name and db_session:
            try:
                from models import models
                project_info = db_session.query(models.ProjectInfo).first()
                if project_info and project_info.project_name:
                    project_name = project_info.project_name
                    if project_info.project_name_hebrew:
                        project_name_hebrew = project_info.project_name_hebrew
            except Exception as e:
                logger.warning(f"Could not fetch project info from database: {e}")
        
        return project_name or "Project Name", project_name_hebrew or ""
    
    def _get_project_name(self, db_session=None, sheet_data=None):
        """Get project name from various sources (backward compatibility)"""
        project_name, project_name_hebrew = self._get_project_names(db_session, sheet_data)
        
        # Combine project names if both exist
        if project_name and project_name_hebrew:
            return f"{project_name} / {project_name_hebrew}"
        elif project_name:
            return project_name
        else:
            return "Project Name"
    
    def _add_boq_header_footer(self, canvas, doc, project_name, project_name_hebrew):
        """Add header and footer to BOQ items PDF pages"""
        canvas.saveState()
        
        # Project name in header (top left)
        if project_name:
            canvas.setFont("Helvetica-Bold", 36)
            canvas.drawString(0.5*inch, doc.pagesize[1] - 0.5*inch, project_name)
        
        # Hebrew project name in header (top right)
        if project_name_hebrew:
            # Use Hebrew-compatible font for Hebrew text
            is_rtl = self._detect_rtl(project_name_hebrew)
            if is_rtl:
                canvas.setFont(self.hebrew_font_bold, 36)
            else:
                canvas.setFont("Helvetica-Bold", 36)
            
            if is_rtl:
                # RTL: draw from right to left
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, project_name_hebrew)
            else:
                # LTR: draw from left to right
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, project_name_hebrew)
        
        # Footer with underlined blanks
        footer_y = 0.5*inch
        line_y = footer_y - 5
        
        # Left side blank
        canvas.setFont("Helvetica", 9)
        canvas.drawString(0.5*inch, footer_y, "________________")
        canvas.line(0.5*inch, line_y, 2*inch, line_y)
        
        # Right side blank
        canvas.drawRightString(doc.pagesize[0] - 0.5*inch, footer_y, "________________")
        canvas.line(doc.pagesize[0] - 2*inch, line_y, doc.pagesize[0] - 0.5*inch, line_y)
        
        canvas.restoreState()
    
    def _add_header_footer(self, canvas, doc, project_name):
        """Add header and footer to PDF pages (backward compatibility)"""
        canvas.saveState()
        
        # Detect RTL
        is_rtl = self._detect_rtl(project_name)
        
        # Project name in header
        if project_name:
            if is_rtl:
                # RTL: top-right - use Hebrew font
                canvas.setFont(self.hebrew_font_bold, 36)
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, project_name)
            else:
                # LTR: top-left - use regular font
                canvas.setFont("Helvetica-Bold", 36)
                canvas.drawString(0.5*inch, doc.pagesize[1] - 0.5*inch, project_name)
        
        # Footer with underlined blanks
        footer_y = 0.5*inch
        line_y = footer_y - 5
        
        if is_rtl:
            # RTL: right side blank
            canvas.setFont("Helvetica", 9)
            canvas.drawRightString(doc.pagesize[0] - 0.5*inch, footer_y, "________________")
            # Underline
            canvas.line(doc.pagesize[0] - 2*inch, line_y, doc.pagesize[0] - 0.5*inch, line_y)
        else:
            # LTR: left side blank
            canvas.setFont("Helvetica", 9)
            canvas.drawString(0.5*inch, footer_y, "________________")
            # Underline
            canvas.line(0.5*inch, line_y, 2*inch, line_y)
        
        # Always add a blank on the opposite side for consistency
        if is_rtl:
            # LTR side blank for RTL documents
            canvas.drawString(0.5*inch, footer_y, "________________")
            canvas.line(0.5*inch, line_y, 2*inch, line_y)
        else:
            # RTL side blank for LTR documents
            canvas.drawRightString(doc.pagesize[0] - 0.5*inch, footer_y, "________________")
            canvas.line(doc.pagesize[0] - 2*inch, line_y, doc.pagesize[0] - 0.5*inch, line_y)
        
        canvas.restoreState()
    
    def export_concentration_sheets(self, sheets, db_session=None):
        """Export concentration sheets to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concentration_sheets_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, sheets)
            
            doc = SimpleDocTemplate(str(filepath), pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            story.append(Paragraph("Concentration Sheets Report", title_style))
            story.append(Spacer(1, 12))
            
            # Add content for each sheet
            for sheet in sheets:
                story.append(Paragraph(f"Sheet: {sheet.sheet_name}", styles['Heading2']))
                story.append(Spacer(1, 6))
                
                # Create table for sheet data
                data = [
                    ['Total Estimate', 'Total Submitted', 'Total PNIMI', 'Total Approved'],
                    [
                        f"${sheet.total_estimate:,.2f}",
                        f"${sheet.total_submitted:,.2f}",
                        f"${sheet.total_pnimi:,.2f}",
                        f"${sheet.total_approved:,.2f}"
                    ]
                ]
                
                # Calculate optimal column widths for concentration sheet summary
                summary_headers = ['Sub-chapter', 'Items', 'Total Estimate', 'Total Submitted', 'Total PNIMI', 'Total Approved']
                column_widths = self._calculate_column_widths(data, summary_headers, 'A4', 12, 12)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 20))
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
            logger.info(f"Generated concentration sheets PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating concentration sheets PDF: {str(e)}")
            raise
    
    def export_single_concentration_sheet(self, sheet, boq_item, entries, db_session=None):
        """Export a single concentration sheet to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concentration_sheet_{sheet.id}_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, sheet)
            
            custom_page_size = (11.7*72, 8.3*72)
            doc = SimpleDocTemplate(str(filepath), pagesize=custom_page_size)
            story = []
            styles = getSampleStyleSheet()
            
            # Project Information Table (like first image)
            project_data = [
                ['Contractor in Charge', 'Project Name', 'Developer Name'],
                [sheet.contractor_in_charge or 'N/A', sheet.project_name or 'N/A', sheet.developer_name or 'N/A'],
                ['Contract No.', '', ''],
                [sheet.contract_no or 'N/A', '', '']
            ]
            
            project_table = Table(project_data, colWidths=[2.5*72, 2.5*72, 2.5*72])
            project_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('SPAN', (0, 2), (1, 2)),  # Merge Contract No. across first two columns
                ('SPAN', (0, 3), (1, 3)),  # Merge Contract No. value across first two columns
            ]))
            
            story.append(project_table)
            story.append(Spacer(1, 20))
            
            # BOQ Item Details Table (like second image)
            boq_details = [
                [boq_item.description, 'Price', 'Unit', 'Contract Quantity', 'Section No.'],
                ['', f"{boq_item.price:,.2f}", boq_item.unit, f"{boq_item.original_contract_quantity:,.2f}", boq_item.section_number]
            ]
            
            boq_table = Table(boq_details, colWidths=[3*72, 1.5*72, 1*72, 2*72, 2*72])
            boq_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),  # Description column right-aligned
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Other columns right-aligned
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('SPAN', (0, 1), (0, 1)),  # Merge description across all columns in second row
            ]))
            
            story.append(boq_table)
            story.append(Spacer(1, 20))
            
            # Concentration Entries Table
            if entries:
                entries_data = [['Notes', 'Approved', 'Int Qty', 'Sub Qty', 'Est Qty', 'Drawing', 'Calc Sheet', 'Description']]
                
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
                
                # Calculate optimal column widths for concentration sheet entries
                concentration_headers = ['Description', 'Unit', 'Contract Qty', 'Price', 'Contract Sum', 'Submitted Qty', 'Est. Qty', 'Submitted Sum', 'Est. Sum', 'Totals']
                column_widths = self._calculate_column_widths(entries_data, concentration_headers, 'A4', 8, 8)
                
                entries_table = Table(entries_data, colWidths=column_widths)
                entries_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                
                story.append(entries_table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
            logger.info(f"Generated concentration sheet PDF with RTL layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating single concentration sheet PDF: {str(e)}")
            raise

    def export_summary(self, summary_data, db_session=None):
        """Export summary report to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_report_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, summary_data)
            
            doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            story.append(Paragraph("BOQ Summary Report", title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            headers = ['Sub-chapter', 'Items', 'Total Estimate', 'Total Submitted', 'Total PNIMI', 'Total Approved']
            data = [headers]
            
            grand_totals = {
                'items': 0,
                'estimate': 0.0,
                'submitted': 0.0,
                'pnimi': 0.0,
                'approved': 0.0
            }
            
            for row in summary_data:
                data.append([
                    row.subsection,
                    str(row.item_count),
                    f"${row.total_estimate:,.2f}",
                    f"${row.total_submitted:,.2f}",
                    f"${row.total_pnimi:,.2f}",
                    f"${row.total_approved:,.2f}"
                ])
                
                grand_totals['items'] += row.item_count
                grand_totals['estimate'] += row.total_estimate
                grand_totals['submitted'] += row.total_submitted
                grand_totals['pnimi'] += row.total_pnimi
                grand_totals['approved'] += row.total_approved
            
            # Add grand totals row
            data.append([
                'GRAND TOTAL',
                str(grand_totals['items']),
                f"${grand_totals['estimate']:,.2f}",
                f"${grand_totals['submitted']:,.2f}",
                f"${grand_totals['pnimi']:,.2f}",
                f"${grand_totals['approved']:,.2f}"
            ])
            
            # Calculate optimal column widths based on content
            column_widths = self._calculate_column_widths(data, headers, 'A4', 10, 10)
            
            table = Table(data, colWidths=column_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
            logger.info(f"Generated summary PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating summary PDF: {str(e)}")
            raise

    def export_structures_summary(self, summaries, db_session=None):
        """Export structures summary to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"structures_summary_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, summaries)
            
            doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            story.append(Paragraph("Structures Summary Report", title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            if summaries:
                headers = list(summaries[0].keys())
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(summaries[0][key], (int, float)) else "" for key in headers}
                
                for summary in summaries:
                    row_data = []
                    for key in headers:
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(f"${value:,.2f}")
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in headers:
                        if isinstance(summary[key], (int, float)):
                            grand_totals[key] += summary[key]
                
                # Add grand totals row
                xxx=0
                totals_row = []
                for key in headers:
                    if isinstance(grand_totals[key], (int, float)):
                        if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                            totals_row.append(f"${grand_totals[key]:,.2f}")
                        else:
                            totals_row.append(str(grand_totals[key]))
                    else:
                        if xxx==0:
                            totals_row.append("GRAND TOTAL")
                            xxx=1 #only add grand total once
                        else:
                            totals_row.append("")
                data.append(totals_row)
                
                # Calculate optimal column widths based on content
                column_widths = self._calculate_column_widths(data, headers, 'A4', 10, 10)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
            logger.info(f"Generated structures summary PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating structures summary PDF: {str(e)}")
            raise

    def export_systems_summary(self, summaries, db_session=None):
        """Export systems summary to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"systems_summary_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, summaries)
            
            doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            story.append(Paragraph("Systems Summary Report", title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            if summaries:
                headers = list(summaries[0].keys())
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(summaries[0][key], (int, float)) else "" for key in headers}
                
                for summary in summaries:
                    row_data = []
                    for key in headers:
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(f"${value:,.2f}")
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in headers:
                        if isinstance(summary[key], (int, float)):
                            grand_totals[key] += summary[key]
                
                # Add grand totals row
                totals_row = []
                xxx=0
                for key in headers:
                    if isinstance(grand_totals[key], (int, float)):
                        if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                            totals_row.append(f"${grand_totals[key]:,.2f}")
                        else:
                            totals_row.append(str(grand_totals[key]))
                    else:
                        if xxx==0:
                            totals_row.append("GRAND TOTAL")
                            xxx=1 #only add grand total once
                        else:
                            totals_row.append("")
                data.append(totals_row)
                
                # Calculate optimal column widths based on content
                column_widths = self._calculate_column_widths(data, headers, 'A4', 10, 10)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
            logger.info(f"Generated systems summary PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating systems summary PDF: {str(e)}")
            raise

    def export_subsections_summary(self, summaries, db_session=None):
        """Export subsections summary to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"subsections_summary_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, summaries)
            
            doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            story.append(Paragraph("Subsections Summary Report", title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            if summaries:
                headers = list(summaries[0].keys())
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(summaries[0][key], (int, float)) else "" for key in headers}
                
                for summary in summaries:
                    row_data = []
                    for key in headers:
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(f"${value:,.2f}")
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in headers:
                        if isinstance(summary[key], (int, float)):
                            grand_totals[key] += summary[key]
                
                # Add grand totals row
                xxx=0
                totals_row = []
                for key in headers:
                    if isinstance(grand_totals[key], (int, float)):
                        if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                            totals_row.append(f"${grand_totals[key]:,.2f}")
                        else:
                            totals_row.append(str(grand_totals[key]))
                    else:
                        if xxx==0:
                            totals_row.append("GRAND TOTAL")
                            xxx=1 #only add grand total once
                        else:
                            totals_row.append("")
                data.append(totals_row)
                
                # Calculate optimal column widths based on content
                column_widths = self._calculate_column_widths(data, headers, 'A4', 10, 10)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
            logger.info(f"Generated subsections summary PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating subsections summary PDF: {str(e)}")
            raise

    def export_boq_items(self, items, db_session=None):
        """Export BOQ items to PDF"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"boq_items_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project names for header
            project_name, project_name_hebrew = self._get_project_names(db_session, items)
            
            # Calculate optimal page size and column widths based on content
            if items:
                # Prepare headers and data for size calculation
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
                headers = [h for h in all_possible_headers if h in items[0].keys()]
                
                # Prepare data for calculation (headers + sample data + totals row)
                calc_data = [headers]
                for item in items[:10]:  # Use first 10 items for calculation to avoid too large pages
                    row_data = []
                    for key in headers:
                        value = item[key]
                        if isinstance(value, (int, float)):
                            if ('total' in key.lower() or 'sum' in key.lower() or 'price' in key.lower()) and 'quantity' not in key.lower():
                                row_data.append(f"${value:,.2f}")
                            else:
                                row_data.append(f"{value:,.2f}" if value != int(value) else str(int(value)))
                        else:
                            row_data.append(str(value))
                    calc_data.append(row_data)
                
                # Add a sample totals row for calculation
                calc_data.append(["GRAND TOTAL"] + [""] * (len(headers) - 1))
                
                # Calculate optimal page size
                page_size, page_name, column_widths = self._calculate_optimal_page_size(headers, calc_data, font_size=8)
                logger.info(f"Calculated optimal page size: {page_name} for {len(items)} BOQ items")
            else:
                # Default to A3 landscape if no items
                page_size = landscape(A3)
                column_widths = None
            
            doc = SimpleDocTemplate(str(filepath), pagesize=page_size)
            story = []
            styles = getSampleStyleSheet()
            
            # Create table for BOQ items data
            if items:
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
                headers = [h for h in all_possible_headers if h in items[0].keys()]
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(items[0][key], (int, float)) else "" for key in headers}
                
                # First pass: collect all data and calculate totals
                for item in items:
                    row_data = []
                    for key in headers:
                        value = item[key]
                        if isinstance(value, (int, float)):
                            # Only apply $ formatting to price and sum/total columns, not quantity columns
                            if ('total' in key.lower() or 'sum' in key.lower() or 'price' in key.lower()) and 'quantity' not in key.lower():
                                row_data.append(f"${value:,.2f}")
                            else:
                                row_data.append(f"{value:,.2f}" if value != int(value) else str(int(value)))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in headers:
                        if isinstance(item[key], (int, float)):
                            grand_totals[key] += item[key]
                
                # Add grand totals row
                totals_row = []
                for key in headers:
                    if isinstance(grand_totals[key], (int, float)):
                        # Only apply $ formatting to price and sum/total columns, not quantity columns
                        if ('total' in key.lower() or 'sum' in key.lower() or 'price' in key.lower()) and 'quantity' not in key.lower():
                            totals_row.append(f"${grand_totals[key]:,.2f}")
                        else:
                            totals_row.append(f"{grand_totals[key]:,.2f}" if grand_totals[key] != int(grand_totals[key]) else str(int(grand_totals[key])))
                    else:
                        totals_row.append("")
                totals_row[0] = "GRAND TOTAL"
                data.append(totals_row)
                
                # Use pre-calculated column widths from page size calculation
                if column_widths is None:
                    # Fallback to old method if column_widths not calculated
                    column_widths = self._calculate_column_widths(data, headers, 'A3', 8, 8)
                
                # Create table with calculated column widths
                table = Table(data, colWidths=column_widths)
                # Use Hebrew-aware table style that applies Hebrew fonts to Hebrew text
                table_style = self._create_hebrew_aware_table_style(data, headers, column_widths)
                table.setStyle(TableStyle(table_style))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_boq_header_footer(canvas, doc, project_name, project_name_hebrew), 
                     onLaterPages=lambda canvas, doc: self._add_boq_header_footer(canvas, doc, project_name, project_name_hebrew))
            logger.info(f"Generated BOQ items PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating BOQ items PDF: {str(e)}")
            raise

    def _calculate_column_widths(self, data, headers, page_size='A3', header_font_size=8, data_font_size=8):
        """Calculate optimal column widths based on actual rendered content width"""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        # Get page width based on page size (landscape orientation)
        if page_size == 'A3':
            page_width = 842  # A3 landscape width in points
        else:  # A4
            page_width = 595  # A4 landscape width in points
            
        margin = 36  # 0.5 inch margin on each side
        available_width = page_width - (2 * margin)
        
        # Font settings for width calculation
        header_font = 'Helvetica-Bold'
        data_font = 'Helvetica'
        hebrew_font = self.hebrew_font
        
        # Calculate maximum width needed for each column
        column_max_widths = []
        
        for col_idx, header in enumerate(headers):
            max_width = 0
            
            # Check header width with bold font
            header_width = stringWidth(header, header_font, header_font_size)
            max_width = max(max_width, header_width)
            
            # Check all data rows for this column
            for row in data:
                if col_idx < len(row):
                    cell_value = str(row[col_idx]) if row[col_idx] is not None else ""
                    # Use Hebrew font for width calculation if text contains Hebrew
                    if self._detect_rtl(cell_value):
                        cell_width = stringWidth(cell_value, hebrew_font, data_font_size)
                    else:
                        cell_width = stringWidth(cell_value, data_font, data_font_size)
                    max_width = max(max_width, cell_width)
            
            # Add padding (30% extra for better readability and cell spacing)
            max_width = max_width * 1.3
            
            # Set minimum and maximum column widths based on page size
            min_width = 90 if page_size == 'A4' else 105  # Minimum width for readability
            max_width = min(max_width, 400 if page_size == 'A4' else 540)  # Maximum width
            column_max_widths.append(max(min_width, max_width))
        
        # Calculate total width needed
        total_width = sum(column_max_widths)
        
        # If total width exceeds available width, scale down proportionally
        if total_width > available_width:
            scale_factor = available_width / total_width
            column_max_widths = [width * scale_factor for width in column_max_widths]
        
        # Ensure minimum width for each column (final check)
        min_final_width = 75 if page_size == 'A4' else 100
        column_max_widths = [max(min_final_width, width) for width in column_max_widths]
        
        return column_max_widths 
    
    def _calculate_optimal_page_size(self, headers, data, font_size=8):
        """Calculate optimal page size based on content volume"""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        # Font settings for width calculation
        header_font = 'Helvetica-Bold'
        data_font = 'Helvetica'
        
        # Calculate maximum width needed for each column
        column_max_widths = []
        
        for col_idx, header in enumerate(headers):
            max_width = 0
            
            # Check header width with bold font
            header_width = stringWidth(header, header_font, font_size)
            max_width = max(max_width, header_width)
            
            # Check all data rows for this column
            for row in data:
                if col_idx < len(row):
                    cell_value = str(row[col_idx]) if row[col_idx] is not None else ""
                    cell_width = stringWidth(cell_value, data_font, font_size)
                    max_width = max(max_width, cell_width)
            
            # Add padding (30% extra for better readability and cell spacing)
            max_width = max_width * 1.3
            
            # Set minimum column width for readability
            min_width = 100
            max_width = max(min_width, max_width)
            column_max_widths.append(max_width)
        
        # Calculate total content width needed
        total_content_width = sum(column_max_widths)
        
        # Add margins (1 inch on each side = 72 points each)
        margin = 72 * 2  # 2 inches total margin
        required_page_width = total_content_width + margin
        
        # Calculate page height based on number of rows
        row_height = font_size + 8  # Font size + padding
        header_height = font_size + 12  # Header row height
        total_content_height = header_height + (len(data) * row_height)
        
        # Add margins for header/footer (2 inches total)
        margin_height = 72 * 2  # 2 inches total margin
        required_page_height = total_content_height + margin_height
        
        # Standard page sizes in points (landscape orientation)
        standard_sizes = {
            'A4': (842, 595),      # A4 landscape
            'A3': (1191, 842),     # A3 landscape  
            'A2': (1684, 1191),    # A2 landscape
            'A1': (2384, 1684),    # A1 landscape
            'A0': (3370, 2384),    # A0 landscape
        }
        
        # Find the smallest standard size that fits our content
        optimal_size = None
        optimal_name = None
        
        for size_name, (width, height) in standard_sizes.items():
            if width >= required_page_width and height >= required_page_height:
                optimal_size = (width, height)
                optimal_name = size_name
                break
        
        # If no standard size fits, create a custom size
        if optimal_size is None:
            # Use the required dimensions, but ensure minimum standards
            custom_width = max(required_page_width, 842)  # At least A4 width
            custom_height = max(required_page_height, 595)  # At least A4 height
            
            # Round up to nearest 50 points for cleaner dimensions
            custom_width = ((int(custom_width) + 49) // 50) * 50
            custom_height = ((int(custom_height) + 49) // 50) * 50
            
            optimal_size = (custom_width, custom_height)
            optimal_name = f"Custom_{custom_width}x{custom_height}"
            logger.info(f"Using custom page size: {custom_width}x{custom_height} points")
        else:
            logger.info(f"Using standard page size: {optimal_name} ({optimal_size[0]}x{optimal_size[1]} points)")
        
        return optimal_size, optimal_name, column_max_widths
