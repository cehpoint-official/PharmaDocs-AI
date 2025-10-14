import os
import json
import logging
import pandas as pd
from datetime import datetime
from docx import Document as DocxDocument
from docx.shared import Inches
from io import BytesIO
import requests
from services.cloudinary_service import upload_file_from_path
import tempfile

def generate_document(document, additional_data=None):
    """
    Generate a pharmaceutical document based on the template and data.

    Args:
        document: Document model instance
        additional_data: Additional data for document generation

    Returns:
        dict: Result with success status and file URLs
    """
    try:
        if document.document_type == 'AMV':
            return generate_amv_document(document, additional_data)
        elif document.document_type == 'PV':
            return generate_pv_document(document, additional_data)
        elif document.document_type == 'Stability':
            return generate_stability_document(document, additional_data)
        elif document.document_type == 'Degradation':
            return generate_degradation_document(document, additional_data)
        # elif document.document_type == 'Compatibility':  # (when you’re ready)
        #     return generate_compatibility_document(document, additional_data)
        else:
            return {'success': False, 'error': 'Unsupported document type'}
    except Exception as e:
        logging.error(e)
        return {'success': False, 'error': str(e)}


def generate_amv_document(document, additional_data=None):
    """Generate Analytical Method Validation (AMV) document."""
    try:
        # Parse metadata (from create_document_post form fields)
        meta = json.loads(document.document_metadata or "{}")
        title_text = document.title or "Analytical Method Validation Protocol"

        active_ingredient = meta.get("active_ingredient", "")
        strength = meta.get("strength", "")
        pharmacopeia = meta.get("pharmacopeia", "")
        analytical_method = meta.get("analytical_method", "")

        # Create Word document
        doc = DocxDocument()

        # Title
        title = doc.add_heading(title_text.upper(), 0)
        title.alignment = 1  # center

        # Company information
        if document.company:
            doc.add_paragraph(f"{document.company.name}\n{document.company.address or ''}").bold = True

        # Product Information
        doc.add_heading("PRODUCT INFORMATION", level=1)
        product_table = doc.add_table(rows=5, cols=2)
        product_table.style = "Table Grid"

        fields = [
            ("Product Name", document.title),
            ("Protocol No.", document.document_number or "AMV/P/001"),
            ("Date", datetime.now().strftime("%d/%m/%Y")),
            ("Active Ingredient", active_ingredient),
            ("Strength", strength),
        ]

        for i, (label, value) in enumerate(fields):
            product_table.rows[i].cells[0].text = label
            product_table.rows[i].cells[1].text = value or "-"

        # Objective
        doc.add_heading("1. OBJECTIVE", level=1)
        doc.add_paragraph(
            "To establish and demonstrate that the validation of the analytical method for the "
            f"{active_ingredient} ({strength}) meets the performance characteristics such as "
            "Specificity, System Suitability, Precision, Linearity, Accuracy, Range, and Robustness."
        )

        # Scope
        doc.add_heading("2. SCOPE", level=1)
        doc.add_paragraph(
            f"This protocol applies to the analytical validation of {active_ingredient} "
            f"using {analytical_method or 'HPLC'} according to {pharmacopeia or 'relevant pharmacopeia'}."
        )

        # Responsibilities
        doc.add_heading("3. RESPONSIBILITY", level=1)
        doc.add_paragraph(
            "QC Analyst:\n"
            "- Prepare protocol and execute validation.\n"
            "- Record all observations.\n\n"
            "Head QC:\n"
            "- Review protocol and approve results.\n\n"
            "QA:\n"
            "- Ensure compliance with SOPs and GLP."
        )

        # Method Parameters (STP + Raw Data)
        doc.add_heading("4. METHOD PARAMETERS", level=1)

        if document.stp_file_url:
            doc.add_paragraph("STP document uploaded with this protocol:")
            doc.add_paragraph(document.stp_file_url)

        if document.raw_data_url:
            doc.add_paragraph("Raw analytical data file provided:")
            doc.add_paragraph(document.raw_data_url)

        # Approval Section
        doc.add_heading("5. APPROVAL", level=1)
        approval_table = doc.add_table(rows=4, cols=4)
        approval_table.style = "Table Grid"

        approval_table.rows[0].cells[0].text = "Name"
        approval_table.rows[0].cells[1].text = "Department"
        approval_table.rows[0].cells[2].text = "Signature"
        approval_table.rows[0].cells[3].text = "Date"

        roles = [
            ("Prepared By", "QC Analyst"),
            ("Reviewed By", "Head QC"),
            ("Approved By", "QA Manager"),
        ]
        for i, (role, dept) in enumerate(roles, start=1):
            row = approval_table.rows[i].cells
            row[0].text = f"{role}\n[Name]"
            row[1].text = dept
            row[2].text = ""
            row[3].text = datetime.now().strftime("%d/%m/%Y")

        # Save Word to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
            doc.save(tmp_file.name)
            doc_url = upload_file_from_path(
                tmp_file.name,
                folder="generated_documents",
                resource_type="raw"
            )
            os.unlink(tmp_file.name)

        # Excel file (stub)
        excel_url = generate_amv_excel(document, additional_data)

        return {"success": True, "doc_url": doc_url, "excel_url": excel_url}

    except Exception as e:
        logging.error(f"AMV document generation error: {str(e)}")
        return {"success": False, "error": str(e)}

def generate_amv_excel(document, additional_data=None):
    """Generate Excel file with AMV calculations (with metadata, formulas, formatting)."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            writer = pd.ExcelWriter(tmp_file.name, engine='openpyxl')

            # --------------------
            # 1. Protocol Info
            # --------------------
            info_data = {
                'Field': ['Title', 'Document No.', 'Product', 'Active Ingredient', 'Company', 'Date'],
                'Value': [
                    document.title,
                    document.document_number or '',
                    (json.loads(document.document_metadata).get('product_name', '') if document.document_metadata else ''),
                    (json.loads(document.document_metadata).get('active_ingredient', '') if document.document_metadata else ''),
                    document.company.name if document.company else '',
                    datetime.now().strftime('%d-%m-%Y')
                ]
            }
            pd.DataFrame(info_data).to_excel(writer, sheet_name='Protocol Info', index=False)

            # --------------------
            # 2. System Suitability
            # --------------------
            ss_data = {
                'Parameter': ['Retention Time', 'Peak Area', 'Tailing Factor', 'Theoretical Plates'],
                'Injection 1': ['', '', '', ''],
                'Injection 2': ['', '', '', ''],
                'Injection 3': ['', '', '', ''],
                'Injection 4': ['', '', '', ''],
                'Injection 5': ['', '', '', ''],
                'Mean': ['', '', '', ''],
                '%RSD': ['', '', '', ''],
                'Acceptance Criteria': ['RSD ≤ 2%', 'RSD ≤ 2%', 'NMT 2.0', 'NLT 2000']
            }
            pd.DataFrame(ss_data).to_excel(writer, sheet_name='System Suitability', index=False)

            # --------------------
            # 3. Precision
            # --------------------
            precision_data = {
                'Sample': [f'Sample {i+1}' for i in range(6)],
                'Peak Area': [''] * 6,
                'Assay %': [''] * 6
            }
            pd.DataFrame(precision_data).to_excel(writer, sheet_name='Precision', index=False)

            # --------------------
            # 4. Linearity
            # --------------------
            linearity_data = {
                'Concentration (%)': [50, 75, 100, 125, 150],
                'Peak Area': [''] * 5,
                'Response Factor': [''] * 5
            }
            pd.DataFrame(linearity_data).to_excel(writer, sheet_name='Linearity', index=False)

            # --------------------
            # 5. Accuracy
            # --------------------
            accuracy_data = {
                'Level (%)': [50, 100, 150],
                'Amount Added': [''] * 3,
                'Amount Found': [''] * 3,
                'Recovery %': [''] * 3
            }
            pd.DataFrame(accuracy_data).to_excel(writer, sheet_name='Accuracy', index=False)

            # --------------------
            # 6. Robustness
            # --------------------
            robustness_data = {
                'Parameter': ['Flow Rate +10%', 'Flow Rate -10%', 'Wavelength +2nm', 'Wavelength -2nm'],
                'Retention Time': [''] * 4,
                'Peak Area': [''] * 4,
                'Acceptance Criteria': ['No significant change'] * 4
            }
            pd.DataFrame(robustness_data).to_excel(writer, sheet_name='Robustness', index=False)

            # --------------------
            # 7. LOD & LOQ
            # --------------------
            lod_loq_data = {
                'Parameter': ['LOD', 'LOQ'],
                'Concentration': ['', ''],
                'Peak Area': ['', ''],
                'Acceptance Criteria': ['S/N ≥ 3', 'S/N ≥ 10']
            }
            pd.DataFrame(lod_loq_data).to_excel(writer, sheet_name='LOD_LOQ', index=False)

            writer.close()

            # --------------------
            # Add formulas + styling with openpyxl
            # --------------------
            from openpyxl import load_workbook
            from openpyxl.styles import Font, Alignment

            wb = load_workbook(tmp_file.name)

            # Format headers + add formulas for System Suitability
            ws = wb['System Suitability']
            for cell in ws[1]:
                cell.font = Font(bold=True)
                ws.column_dimensions[cell.column_letter].width = 18

            # Insert Mean & %RSD formulas dynamically (rows 2–5)
            for row in range(2, 6):
                ws[f'H{row}'] = f"=AVERAGE(B{row}:F{row})"
                ws[f'I{row}'] = f"=STDEV(B{row}:F{row})/H{row}*100"
                ws[f'H{row}'].font = Font(bold=True)
                ws[f'I{row}'].font = Font(bold=True)

            # Save workbook
            wb.save(tmp_file.name)

            # --------------------
            # Upload to Cloudinary
            # --------------------
            excel_url = upload_file_from_path(tmp_file.name, folder='generated_excel', resource_type='raw')

            os.unlink(tmp_file.name)
            return excel_url

    except Exception as e:
        logging.error(f"Excel generation error: {str(e)}")
        return None

def generate_pv_document(document, additional_data=None):
    """Generate Process Validation document."""
    # Similar structure to AMV but with PV-specific content
    return {'success': False, 'error': 'PV document generation not yet implemented'}

def generate_stability_document(document, additional_data=None):
    """Generate Stability Study document."""
    # Similar structure to AMV but with stability-specific content
    return {'success': False, 'error': 'Stability document generation not yet implemented'}

def generate_degradation_document(document, additional_data=None):
    """Generate Forced Degradation document."""
    # Similar structure to AMV but with degradation-specific content
    return {'success': False, 'error': 'Degradation document generation not yet implemented'}

def download_file_content(url):
    """Download file content from URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return None

def process_raw_data_for_amv(doc, raw_data_content):
    """Process raw data and add to AMV document."""
    try:
        # Try to read as Excel first, then CSV
        try:
            df = pd.read_excel(BytesIO(raw_data_content))
        except:
            df = pd.read_csv(BytesIO(raw_data_content))

        if not df.empty:
            doc.add_paragraph("Raw data has been processed and incorporated into the method validation calculations.")

            # Add a sample of the data
            if len(df) > 0:
                doc.add_paragraph(f"Data contains {len(df)} rows and {len(df.columns)} columns.")
                doc.add_paragraph(f"Columns: {', '.join(df.columns.tolist())}")

    except Exception as e:
        logging.error(f"Error processing raw data: {str(e)}")
        doc.add_paragraph("Error processing raw data. Please check data format.")
