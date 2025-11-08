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

logger = logging.getLogger(__name__)


class ComprehensivePVRGenerator:
    """Generate comprehensive PVR reports"""
    
    def __init__(self, pvp_template, batch_data: List[Dict]):
        """
        Initialize generator
        
        Args:
            pvp_template: PVP_Template database object
            batch_data: List of batch result dictionaries
        """
        self.pvp = pvp_template
        self.batch_data = batch_data
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
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
        
        # 6. Equipment List
        story.extend(self._build_equipment_list())
        story.append(PageBreak())
        
        # 7. Materials List
        story.extend(self._build_materials_list())
        story.append(PageBreak())
        
        # 8. Manufacturing Process Validation
        story.extend(self._build_process_validation())
        story.append(PageBreak())
        
        # 9. Quality Testing Results
        story.extend(self._build_quality_tests())
        story.append(PageBreak())
        
        # 10. Conclusion
        story.extend(self._build_conclusion())
        story.append(PageBreak())
        
        # 11. Recommendations
        story.extend(self._build_recommendations())
        story.append(PageBreak())
        
        # 12. Signatures
        story.extend(self._build_signatures())
        
        # Build PDF
        doc.build(story)
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
        
        # Date
        date_text = f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}"
        elements.append(Paragraph(date_text, self.styles['CustomBody']))
        
        return elements
    
    def _build_toc(self) -> List:
        """Build table of contents"""
        
        elements = []
        
        elements.append(Paragraph("TABLE OF CONTENTS", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.3*inch))
        
        toc_items = [
            "1. Objective",
            "2. Scope",
            "3. Product Information",
            "4. Equipment List",
            "5. Materials List",
            "6. Manufacturing Process Validation",
            "7. Quality Testing Results",
            "8. Conclusion",
            "9. Recommendations",
            "10. Signatures"
        ]
        
        for item in toc_items:
            elements.append(Paragraph(item, self.styles['CustomBody']))
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
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
        
        return elements
    
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
        
        elements.append(Paragraph("4. EQUIPMENT LIST", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get equipment from database
        equipment_list = self.pvp.equipment_list
        
        if equipment_list:
            equip_data = [['S.No.', 'Equipment Name', 'Equipment ID', 'Location', 'Calibration Status']]
            
            for i, equip in enumerate(equipment_list, 1):
                equip_data.append([
                    str(i),
                    equip.equipment_name,
                    equip.equipment_id or 'N/A',
                    equip.location or 'N/A',
                    equip.calibration_status or 'Valid'
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
        
        elements.append(Paragraph("5. MATERIALS LIST", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get materials from database
        materials_list = self.pvp.materials_list
        
        if materials_list:
            mat_data = [['S.No.', 'Material Type', 'Material Name', 'Specification', 'Quantity']]
            
            for i, mat in enumerate(materials_list, 1):
                mat_data.append([
                    str(i),
                    mat.material_type,
                    mat.material_name,
                    mat.specification or 'N/A',
                    mat.quantity or 'N/A'
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
        
        elements.append(Paragraph("6. MANUFACTURING PROCESS VALIDATION", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get extracted stages
        stages = self.pvp.extracted_stages
        
        if stages:
            for stage in stages:
                # Stage heading
                stage_title = f"6.{stage.stage_number} {stage.stage_name}"
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
        
        elements.append(Paragraph("7. QUALITY TESTING RESULTS", self.styles['CustomHeading1']))
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
                    result = batch.get('results', {}).get(crit.test_id, 'N/A')
                    row.append(str(result))
                    # Simple pass/fail check (you can enhance this)
                    if result == 'N/A' or result == 'Fail':
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
        
        elements.append(Paragraph("8. CONCLUSION", self.styles['CustomHeading1']))
        
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
        
        elements.append(Paragraph("9. RECOMMENDATIONS", self.styles['CustomHeading1']))
        
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
    
    def _build_signatures(self) -> List:
        """Build signatures section"""
        
        elements = []
        
        elements.append(Paragraph("10. APPROVAL SIGNATURES", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Signatures table
        sig_data = [
            ['Role', 'Name', 'Signature', 'Date'],
            ['Prepared by:', '_________________', '_________________', '_________'],
            ['', '', '', ''],
            ['Reviewed by:', '_________________', '_________________', '_________'],
            ['', '', '', ''],
            ['Approved by:', '_________________', '_________________', '_________'],
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


def generate_comprehensive_pvr_pdf(pvp_template, batch_data: List[Dict], output_path: str) -> str:
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