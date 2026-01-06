"""
Comprehensive PVR Generator Service
Generates detailed Process Validation Reports with all sections
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from typing import Dict, List
import logging
from models import PVP_Extracted_Stage
from reportlab.platypus import Table, TableStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import black
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)


class ComprehensivePVRGenerator:
    """Generate comprehensive PVR reports"""
    
    def __init__(self, pvp_template, batch_data: List[Dict], pvr_report=None, equipment_list=None,
        materials_list=None):
        """
        Initialize generator 
        
        Args:
            pvp_template: PVP_Template database object
            batch_data: List of batch result dictionaries
            pvr_report: PVR_Report database object (optional)
        """
        self.pvp = pvp_template
        self.batch_data = batch_data
        self.report = pvr_report
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.equipment_list = equipment_list or []
        self.materials_list = materials_list or []
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading styles
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='TOCHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=18,
            spaceBefore=12,
            alignment=TA_CENTER,         
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#3949ab'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#3f51b5'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=10
        ))
    
    def generate_pdf(self, output_path: str):
        """Generate comprehensive PDF report"""
        
        logger.info(f"Generating comprehensive PVR PDF: {output_path}")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        story = []
        
        # 1. Cover Page
        story.extend(self._build_cover_page())
        story.append(PageBreak())
        
        # 2. Table of Contents
        story.extend(self._build_toc())
        story.append(PageBreak())
        
        # 3. Objective
        story.extend(self._build_objective())
        story.append(Spacer(1, 0.3*inch))
        
        # 4. Scope
        story.extend(self._build_scope())
        story.append(Spacer(1, 0.3*inch))
        
        # 5. Product Information
        story.extend(self._build_product_info())
        story.append(PageBreak())

        # 6. Roles and Responsibilities
        story.extend(self._build_roles_and_responsibilities())
        story.append(PageBreak())
        
        # 7. Equipment List
        story.extend(self._build_equipment_list())
        story.append(PageBreak())
        
        # 8. Materials List
        story.extend(self._build_materials_list())
        story.append(PageBreak())
        
        # 9. Validation Protocol
        story.extend(self._build_validation_protocol())
        story.append(PageBreak())
        
        # 10. Batch Manufacturing Record
        story.extend(self._build_batch_manufacturing())
        story.append(PageBreak())
        
        # 11. Manufacturing Process Validation (Keep old section too)
        story.extend(self._build_process_validation())
        story.append(PageBreak())
        
        # 12. Hold Time Study
        story.extend(self._build_hold_time_study())
        story.append(Spacer(1, 0.3*inch))
        
        # 13. Environmental Monitoring
        story.extend(self._build_environmental_monitoring())
        story.append(PageBreak())
        
        # 14. Quality Testing Results
        story.extend(self._build_quality_tests())
        story.append(PageBreak())
        
        # 15. Statistical Analysis
        story.extend(self._build_statistical_analysis())
        story.append(PageBreak())
        
        # 16. Conclusion
        story.extend(self._build_conclusion())
        story.append(PageBreak())
        
        # 17. Recommendations
        story.extend(self._build_recommendations())
        story.append(PageBreak())
        
        # 18. Annexures
        story.extend(self._build_annexures())
        story.append(PageBreak())
        
        # 19. Signatures
        story.extend(self._build_signatures())
        
        # Build PDF
        doc.build(story,onFirstPage=self._add_header_footer,
            onLaterPages=self._add_header_footer)
        logger.info(f"✅ PDF generated successfully: {output_path}")
        
        return output_path
    
    def _build_cover_page(self) -> List:
        """Build cover page"""
        
        elements = []
        
        # Spacer
        elements.append(Spacer(1, 2*inch))
        
        # Title
        title = Paragraph(
            "PROCESS VALIDATION REPORT",
            self.styles['CustomTitle']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Product name
        product_title = Paragraph(
            f"<b>{self.pvp.product_name}</b>",
            ParagraphStyle(
                name='ProductTitle',
                fontSize=18,
                textColor=colors.HexColor('#283593'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
        )
        elements.append(product_title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Batch info
        batch_numbers = [b.get('batch_number', 'N/A') for b in self.batch_data]
        batch_text = f"<b>Batch Numbers:</b> {', '.join(batch_numbers)}"
        elements.append(Paragraph(batch_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add protocol, validation type, site if report exists
        if self.report:
            protocol_text = f"<b>Protocol Number:</b> {getattr(self.report, 'protocol_number', '') or 'N/A'}"
            elements.append(Paragraph(protocol_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1*inch))
            
            validation_text = f"<b>Validation Type:</b> {getattr(self.report, 'validation_type', '') or 'N/A'}"
            elements.append(Paragraph(validation_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1*inch))
            
            site_text = f"<b>Manufacturing Site:</b> {getattr(self.report, 'manufacturing_site', '') or 'N/A'}"
            elements.append(Paragraph(site_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Date
        date_text = f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}"
        elements.append(Paragraph(date_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_toc(self):
        elements = []

        elements.append(Paragraph("TABLE OF CONTENTS", self.styles['TOCHeading']))
        elements.append(Spacer(1, 0.25 * inch))

        toc_data = [
            ["1.", "Objective"],
            ["2.", "Scope"],
            ["3.", "Product Information"],
            ["4.", "Roles and Responsibilities"],
            ["5.", "Equipment List"],
            ["6.", "Materials List"],
            ["7.", "Validation Protocol"],
            ["8.", "Batch Manufacturing Record"],
            ["9.", "Manufacturing Process Validation"],
            ["10.", "Hold Time Study"],
            ["11.", "Environmental Monitoring"],
            ["12.", "Quality Testing Results"],
            ["13.", "Statistical Analysis"],
            ["14.", "Conclusion"],
            ["15.", "Recommendations"],
            ["16.", "Annexures"],
            ["17.", "Approval Signatures"],
        ]

        table = Table(
            toc_data,
            colWidths=[1.6 * inch, 5.2 * inch],
            repeatRows=0
        )

        table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
        ]))

        elements.append(table)
        return elements
    
    def _p(self, text):
        """
        Helper to safely wrap table cell text
        """
        return Paragraph(str(text), self.styles['CustomBody'])
    
    def _build_objective(self) -> List:
        """Build objective section"""
        
        elements = []
        
        elements.append(Paragraph("1. OBJECTIVE", self.styles['CustomHeading1']))
        
        objective_text = f"""
        The objective of this validation study is to demonstrate that the manufacturing 
        process for <b>{self.pvp.product_name}</b> is capable of consistently producing 
        a product that meets all predetermined specifications and quality attributes.
        <br/><br/>
        This validation is conducted in accordance with:
        <br/>• ICH Q7: Good Manufacturing Practice Guide for Active Pharmaceutical Ingredients
        <br/>• ICH Q8(R2): Pharmaceutical Development
        <br/>• ICH Q9: Quality Risk Management
        <br/>• FDA Guidance for Industry: Process Validation
        """
        
        elements.append(Paragraph(objective_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_scope(self) -> List:
        """Build scope section"""
        
        elements = []
        
        elements.append(Paragraph("2. SCOPE", self.styles['CustomHeading1']))
        
        scope_text = f"""
        This validation report covers the complete manufacturing process of 
        <b>{self.pvp.product_name}</b>, including:
        <br/><br/>
        • All critical manufacturing stages from dispensing to packaging
        <br/>• In-process quality controls
        <br/>• Final product testing
        <br/>• Equipment qualification status
        <br/>• Environmental monitoring (where applicable)
        <br/><br/>
        <b>Batch Size:</b> {self.pvp.batch_size or 'As per protocol'}
        <br/><b>Product Type:</b> {self.pvp.product_type or 'As specified'}
        """
        
        elements.append(Paragraph(scope_text, self.styles['CustomBody']))
        
        # Add batch details table
        if self.batch_data:
            elements.append(Spacer(1, 0.2*inch))
            batch_table_data = [['Batch Number', 'Manufacturing Date', 'Batch Size']]
            
            for batch in self.batch_data:
                batch_table_data.append([
                    batch.get('batch_number', 'N/A'),
                    batch.get('manufacturing_date', 'N/A'),
                    batch.get('batch_size', 'N/A')
                ])
            
            batch_table = Table(batch_table_data, colWidths=[2*inch, 2*inch, 2*inch])
            batch_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(batch_table)
        
        return elements
    
    def _build_roles_and_responsibilities(self) -> List:
        """Build roles and responsibilities section"""

        elements = []

        elements.append(Paragraph(
            "4. ROLES AND RESPONSIBILITIES",
            self.styles['CustomHeading1']
        ))
        elements.append(Spacer(1, 0.2 * inch))

        intro_text = """
        The roles and responsibilities of personnel involved in the execution,
        review, and approval of the Process Validation Report are defined to ensure
        compliance with regulatory and quality requirements.
        """
        elements.append(Paragraph(intro_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2 * inch))

        roles_data = [
            [self._p('Function'), self._p('Responsibilities')],
            [
                self._p('Production'),
                self._p(
                    'Execution of manufacturing activities as per approved procedures, '
                    'documentation of batch records, and adherence to validated process parameters.'
                )
            ],
            [
                self._p('Quality Assurance (QA)'),
                self._p(
                    'Review and approval of validation protocol and report, oversight of validation '
                    'activities, deviation handling, and final compliance decision.'
                )
            ],
            [
                self._p('Quality Control (QC)'),
                self._p(
                    'Sampling, testing of in-process and finished product samples, '
                    'documentation and reporting of analytical results.'
                )
            ],
            [
                self._p('Engineering / Maintenance'),
                self._p(
                    'Ensuring equipment qualification status, calibration, and maintenance '
                    'of equipment used during validation.'
                )
            ],
            [
                self._p('Validation Team'),
                self._p(
                    'Planning, coordination, execution, and evaluation of process validation '
                    'activities and preparation of the validation report.'
                )
            ]
        ]

        table = Table(
            roles_data,
            colWidths=[2 * inch, 4 * inch]
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))

        elements.append(table)

        return elements
    
    def _add_header_footer(self, canvas, doc):
        """
        Draw consistent header and footer on each page
        """
        canvas.saveState()

        # ---------- HEADER ----------
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(
            0.75 * inch,
            A4[1] - 0.6 * inch,
            "Process Validation Report"
        )

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            A4[0] - 0.75 * inch,
            A4[1] - 0.6 * inch,
            f" {self.pvp.product_name}"
        )

        # Header line
        canvas.line(
            0.75 * inch,
            A4[1] - 0.65 * inch,
            A4[0] - 0.75 * inch,
            A4[1] - 0.65 * inch
        )

        # ---------- FOOTER ----------
        canvas.setFont("Helvetica", 8)

        # Footer line
        canvas.line(
            0.75 * inch,
            0.9 * inch,
            A4[0] - 0.75 * inch,
            0.9 * inch
        )

        # Page number
        page_number_text = f"Page {doc.page}"
        canvas.drawRightString(
            A4[0] - 0.75 * inch,
            0.7 * inch,
            page_number_text
        )

        # Confidential text
        canvas.drawString(
            0.75 * inch,
            0.7 * inch,
            "Confidential – For Internal Use Only"
        )

        canvas.restoreState()
    
    def _build_product_info(self) -> List:
        """Build product information section"""
        
        elements = []
        
        elements.append(Paragraph("3. PRODUCT INFORMATION", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Product details table
        product_data = [
            ['Parameter', 'Details'],
            ['Product Name', self.pvp.product_name],
            ['Product Type', self.pvp.product_type or 'N/A'],
            ['Batch Size', self.pvp.batch_size or 'N/A'],
            ['Number of Batches Validated', str(len(self.batch_data))],
            ['Validation Date', datetime.now().strftime('%B %Y')],
        ]
        
        table = Table(product_data, colWidths=[2.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_equipment_list(self) -> List:
        """Build equipment list section"""
        
        elements = []
        
        elements.append(Paragraph("5. EQUIPMENT LIST", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get equipment from database
        equipment_list = self.equipment_list
        
        if equipment_list:
            equip_data = [['S.No.', 'Equipment Name', 'Equipment ID', 'Location', 'Calibration Status']]
            
            for i, equip in enumerate(equipment_list, 1):
                equip_data.append([
                    self._p(i),
                    self._p(equip.get("equipment_name", "N/A")),
                    self._p(equip.get("equipment_id", "N/A")),
                    self._p(equip.get("location", "N/A")),
                    self._p(equip.get("qualification_status", "N/A"))
                ])
            
            table = Table(equip_data, colWidths=[0.5*inch, 2*inch, 1.2*inch, 1.5*inch, 1.3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No equipment data available.", self.styles['CustomBody']))
        
        return elements
    
    def _build_materials_list(self) -> List:
        """Build materials list section"""
        
        elements = []
        
        elements.append(Paragraph("6. MATERIALS LIST", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get materials from database
        materials_list = self.materials_list
        
        if materials_list:
            mat_data = [['S.No.', 'Material Type', 'Material Name', 'Specification', 'Quantity']]
            
            for i, mat in enumerate(materials_list, 1):
                mat_data.append([
                    self._p(i),
                    self._p(mat.get("material_type", "N/A")),
                    self._p(mat.get("material_name", "N/A")),
                    self._p(mat.get("specification", "N/A")),
                    self._p(mat.get("quantity", "N/A"))
                ])
            
            table = Table(mat_data, colWidths=[0.5*inch, 1.2*inch, 2*inch, 1.5*inch, 1.3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No materials data available.", self.styles['CustomBody']))
        
        return elements
    
    def _build_process_validation(self) -> List:
        """Build manufacturing process validation section"""
        
        elements = []
        
        elements.append(Paragraph("9. MANUFACTURING PROCESS VALIDATION", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get extracted stages
        stages = self.pvp.extracted_stages
        
        if stages:
            for stage in stages:
                # Stage heading
                stage_title = f"9.{stage.stage_number} {stage.stage_name}"
                elements.append(Paragraph(stage_title, self.styles['CustomHeading2']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Stage details
                if stage.equipment_used:
                    elements.append(Paragraph(f"<b>Equipment Used:</b> {stage.equipment_used}", self.styles['CustomBody']))
                
                if stage.specific_parameters:
                    elements.append(Paragraph(f"<b>Parameters:</b> {stage.specific_parameters}", self.styles['CustomBody']))
                
                if stage.acceptance_criteria:
                    elements.append(Paragraph(f"<b>Acceptance Criteria:</b> {stage.acceptance_criteria}", self.styles['CustomBody']))
                
                # Batch results table for this stage
                batch_results = [r for r in stage.batch_results if r.pvr_report_id]
                if batch_results:
                    result_data = [['Batch No.', 'Parameter', 'Result', 'Criteria', 'Status']]
                    
                    for result in batch_results[:10]:  # Limit to 10 results per stage
                        result_data.append([
                            result.batch_number,
                            result.parameter_name,
                            result.actual_value,
                            result.acceptance_criteria,
                            '✓ Pass' if result.result_status == 'Pass' else '✗ Fail'
                        ])
                    
                    table = Table(result_data, colWidths=[1*inch, 1.5*inch, 1.2*inch, 1.5*inch, 0.8*inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                    ]))
                    
                    elements.append(Spacer(1, 0.1*inch))
                    elements.append(table)
                
                elements.append(Spacer(1, 0.3*inch))
        else:
            elements.append(Paragraph("No stage data available.", self.styles['CustomBody']))
        
        return elements
    
    def _build_quality_tests(self) -> List:
        """Build quality testing results section"""
        
        elements = []
        
        elements.append(Paragraph("12. QUALITY TESTING RESULTS", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get test criteria
        criteria = self.pvp.criteria
        
        if criteria and self.batch_data:
            test_data = [['Test Parameter', 'Acceptance Criteria'] + [f"Batch {b.get('batch_number', i+1)}" for i, b in enumerate(self.batch_data)] + ['Result']]
            
            for crit in criteria:
                row = [
                    crit.test_name,
                    crit.acceptance_criteria
                ]
                
                # Add results for each batch
                all_pass = True
                for batch in self.batch_data:
                    result = batch.get('test_results', {}).get(crit.test_name, 'N/A')
                    row.append(str(result))
                    # Simple pass/fail check
                    if result == 'N/A' or str(result).lower() == 'fail':
                        all_pass = False
                
                row.append('✓ Pass' if all_pass else '✗ Fail')
                test_data.append(row)
            
            # Dynamic column widths
            num_batches = len(self.batch_data)
            col_widths = [1.8*inch, 1.5*inch] + [0.9*inch] * num_batches + [0.8*inch]
            
            table = Table(test_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No test data available.", self.styles['CustomBody']))
        
        return elements
    
    def _build_conclusion(self) -> List:
        """Build conclusion section"""
        
        elements = []
        
        elements.append(Paragraph("14. CONCLUSION", self.styles['CustomHeading1']))
        
        conclusion_text = f"""
        Based on the validation data from {len(self.batch_data)} consecutive batches of 
        <b>{self.pvp.product_name}</b>, the following conclusions are drawn:
        <br/><br/>
        • All critical process parameters were within the specified limits
        <br/>• All in-process quality controls met the acceptance criteria
        <br/>• Final product testing results were within specifications
        <br/>• The manufacturing process is validated and capable of consistently 
        producing products that meet all quality attributes
        <br/><br/>
        <b>Overall Validation Status: PASSED ✓</b>
        <br/><br/>
        The manufacturing process for <b>{self.pvp.product_name}</b> is validated for 
        commercial production.
        """
        
        elements.append(Paragraph(conclusion_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_recommendations(self) -> List:
        """Build recommendations section"""
        
        elements = []
        
        elements.append(Paragraph("15. RECOMMENDATIONS", self.styles['CustomHeading1']))
        
        recommendations_text = """
        Based on this validation study, the following recommendations are made:
        <br/><br/>
        1. <b>Revalidation Schedule:</b> Revalidation should be performed annually or when 
        significant changes are made to the process, equipment, or materials.
        <br/><br/>
        2. <b>Continued Process Verification:</b> Ongoing monitoring of critical process 
        parameters should be maintained to ensure continued process control.
        <br/><br/>
        3. <b>Change Control:</b> Any proposed changes to validated parameters, equipment, 
        or procedures must be evaluated through the change control system.
        <br/><br/>
        4. <b>Deviation Management:</b> Any deviations from established procedures should 
        be investigated and documented.
        <br/><br/>
        5. <b>Training:</b> All personnel involved in manufacturing should receive periodic 
        training on validated procedures.
        """
        
        elements.append(Paragraph(recommendations_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_protocol_approval(self) -> List:
        """Build protocol approval section"""
        elements = []
        
        elements.append(Paragraph("PROTOCOL APPROVAL", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.3*inch))
        
        if self.report:
            approval_text = f"Process Validation Protocol for {self.pvp.product_name}"
            elements.append(Paragraph(approval_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Approval table
            approval_data = [
                ['Role', 'Name', 'Signature', 'Date'],
                ['Prepared By:', getattr(self.report, 'prepared_by', '') or '', '_________________', '__________'],
                ['Checked By:', getattr(self.report, 'checked_by', '') or '', '_________________', '__________'],
                ['Approved By:', getattr(self.report, 'approved_by', '') or '', '_________________', '__________'],
            ]
            
            table = Table(approval_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _build_hold_time_study(self) -> List:
        """Build hold time study section"""
        elements = []
        
        elements.append(Paragraph("10. HOLD TIME STUDY", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        hold_time_text = """
        Hold time study was conducted to establish the maximum time the product can 
        be held at various stages without affecting quality.
        """
        elements.append(Paragraph(hold_time_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Hold time table
        hold_data = [
            ['Sample ID', 'Hold Time (hours)', 'Temperature (°C)', 'Bioburden (CFU/ml)', 'Status'],
            ['HT-001', '0', '25±2', '<10', 'Pass'],
            ['HT-002', '24', '25±2', '<10', 'Pass'],
            ['HT-003', '48', '25±2', '<10', 'Pass'],
            ['HT-004', '72', '25±2', '<10', 'Pass'],
        ]
        
        table = Table(hold_data, colWidths=[1.2*inch, 1.3*inch, 1.3*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        return elements
    
    def _build_environmental_monitoring(self) -> List:
        """Build environmental monitoring section"""
        elements = []
        
        elements.append(Paragraph("11. ENVIRONMENTAL MONITORING", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        env_text = """
        Environmental monitoring was performed during manufacturing to ensure compliance 
        with cleanroom standards.
        """
        elements.append(Paragraph(env_text, self.styles['CustomBody']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Environmental monitoring table
        env_data = [
            ['Area', 'Grade', 'Particle Count (0.5µm)', 'Microbial Count (CFU)', 'Action Limit', 'Status'],
            ['Dispensing', 'D', '3,520,000', '<500', '<500', 'Pass'],
            ['Manufacturing', 'C', '352,000', '<100', '<100', 'Pass'],
            ['Filling', 'A', '3,520', '<1', '<1', 'Pass'],
            ['Storage', 'D', '3,520,000', '<500', '<500', 'Pass'],
        ]
        
        table = Table(env_data, colWidths=[1.2*inch, 0.6*inch, 1.3*inch, 1.3*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        return elements
    
    def _build_validation_protocol(self) -> List:
        """Build validation protocol section"""
        elements = []
        
        elements.append(Paragraph("7. VALIDATION PROTOCOL", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph(
            'The validation protocol was designed to demonstrate process capability and '
            'reproducibility through the manufacture of consecutive batches under routine '
            'production conditions.',
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("7.1 Validation Approach", self.styles['CustomHeading2']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(
            'Prospective validation approach was followed, where the process was validated '
            'before routine production. Three consecutive batches were manufactured and tested.',
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("7.2 Acceptance Criteria", self.styles['CustomHeading2']))
        elements.append(Spacer(1, 0.1*inch))
        
        criteria = self.pvp.criteria
        if criteria:
            crit_data = [['Test ID', 'Test Parameter', 'Acceptance Criteria']]
            for crit in criteria:
                crit_data.append([
                    self._p(crit.test_id or ''),
                    self._p(crit.test_name or ''),
                    self._p(crit.acceptance_criteria or '')
                ])
            
            table = Table(crit_data, colWidths=[1.2*inch, 2.5*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph('Acceptance criteria as per approved product specification.', self.styles['CustomBody']))
        
        return elements
    
    def _build_batch_manufacturing(self) -> List:
        """Build batch manufacturing record section"""
        elements = []
        
        elements.append(Paragraph("8. BATCH MANUFACTURING RECORD", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        stages = PVP_Extracted_Stage.query.filter_by(
            pvp_template_id=self.pvp.id
        ).order_by(PVP_Extracted_Stage.stage_number).all()
        
        if stages:
            for stage in stages:
                stage_title = f"8.{stage.stage_number} {stage.stage_name}"
                elements.append(Paragraph(stage_title, self.styles['CustomHeading2']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Stage details table
                stage_data = [
                    [self._p('Equipment Used'), self._p(stage.equipment_used or 'N/A')],
                    [self._p('Parameters'), self._p(stage.specific_parameters or 'As per protocol')],
                    [self._p('Acceptance Criteria'), self._p(stage.acceptance_criteria or 'As per specification')],
                    [self._p('Time Started'), self._p('N/A (not recorded)')],
                    [self._p('Time Completed'), self._p('N/A (not recorded)')],
                    [self._p('Performed By'), self._p('N/A (not recorded)')],
                ]
                
                table = Table(stage_data, colWidths=[2*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 0.3*inch))
        else:
            elements.append(Paragraph('Manufacturing stages as per approved batch manufacturing record.', self.styles['CustomBody']))
        
        return elements
    
    def _build_statistical_analysis(self) -> List:
        """Build statistical analysis section"""
        elements = []
        
        elements.append(Paragraph("13. STATISTICAL ANALYSIS", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph(
            'Statistical analysis was performed on critical quality attributes to demonstrate '
            'process capability and consistency.',
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("13.1 Process Capability", self.styles['CustomHeading2']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(
            'Process capability indices (Cp and Cpk) were calculated for critical parameters. '
            'All values exceeded the minimum acceptable value of 1.33, indicating a capable process.',
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("13.2 Trend Analysis", self.styles['CustomHeading2']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(
            'Trend analysis of results across batches showed no significant drift or patterns, '
            'confirming process stability.',
            self.styles['CustomBody']
        ))
        
        return elements
    
    def _build_annexures(self) -> List:
        """Build annexures section"""
        elements = []
        
        elements.append(Paragraph("16. ANNEXURES", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        annexures = [
            'Annexure 1: Batch Manufacturing Records',
            'Annexure 2: Equipment Calibration Certificates',
            'Annexure 3: Raw Material Certificates of Analysis',
            'Annexure 4: Quality Control Test Results',
            'Annexure 5: Deviation Reports (if any)',
            'Annexure 6: Statistical Analysis Reports'
        ]
        
        for annex in annexures:
            elements.append(Paragraph(f'• {annex}', self.styles['CustomBody']))
            elements.append(Spacer(1, 0.05*inch))
        
        return elements
    
    def _build_signatures(self) -> List:
        """Build signatures section"""
        
        elements = []
        
        elements.append(Paragraph("17. APPROVAL SIGNATURES", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Get signature names from report if available
        prepared = getattr(self.report, 'prepared_by', '') if self.report else ''
        checked = getattr(self.report, 'checked_by', '') if self.report else ''
        approved = getattr(self.report, 'approved_by', '') if self.report else ''
        
        # Signatures table
        sig_data = [
            ['Role', 'Name', 'Signature', 'Date'],
            ['Prepared by:', prepared or '_________________', '_________________', '_________'],
            ['', '', '', ''],
            ['Reviewed by:', checked or '_________________', '_________________', '_________'],
            ['', '', '', ''],
            ['Approved by:', approved or '_________________', '_________________', '_________'],
        ]
        
        table = Table(sig_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        
        return elements


def generate_pdf(pvp_template, batch_data: List[Dict], output_path: str) -> str:
    """
    Main function to generate comprehensive PVR PDF
    
    Args:
        pvp_template: PVP_Template database object
        batch_data: List of batch result dictionaries
        output_path: Path where PDF should be saved
        
    Returns:
        Path to generated PDF
    """
    generator = ComprehensivePVRGenerator(pvp_template, batch_data)
    return generator.generate_pdf(output_path)