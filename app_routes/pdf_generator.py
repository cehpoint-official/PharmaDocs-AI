"""
PDF Generator for Process Validation Reports
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import os

class PVRPDFGenerator:
    def __init__(self, data):
        self.data = data
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e3c72'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2a5298'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Subsection heading
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1e3c72'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='PVRBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))
    
    def generate(self, filename):
        """Generate the complete PDF report"""
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        
        # Build document sections
        story.extend(self.create_cover_page())
        story.append(PageBreak())
        
        story.extend(self.create_table_of_contents())
        story.append(PageBreak())
        
        story.extend(self.create_objective_section())
        story.append(PageBreak())
        
        story.extend(self.create_product_details())
        story.append(PageBreak())
        
        story.extend(self.create_equipment_list())
        story.append(PageBreak())
        
        story.extend(self.create_batch_results())
        story.append(PageBreak())
        
        story.extend(self.create_quality_control_results())
        story.append(PageBreak())
        
        story.extend(self.create_conclusion())
        
        # Build PDF
        doc.build(story, onFirstPage=self.add_header_footer, onLaterPages=self.add_header_footer)
        
        return filename
    
    def add_header_footer(self, canvas, doc):
        """Add header and footer to each page"""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(0.5*inch, A4[1] - 0.3*inch, self.data.get('companyName', 'Company Name'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(0.5*inch, A4[1] - 0.45*inch, self.data.get('companyAddress', '')[:80])
        
        # Draw line
        canvas.setStrokeColor(colors.HexColor('#2a5298'))
        canvas.setLineWidth(1)
        canvas.line(0.5*inch, A4[1] - 0.5*inch, A4[0] - 0.5*inch, A4[1] - 0.5*inch)
        
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.drawString(0.5*inch, 0.3*inch, f"Report No: {self.data.get('reportNo', 'N/A')}")
        canvas.drawRightString(A4[0] - 0.5*inch, 0.3*inch, f"Page {doc.page}")
        
        canvas.restoreState()
    
    def create_cover_page(self):
        """Create cover page"""
        story = []
        
        # Company name
        story.append(Spacer(1, 1*inch))
        story.append(Paragraph(
            self.data.get('companyName', 'COMPANY NAME').upper(),
            self.styles['CustomTitle']
        ))
        
        # Address
        story.append(Paragraph(
            self.data.get('companyAddress', ''),
            ParagraphStyle('CenterSmall', parent=self.styles['Normal'], alignment=TA_CENTER, fontSize=9)
        ))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Document title
        story.append(Paragraph(
            "PROCESS VALIDATION REPORT",
            self.styles['CustomTitle']
        ))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Product details
        story.append(Paragraph(
            f"<b>Product Name:</b><br/>{self.data.get('productName', 'N/A')}",
            ParagraphStyle('CenterBold', parent=self.styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=10)
        ))
        
        story.append(Paragraph(
            f"<b>Strength:</b> {self.data.get('strength', 'N/A')}",
            ParagraphStyle('Center', parent=self.styles['Normal'], alignment=TA_CENTER, fontSize=11)
        ))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Report details
        story.append(Paragraph(
            f"<b>Report No:</b> {self.data.get('reportNo', 'N/A')}",
            ParagraphStyle('Center', parent=self.styles['Normal'], alignment=TA_CENTER, fontSize=11, spaceAfter=8)
        ))
        
        story.append(Paragraph(
            f"<b>Batch Size:</b> {self.data.get('batchSize', 'N/A')}",
            ParagraphStyle('Center', parent=self.styles['Normal'], alignment=TA_CENTER, fontSize=11)
        ))
        
        return story
    
    def create_table_of_contents(self):
        """Create table of contents"""
        story = []
        
        story.append(Paragraph("TABLE OF CONTENTS", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        toc_data = [
            ['Sr. No', 'Content', 'Page No.'],
            ['1', 'Objective', '3'],
            ['2', 'Scope', '3'],
            ['3', 'Responsibility', '3'],
            ['4', 'Product & Batch Details', '4'],
            ['5', 'Equipment & Machinery List', '5'],
            ['6', 'Observations/Results', '7'],
            ['7', 'Quality Control Results', '15'],
            ['8', 'Conclusion', '16'],
            ['9', 'Summary', '16'],
        ]
        
        table = Table(toc_data, colWidths=[1*inch, 4*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        story.append(table)
        
        return story
    
    def create_objective_section(self):
        """Create objective, scope and responsibility sections"""
        story = []
        
        # Objective
        story.append(Paragraph("1. OBJECTIVE", self.styles['SectionHeading']))
        story.append(Paragraph(
            f"The purpose of this report is to provide the documented evidence for the batch manufacturing "
            f"process of {self.data.get('productName', 'the product')} that was manufactured at the facility. "
            f"This validation summary report provides an overview of the entire validation process and documents "
            f"the process results and process parameters obtained during the manufacturing of three batches.",
            self.styles['PVRBodyText']
        ))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Scope
        story.append(Paragraph("2. SCOPE", self.styles['SectionHeading']))
        story.append(Paragraph(
            f"This report is applicable for three consecutive batches manufactured with specific batch size "
            f"({self.data.get('batchSize', 'N/A')}) and equipment for {self.data.get('productName', 'the product')}.",
            self.styles['PVRBodyText']
        ))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Responsibility
        story.append(Paragraph("3. RESPONSIBILITY", self.styles['SectionHeading']))
        story.append(Paragraph(
            "<b>3.1 QA Personnel:</b> Responsible for preparation and approval of process validation summary "
            "report and review of data compiled.",
            self.styles['PVRBodyText']
        ))
        story.append(Paragraph(
            "<b>3.2 Production Personnel:</b> Responsible for review of process validation summary report.",
            self.styles['PVRBodyText']
        ))
        story.append(Paragraph(
            "<b>3.3 Quality Control Personnel:</b> Responsible for review of process validation summary report "
            "and compiled data.",
            self.styles['PVRBodyText']
        ))
        
        return story
    
    def create_product_details(self):
        """Create product and batch details section"""
        story = []
        
        story.append(Paragraph("4. PRODUCT & BATCH DETAILS", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        # Product info table
        product_data = [
            ['Product/Generic Name', self.data.get('productName', 'N/A')],
            ['Strength', self.data.get('strength', 'N/A')],
            ['Report Number', self.data.get('reportNo', 'N/A')],
            ['Batch Size', self.data.get('batchSize', 'N/A')],
            ['Dosage Form', self.data.get('template', {}).get('dosage_form', 'Liquid Injection')],
            ['Storage Conditions', self.data.get('storageConditions', 'As per specification')],
        ]
        
        table = Table(product_data, colWidths=[2.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Batch details
        story.append(Paragraph("Batch Details for Validation:", self.styles['SubsectionHeading']))
        
        batch_data = [
            ['Sr. No', 'Batch No', 'Batch Size', 'Mfg. Date', 'Exp. Date']
        ]
        
        for i, batch_key in enumerate(['batch1', 'batch2', 'batch3'], 1):
            batch = self.data.get(batch_key, {})
            batch_data.append([
                str(i),
                batch.get('no', 'N/A'),
                self.data.get('batchSize', 'N/A'),
                batch.get('mfg', 'N/A'),
                batch.get('exp', 'N/A')
            ])
        
        table = Table(batch_data, colWidths=[0.8*inch, 1.5*inch, 1.8*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        story.append(table)
        
        return story
    
    def create_equipment_list(self):
        """Create equipment list section"""
        story = []
        
        story.append(Paragraph("5. EQUIPMENT & MACHINERY LIST", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        template = self.data.get('template', {})
        equipment = template.get('equipment', [])
        
        if equipment:
            # Split into chunks for multiple pages if needed
            chunk_size = 25
            for i in range(0, len(equipment), chunk_size):
                equipment_chunk = equipment[i:i+chunk_size]
                
                equip_data = [['Sr. No', 'Equipment Name', 'Make', 'Equipment ID']]
                
                for eq in equipment_chunk:
                    equip_data.append([
                        str(eq.get('sr', '')),
                        eq.get('name', ''),
                        eq.get('make', ''),
                        eq.get('id', '')
                    ])
                
                table = Table(equip_data, colWidths=[0.7*inch, 2.5*inch, 1.8*inch, 1.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                story.append(table)
                
                if i + chunk_size < len(equipment):
                    story.append(PageBreak())
        
        return story
    
    def create_batch_results(self):
        """Create observations/results section"""
        story = []
        
        story.append(Paragraph("6. OBSERVATIONS/RESULTS", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        # Manufacturing - During Mixing
        story.append(Paragraph("6.1 Stage: Manufacturing - During Mixing", self.styles['SubsectionHeading']))
        
        for batch_key in ['batch1', 'batch2', 'batch3']:
            batch = self.data.get(batch_key, {})
            batch_no = batch.get('no', 'N/A')
            
            story.append(Paragraph(f"<b>Batch No: {batch_no}</b>", self.styles['PVRBodyText']))
            
            mixing_data = [
                ['Time Point', 'pH', 'Assay (%)', 'Description']
            ]
            
            mixing = batch.get('mixing', {})
            for time_key, time_label in [('min_10', '10 minutes'), ('min_15', '15 minutes'), ('min_20', '20 minutes')]:
                time_data = mixing.get(time_key, {})
                mixing_data.append([
                    time_label,
                    time_data.get('ph', '-'),
                    time_data.get('assay', '-'),
                    time_data.get('desc', '-')
                ])
            
            table = Table(mixing_data, colWidths=[1.3*inch, 1*inch, 1.2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.15*inch))
        
        story.append(PageBreak())
        
        # Filling & Sealing
        story.append(Paragraph("6.2 Stage: Filling & Sealing", self.styles['SubsectionHeading']))
        
        for batch_key in ['batch1', 'batch2', 'batch3']:
            batch = self.data.get(batch_key, {})
            batch_no = batch.get('no', 'N/A')
            
            story.append(Paragraph(f"<b>Batch No: {batch_no}</b>", self.styles['PVRBodyText']))
            
            filling_data = [
                ['Stage', 'pH', 'Assay (%)', 'Leak Test']
            ]
            
            filling = batch.get('filling', {})
            for stage_key, stage_label in [('initial', 'Initial'), ('middle', 'Middle'), ('end', 'End')]:
                stage_data = filling.get(stage_key, {})
                filling_data.append([
                    stage_label,
                    stage_data.get('ph', '-'),
                    stage_data.get('assay', '-'),
                    stage_data.get('leak', '-')
                ])
            
            table = Table(filling_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.15*inch))
        
        return story
    
    def create_quality_control_results(self):
        """Create quality control results section"""
        story = []
        
        story.append(Paragraph("7. QUALITY CONTROL RESULTS OF FINISHED PRODUCT", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        # Final product analysis table
        qc_data = [
            ['Quality Attribute', 'Specification', 'Batch 1', 'Batch 2', 'Batch 3']
        ]
        
        batch1 = self.data.get('batch1', {}).get('final', {})
        batch2 = self.data.get('batch2', {}).get('final', {})
        batch3 = self.data.get('batch3', {}).get('final', {})
        
        qc_data.extend([
            ['pH', '8.5 to 9.1', batch1.get('ph', '-'), batch2.get('ph', '-'), batch3.get('ph', '-')],
            ['Extractable Volume (ml)', 'NLT 20 ml', batch1.get('volume', '-'), batch2.get('volume', '-'), batch3.get('volume', '-')],
            ['Assay (mg)', '900-1100 mg\n(90-110%)', batch1.get('assay', '-'), batch2.get('assay', '-'), batch3.get('assay', '-')],
            ['Particulate Matter\n10-25 μm', 'NMT 6000', batch1.get('pm_small', '-'), batch2.get('pm_small', '-'), batch3.get('pm_small', '-')],
            ['Particulate Matter\n≥25 μm', 'NMT 600', batch1.get('pm_large', '-'), batch2.get('pm_large', '-'), batch3.get('pm_large', '-')],
        ])
        
        table = Table(qc_data, colWidths=[2*inch, 1.8*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        
        return story
    
    def create_conclusion(self):
        """Create conclusion and summary section"""
        story = []
        
        story.append(Paragraph("8. CONCLUSION", self.styles['SectionHeading']))
        story.append(Paragraph(
            f"Based on the compilation of all three batches data, it is concluded that {self.data.get('productName', 'the product')} "
            f"was challenged against various parameters at different time intervals and the results found were within the "
            f"acceptance criteria. All quality control attributes meet their predetermined specifications.",
            self.styles['PVRBodyText']
        ))
        
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("9. SUMMARY", self.styles['SectionHeading']))
        story.append(Paragraph(
            f"From the observed data of process validation of {self.data.get('productName', 'the product')}, it has been found that "
            f"the process consistently produces a product meeting predetermined specifications and quality characteristics. "
            f"The process is validated and can be used for commercial batch production.",
            self.styles['PVRBodyText']
        ))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Approval section
        story.append(Paragraph("APPROVAL SIGNATURES", self.styles['SubsectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        approval_data = [
            ['Prepared By:', '', 'Date:'],
            ['Name:', '', ''],
            ['', '', ''],
            ['Reviewed By:', '', 'Date:'],
            ['Name:', '', ''],
            ['', '', ''],
            ['Approved By:', '', 'Date:'],
            ['Name:', '', ''],
            ['', '', ''],
        ]
        
        table = Table(approval_data, colWidths=[2*inch, 3*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(table)
        
        return story


def generate_pvr_pdf(data, output_folder='uploads/pvr_reports'):
    """
    Generate PVR PDF from data
    
    Args:
        data: Dictionary containing all PVR data
        output_folder: Folder to save PDF
    
    Returns:
        Path to generated PDF file
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        product_name = data.get('productName', 'Product').replace(' ', '_')
        filename = f"PVR_{product_name}_{timestamp}.pdf"
        filepath = os.path.join(output_folder, filename)
        
        # Generate PDF
        generator = PVRPDFGenerator(data)
        generator.generate(filepath)
        
        return filepath
        
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")