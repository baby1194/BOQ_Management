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
from models import models

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
                    ('NotoSans', 'C:/Windows/Fonts/NotoSans-Regular.ttf'),
                    ('NotoSans', 'C:/Windows/Fonts/NotoSans-Bold.ttf'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/arialuni.ttf'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/ARIALUNI.TTF'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/arial.ttf'),
                    ('ArialUnicodeMS', 'C:/Windows/Fonts/ARIAL.TTF'),
                    ('Tahoma', 'C:/Windows/Fonts/tahoma.ttf'),
                    ('Tahoma', 'C:/Windows/Fonts/TAHOMA.TTF'),
                    ('David', 'C:/Windows/Fonts/david.ttf'),
                    ('David', 'C:/Windows/Fonts/DAVID.TTF'),
                    ('Miriam', 'C:/Windows/Fonts/miriam.ttf'),
                    ('Miriam', 'C:/Windows/Fonts/MIRIAM.TTF'),
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
                        logger.info(f"Hebrew font set to: {self.hebrew_font}, Hebrew bold font set to: {self.hebrew_font_bold}")
                        font_registered = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to register font {font_name} from {font_path}: {e}")
                    continue
            
            if not font_registered:
                logger.warning("Could not register any Hebrew-compatible fonts. Hebrew text may not display correctly.")
                logger.warning(f"Falling back to default fonts: {self.hebrew_font}, {self.hebrew_font_bold}")
                
        except Exception as e:
            logger.warning(f"Font registration failed: {e}. Hebrew text may not display correctly.")
        
        # Test the Hebrew font after registration
        self._test_hebrew_font()
    
    def _test_hebrew_font(self, text="בדיקת טקסט עברי"):
        """Test if the current Hebrew font can render Hebrew text correctly"""
        try:
            from reportlab.pdfbase.pdfmetrics import stringWidth
            # Try to calculate width with Hebrew font
            width = stringWidth(text, self.hebrew_font, 12)
            logger.info(f"Hebrew font test successful: '{text}' width = {width} using font '{self.hebrew_font}'")
            
            # Also test shekel symbol
            shekel_text = "₪ 1,234.56"
            shekel_width = stringWidth(shekel_text, self.hebrew_font, 12)
            logger.info(f"Shekel symbol test successful: '{shekel_text}' width = {shekel_width} using font '{self.hebrew_font}'")
            
            return True
        except Exception as e:
            logger.warning(f"Hebrew font test failed: {e}")
            return False
    
    def _format_currency(self, value, language="en"):
        """Format currency value with proper shekel symbol handling"""
        if isinstance(value, (int, float)):
            if language == "he":
                # For Hebrew, use NIS instead of shekel symbol to avoid font issues
                return f"₪ {value:,.2f}"
            else:
                # For English, use NIS instead of shekel symbol to avoid font issues
                return f"₪ {value:,.2f}"
        return str(value)
    
    def _is_currency_value(self, text):
        """Check if text contains currency symbols that need special font handling"""
        if isinstance(text, str):
            return '₪' in text or 'NIS' in text.upper()
            return False
    
    def _detect_rtl(self, text):
        """Detect if text contains RTL characters (Hebrew, Arabic, etc.) or currency symbols"""
        if not text:
            return False
        # Check for Hebrew, Arabic, and other RTL characters
        rtl_pattern = re.compile(r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]')
        # Also check for shekel symbol (₪) which needs Hebrew font support
        has_rtl = bool(rtl_pattern.search(text))
        has_shekel = '₪' in text
        return has_rtl or has_shekel
    
    def _reverse_hebrew_text(self, text):
        """Reverse Hebrew text to display correctly in PDFs (RTL to LTR for PDF rendering)"""
        if not text or not self._detect_rtl(text):
            return text
        
        # Check if text contains only shekel symbol or currency - don't reverse these
        if text.strip() == '₪' or (text.strip().startswith('₪') and not re.search(r'[\u0590-\u05FF]', text)):
            return text
        
        # For Hebrew text, we need to reverse the entire text character by character
        # This is because PDF rendering engines don't handle RTL properly
        return text[::-1]
    
    def _create_hebrew_aware_table_style(self, data, headers, column_widths):
        """Create table style that uses Hebrew fonts for Hebrew text in cells"""
        # Process data to reverse Hebrew text for proper PDF display
        processed_data = []
        for row in data:
            processed_row = []
            for cell_value in row:
                if cell_value and self._detect_rtl(str(cell_value)):
                    # Reverse Hebrew text for proper PDF display
                    processed_row.append(self._reverse_hebrew_text(str(cell_value)))
                else:
                    processed_row.append(cell_value)
            processed_data.append(processed_row)
        
        # Start with basic table style
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]
        
        # Add Hebrew font styling for individual cells
        # Note: processed_data includes headers as first row, so we start from row 0
        hebrew_cells_count = 0
        for row_idx, row in enumerate(processed_data):
            for col_idx, cell_value in enumerate(row):
                if cell_value and (self._detect_rtl(str(cell_value)) or self._is_currency_value(str(cell_value))):
                    # Use Hebrew font for this cell (Hebrew text or currency symbols)
                    table_style.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), self.hebrew_font))
                    # Also set font size for Hebrew cells to ensure proper rendering
                    table_style.append(('FONTSIZE', (col_idx, row_idx), (col_idx, row_idx), 8))
                    hebrew_cells_count += 1
                    logger.debug(f"Applied Hebrew font to cell ({row_idx}, {col_idx}): '{cell_value}' using font '{self.hebrew_font}'")
        
        logger.info(f"Applied Hebrew font to {hebrew_cells_count} cells in table")
        
        return table_style, processed_data
    
    def _create_robust_hebrew_table(self, data, headers, column_widths, repeat_rows=0):
        """Create a table with robust Hebrew support using Paragraph objects"""
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import ParagraphStyle
        
        # Create Hebrew-aware paragraph styles
        hebrew_style = ParagraphStyle(
            'HebrewStyle',
            fontName=self.hebrew_font,
            fontSize=8,
            alignment=1,  # Center alignment
            spaceAfter=0,
            spaceBefore=0,
            leftIndent=0,
            rightIndent=0,
        )
        
        english_style = ParagraphStyle(
            'EnglishStyle',
            fontName='Helvetica',
            fontSize=8,
            alignment=1,  # Center alignment
            spaceAfter=0,
            spaceBefore=0,
            leftIndent=0,
            rightIndent=0,
        )
        
        # Convert data to Paragraph objects for better text rendering
        paragraph_data = []
        for row_idx, row in enumerate(data):
            paragraph_row = []
            for col_idx, cell_value in enumerate(row):
                if cell_value and self._detect_rtl(str(cell_value)):
                    # Use Hebrew paragraph style for Hebrew text with reversed text
                    reversed_text = self._reverse_hebrew_text(str(cell_value))
                    paragraph_row.append(Paragraph(reversed_text, hebrew_style))
                else:
                    # Use English paragraph style for non-Hebrew text
                    paragraph_row.append(Paragraph(str(cell_value) if cell_value else "", english_style))
            paragraph_data.append(paragraph_row)
        
        # Create table with Paragraph objects and repeatRows if specified
        table = Table(paragraph_data, colWidths=column_widths, repeatRows=repeat_rows)
        
        # Apply basic table styling
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]
        
        table.setStyle(TableStyle(table_style))
        return table
    
    def _get_project_names(self, db_session=None, sheet_data=None):
        """Get project names (English and Hebrew) from various sources"""
        project_name = ""
        project_name_hebrew = ""
        
        # Always try to get project info from database first for Hebrew project name
        if db_session:
            try:
                from models import models
                project_info = db_session.query(models.ProjectInfo).first()
                if project_info:
                    if project_info.project_name:
                        project_name = project_info.project_name
                    if project_info.project_name_hebrew:
                        project_name_hebrew = project_info.project_name_hebrew
            except Exception as e:
                logger.warning(f"Could not fetch project info from database: {e}")
        
        # If project name not found in database, try to get from sheet data
        if not project_name and sheet_data:
            if sheet_data and hasattr(sheet_data, 'project_name') and sheet_data.project_name:
                project_name = sheet_data.project_name
            elif sheet_data and isinstance(sheet_data, dict) and sheet_data.get('project_name'):
                project_name = sheet_data['project_name']
            elif sheet_data and isinstance(sheet_data, list) and len(sheet_data) > 0:
                # For lists, try to get from first item
                first_item = sheet_data[0]
                if hasattr(first_item, 'project_name') and first_item.project_name:
                    project_name = first_item.project_name
                elif isinstance(first_item, dict) and first_item.get('project_name'):
                    project_name = first_item['project_name']
        
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
                # Don't reverse Hebrew text - display as is
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, self._reverse_hebrew_text(project_name_hebrew))
            else:
                canvas.setFont("Helvetica-Bold", 36)
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, self._reverse_hebrew_text(project_name_hebrew))
        
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
    
    def _add_concentration_header_footer(self, canvas, doc, title_text, language="en"):
        """Add header and footer to concentration sheet PDF pages with title"""
        canvas.saveState()
        
        # Title at top
        if title_text:
            if language == "he":
                # Hebrew: right-aligned with Hebrew font
                canvas.setFont(self.hebrew_font_bold, 24)
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, self._reverse_hebrew_text(title_text))
            else:
                # English: left-aligned with regular font
                canvas.setFont("Helvetica-Bold", 24)
                canvas.drawString(0.5*inch, doc.pagesize[1] - 0.5*inch, title_text)
        
        
        # Footer
        footer_y = 0.5*inch
        line_y = footer_y + 0.1*inch
        
        if language == "he":
            # Hebrew footer: right-aligned
            canvas.setFont("Helvetica", 10)
            canvas.drawRightString(doc.pagesize[0] - 0.5*inch, footer_y, "________________")
            canvas.line(doc.pagesize[0] - 2*inch, line_y, doc.pagesize[0] - 0.5*inch, line_y)
        else:
            # English footer: left-aligned
            canvas.setFont("Helvetica", 10)
        canvas.drawString(0.5*inch, footer_y, "________________")
        canvas.line(0.5*inch, line_y, 2*inch, line_y)
        
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
                # Reverse Hebrew text for proper PDF display
                reversed_project_name = self._reverse_hebrew_text(project_name)
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, reversed_project_name)
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
                        self._format_currency(sheet.total_estimate),
                        self._format_currency(sheet.total_submitted),
                        self._format_currency(sheet.total_pnimi),
                        self._format_currency(sheet.total_approved)
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
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
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
    
    def _calculate_concentration_sheet_page_size(self, entries):
        """Calculate optimal page size for concentration sheet based on content"""
        try:
            from reportlab.pdfbase.pdfmetrics import stringWidth
            
            # Base dimensions for the three tables
            # Table 1: Project Information (2 rows, 4 columns)
            project_table_height = 2 * 35  # 2 rows * 35 points per row (including padding)
            
            # Table 2: BOQ Item Details (2 rows, 5 columns)
            boq_table_height = 2 * 35  # 2 rows * 35 points per row (including padding)
            
            # Table 3: Concentration Entries (header + data rows + totals)
            entries_header_height = 35  # Header row
            entries_data_height = max(1, len(entries)) * 30  # Data rows (minimum 1 row)
            entries_totals_height = 35  # Totals row
            entries_table_height = entries_header_height + entries_data_height + entries_totals_height
            
            # Spacing between tables (2 spacers of 20 points each)
            spacing_height = 2 * 20
            
            # Header and footer space
            header_footer_height = 120
            
            # Total content height
            total_content_height = (
                project_table_height + 
                boq_table_height + 
                entries_table_height + 
                spacing_height + 
                header_footer_height
            )
            
            # Add margins: top and bottom margins (1 inch each = 72 points each)
            top_bottom_margin = 72 * 2  # 2 inches total
            total_height = total_content_height + top_bottom_margin
            
            # Calculate width based on content requirements
            # Project table: 4 columns
            # BOQ table: 5 columns  
            # Entries table: 8 columns (widest)
            # Use the widest table as base and ensure good readability
            
            # Calculate column widths for entries table (widest table)
            entries_headers = ['Description', 'Calculation Sheet No', 'Drawing No', 'Estimated Quantity', 
                             'Quantity Submitted', 'Internal Quantity', 'Approved by Project Manager', 'Notes']
            
            # Calculate width for each column based on content
            column_widths = []
            font_size = 8
            header_font = 'Helvetica-Bold'
            data_font = 'Helvetica'
            
            for header in entries_headers:
                # Calculate header width
                header_width = stringWidth(header, header_font, font_size)
                
                # Add some padding for data content (estimate 50% more than header)
                estimated_width = header_width * 1.5
                
                # Set minimum width for readability
                min_width = 80
                max_width = 200  # Maximum width per column
                
                column_width = max(min_width, min(estimated_width, max_width))
                column_widths.append(column_width)
            
            # Total table width
            total_table_width = sum(column_widths)
            
            # Add margins: left and right margins (0.75 inch each = 54 points each)
            left_right_margin = 54 * 2  # 1.5 inches total margin
            total_width = total_table_width + left_right_margin
            
            # Ensure minimum dimensions for standard printing
            min_width = 8.5 * 72   # 8.5 inches
            min_height = 11 * 72   # 11 inches
            
            # Use larger of calculated or minimum dimensions
            final_width = max(total_width, min_width)
            final_height = max(total_height, min_height)
            
            # Limit maximum size to reasonable bounds (A0 size max)
            max_width = 33.1 * 72   # A0 width
            max_height = 46.8 * 72  # A0 height
            
            final_width = min(final_width, max_width)
            final_height = min(final_height, max_height)
            
            logger.info(f"Calculated concentration sheet page size: {final_width/72:.2f}\" x {final_height/72:.2f}\" for {len(entries)} entries")
            
            return (final_width, final_height)
            
        except Exception as e:
            logger.error(f"Error calculating page size: {str(e)}")
            # Fallback to A4 size
            return (8.5*72, 11*72)

    def export_single_concentration_sheet(self, sheet, boq_item, entries, db_session=None, entry_columns=None, language="en"):
        """Export a single concentration sheet to PDF with custom page sizing"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concentration_sheet_{sheet.id}_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project information from ProjectInfo table
            project_info = None
            if db_session:
                project_info = db_session.query(models.ProjectInfo).first()
            
            # Define translations for headers based on language
            if language == "he":
                # Hebrew translations
                headers_translations = {
                    'Description': 'תיאור:',
                    'Calculation Sheet No': 'מס\' דף חישוב',
                    'Drawing No': 'מס\' שרטוט',
                    'Estimated Quantity': 'כמות מוערכת',
                    'Quantity Submitted': 'כמות הוגשה',
                    'Internal Quantity': 'כמות פנימית',
                    'Approved by Project Manager': 'כמות מוגשת',
                    'Notes': 'הערות'
                }
                project_headers_translations = {
                    'Contract No': 'מספר החוזה',
                    'Developer Name': 'שם יזם',
                    'Project Name': 'שם הפרויקט',
                    'Contractor in Charge': 'הקבלן האחראי'
                }
                boq_headers_translations = {
                    'Section No': 'סעיף מספר',
                    'Contract Quantity': 'כמות החוזה',
                    'Unit': 'יחידה',
                    'Price': 'מחיר',
                    'Description': 'תיאור:'
                }
                # Use project_name_hebrew from ProjectInfo if available, otherwise fall back to project_name
                if project_info and project_info.project_name_hebrew:
                    title_text = project_info.project_name_hebrew
                elif project_info and project_info.project_name:
                    title_text = project_info.project_name
                else:
                    title_text = f"דף ריכוז - {boq_item.section_number}"
                entries_title = "רשומות ריכוז"
                totals_text = "סיכומים"
            else:
                # English (default)
                headers_translations = {
                    'Description': 'Description:',
                    'Calculation Sheet No': 'Calc. Sheet No',
                    'Drawing No': 'Drawing No',
                    'Estimated Quantity': 'Est. Quantity',
                    'Quantity Submitted': 'Qty Submitted',
                    'Internal Quantity': 'Internal Qty',
                    'Approved by Project Manager': 'Approved Qty',
                    'Notes': 'Notes'
                }
                project_headers_translations = {
                    'Contract No': 'Contract No',
                    'Developer Name': 'Developer Name',
                    'Project Name': 'Project Name',
                    'Contractor in Charge': 'Contractor in Charge'
                }
                boq_headers_translations = {
                    'Section No': 'Section No',
                    'Contract Quantity': 'Contract Quantity',
                    'Unit': 'Unit',
                    'Price': 'Price',
                    'Description': 'Description:'
                }
                # Use project_name from ProjectInfo if available, otherwise fall back to concentration sheet
                if project_info and project_info.project_name:
                    title_text = project_info.project_name
                elif sheet.project_name:
                    title_text = sheet.project_name
                else:
                    title_text = f"Concentration Sheet - {boq_item.section_number}"
                entries_title = "Concentration Entries"
                totals_text = "TOTALS"
            
            # Apply column filtering based on entry_columns if provided (define early for use throughout method)
            all_headers = ['Description', 'Calculation Sheet No', 'Drawing No', 'Estimated Quantity', 
                           'Quantity Submitted', 'Internal Quantity', 'Approved by Project Manager', 'Notes']
            
            # Filter headers and their indices based on entry_columns configuration
            filtered_headers = []
            if entry_columns:
                if entry_columns.get('include_description', True):
                    filtered_headers.append('Description')
                if entry_columns.get('include_calculation_sheet_no', True):
                    filtered_headers.append('Calculation Sheet No')
                if entry_columns.get('include_drawing_no', True):
                    filtered_headers.append('Drawing No')
                if entry_columns.get('include_estimated_quantity', True):
                    filtered_headers.append('Estimated Quantity')
                if entry_columns.get('include_quantity_submitted', True):
                    filtered_headers.append('Quantity Submitted')
                if entry_columns.get('include_internal_quantity', True):
                    filtered_headers.append('Internal Quantity')
                if entry_columns.get('include_approved_by_project_manager', True):
                    filtered_headers.append('Approved by Project Manager')
                if entry_columns.get('include_notes', True):
                    filtered_headers.append('Notes')
            else:
                # If no filtering specified, include all columns
                filtered_headers = all_headers
            
            # Translate headers based on language
            translated_headers = [headers_translations[header] for header in filtered_headers]
            
            # Create list of column indices to include
            header_indices = [all_headers.index(header) for header in filtered_headers]
            
            # Calculate optimal page size based on content using the same method as BOQ items
            page_size = None
            page_width = None
            concentration_column_widths = None
            
            if entries:
                # Prepare data for optimal page size calculation using translated headers
                calc_data = [translated_headers]
                for entry in entries[:10]:  # Use first 10 entries for calculation
                    all_entry_data = [
                        entry.description or '',
                        entry.calculation_sheet_no or '',
                        entry.drawing_no or '',
                        f"{entry.estimated_quantity:,.2f}",
                        f"{entry.quantity_submitted:,.2f}",
                        f"{entry.internal_quantity:,.2f}",
                        f"{entry.approved_by_project_manager:,.2f}",
                        entry.notes or ''
                    ]
                    # Filter data based on selected columns
                    filtered_entry_data = [all_entry_data[i] for i in header_indices]
                    calc_data.append(filtered_entry_data)
                
                # Add a sample totals row for calculation
                calc_data.append([totals_text] + [""] * (len(translated_headers) - 1))
                
                # Calculate optimal page size using the same method as BOQ items
                page_size, page_name, concentration_column_widths = self._calculate_optimal_page_size(
                    translated_headers, calc_data, font_size=9
                )
                page_width = page_size[0]
                logger.info(f"Calculated optimal page size: {page_name} for concentration sheet")
            else:
                # Default to A3 landscape if no entries
                page_size = landscape(A3)
                page_width = page_size[0]
            
            # Add smaller margins (0.75 inches each)
            doc = SimpleDocTemplate(str(filepath), pagesize=page_size, 
                                  leftMargin=54, rightMargin=54, topMargin=36, bottomMargin=36)
            story = []
            styles = getSampleStyleSheet()
            story.append(Spacer(1, 20))
            # First Table: Project Information (2 rows, 3 columns) - Removed Project Name
            project_headers = ['Contract No', 'Developer Name', 'Contractor in Charge']
            # Use ProjectInfo data if available, otherwise fall back to ConcentrationSheet data
            project_values = [
                (project_info.contract_no if project_info else None) or sheet.contract_no or 'N/A',
                (project_info.developer_name if project_info else None) or sheet.developer_name or 'N/A', 
                (project_info.main_contractor_name if project_info else None) or sheet.contractor_in_charge or 'N/A'
            ]
            
            # Translate project headers
            translated_project_headers = [project_headers_translations[header] for header in project_headers]
            
            project_data = [translated_project_headers, project_values]
            # Calculate column widths based on actual content
            project_col_widths = self._calculate_column_widths(project_data, translated_project_headers, page_width, 12, 12)
            project_table = Table(project_data, colWidths=project_col_widths)
            project_table_style, processed_project_data = self._create_hebrew_aware_table_style(project_data, translated_project_headers, project_col_widths)
            # Set alignment based on language
            if language == "he":
                # Hebrew mode: right-aligned
                project_table_style.extend([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ])
            else:
                # English mode: left-aligned
                project_table_style.extend([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
            
            # Create table with processed data (Hebrew text reversed)
            project_table = Table(processed_project_data, colWidths=project_col_widths)
            project_table.setStyle(TableStyle(project_table_style))
            story.append(project_table)
            story.append(Spacer(1, 20))
            
            # Second Table: BOQ Item Details (2 rows, 5 columns)
            boq_headers = ['Section No', 'Contract Quantity', 'Unit', 'Price', 'Description']
            boq_values = [
                boq_item.section_number,
                f"{boq_item.original_contract_quantity:,.2f}",
                boq_item.unit,
                f"{boq_item.price:,.2f}",
                boq_item.description or ''
            ]
            
            # Translate BOQ headers
            translated_boq_headers = [boq_headers_translations[header] for header in boq_headers]
            
            boq_data = [translated_boq_headers, boq_values]
            # Calculate column widths based on actual content with special handling for description
            boq_col_widths = self._calculate_column_widths(boq_data, translated_boq_headers, page_width, 11, 11)
            boq_table = Table(boq_data, colWidths=boq_col_widths)
            
            # Use Hebrew-aware styling for the BOQ item details table
            boq_table_style, processed_boq_data = self._create_hebrew_aware_table_style(boq_data, translated_boq_headers, boq_col_widths)
            
            # Customize the style for BOQ item details based on language
            if language == "he":
                # Hebrew mode: right-aligned
                boq_table_style.extend([
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),  # All columns right-aligned for Hebrew
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),   # Top alignment for potential multi-line description
                ])
            else:
                # English mode: left-aligned
                boq_table_style.extend([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # All columns left-aligned for English
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),   # Top alignment for potential multi-line description
                ])
            
            # Create table with processed data (Hebrew text reversed)
            boq_table = Table(processed_boq_data, colWidths=boq_col_widths)
            boq_table.setStyle(TableStyle(boq_table_style))
            
            story.append(boq_table)
            story.append(Spacer(1, 20))
            
            # Third Table: Concentration Entries (following the order shown on concentration sheets page)
            if entries:
                # Use the already defined translated_headers and header_indices from page size calculation
                entries_data = [translated_headers]
                
                for entry in entries:
                    all_entry_data = [
                        entry.description or '',
                        entry.calculation_sheet_no or '',
                        entry.drawing_no or '',
                        f"{entry.estimated_quantity:,.2f}",
                        f"{entry.quantity_submitted:,.2f}",
                        f"{entry.internal_quantity:,.2f}",
                        f"{entry.approved_by_project_manager:,.2f}",
                        entry.notes or ''
                    ]
                    # Filter data based on selected columns
                    filtered_entry_data = [all_entry_data[i] for i in header_indices]
                    entries_data.append(filtered_entry_data)
                
                # Add totals row with filtered columns
                total_estimate = sum(entry.estimated_quantity for entry in entries)
                total_submitted = sum(entry.quantity_submitted for entry in entries)
                total_internal = sum(entry.internal_quantity for entry in entries)
                total_approved = sum(entry.approved_by_project_manager for entry in entries)
                
                # Create full totals row and filter based on selected columns
                all_totals_row = [
                    totals_text,
                    '',
                    '',
                    f"{total_estimate:,.2f}",
                    f"{total_submitted:,.2f}",
                    f"{total_internal:,.2f}",
                    f"{total_approved:,.2f}",
                    ''
                ]
                filtered_totals_row = [all_totals_row[i] for i in header_indices]
                entries_data.append(filtered_totals_row)
                
                # Use pre-calculated column widths from page size calculation (same as BOQ items)
                # Use translated headers for table creation
                current_headers = translated_headers
                
                if concentration_column_widths is None:
                    # Fallback: calculate column widths if not pre-calculated
                    column_widths = self._calculate_column_widths(entries_data, current_headers, page_width, 9, 9)
                else:
                    # Note: concentration_column_widths was calculated for all columns, we need to filter it too
                    # For now, calculate new widths based on filtered data
                    column_widths = self._calculate_column_widths(entries_data, current_headers, page_width, 9, 9)
                
                # Try to use robust Hebrew table method first, fallback to regular table if it fails
                try:
                    entries_table = self._create_robust_hebrew_table(entries_data, current_headers, column_widths, repeat_rows=1)
                    logger.info("Successfully created robust Hebrew table for concentration entries with repeatRows")
                except Exception as e:
                    logger.warning(f"Failed to create robust Hebrew table, falling back to regular table: {e}")
                    entries_table = Table(entries_data, colWidths=column_widths, repeatRows=1)
                    # Use Hebrew-aware table style that applies Hebrew fonts to Hebrew text (same as BOQ items)
                    entries_table_style, processed_entries_data = self._create_hebrew_aware_table_style(entries_data, current_headers, column_widths)
                    
                    # Customize the style for concentration entries based on language
                    if language == "he":
                        # Hebrew mode: right-aligned content
                        entries_table_style.extend([
                            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),  # All columns right-aligned for Hebrew
                            ('FONTSIZE', (0, 0), (-1, -1), 9),  # Slightly smaller font for concentration entries
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),  # Less padding for more compact rows
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for multi-line content
                            ('BACKGROUND', (0, 1), (-1, -2), colors.white),  # Data rows background - white
                            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # Totals row background
                        ])
                    else:
                        # English mode: left-aligned content
                        entries_table_style.extend([
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # All columns left-aligned for English
                        ('FONTSIZE', (0, 0), (-1, -1), 9),  # Slightly smaller font for concentration entries
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),  # Less padding for more compact rows
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for multi-line content
                        ('BACKGROUND', (0, 1), (-1, -2), colors.white),  # Data rows background - white
                        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # Totals row background
                    ])
                    
                    # Create table with processed data (Hebrew text reversed)
                    entries_table = Table(processed_entries_data, colWidths=column_widths)
                    entries_table.setStyle(TableStyle(entries_table_style))
                
                story.append(entries_table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, title_text, language), 
                     onLaterPages=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, title_text, language))
            logger.info(f"Generated concentration sheet PDF with RTL layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating single concentration sheet PDF: {str(e)}")
            raise

    def export_summary(self, summary_data, db_session=None, language="en"):
        """Export summary report to PDF with language support"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_report_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project information from ProjectInfo table
            project_info = None
            if db_session:
                project_info = db_session.query(models.ProjectInfo).first()
            
            # Define translations based on language
            if language == "he":
                # Hebrew translations
                headers_translations = {
                    'Sub-chapter': 'תת-פרק',
                    'Items': 'פריטים',
                    'Total Estimate': 'סה"כ הערכה',
                    'Total Submitted': 'סה"כ הוגש',
                    'Total PNIMI': 'סה"כ פנימי',
                    'Total Approved': 'סה"כ מאושר'
                }
                title_text = "דוח סיכום BOQ"
                grand_total_text = "סה\"כ כללי"
            else:
                # English (default)
                headers_translations = {
                    'Sub-chapter': 'Sub-chapter',
                    'Items': 'Items',
                    'Total Estimate': 'Total Estimate',
                    'Total Submitted': 'Total Submitted',
                    'Total PNIMI': 'Total PNIMI',
                    'Total Approved': 'Total Approved'
                }
                title_text = "BOQ Summary Report"
                grand_total_text = "GRAND TOTAL"
            
            # Get project name for title
            if language == "he":
                project_name = (project_info.project_name_hebrew if project_info and project_info.project_name_hebrew 
                               else project_info.project_name if project_info 
                               else "דוח סיכום BOQ")
            else:
                project_name = (project_info.project_name if project_info and project_info.project_name
                               else "BOQ Summary Report")
            
            doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            
            # Create table for summary data with translated headers
            headers = ['Sub-chapter', 'Items', 'Total Estimate', 'Total Submitted', 'Total PNIMI', 'Total Approved']
            translated_headers = [headers_translations[header] for header in headers]
            data = [translated_headers]
            
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
                    self._format_currency(row.total_estimate),
                    self._format_currency(row.total_submitted),
                    self._format_currency(row.total_pnimi),
                    self._format_currency(row.total_approved)
                ])
                
                grand_totals['items'] += row.item_count
                grand_totals['estimate'] += row.total_estimate
                grand_totals['submitted'] += row.total_submitted
                grand_totals['pnimi'] += row.total_pnimi
                grand_totals['approved'] += row.total_approved
            
            # Add grand totals row with translated text
            data.append([
                grand_total_text,
                str(grand_totals['items']),
                self._format_currency(grand_totals['estimate']),
                self._format_currency(grand_totals['submitted']),
                self._format_currency(grand_totals['pnimi']),
                self._format_currency(grand_totals['approved'])
            ])
            
            # Calculate optimal column widths based on content
            column_widths = self._calculate_column_widths(data, translated_headers, 'A4', 10, 10)
            
            # Use Hebrew-aware table creation
            try:
                table = self._create_robust_hebrew_table(data, translated_headers, column_widths, repeat_rows=1)
                logger.info("Successfully created robust Hebrew table for summary with repeatRows")
            except Exception as e:
                logger.warning(f"Failed to create robust Hebrew table, falling back to regular table: {e}")
                table = Table(data, colWidths=column_widths, repeatRows=1)
                table_style, processed_data = self._create_hebrew_aware_table_style(data, translated_headers, column_widths)
                
                # Set alignment based on language
            if language == "he":
                # Hebrew mode: right-aligned
                table_style.extend([
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Bright gray for header row
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Black text for better contrast
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.white),  # White background for data rows
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ])
            else:
                # English mode: left-aligned
                table_style.extend([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Bright gray for header row
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Black text for better contrast
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.white),  # White background for data rows
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ])
            
            table = Table(processed_data, colWidths=column_widths)
            table.setStyle(TableStyle(table_style))
            
            story.append(table)
            
            # Use the same header approach as concentration sheets
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language), 
                     onLaterPages=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language))
            logger.info(f"Generated summary PDF with {language} layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating summary PDF: {str(e)}")
            raise

    def export_structures_summary(self, summaries, db_session=None, language="en"):
        """Export structures summary to PDF with language support"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"structures_summary_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project name for header
            project_name = self._get_project_name(db_session, summaries)
            
            # Define translations for headers based on language
            if language == "he":
                # Hebrew translations for structures summary
                headers_translations = {
                    'structure': 'מבנה',
                    'description': 'תיאור',
                    'total_contract_sum': 'סה"כ חוזה',
                    'total_estimate': 'סה"כ הערכה',
                    'total_submitted': 'סה"כ הוגש',
                    'internal_total': 'סה"כ פנימי',
                    'total_approved': 'סה"כ מאושר',
                    'approved_signed_total': 'סה"כ מאושר חתום',
                    'item_count': 'מספר פריטים'
                }
                grand_total_text = "סה\"כ כללי"
            else:
                # English (default)
                headers_translations = {
                    'structure': 'Structure',
                    'description': 'Description',
                    'total_contract_sum': 'Total Contract Sum',
                    'total_estimate': 'Total Estimate',
                    'total_submitted': 'Total Submitted',
                    'internal_total': 'Internal Total',
                    'total_approved': 'Total Approved',
                    'approved_signed_total': 'Approved Signed Total',
                    'item_count': 'Item Count'
                }
                grand_total_text = "GRAND TOTAL"
            
            # Calculate optimal page size and column widths based on content
            if summaries:
                raw_headers = list(summaries[0].keys())
                # Translate headers
                headers = [headers_translations.get(header, header) for header in raw_headers]
                
                # Prepare data for size calculation (headers + sample data + totals row)
                calc_data = [headers]
                for summary in summaries[:10]:  # Use first 10 items for calculation to avoid too large pages
                    row_data = []
                    for key in raw_headers:  # Use raw headers for data access
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    calc_data.append(row_data)
                
                # Add a sample totals row for calculation
                calc_data.append([grand_total_text] + [""] * (len(headers) - 1))
                
                # Calculate optimal page size
                page_size, page_name, column_widths = self._calculate_optimal_page_size(headers, calc_data, font_size=8)
                logger.info(f"Calculated optimal page size: {page_name} for {len(summaries)} structures")
            else:
                # Default to A4 landscape if no summaries
                page_size = landscape(A4)
                column_widths = None
            
            doc = SimpleDocTemplate(str(filepath), pagesize=page_size)
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
            # Use language-specific title
            if language == "he":
                title_text = "דוח סיכום מבנים"
            else:
                title_text = "Structures Summary Report"
            
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            if summaries:
                # Use the same raw_headers and translated headers from above
                raw_headers = list(summaries[0].keys())
                headers = [headers_translations.get(header, header) for header in raw_headers]
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(summaries[0][key], (int, float)) else "" for key in raw_headers}
                
                for summary in summaries:
                    row_data = []
                    for key in raw_headers:  # Use raw headers for data access
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in raw_headers:  # Use raw headers for data access
                        if isinstance(summary[key], (int, float)):
                            grand_totals[key] += summary[key]
                
                # Add grand totals row
                totals_row = []
                for i, key in enumerate(raw_headers):  # Use raw headers for data access
                    if isinstance(grand_totals[key], (int, float)):
                        if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                            totals_row.append(self._format_currency(grand_totals[key]))
                        else:
                            totals_row.append(str(grand_totals[key]))
                    else:
                        if i == 0:  # Only add grand total text in first column
                            totals_row.append(grand_total_text)
                        else:
                            totals_row.append("")
                data.append(totals_row)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language), 
                     onLaterPages=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language))
            logger.info(f"Generated structures summary PDF with {language} layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating structures summary PDF: {str(e)}")
            raise

    def export_systems_summary(self, summaries, db_session=None, language="en"):
        """Export systems summary to PDF with language support"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"systems_summary_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project information from ProjectInfo table
            project_info = None
            if db_session:
                project_info = db_session.query(models.ProjectInfo).first()
            
            # Get project name for title
            if language == "he":
                project_name = (project_info.project_name_hebrew if project_info and project_info.project_name_hebrew 
                               else project_info.project_name if project_info 
                               else "דוח סיכום מערכות")
            else:
                project_name = (project_info.project_name if project_info and project_info.project_name
                               else "Systems Summary Report")
            
            # Define translations for headers based on language
            if language == "he":
                # Hebrew translations for systems summary
                headers_translations = {
                    'system': 'מערכת',
                    'description': 'תיאור',
                    'total_contract_sum': 'סה"כ חוזה',
                    'total_estimate': 'סה"כ הערכה',
                    'total_submitted': 'סה"כ הוגש',
                    'internal_total': 'סה"כ פנימי',
                    'total_approved': 'סה"כ מאושר',
                    'approved_signed_total': 'סה"כ מאושר חתום',
                    'item_count': 'מספר פריטים'
                }
                grand_total_text = "סה\"כ כללי"
            else:
                # English (default)
                headers_translations = {
                    'system': 'System',
                    'description': 'Description',
                    'total_contract_sum': 'Total Contract Sum',
                    'total_estimate': 'Total Estimate',
                    'total_submitted': 'Total Submitted',
                    'internal_total': 'Internal Total',
                    'total_approved': 'Total Approved',
                    'approved_signed_total': 'Approved Signed Total',
                    'item_count': 'Item Count'
                }
                grand_total_text = "GRAND TOTAL"
            
            # Calculate optimal page size and column widths based on content
            if summaries:
                raw_headers = list(summaries[0].keys())
                # Translate headers
                headers = [headers_translations.get(header, header) for header in raw_headers]
                
                # Prepare data for size calculation (headers + sample data + totals row)
                calc_data = [headers]
                for summary in summaries[:10]:  # Use first 10 items for calculation to avoid too large pages
                    row_data = []
                    for key in raw_headers:  # Use raw headers for data access
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    calc_data.append(row_data)
                
                # Add a sample totals row for calculation
                calc_data.append([grand_total_text] + [""] * (len(headers) - 1))
                
                # Calculate optimal page size
                page_size, page_name, column_widths = self._calculate_optimal_page_size(headers, calc_data, font_size=8)
                logger.info(f"Calculated optimal page size: {page_name} for {len(summaries)} systems")
            else:
                # Default to A4 landscape if no summaries
                page_size = landscape(A4)
                column_widths = None
            
            doc = SimpleDocTemplate(str(filepath), pagesize=page_size)
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
            # Use language-specific title
            if language == "he":
                title_text = "דוח סיכום מערכות"
            else:
                title_text = "Systems Summary Report"
            
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            if summaries:
                # Use the same raw_headers and translated headers from above
                raw_headers = list(summaries[0].keys())
                headers = [headers_translations.get(header, header) for header in raw_headers]
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(summaries[0][key], (int, float)) else "" for key in raw_headers}
                
                for summary in summaries:
                    row_data = []
                    for key in raw_headers:  # Use raw headers for data access
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in raw_headers:  # Use raw headers for data access
                        if isinstance(summary[key], (int, float)):
                            grand_totals[key] += summary[key]
                
                # Add grand totals row
                totals_row = []
                for i, key in enumerate(raw_headers):  # Use raw headers for data access
                    if isinstance(grand_totals[key], (int, float)):
                        if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                            totals_row.append(self._format_currency(grand_totals[key]))
                        else:
                            totals_row.append(str(grand_totals[key]))
                    else:
                        if i == 0:  # Only add grand total text in first column
                            totals_row.append(grand_total_text)
                        else:
                            totals_row.append("")
                data.append(totals_row)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language), 
                     onLaterPages=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language))
            logger.info(f"Generated systems summary PDF with {language} layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating systems summary PDF: {str(e)}")
            raise

    def export_subsections_summary(self, summaries, db_session=None, language="en"):
        """Export subsections summary to PDF with language support"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"subsections_summary_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project information from ProjectInfo table
            project_info = None
            if db_session:
                project_info = db_session.query(models.ProjectInfo).first()
            
            # Get project name for title
            if language == "he":
                project_name = (project_info.project_name_hebrew if project_info and project_info.project_name_hebrew 
                               else project_info.project_name if project_info 
                               else "דוח סיכום תת-פרקים")
            else:
                project_name = (project_info.project_name if project_info and project_info.project_name
                               else "Subsections Summary Report")
            
            # Define translations for headers based on language
            if language == "he":
                # Hebrew translations for subsections summary
                headers_translations = {
                    'subsection': 'תת-פרק',
                    'description': 'תיאור',
                    'total_contract_sum': 'סה"כ חוזה',
                    'total_estimate': 'סה"כ הערכה',
                    'total_submitted': 'סה"כ הוגש',
                    'internal_total': 'סה"כ פנימי',
                    'total_approved': 'סה"כ מאושר',
                    'approved_signed_total': 'סה"כ מאושר חתום',
                    'item_count': 'מספר פריטים'
                }
                grand_total_text = "סה\"כ כללי"
            else:
                # English (default)
                headers_translations = {
                    'subsection': 'Subsection',
                    'description': 'Description',
                    'total_contract_sum': 'Total Contract Sum',
                    'total_estimate': 'Total Estimate',
                    'total_submitted': 'Total Submitted',
                    'internal_total': 'Internal Total',
                    'total_approved': 'Total Approved',
                    'approved_signed_total': 'Approved Signed Total',
                    'item_count': 'Item Count'
                }
                grand_total_text = "GRAND TOTAL"
            
            # Calculate optimal page size and column widths based on content
            if summaries:
                raw_headers = list(summaries[0].keys())
                # Translate headers
                headers = [headers_translations.get(header, header) for header in raw_headers]
                
                # Prepare data for size calculation (headers + sample data + totals row)
                calc_data = [headers]
                for summary in summaries[:10]:  # Use first 10 items for calculation to avoid too large pages
                    row_data = []
                    for key in raw_headers:  # Use raw headers for data access
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    calc_data.append(row_data)
                
                # Add a sample totals row for calculation
                calc_data.append([grand_total_text] + [""] * (len(headers) - 1))
                
                # Calculate optimal page size
                page_size, page_name, column_widths = self._calculate_optimal_page_size(headers, calc_data, font_size=8)
                logger.info(f"Calculated optimal page size: {page_name} for {len(summaries)} subsections")
            else:
                # Default to A4 landscape if no summaries
                page_size = landscape(A4)
                column_widths = None
            
            doc = SimpleDocTemplate(str(filepath), pagesize=page_size)
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
            # Use language-specific title
            if language == "he":
                title_text = "דוח סיכום תת-פרקים"
            else:
                title_text = "Subsections Summary Report"
            
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 12))
            
            # Create table for summary data
            if summaries:
                # Use the same raw_headers and translated headers from above
                raw_headers = list(summaries[0].keys())
                headers = [headers_translations.get(header, header) for header in raw_headers]
                data = [headers]
                
                grand_totals = {key: 0 if isinstance(summaries[0][key], (int, float)) else "" for key in raw_headers}
                
                for summary in summaries:
                    row_data = []
                    for key in raw_headers:  # Use raw headers for data access
                        value = summary[key]
                        if isinstance(value, (int, float)):
                            if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(str(value))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals
                    for key in raw_headers:  # Use raw headers for data access
                        if isinstance(summary[key], (int, float)):
                            grand_totals[key] += summary[key]
                
                # Add grand totals row
                totals_row = []
                for i, key in enumerate(raw_headers):  # Use raw headers for data access
                    if isinstance(grand_totals[key], (int, float)):
                        if 'total' in key.lower() or 'estimate' in key.lower() or 'submitted' in key.lower() or 'approved' in key.lower():
                            totals_row.append(self._format_currency(grand_totals[key]))
                        else:
                            totals_row.append(str(grand_totals[key]))
                    else:
                        if i == 0:  # Only add grand total text in first column
                            totals_row.append(grand_total_text)
                        else:
                            totals_row.append("")
                data.append(totals_row)
                
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.white),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language), 
                     onLaterPages=lambda canvas, doc: self._add_concentration_header_footer(canvas, doc, project_name, language))
            logger.info(f"Generated subsections summary PDF with {language} layout: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating subsections summary PDF: {str(e)}")
            raise

    def export_boq_items(self, items, db_session=None, language="en"):
        """Export BOQ items to PDF with language support"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"boq_items_{timestamp}.pdf"
            filepath = self.exports_dir / filename
            
            # Get project names for header
            project_name, project_name_hebrew = self._get_project_names(db_session, items)
            
            # Define Hebrew translations for BOQ column headers
            if language == "he":
                headers_translations = {
                    'serial_number': 'מספר סידורי',
                    'structure': 'מבנה',
                    'system': 'מערכת',
                    'section_number': 'מספר סעיף',
                    'description': 'תיאור',
                    'unit': 'יחידה',
                    'price': 'מחיר',
                    'original_contract_quantity': 'כמות חוזה מקורית',
                    'total_contract_sum': 'סכום חוזה כולל',
                    'estimated_quantity': 'כמות מוערכת',
                    'quantity_submitted': 'כמות שהוגשה',
                    'internal_quantity': 'כמות פנימית',
                    'approved_by_project_manager': 'אושר על ידי מנהל פרויקט',
                    'approved_signed_quantity': 'כמות אושרה וחתומה',
                    'total_estimate': 'הערכה כוללת',
                    'total_submitted': 'סה"כ הוגש',
                    'internal_total': 'סה"כ פנימי',
                    'total_approved_by_project_manager': 'סה"כ אושר על ידי מנהל פרויקט',
                    'approved_signed_total': 'סה"כ אושר וחתום',
                    'subsection': 'תת סעיף',
                    'notes': 'הערות'
                }
            else:
                headers_translations = {
                    'serial_number': 'Serial Number',
                    'structure': 'Structure',
                    'system': 'System',
                    'section_number': 'Section Number',
                    'description': 'Description',
                    'unit': 'Unit',
                    'price': 'Price',
                    'original_contract_quantity': 'Original Contract Quantity',
                    'total_contract_sum': 'Total Contract Sum',
                    'estimated_quantity': 'Estimated Quantity',
                    'quantity_submitted': 'Quantity Submitted',
                    'internal_quantity': 'Internal Quantity',
                    'approved_by_project_manager': 'Approved by Project Manager',
                    'approved_signed_quantity': 'Approved Signed Quantity',
                    'total_estimate': 'Total Estimate',
                    'total_submitted': 'Total Submitted',
                    'internal_total': 'Internal Total',
                    'total_approved_by_project_manager': 'Total Approved by Project Manager',
                    'approved_signed_total': 'Approved Signed Total',
                    'subsection': 'Subsection',
                    'notes': 'Notes'
                }
            
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
                                row_data.append(self._format_currency(value))
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
                    'price', 'original_contract_quantity', 'total_contract_sum'
                ]
                
                # Add contract update quantity columns in order
                for key in items[0].keys():
                    if key.startswith('updated_contract_quantity_'):
                        all_possible_headers.append(key)
                
                # Add contract update sum columns in order
                for key in items[0].keys():
                    if key.startswith('updated_contract_sum_'):
                        all_possible_headers.append(key)
                
                all_possible_headers.extend([
                    'estimated_quantity', 'quantity_submitted', 'internal_quantity',
                    'approved_by_project_manager', 'approved_signed_quantity', 'total_estimate',
                    'total_submitted', 'internal_total', 'total_approved_by_project_manager',
                    'approved_signed_total', 'subsection', 'notes'
                ])
                
                # Only include headers that exist in the data
                raw_headers = [h for h in all_possible_headers if h in items[0].keys()]
                # Translate headers based on language
                headers = [headers_translations.get(header, header) for header in raw_headers]
                data = [headers]
                
                # Define columns that should have grand totals (same as Excel export)
                total_columns = {
                    'total_contract_sum',
                    'total_estimate',
                    'total_submitted',
                    'internal_total',
                    'total_approved_by_project_manager',
                    'approved_signed_total'
                }
                # Add updated contract sum columns
                for key in raw_headers:
                    if key.startswith('updated_contract_sum_'):
                        total_columns.add(key)
                
                grand_totals = {key: 0 if isinstance(items[0][key], (int, float)) else "" for key in raw_headers}
                
                # First pass: collect all data and calculate totals
                for item in items:
                    row_data = []
                    for key in raw_headers:
                        value = item[key]
                        if isinstance(value, (int, float)):
                            # Only apply ₪ formatting to price and sum/total columns, not quantity columns
                            if ('total' in key.lower() or 'sum' in key.lower() or 'price' in key.lower()) and 'quantity' not in key.lower():
                                row_data.append(self._format_currency(value))
                            else:
                                row_data.append(f"{value:,.2f}" if value != int(value) else str(int(value)))
                        else:
                            row_data.append(str(value))
                    data.append(row_data)
                    
                    # Calculate grand totals only for specified columns
                    for key in raw_headers:
                        if key in total_columns and isinstance(item[key], (int, float)):
                            grand_totals[key] += item[key]
                
                # Add grand totals row
                totals_row = []
                for i, key in enumerate(raw_headers):
                    if i == 0:
                        # First column shows "GRAND TOTAL"
                        if language == "he":
                            totals_row.append("סה\"כ כולל")
                        else:
                            totals_row.append("GRAND TOTAL")
                    elif key in total_columns and isinstance(grand_totals[key], (int, float)):
                        # Only show totals for specified columns
                        totals_row.append(self._format_currency(grand_totals[key]))
                    else:
                        # Empty values for all other columns
                        totals_row.append("")
                data.append(totals_row)
                
                # Use pre-calculated column widths from page size calculation
                if column_widths is None:
                    # Fallback to old method if column_widths not calculated
                    column_widths = self._calculate_column_widths(data, headers, 'A3', 8, 8)
                
                # Try to use robust Hebrew table method first, fallback to regular table if it fails
                try:
                    table = self._create_robust_hebrew_table(data, headers, column_widths, repeat_rows=1)
                    logger.info("Successfully created robust Hebrew table for BOQ items with repeatRows")
                except Exception as e:
                    logger.warning(f"Failed to create robust Hebrew table, falling back to regular table: {e}")
                    # Use Hebrew-aware table style that applies Hebrew fonts to Hebrew text
                    table_style, processed_data = self._create_hebrew_aware_table_style(data, headers, column_widths)
                    # Create table with processed data (Hebrew text reversed) and repeatRows
                    table = Table(processed_data, colWidths=column_widths, repeatRows=1)
                    table.setStyle(TableStyle(table_style))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_boq_header_footer(canvas, doc, project_name, project_name_hebrew), 
                     onLaterPages=lambda canvas, doc: self._add_boq_header_footer(canvas, doc, project_name, project_name_hebrew))
            logger.info(f"Generated BOQ items PDF: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error generating BOQ items PDF: {str(e)}")
            raise

    def _calculate_column_widths(self, data, headers, page_size_or_width='A3', header_font_size=8, data_font_size=8):
        """Calculate optimal column widths based on actual content length"""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        # Handle both page size strings and direct width values
        if isinstance(page_size_or_width, (int, float)):
            # Direct width value provided
            page_width = page_size_or_width
        else:
            # Get page width based on page size (landscape orientation)
            if page_size_or_width == 'A3':
                page_width = 842  # A3 landscape width in points
            else:  # A4
                page_width = 595  # A4 landscape width in points
        
        # Use 0.75 inch margin on each side (54 points each) for better readability
        margin = 54 * 2  # 1.5 inches total margin
        available_width = page_width - margin
        
        # Font settings for width calculation
        header_font = 'Helvetica-Bold'
        data_font = 'Helvetica'
        hebrew_font = self.hebrew_font
        
        # Calculate maximum width needed for each column based on actual content
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
                    # Use appropriate font for width calculation
                    if self._detect_rtl(cell_value) or self._is_currency_value(cell_value):
                        cell_width = stringWidth(cell_value, hebrew_font, data_font_size)
                        # Add extra padding for Hebrew text as it often needs more space
                        cell_width = cell_width * 1.3
                    else:
                        cell_width = stringWidth(cell_value, data_font, data_font_size)
                    max_width = max(max_width, cell_width)
            
            # Special handling for description columns
            is_description_column = header.lower() == 'description'
            
            # Check if this column contains Hebrew text
            contains_hebrew = any(
                self._detect_rtl(str(row[col_idx])) if col_idx < len(row) and row[col_idx] is not None else False
                for row in data
            )
            
            if is_description_column:
                # For description columns, give more generous width and padding
                max_width = max_width * 1.5  # More padding for descriptions
                min_width = 150  # Higher minimum width for descriptions
                if contains_hebrew:
                    max_width = max_width * 1.2  # Extra space for Hebrew descriptions
                    min_width = 180  # Higher minimum for Hebrew descriptions
            else:
                # Add padding (20% extra for better readability and cell spacing)
                max_width = max_width * 1.2
                min_width = 60
                if contains_hebrew:
                    max_width = max_width * 1.1  # Extra space for Hebrew text
                    min_width = 80  # Higher minimum for Hebrew text
            
            max_width = max(min_width, max_width)
            column_max_widths.append(max_width)
        
        # Calculate total width needed
        total_width = sum(column_max_widths)
        
        # If total width exceeds available width, scale down proportionally
        if total_width > available_width:
            scale_factor = available_width / total_width
            column_max_widths = [width * scale_factor for width in column_max_widths]
            
            # Ensure minimum width after scaling
            min_final_width = 40
            column_max_widths = [max(min_final_width, width) for width in column_max_widths]
        
        # Log the calculated widths for debugging
        logger.info(f"Column widths calculated: {[f'{w:.1f}' for w in column_max_widths]}")
        logger.info(f"Total width: {sum(column_max_widths):.1f}, Available width: {available_width:.1f}")
        
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
            
            # Special handling for description columns
            is_description_column = header.lower() == 'description'
            
            if is_description_column:
                # For description columns, give more generous width and padding
                max_width = max_width * 1.5  # More padding for descriptions
                min_width = 200  # Higher minimum width for descriptions in optimal page size
            else:
                # Add padding (30% extra for better readability and cell spacing)
                max_width = max_width * 1.3
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
