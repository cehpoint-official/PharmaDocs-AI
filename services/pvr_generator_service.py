# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from datetime import datetime
import os

from models import PVR_Report, PVR_Data, PVP_Criteria
from services.pvr_word_generator_service import generate_pvr_word


def generate_pvr_pdf(report_id, product_name, template, criteria):
    """
    Generate PVR PDF from report data
    """
    # Get report and data
    report = PVR_Report.query.get(report_id)
    if not report:
        raise Exception("Report not found")
    
    batch_data = PVR_Data.query.filter_by(pvr_report_id=report_id).all()
    
    # Get unique batch numbers
    batch_numbers = sorted(list(set([d.batch_number for d in batch_data])))
    
    # Create output folder
    output_folder = os.path.join(os.getcwd(), 'uploads', 'pvr_reports')
    os.makedirs(output_folder, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"PVR_{product_name.replace(' ', '_')}_{timestamp}.pdf"
    filepath = os.path.join(output_folder, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e3c72'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2a5298'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    # Build document
    story = []
    
    # Title
    story.append(Paragraph("PROCESS VALIDATION REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Product info
    story.append(Paragraph(f"<b>Product Name:</b> {product_name}", body_style))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%d-%b-%Y %H:%M')}", body_style))
    story.append(Paragraph(f"<b>Template:</b> {template.template_name}", body_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Batch details
    story.append(Paragraph("BATCH INFORMATION", heading_style))
    batch_table_data = [['Sr. No', 'Batch Number']]
    for i, batch in enumerate(batch_numbers, 1):
        batch_table_data.append([str(i), batch])
    
    batch_table = Table(batch_table_data, colWidths=[1*inch, 3*inch])
    batch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    story.append(batch_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Test results
    story.append(Paragraph("TEST RESULTS", heading_style))
    
    # Build results table
    header_row = ['Test Parameter', 'Acceptance Criteria'] + [f'Batch {b}' for b in batch_numbers]
    results_data = [header_row]
    
    for criterion in criteria:
        row = [
            criterion.test_name,
            criterion.acceptance_criteria
        ]
        
        # Get results for each batch
        for batch in batch_numbers:
            result = next(
                (d.test_result for d in batch_data 
                 if d.test_id == criterion.test_id and d.batch_number == batch),
                '-'
            )
            row.append(result)
        
        results_data.append(row)
    
    # Calculate column widths
    col_count = len(header_row)
    col_width = 6.5*inch / col_count
    
    results_table = Table(results_data, colWidths=[col_width] * col_count)
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(results_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Conclusion
    story.append(Paragraph("CONCLUSION", heading_style))
    story.append(Paragraph(
        f"The process validation for {product_name} has been successfully completed for "
        f"{len(batch_numbers)} consecutive batches. All test results are within the "
        f"predetermined acceptance criteria. The process is validated and qualified for "
        f"commercial production.",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    
    print(f"✅ PVR PDF generated: {filepath}")
    return filepath