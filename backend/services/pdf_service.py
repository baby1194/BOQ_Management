from reportlab.lib.pagesizes import A3, letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from pathlib import Path
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        self.exports_dir = Path("exports")
        self.exports_dir.mkdir(exist_ok=True)
    
    def _detect_rtl(self, text):
        """Detect if text contains RTL characters (Hebrew, Arabic, etc.)"""
        if not text:
            return False
        # Check for Hebrew, Arabic, and other RTL characters
        rtl_pattern = re.compile(r'[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]')
        return bool(rtl_pattern.search(text))
    
    def _get_project_name(self, db_session=None, sheet_data=None):
        """Get project name from various sources"""
        project_name = ""
        
        # Try to get from sheet data first (for concentration sheets)
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
        
        # If not found in data, try database
        if not project_name and db_session:
            try:
                from models import models
                project_info = db_session.query(models.ProjectInfo).first()
                if project_info and project_info.project_name:
                    project_name = project_info.project_name
            except Exception as e:
                logger.warning(f"Could not fetch project info from database: {e}")
        
        return project_name or "Project Name"
    
    def _add_header_footer(self, canvas, doc, project_name):
        """Add header and footer to PDF pages"""
        canvas.saveState()
        
        # Detect RTL
        is_rtl = self._detect_rtl(project_name)
        
        # Project name in header
        if project_name:
            if is_rtl:
                # RTL: top-right
                canvas.setFont("Helvetica-Bold", 10)
                canvas.drawRightString(doc.pagesize[0] - 0.5*inch, doc.pagesize[1] - 0.5*inch, project_name)
            else:
                # LTR: top-left
                canvas.setFont("Helvetica-Bold", 10)
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
            
            # Get project name for header
            project_name = self._get_project_name(db_session, items)
            
            doc = SimpleDocTemplate(str(filepath), pagesize=landscape(A3))
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
            story.append(Paragraph("BOQ Items Report", title_style))
            story.append(Spacer(1, 12))
            
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
                
                # Calculate optimal column widths based on content
                column_widths = self._calculate_column_widths(data, headers, 'A3', 8, 8)
                
                # Create table with calculated column widths
                table = Table(data, colWidths=column_widths)
                table.setStyle(TableStyle([
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
                ]))
                
                story.append(table)
            
            doc.build(story, onFirstPage=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name), 
                     onLaterPages=lambda canvas, doc: self._add_header_footer(canvas, doc, project_name))
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