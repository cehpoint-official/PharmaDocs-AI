import os
import json
import re
import PyPDF2
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, jsonify, session, send_file
import io
from werkzeug.utils import secure_filename
# Add this import at the top with your other imports
from models import Document, User, Company, AMVDocument, Equipment, GlassMaterial, Reagent, ReferenceProduct, OtherMaterial, AMVVerificationDocument
from database import db
from datetime import datetime
from services.cloudinary_service import upload_file
from services.method_extraction_service import method_extraction_service
from services.amv_report_service import AMVReportGenerator, extract_method_from_pdf, process_raw_data_file, calculate_validation_statistics
from services.analytical_method_verification_service import analytical_method_verification_service
import traceback
from services.smiles_service import smiles_generator
from utils.validators import validate_file_type

# PDF Method Extraction Class
class MethodPDFExtractor:
    """Extract method parameters from uploaded PDF files"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.extracted_data = {}
    
    def extract_text_from_pdf(self):
        """Extract all text from PDF"""
        text = ""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        return text
    
    def parse_method_parameters(self, text):
        """Parse method parameters using comprehensive regex patterns"""
        
        # Enhanced patterns for all instrument types with more variations
        patterns = {
            # Common parameters with multiple variations
            'weight_standard': [
                r'(?:weight|wt|mass)[\s:]*of\s+standard[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:standard|reference)[\s:]*weight[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:accurately\s+weighed|weigh)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:transfer.*?weighed)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:weigh.*?containing)[\s:]*(\d+\.?\d*)\s*(?:mg|g)'
            ],
            'weight_sample': [
                r'(?:sample|tablet)[\s:]*weight[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:weight|wt)[\s:]*of\s+sample[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:powdered.*?containing)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:equivalent\s+to)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:pooled\s+sample\s+equivalent\s+to)[\s:]*(\d+\.?\d*)\s*(?:mg|g)'
            ],
            'final_concentration_standard': [
                r'(?:final\s+concentration|concentration)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)',
                r'(?:standard\s+solution)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)',
                r'(?:dilute.*?to\s+obtain)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)',
                r'(?:concentration\s+of)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)'
            ],
            'final_concentration_sample': [
                r'(?:sample\s+concentration)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)',
                r'(?:sample\s+solution)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)',
                r'(?:filtrate.*?concentration)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL|mcg/ml)'
            ],
            'potency': [
                r'(?:potency|assay|purity)[\s:]*(\d+\.?\d*)\s*%?',
                r'(?:taking\s+)(\d+\.?\d*)\s*(?:as\s+the\s+value)',
                r'(?:value\s+of\s+A)[\s:]*(\d+\.?\d*)',
                r'(?:A\s*\(1%,\s*1cm\))[\s:]*(\d+\.?\d*)'
            ],
            'average_weight': [
                r'(?:average\s+weight|avg\s+weight)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:tablet\s+weight)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:weight\s+per\s+tablet)[\s:]*(\d+\.?\d*)\s*(?:mg|g)'
            ],
            'weight_per_ml': [
                r'(?:weight\s+per\s+ml|weight/ml)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|g/ml)',
                r'(?:density)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|g/ml)',
                r'(?:specific\s+gravity)[\s:]*(\d+\.?\d*)'
            ],
            'wavelength': [
                r'(?:wavelength|λ|nm|detection)[\s:]*(\d{3,4})',
                r'(?:at\s+)(\d{3,4})\s*nm',
                r'(?:measure.*?at\s+)(\d{3,4})\s*nm',
                r'(?:detection\s+wavelength)[\s:]*(\d{3,4})'
            ],
            
            # HPLC/UPLC/GC specific with more patterns
            'reference_area_standard': [
                r'(?:reference\s+area|area\s+of\s+standard|standard\s+area)[\s:]*(\d+\.?\d*)',
                r'(?:peak\s+area)[\s:]*(\d+\.?\d*)',
                r'(?:area\s+under\s+curve)[\s:]*(\d+\.?\d*)'
            ],
            'flow_rate': [
                r'(?:flow\s+rate|flowrate|flow)[\s:]*(\d+\.?\d*)\s*(?:ml/min|ml/min|mL/min)',
                r'(?:flow\s+rate)[\s:]*(\d+\.?\d*)\s*(?:ml\s+per\s+minute)',
                r'(?:pump\s+rate)[\s:]*(\d+\.?\d*)\s*(?:ml/min)'
            ],
            'injection_volume': [
                r'(?:injection\s+volume|inject|injection)[\s:]*(\d+\.?\d*)\s*(?:μl|μL|ul|UL)',
                r'(?:inject.*?volume)[\s:]*(\d+\.?\d*)\s*(?:μl|μL|ul|UL)',
                r'(?:volume.*?inject)[\s:]*(\d+\.?\d*)\s*(?:μl|μL|ul|UL)'
            ],
            'column': [
                r'(?:column|stationary\s+phase|packing)[\s:]*([^,\n\r]+)',
                r'(?:stainless\s+steel\s+column)[\s:]*([^,\n\r]+)',
                r'(?:packed\s+with)[\s:]*([^,\n\r]+)'
            ],
            'mobile_phase': [
                r'(?:mobile\s+phase|eluent|solvent)[\s:]*([^,\n\r]+)',
                r'(?:buffer\s+solution)[\s:]*([^,\n\r]+)',
                r'(?:diluent)[\s:]*([^,\n\r]+)'
            ],
            
            # UV/AAS specific with more patterns
            'reference_absorbance_standard': [
                r'(?:reference\s+absorbance|absorbance\s+of\s+standard|standard\s+absorbance)[\s:]*(\d+\.?\d*)',
                r'(?:absorbance\s+value)[\s:]*(\d+\.?\d*)',
                r'(?:A\s*\(1%,\s*1cm\))[\s:]*(\d+\.?\d*)',
                r'(?:taking\s+)(\d+\.?\d*)\s*(?:as\s+the\s+value)'
            ],
            'absorbance': [
                r'(?:absorbance|abs|A)[\s:]*(\d+\.?\d*)',
                r'(?:measure\s+absorbance)[\s:]*(\d+\.?\d*)',
                r'(?:absorbance\s+reading)[\s:]*(\d+\.?\d*)'
            ],
            'path_length': [
                r'(?:path\s+length|cell|cuvette)[\s:]*(\d+\.?\d*)\s*(?:cm|mm)',
                r'(?:cell\s+path)[\s:]*(\d+\.?\d*)\s*(?:cm|mm)',
                r'(?:optical\s+path)[\s:]*(\d+\.?\d*)\s*(?:cm|mm)'
            ],
            
            # Titration specific with more patterns
            'reference_volume': [
                r'(?:reference\s+volume|volume)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)',
                r'(?:titrant\s+volume)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)',
                r'(?:consumption)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)'
            ],
            'weight_sample_gm': [
                r'(?:weigh.*?containing\s+)(\d+\.?\d*)\s*(?:g|gm)',
                r'(?:add.*?containing\s+)(\d+\.?\d*)\s*(?:g|gm)',
                r'(?:quantity.*?containing\s+)(\d+\.?\d*)\s*(?:g|gm)',
                r'(?:powder\s+containing\s+)(\d+\.?\d*)\s*(?:g|gm)'
            ],
            'standard_factor': [
                r'(?:each\s+ml.*?equivalent\s+to\s+)(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:equivalent\s+to\s+)(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:factor)[\s:]*(\d+\.?\d*)',
                r'(?:conversion\s+factor)[\s:]*(\d+\.?\d*)'
            ],
            'indicator': [
                r'(?:indicator)[\s:]*([^,\n\r]+)',
                r'(?:using.*?as\s+indicator)[\s:]*([^,\n\r]+)',
                r'(?:with.*?indicator)[\s:]*([^,\n\r]+)'
            ],
            'titrant': [
                r'(?:titrant|standard|reagent)[\s:]*([^,\n\r]+)',
                r'(?:titrate.*?with)[\s:]*([^,\n\r]+)',
                r'(?:using.*?VS)[\s:]*([^,\n\r]+)'
            ],
        }
        
        extracted = {}
        
        # Extract parameters using multiple patterns
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # Clean up numeric values
                    if key in ['weight_standard', 'weight_sample', 'final_concentration_standard', 
                              'final_concentration_sample', 'potency', 'average_weight', 'weight_per_ml',
                              'wavelength', 'reference_area_standard', 'flow_rate', 'injection_volume',
                              'reference_absorbance_standard', 'absorbance', 'path_length',
                              'reference_volume', 'weight_sample_gm', 'standard_factor']:
                        numeric_match = re.search(r'(\d+\.?\d*)', value)
                        if numeric_match:
                            extracted[key] = numeric_match.group(1)
                    else:
                        extracted[key] = value
                    break  # Use first match found
        
        # Add smart defaults for missing parameters
        extracted = self._add_smart_defaults(extracted, text)
        
        return extracted
    
    def _add_smart_defaults(self, extracted, text):
        """Add smart default values for parameters not found in PDF"""
        
        # Smart defaults based on instrument type detection
        instrument_type = self._detect_instrument_type(text)
        
        defaults = {
            # Common defaults
            'weight_standard': '100.0',
            'weight_sample': '50.0',
            'final_concentration_standard': '100.0',
            'final_concentration_sample': '100.0',
            'potency': '99.5',
            'average_weight': '500.0',
            'weight_per_ml': '1.0',
            'wavelength': '254',
        }
        
        # Instrument-specific defaults
        if instrument_type in ['hplc', 'uplc', 'gc']:
            defaults.update({
                'reference_area_standard': '50000.0',
                'flow_rate': '1.0',
                'injection_volume': '20.0',
                'column': 'C18, 250mm x 4.6mm, 5μm',
                'mobile_phase': 'Methanol:Water (70:30)'
            })
        elif instrument_type in ['uv', 'aas']:
            defaults.update({
                'reference_absorbance_standard': '0.450',
                'absorbance': '0.400',
                'path_length': '1.0'
            })
        elif instrument_type == 'titration':
            defaults.update({
                'reference_volume': '25.0',
                'weight_sample_gm': '1.0',
                'standard_factor': '36.95',
                'indicator': 'Methyl Orange',
                'titrant': '1M Hydrochloric Acid VS'
            })
        
        # Apply defaults only for missing parameters
        for key, default_value in defaults.items():
            if key not in extracted:
                extracted[key] = default_value
        
        return extracted
    
    def _detect_instrument_type(self, text):
        """Detect instrument type from text content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['hplc', 'high performance liquid chromatography', 'chromatograph', 'column', 'mobile phase']):
            return 'hplc'
        elif any(word in text_lower for word in ['uplc', 'ultra performance liquid chromatography']):
            return 'uplc'
        elif any(word in text_lower for word in ['gc', 'gas chromatography', 'gas chromatograph']):
            return 'gc'
        elif any(word in text_lower for word in ['uv', 'uv-vis', 'ultraviolet', 'spectrophotometer', 'absorbance']):
            return 'uv'
        elif any(word in text_lower for word in ['aas', 'atomic absorption', 'atomic absorption spectroscopy']):
            return 'aas'
        elif any(word in text_lower for word in ['titration', 'titrate', 'titrant', 'indicator']):
            return 'titration'
        
        return 'hplc'  # Default to HPLC
    
    def extract_method_data(self):
        """Main method to extract all data"""
        text = self.extract_text_from_pdf()
        self.extracted_data = self.parse_method_parameters(text)
        
        # Extract sample preparation if available
        sample_prep_match = re.search(r'Sample\s+Preparation[:\s]+(.{0,500})', text, re.IGNORECASE | re.DOTALL)
        if sample_prep_match:
            self.extracted_data['sample_preparation'] = sample_prep_match.group(1).strip()
        
        # Extract standard preparation
        standard_prep_match = re.search(r'Standard\s+Preparation[:\s]+(.{0,500})', text, re.IGNORECASE | re.DOTALL)
        if standard_prep_match:
            self.extracted_data['standard_preparation'] = standard_prep_match.group(1).strip()
        
        return self.extracted_data

amv_bp = Blueprint('amv_bp', __name__, url_prefix='/amv')

@amv_bp.route('/create', methods=['GET', 'POST'])
def create_amv_form():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    company_id = session.get('user_id', 1)
    
    if request.method == 'POST':
        try:
            current_app.logger.info("=== AMV FORM SUBMITTED ===")
            current_app.logger.info(f"Form files received: {list(request.files.keys())}")
            
            # Validate method PDF upload
            if 'method_pdf' not in request.files:
                flash('Method PDF is required. Please upload a method analysis PDF.', 'error')
                return redirect(url_for('amv_bp.create_amv_form'))
            
            method_pdf = request.files['method_pdf']
            if method_pdf.filename == '':
                flash('Method PDF is required. Please select a method analysis PDF file.', 'error')
                return redirect(url_for('amv_bp.create_amv_form'))
            
            if not method_pdf.filename.lower().endswith('.pdf'):
                flash('Please upload a valid PDF file for method analysis.', 'error')
                return redirect(url_for('amv_bp.create_amv_form'))
            
            # Get selected items from database - USE DIRECT QUERIES
            selected_equipment_ids = request.form.getlist('selected_equipment')
            selected_glass_ids = request.form.getlist('selected_glass_materials')
            selected_reagent_ids = request.form.getlist('selected_reagents')
            selected_reference_id = request.form.get('selected_reference')
            
            # Fetch actual data from database - USING DIRECT QUERIES
            equipment_data = []
            for eq_id in selected_equipment_ids:
                equipment = Equipment.query.filter_by(id=eq_id).first()
                if equipment:
                    equipment_data.append({
                        'name': equipment.name,
                        'code': equipment.code,
                        'brand': equipment.brand,
                        'verification_frequency': equipment.verification_frequency,
                        'last_calibration': equipment.last_calibration,
                        'next_calibration': equipment.next_calibration
                    })
            
            glass_materials = []
            for gm_id in selected_glass_ids:
                glass = GlassMaterial.query.filter_by(id=gm_id).first()
                if glass:
                    glass_materials.append({
                        'name': glass.name,
                        'characteristics': glass.characteristics
                    })
            
            reagents = []
            for r_id in selected_reagent_ids:
                reagent = Reagent.query.filter_by(id=r_id).first()
                if reagent:
                    reagents.append({
                        'name': reagent.name,
                        'batch': reagent.batch,
                        'expiry': reagent.expiry_date
                    })
            
            reference_product = None
            if selected_reference_id:
                ref = ReferenceProduct.query.filter_by(id=selected_reference_id).first()
                if ref:
                    reference_product = {
                        'standard_type': ref.standard_type,
                        'standard_name': ref.standard_name,
                        'code': ref.code,
                        'potency': ref.potency,
                        'due_date': ref.due_date
                    }
            
            # Collect form data
            form_data = {
                'document_title': request.form.get('document_title', ''),
                'product_name': request.form.get('product_name', ''),
                'label_claim': request.form.get('label_claim', ''),
                'company_name': request.form.get('company_name', ''),
                'document_number': request.form.get('document_number') or f'AMV/R/{datetime.now().strftime("%Y%m%d")}',
                'active_ingredient': request.form.get('active_ingredient', ''),
                'molecular_weight': request.form.get('molecular_weight', ''),
                'molecular_formula': request.form.get('molecular_formula', ''),
                'smiles': request.form.get('smiles', ''),
                'instrument_type': request.form.get('instrument_type', ''),
                'val_params': request.form.getlist('val_params') or [],
                'date_option': request.form.get('date_option', 'auto'),
                'prepared_by': request.form.get('prepared_by', ''),
                'checked_by': request.form.get('checked_by', ''),
                'approved_by': request.form.get('approved_by', ''),
                # Instrument-specific parameters
                'weight_standard': request.form.get('weight_standard', ''),
                'weight_sample': request.form.get('weight_sample', ''),
                'final_concentration_standard': request.form.get('final_concentration_standard', ''),
                'final_concentration_sample': request.form.get('final_concentration_sample', ''),
                'potency': request.form.get('potency', ''),
                'average_weight': request.form.get('average_weight', ''),
                'weight_per_ml': request.form.get('weight_per_ml', ''),
                'wavelength': request.form.get('wavelength', ''),
                # UV/AAS specific
                'reference_absorbance_standard': request.form.get('reference_absorbance_standard', ''),
                # HPLC/UPLC/GC specific
                'reference_area_standard': request.form.get('reference_area_standard', ''),
                'flow_rate': request.form.get('flow_rate', ''),
                'injection_volume': request.form.get('injection_volume', ''),
                # Titration specific
                'reference_volume': request.form.get('reference_volume', ''),
                'weight_sample_gm': request.form.get('weight_sample_gm', ''),
                'standard_factor': request.form.get('standard_factor', ''),
                # Database retrieved data
                'equipment_list': equipment_data or [],
                'glass_materials': glass_materials or [],
                'reagents': reagents or [],
                'reference_product': reference_product or {}
            }
            
            # Process method PDF upload
            method_pdf_filename = secure_filename(method_pdf.filename)
            method_pdf_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), method_pdf_filename)
           
             # FOR SIGNATURES ````````````````````````````````
            prepared_sig_file = request.files.get('prepared_signature')
            checked_sig_file = request.files.get('checked_signature')
            approved_sig_file = request.files.get('approved_signature')
            
            # DEBUG: Log what files were received
            current_app.logger.info(f"Signature files received:")
            current_app.logger.info(f"  prepared_signature: {prepared_sig_file}")
            current_app.logger.info(f"  checked_signature: {checked_sig_file}")
            current_app.logger.info(f"  approved_signature: {approved_sig_file}")
            
            # Define a folder to store signature uploads
            UPLOAD_FOLDER = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'signatures')
            os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Create folder if it doesn't exist

            signature_paths = {} # Dictionary to store the file paths

            if prepared_sig_file:
                filename = secure_filename(prepared_sig_file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                prepared_sig_file.save(filepath)
                signature_paths['prepared_by_sig'] = filepath
                current_app.logger.info(f"Saved prepared signature to: {filepath}")

            if checked_sig_file:
                filename = secure_filename(checked_sig_file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                checked_sig_file.save(filepath)
                signature_paths['checked_by_sig'] = filepath
                current_app.logger.info(f"Saved checked signature to: {filepath}")

            if approved_sig_file:
                filename = secure_filename(approved_sig_file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                approved_sig_file.save(filepath)
                signature_paths['approved_by_sig'] = filepath
                current_app.logger.info(f"Saved approved signature to: {filepath}")

            current_app.logger.info(f"Final signature_paths: {signature_paths}")

            # Ensure upload directory exists
            os.makedirs(os.path.dirname(method_pdf_path), exist_ok=True)
            
            # Save method PDF
            method_pdf.save(method_pdf_path)
            
            # Extract method data from PDF
            extractor = MethodPDFExtractor(method_pdf_path)
            extracted_method_data = extractor.extract_method_data()
            
            # Add method parameters to form data
            if extracted_method_data:
                form_data['method_parameters'] = extracted_method_data
                form_data['method_pdf_path'] = method_pdf_path
            
            # Handle extracted method data if available (fallback)
            extracted_data = request.form.get('extracted_method_data', '')
            if extracted_data and extracted_data.strip():
                try:
                    form_data['method_parameters'] = json.loads(extracted_data)
                except json.JSONDecodeError:
                    # If JSON parsing fails, skip the method parameters
                    pass
            
            # Generate report using mathematical calculations
            output_filename = f"AMV_Report_{form_data['product_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            output_path = os.path.join(current_app.config.get('REPORTS_FOLDER', 'reports'), output_filename)
            
            # Ensure reports directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Validate required fields
            required_fields = ['product_name', 'active_ingredient', 'label_claim', 'company_name', 'instrument_type']
            for field in required_fields:
                if not form_data.get(field):
                    raise ValueError(f"Required field '{field}' is missing")
            
            # Get company data for logo and address
            # Get or create company
            company_name = form_data.get('company_name', '')
            company = Company.query.filter_by(name=company_name, user_id=session.get('user_id')).first()
            if not company:
                company = Company.query.filter_by(user_id=session.get('user_id')).first()
            
            # Generate document number if not provided
            document_number = form_data.get('document_number')
            if not document_number:
                document_number = f"AMV-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            # 1. Create main Document record for AMV Report
            document = Document(
                user_id=session.get('user_id'),
                company_id=company.id if company else 1,
                document_type='AMV',  # This is for AMV Reports
                document_number=document_number,
                title=f"AMV Report - {form_data.get('product_name', 'Unknown Product')}",
                status='completed',
                method_analysis_file_url=form_data.get('method_pdf_path'),
                document_metadata=json.dumps(form_data),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(document)
            db.session.flush()  # Get the document ID
            
            # 2. Create AMVDocument record
            amv_document = AMVDocument(
                document_id=document.id,
                product_name=form_data.get('product_name', ''),
                label_claim=form_data.get('label_claim', ''),
                active_ingredient=form_data.get('active_ingredient', ''),
                instrument_type=form_data.get('instrument_type', ''),
                validation_params=json.dumps(form_data.get('val_params', [])),
                protocol_generated=True,
                report_generated=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Set instrument parameters
            instrument_params = {
                'weight_standard': form_data.get('weight_standard'),
                'weight_sample': form_data.get('weight_sample'),
                'final_concentration_standard': form_data.get('final_concentration_standard'),
                'final_concentration_sample': form_data.get('final_concentration_sample'),
                'potency': form_data.get('potency'),
                'wavelength': form_data.get('wavelength'),
                'reference_volume': form_data.get('reference_volume'),
                'weight_sample_gm': form_data.get('weight_sample_gm'),
                'standard_factor': form_data.get('standard_factor')
            }
            amv_document.set_instrument_params(instrument_params)
            
            db.session.add(amv_document)

            company_data = {
                'name': company.name if company else form_data.get('company_name', 'Company'),
                'address': company.address if company else '',
                'logo_url': company.logo_url if company else None
            }
            
            current_app.logger.info(f"Company data being passed: {company_data}")
            
            generator = AMVReportGenerator(form_data, company_data=company_data)
            report_path = generator.generate_report(output_path)
            
            # 4. Update document with generated file path
            document.generated_doc_url = report_path
            
            # 5. COMMIT TO DATABASE
            db.session.commit()
            
            current_app.logger.info(f"AMV Report saved to database. Document ID: {document.id}")
            
            # ========== END DATABASE SAVING ==========
            
            flash('AMV Report generated successfully using mathematical calculations!', 'success')
            return send_file(
                report_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
        except Exception as e:
            current_app.logger.error(f"Error generating AMV report: {str(e)}")
            current_app.logger.error(f"Form data: {form_data}")
            flash(f'Error generating report: {str(e)}', 'error')
            return redirect(url_for('amv_bp.create_amv_form'))

    # GET request - load data for selection - USING DIRECT QUERIES
    equipment_list = Equipment.query.filter_by(company_id=company_id).all()
    glass_materials_list = GlassMaterial.query.filter_by(company_id=company_id).all()
    reagents_list = Reagent.query.filter_by(company_id=company_id).all()
    references_list = ReferenceProduct.query.filter_by(company_id=company_id).all()
    
    # Get user and companies for dropdown
    user = User.query.get(session.get('user_id'))
    companies = Company.query.filter_by(user_id=session.get('user_id')).all()
    
    return render_template('create_amv.html',
                         user=user,
                         companies=companies,
                         equipment_list=equipment_list,
                         glass_materials_list=glass_materials_list,
                         reagents_list=reagents_list,
                         references_list=references_list)

@amv_bp.route('/<int:document_id>')
def view_amv(document_id):
    """View AMV document details"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('dashboard.user_dashboard'))
    
    if document.document_type != 'AMV':
        flash('Document not found', 'error')
        return redirect(url_for('dashboard.user_dashboard'))
    
    metadata = {}
    if document.document_metadata:
        try:
            metadata = json.loads(document.document_metadata)
        except:
            metadata = {}
    
    # Get AMV details
    amv_details = AMVDocument.query.filter_by(document_id=document_id).first()
    
    return render_template('view_amv.html', document=document, metadata=metadata, amv_details=amv_details)

@amv_bp.route('/api/generate-number', methods=['POST'])
def generate_amv_number():
    """Generate AMV document number"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        company_id = data.get('company_id')
        
        if not company_id:
            return jsonify({'error': 'Company ID required'}), 400
        
        # Get company name for prefix and validate ownership
        company = Company.query.filter_by(id=company_id, user_id=session['user_id']).first()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        
        # Generate document number
        current_year = datetime.now().year
        company_prefix = company.name[:3].upper()
        
        # Count existing AMV documents for this company
        count = Document.query.filter_by(
            company_id=company_id,
            document_type='AMV'
        ).count()
        
        document_number = f"{company_prefix}/AMV/{current_year}/{count + 1:04d}"
        
        return jsonify({'document_number': document_number})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@amv_bp.route('/api/extract-method', methods=['POST'])
def extract_method_parameters():
    """API endpoint to extract method parameters from uploaded PDF"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        if 'method_file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['method_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
        # Get instrument type from request
        instrument_type = request.form.get('instrument_type', 'hplc')
        
        # Read file content
        file_content = file.read()
        
        # Extract parameters using the service
        extracted_params = method_extraction_service.extract_method_parameters(
            file_content, instrument_type
        )
        
        # Generate summary
        summary = method_extraction_service.generate_method_summary(extracted_params)
        
        return jsonify({
            'success': True,
            'parameters': extracted_params,
            'summary': summary
        })
        
    except Exception as e:
        current_app.logger.error(f"Error extracting method parameters: {str(e)}")
        return jsonify({'error': 'Failed to extract parameters'}), 500

@amv_bp.route('/api/suggest-validation', methods=['POST'])
def suggest_validation_parameters():
    """API endpoint to suggest validation parameters"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        parameters_to_validate = data.get('parameters_to_validate', [])
        extracted_params = data.get('extracted_params', {})
        
        suggestions = method_extraction_service.suggest_validation_parameters(
            extracted_params, parameters_to_validate
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error suggesting validation parameters: {str(e)}")
        return jsonify({'error': 'Failed to generate suggestions'}), 500

@amv_bp.route('/<int:document_id>/generate-report', methods=['POST'])
def generate_amv_report(document_id):
    """Generate AMV report for a document"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    try:
        engineer_signature = request.files.get('engineer_signature')
        manager_signature = request.files.get('manager_signature')
        approved_signature = request.files.get('approved_signature') 
        engineer_sig_path: str | None = None
        manager_sig_path: str | None = None
        approved_sig_path: str | None = None

        # Create folder to store signature images
        sig_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'signatures')
        os.makedirs(sig_folder, exist_ok=True)
        # Save uploaded files if present
        if engineer_signature:
            engineer_sig_path = os.path.join(sig_folder, secure_filename(engineer_signature.filename))
            engineer_signature.save(engineer_sig_path)
        if manager_signature:
            manager_sig_path = os.path.join(sig_folder, secure_filename(manager_signature.filename))
            manager_signature.save(manager_sig_path)
        if approved_signature:
            approved_sig_path = os.path.join(sig_folder, secure_filename(approved_signature.filename))
            approved_signature.save(approved_sig_path)

        # Get document and validate ownership
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document or document.document_type != 'AMV':
            flash('Document not found', 'error')
            return redirect(url_for('dashboard.user_dashboard'))
        
        # Get AMV details
        amv_details = AMVDocument.query.filter_by(document_id=document_id).first()
        if not amv_details:
            flash('AMV details not found', 'error')
            return redirect(url_for('dashboard.user_dashboard'))
        
        # Get company data
        company = Company.query.get(document.company_id)
        
        # Prepare form data for report generation
        form_data = {
            'document_title': document.title,
            'product_name': amv_details.product_name,
            'label_claim': amv_details.label_claim,
            'active_ingredient': amv_details.active_ingredient,
            'strength': amv_details.strength,
            'instrument_type': amv_details.instrument_type,
            'document_number': document.document_number,
            'val_params': amv_details.get_validation_params(),
            'parameters_to_validate': amv_details.get_parameters_to_validate(),
            'instrument_params': amv_details.get_instrument_params(),
            'prepared_by_sign': engineer_sig_path,
            'checked_by_sign': manager_sig_path,
            'approved_by_sign': approved_sig_path,
        }
        
        # Generate report using MATHEMATICAL CALCULATIONS (NO AI)
        company_data = {
            'name': company.name if company else 'Company',
            'address': company.address if company else '',
            'logo_url': company.logo_url if company else None
        }
        generator = AMVReportGenerator(form_data, company_data=company_data)
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(current_app.root_path, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate filename
        output_filename = f"AMV_Report_{amv_details.product_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        output_path = os.path.join(reports_dir, output_filename)
        
        # Generate the report using mathematical calculations
        generator.generate_report(output_path)
        
        # Update document with generated file path
        document.generated_doc_url = output_path
        document.status = 'generated'
        amv_details.report_generated = True
        db.session.commit()
        
        flash('AMV Report generated successfully!', 'success')
        
        # Return the file for download
        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating AMV report: {str(e)}")
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('amv_bp.view_amv', document_id=document_id))

@amv_bp.route('/<int:document_id>/download')
def download_amv_report(document_id):
    """Download generated AMV report"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        # Get document and validate ownership
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document or document.document_type != 'AMV':
            flash('Document not found', 'error')
            return redirect(url_for('dashboard.user_dashboard'))
        
        if not document.generated_doc_url or not os.path.exists(document.generated_doc_url):
            flash('Report not generated yet. Please generate the report first.', 'error')
            return redirect(url_for('amv_bp.view_amv', document_id=document_id))
        
        # Get AMV details for filename
        amv_details = AMVDocument.query.filter_by(document_id=document_id).first()
        filename = f"AMV_Report_{amv_details.product_name.replace(' ', '_')}.docx" if amv_details else "AMV_Report.docx"
        
        return send_file(
            document.generated_doc_url,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading AMV report: {str(e)}")
        flash(f'Error downloading report: {str(e)}', 'error')
        return redirect(url_for('amv_bp.view_amv', document_id=document_id))

@amv_bp.route('/list')
def list_amv_documents():
    """List all AMV documents for the user"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    documents = Document.query.filter_by(
        user_id=user_id, 
        document_type='AMV'
    ).order_by(Document.created_at.desc()).all()
    
    return render_template('amv_list.html', documents=documents)

@amv_bp.route('/<int:document_id>/delete', methods=['POST'])
def delete_amv_document(document_id):
    """Delete AMV document with proper error handling and redirect"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Get document and validate ownership
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document:
            flash('Document not found', 'error')
            return redirect(url_for('amv_bp.list_amv_documents'))
        
        # Store document type for flash message
        doc_type = document.document_type
        doc_title = document.title
        
        # Delete generated file if exists
        if document.generated_doc_url and os.path.exists(document.generated_doc_url):
            try:
                os.remove(document.generated_doc_url)
                current_app.logger.info(f"Deleted file: {document.generated_doc_url}")
            except Exception as e:
                current_app.logger.warning(f"Could not delete file {document.generated_doc_url}: {str(e)}")
        
        # Delete related records based on document type
        if document.document_type == 'AMV':
            # Delete AMV details first
            amv_doc = AMVDocument.query.filter_by(document_id=document_id).first()
            if amv_doc:
                db.session.delete(amv_doc)
        elif document.document_type == 'AMV_VERIFICATION':
            # Delete AMV verification details first
            amv_verification = AMVVerificationDocument.query.filter_by(document_id=document_id).first()
            if amv_verification:
                db.session.delete(amv_verification)
        
        # Now delete the main document
        db.session.delete(document)
        db.session.commit()
        
        flash(f'{doc_type.replace("_", " ").title()} "{doc_title}" deleted successfully', 'success')
        current_app.logger.info(f"Successfully deleted document {document_id} of type {doc_type}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting document {document_id}: {str(e)}")
        flash(f'Error deleting document: {str(e)}', 'error')
    
    # Redirect based on document type
    return redirect(url_for('dashboard.user_dashboard'))


@amv_bp.route('/api/test-mathematical-calculations', methods=['POST'])
def test_mathematical_calculations():
    """Test endpoint for mathematical calculations"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        parameter = data.get('parameter', 'system_suitability')
        instrument_type = data.get('instrument_type', 'hplc')
        
        # Create a test generator
        test_form_data = {
            'label_claim': '25 mg',
            'active_ingredient': 'Test Ingredient',
            'product_name': 'Test Product'
        }
        
        generator = AMVReportGenerator(test_form_data)
        results = generator.generate_results_mathematical(parameter, instrument_type)
        
        return jsonify({
            'success': True,
            'parameter': parameter,
            'instrument_type': instrument_type,
            'results': results,
            'message': 'Mathematical calculations completed successfully - NO AI REQUIRED'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in mathematical calculations: {str(e)}")
        return jsonify({'error': f'Mathematical calculation failed: {str(e)}'}), 500

@amv_bp.route('/api/validate-ich-criteria', methods=['POST'])
def validate_ich_criteria():
    """Validate results against ICH Q2(R1) criteria"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        results = data.get('results', {})
        parameter = data.get('parameter', 'system_suitability')
        
        validation_status = {}
        
        if parameter == 'system_suitability':
            # ICH Guidelines validation
            rt_cv = results.get('retention_time_cv', 0)
            area_cv = results.get('area_cv', 0)
            tailing = results.get('tailing_factor', 0)
            
            validation_status = {
                'retention_time_cv': {
                    'value': rt_cv,
                    'criteria': 'RT < 2.00%',
                    'pass': rt_cv < 2.0,
                    'ich_compliant': True
                },
                'area_cv': {
                    'value': area_cv,
                    'criteria': 'CV < 2.00%',
                    'pass': area_cv < 2.0,
                    'ich_compliant': True
                },
                'tailing_factor': {
                    'value': tailing,
                    'criteria': '0.80 < T < 2.00',
                    'pass': 0.8 < tailing < 2.0,
                    'ich_compliant': True
                }
            }
        
        elif parameter == 'linearity':
            # Linearity validation
            r_value = results.get('r_value', 0)
            r_squared = results.get('r_squared', 0)
            
            validation_status = {
                'correlation_coefficient': {
                    'value': r_value,
                    'criteria': 'r > 0.9970',
                    'pass': r_value > 0.9970,
                    'ich_compliant': True
                },
                'determination_coefficient': {
                    'value': r_squared,
                    'criteria': 'R² > 0.9950',
                    'pass': r_squared > 0.9950,
                    'ich_compliant': True
                }
            }
        
        elif parameter == 'recovery':
            # Recovery validation
            recovery_80 = results.get('80', 0)
            recovery_100 = results.get('100', 0)
            recovery_120 = results.get('120', 0)
            
            validation_status = {
                '80_percent_level': {
                    'value': recovery_80,
                    'criteria': '98.00 - 102.00%',
                    'pass': 98.0 <= recovery_80 <= 102.0,
                    'ich_compliant': True
                },
                '100_percent_level': {
                    'value': recovery_100,
                    'criteria': '98.00 - 102.00%',
                    'pass': 98.0 <= recovery_100 <= 102.0,
                    'ich_compliant': True
                },
                '120_percent_level': {
                    'value': recovery_120,
                    'criteria': '98.00 - 102.00%',
                    'pass': 98.0 <= recovery_120 <= 102.0,
                    'ich_compliant': True
                }
            }
        
        # Calculate overall compliance
        all_passed = all(item['pass'] for item in validation_status.values())
        
        return jsonify({
            'success': True,
            'parameter': parameter,
            'validation_status': validation_status,
            'overall_compliance': all_passed,
            'ich_guidelines': 'ICH Q2(R1)',
            'message': 'ICH criteria validation completed using mathematical calculations'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error validating ICH criteria: {str(e)}")
        return jsonify({'error': f'ICH validation failed: {str(e)}'}), 500

@amv_bp.route('/settings/equipment', methods=['GET', 'POST'])
def manage_equipment():
    """Manage company equipment database"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    company_id = session.get('user_id', 1)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            # ✅ QUICK FIX: Set date fields to None if empty
            last_calibration = request.form.get('last_calibration') or None
            next_calibration = request.form.get('next_calibration') or None
            
            # Convert to datetime if provided, else keep as None
            if last_calibration:
                try:
                    last_calibration = datetime.strptime(last_calibration, '%Y-%m-%d')
                except ValueError:
                    last_calibration = None  # Invalid date, set to None
            
            if next_calibration:
                try:
                    next_calibration = datetime.strptime(next_calibration, '%Y-%m-%d')
                except ValueError:
                    next_calibration = None  # Invalid date, set to None
            
            equipment = Equipment(
                company_id=company_id,
                name=request.form.get('name'),
                code=request.form.get('code'),
                brand=request.form.get('brand'),
                verification_frequency=request.form.get('verification_frequency'),
                last_calibration=last_calibration,
                next_calibration=next_calibration
            )
            db.session.add(equipment)
            db.session.commit()
            flash('Equipment added successfully!', 'success')
        
        elif action == 'delete':
            equip_id = request.form.get('equipment_id')
            equipment = Equipment.query.filter_by(id=equip_id).first()
            if equipment:
                db.session.delete(equipment)
                db.session.commit()
                flash('Equipment deleted successfully!', 'success')
    
    equipment_list = Equipment.query.filter_by(company_id=company_id).all()
    
    return render_template('manage_equipment.html', equipment_list=equipment_list)

@amv_bp.route('/settings/materials', methods=['GET', 'POST'])
def manage_materials():
    """Manage glass and other materials"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    

    company_id = session.get('user_id', 1)
    
    if request.method == 'POST':
        material_type = request.form.get('material_type')
        action = request.form.get('action')
        
        if action == 'add':
            if material_type == 'glass':
                material = GlassMaterial(
                    company_id=company_id,
                    name=request.form.get('name'),
                    characteristics=request.form.get('characteristics')
                )
                db.session.add(material)
                db.session.commit()
            elif material_type == 'other':
                material = OtherMaterial(
                    company_id=company_id,
                    name=request.form.get('name'),
                    characteristics=request.form.get('characteristics')
                )
                db.session.add(material)
                db.session.commit()
            flash(f'{material_type.title()} material added successfully!', 'success')
    
    glass_materials = GlassMaterial.query.filter_by(company_id=company_id).all()
    other_materials = OtherMaterial.query.filter_by(company_id=company_id).all()
    
    
    return render_template('manage_materials.html', 
                         glass_materials=glass_materials,
                         other_materials=other_materials)

@amv_bp.route('/settings/reagents', methods=['GET', 'POST'])
def manage_reagents():
    """Manage reagents database"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    

    company_id = session.get('user_id', 1)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            reagent = Reagent(
                company_id=company_id,
                name=request.form.get('name'),
                batch=request.form.get('batch'),
                expiry_date=request.form.get('expiry_date')
            )
            db.session.add(reagent)
            db.session.commit()
            flash('Reagent added successfully!', 'success')
    
    reagents = Reagent.query.filter_by(company_id=company_id).all()
    
    return render_template('manage_reagents.html', reagents=reagents)

@amv_bp.route('/settings/reference-products', methods=['GET', 'POST'])
def manage_reference_products():
    """Manage reference products"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    

    company_id = session.get('user_id', 1)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            reference = ReferenceProduct(
                company_id=company_id,
                standard_type=request.form.get('standard_type'),
                standard_name=request.form.get('standard_name'),
                code=request.form.get('code'),
                potency=request.form.get('potency'),
                due_date=request.form.get('due_date')
            )
            db.session.add(reference)
            db.session.commit()
            flash('Reference product added successfully!', 'success')
    
    references = ReferenceProduct.query.filter_by(company_id=company_id).all()
    
    return render_template('manage_reference_products.html', references=references)

@amv_bp.route('/test-extract', methods=['GET'])
def test_extract_route():
    """Test route to verify routing is working"""
    return jsonify({'success': True, 'message': 'Route is working'})





@amv_bp.route('/verification', methods=['GET'])
def amv_verification_protocol_page():
    """Render the AMV Verification Protocol form page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

  
    company_id = session.get('user_id', 1)
    user_id = session.get('user_id')
    
    # Get user from main database
    user = User.query.get(user_id) if user_id else None
    
    # USE DIRECT QUERIES INSTEAD OF Session()
    equipment_list = Equipment.query.filter_by(company_id=company_id).all()
    glass_materials_list = GlassMaterial.query.filter_by(company_id=company_id).all()
    reagents_list = Reagent.query.filter_by(company_id=company_id).all()
    references_list = ReferenceProduct.query.filter_by(company_id=company_id).all()
    companies = Company.query.filter_by(user_id=user_id).all() if user_id else []
    
    return render_template('amv_verification_protocol.html',
                           equipment_list=equipment_list,
                           glass_materials_list=glass_materials_list,
                           reagents_list=reagents_list,
                           references_list=references_list,
                           user=user,
                           companies=companies)

@amv_bp.route('/generate-verification-protocol', methods=['POST'])
def generate_verification_protocol():
    """Generate AMV Verification Protocol from form data"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        print("🔍 Received form data:", request.form)
        print("🔍 Form keys:", list(request.form.keys()))
        
        # Get validation parameters from form
        val_params_json = request.form.get('val_params_json', '[]')
        selected_val_params = json.loads(val_params_json) if val_params_json else []
        
        print(f"🎯 Selected validation parameters from form: {selected_val_params}")





        form_data = request.form
        
        # Get the actual selected IDs from form
        equipment_ids = form_data.getlist('selected_equipment')
        glass_ids = form_data.getlist('selected_glass_materials')
        reagent_ids = form_data.getlist('selected_reagents')
        reference_id = form_data.get('selected_reference')
        
        # Fetch actual data from database - USING DIRECT QUERIES
        selected_equipment = []
        for eq_id in equipment_ids:
            if eq_id:
                equipment = Equipment.query.filter_by(id=int(eq_id)).first()
                if equipment:
                    selected_equipment.append({
                        'id': equipment.id,
                        'name': equipment.name,
                        'code': equipment.code or '',
                        'brand': equipment.brand or '',
                        'verification_frequency': equipment.verification_frequency or '',
                        'last_calibration': equipment.last_calibration or '',
                        'next_calibration': equipment.next_calibration or ''
                    })
        
        selected_glass = []
        for glass_id in glass_ids:
            if glass_id:
                glass = GlassMaterial.query.filter_by(id=int(glass_id)).first()
                if glass:
                    selected_glass.append({
                        'id': glass.id,
                        'name': glass.name,
                        'characteristics': glass.characteristics or ''
                    })
        
        selected_reagents = []
        for reagent_id in reagent_ids:
            if reagent_id:
                reagent = Reagent.query.filter_by(id=int(reagent_id)).first()
                if reagent:
                    selected_reagents.append({
                        'id': reagent.id,
                        'name': reagent.name,
                        'batch': reagent.batch or '',
                        'expiry_date': reagent.expiry_date or ''
                    })
        
        selected_reference = None
        if reference_id:
            reference = ReferenceProduct.query.filter_by(id=int(reference_id)).first()
            if reference:
                selected_reference = {
                    'id': reference.id,
                    'standard_name': reference.standard_name,
                    'standard_type': reference.standard_type or '',
                    'code': reference.code or '',
                    'potency': reference.potency or '',
                    'due_date': reference.due_date or ''
                }
        
        # Prepare protocol data
        protocol_data = {
            'product_name': form_data.get('product_name', ''),
            'active_ingredient': form_data.get('active_ingredient', ''),
            'test_method': form_data.get('test_method', ''),
            'label_claim': form_data.get('label_claim', ''),
            'protocol_number': form_data.get('protocol_number', ''),
            'company_name': form_data.get('company_name', ''),
            'company_location': form_data.get('company_location', ''),
            'specification_range': form_data.get('specification_range', ''),
            'wavelength': form_data.get('wavelength', ''),
            'molecular_weight': form_data.get('molecular_weight', ''),
            'molecular_formula': form_data.get('molecular_formula', ''),
            'smiles': form_data.get('smiles', ''),
            'weight_standard': form_data.get('weight_standard', ''),
            'weight_sample': form_data.get('weight_sample', ''),
            'final_concentration_standard': form_data.get('final_concentration_standard', ''),
            'final_concentration_sample': form_data.get('final_concentration_sample', ''),
            'potency': form_data.get('potency', ''),
            'average_weight': form_data.get('average_weight', ''),
            'weight_per_ml': form_data.get('weight_per_ml', ''),
            'reference_absorbance_standard': form_data.get('reference_absorbance_standard', ''),
            'reference_area_standard': form_data.get('reference_area_standard', ''),
            'flow_rate': form_data.get('flow_rate', ''),
            'injection_volume': form_data.get('injection_volume', ''),
            'reference_volume': form_data.get('reference_volume', ''),
            'weight_sample_gm': form_data.get('weight_sample_gm', ''),
            'standard_factor': form_data.get('standard_factor', ''),
            'prepared_by_name': form_data.get('prepared_by_name', ''),
            'prepared_by_dept': form_data.get('prepared_by_dept', 'Quality Control'),
            'reviewed_by_name': form_data.get('reviewed_by_name', ''),
            'reviewed_by_dept': form_data.get('reviewed_by_dept', 'Quality Control'),
            'approved_by_name': form_data.get('approved_by_name', ''),
            'approved_by_dept': form_data.get('approved_by_dept', 'Quality Assurance'),
            'authorized_by_name': form_data.get('authorized_by_name', ''),
            'authorized_by_dept': form_data.get('authorized_by_dept', 'Quality Assurance'),
            
            # Add the fetched data as JSON strings for the protocol generator
            'selected_equipment': selected_equipment,
            'selected_glass_materials': selected_glass,
            'selected_reagents': selected_reagents,
            'selected_reference': selected_reference,
            'selected_equipment_json': json.dumps(selected_equipment),
            'selected_glass_materials_json': json.dumps(selected_glass),
            'selected_reagents_json': json.dumps(selected_reagents),
            'selected_reference_json': json.dumps(selected_reference),
            'val_params': selected_val_params
        }
        
        # Get validation parameters
        selected_params = []
        param_mapping = {
            'system_suitability': 'System Suitability',
            'specificity': 'Specificity',
            'system_precision': 'System Precision',
            'method_precision': 'Method Precision',
            'intermediate_precision': 'Intermediate Precision',
            'linearity': 'Linearity',
            'recovery': 'Recovery',
            'robustness': 'Robustness',
            'range': 'Range',
            'lod_loq': 'LOD and LOQ',
            'lod_loq_precision': 'LOD and LOQ Precision'
        }
        
        val_params = form_data.getlist('val_params')
        for param_key in val_params:
            if param_key in param_mapping:
                selected_params.append(param_mapping[param_key])
        
        company_name = form_data.get('company_name', '')
        company = Company.query.filter_by(name=company_name, user_id=session.get('user_id')).first()
        if not company:
            company = Company.query.filter_by(user_id=session.get('user_id')).first()

        # Generate protocol number if not provided
        protocol_number = form_data.get('protocol_number')
        if not protocol_number:
            protocol_number = f"AMV-PROTOCOL-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        # 1. Create main Document record for AMV Verification
        document = Document(
            user_id=session.get('user_id'),
            company_id=company.id if company else 1,
            document_type='AMV_VERIFICATION',  # This is for AMV Verification Protocols
            document_number=protocol_number,
            title=f"AMV Verification Protocol - {form_data.get('product_name', 'Unknown Product')}",
            status='completed',
            document_metadata=json.dumps({
                'product_name': form_data.get('product_name'),
                'active_ingredient': form_data.get('active_ingredient'),
                'test_method': form_data.get('test_method'),
                'protocol_number': protocol_number
            }),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.session.add(document)
        db.session.flush()  # Get the document ID
        
        # 2. Create AMVVerificationDocument record
        amv_verification = AMVVerificationDocument(
            document_id=document.id,
            product_name=form_data.get('product_name', ''),
            active_ingredient=form_data.get('active_ingredient', ''),
            label_claim=form_data.get('label_claim', ''),
            test_method=form_data.get('test_method', ''),
            company_name=form_data.get('company_name', ''),
            company_location=form_data.get('company_location', ''),
            protocol_number=protocol_number,
            specification_range=form_data.get('specification_range', ''),
            wavelength=form_data.get('wavelength', ''),
            molecular_weight=form_data.get('molecular_weight', ''),
            molecular_formula=form_data.get('molecular_formula', ''),
            smiles=form_data.get('smiles', ''),
            prepared_by_name=form_data.get('prepared_by_name', ''),
            prepared_by_dept=form_data.get('prepared_by_dept', 'Quality Control'),
            reviewed_by_name=form_data.get('reviewed_by_name', ''),
            reviewed_by_dept=form_data.get('reviewed_by_dept', 'Quality Control'),
            protocol_generated=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Set JSON data
        method_params = {
            'weight_standard': form_data.get('weight_standard'),
            'weight_sample': form_data.get('weight_sample'),
            'final_concentration_standard': form_data.get('final_concentration_standard'),
            'final_concentration_sample': form_data.get('final_concentration_sample'),
            'potency': form_data.get('potency'),
            'wavelength': form_data.get('wavelength')
        }
        amv_verification.set_method_parameters(method_params)
        
        # Set selected items
        amv_verification.set_selected_equipment(selected_equipment)
        amv_verification.set_selected_glass_materials(selected_glass)
        amv_verification.set_selected_reagents(selected_reagents)
        amv_verification.set_selected_reference(selected_reference)
        
        # Set validation parameters
        val_params = form_data.getlist('val_params')
        amv_verification.set_validation_parameters(val_params)
        
        db.session.add(amv_verification)
        
        # 3. Generate the protocol document
        from services.analytical_method_verification_service import analytical_method_verification_service
        
        method_info = {
            'product_name': protocol_data['product_name'],
            'active_ingredient': protocol_data['active_ingredient'],
            'concentration': protocol_data.get('final_concentration_standard', '') or protocol_data.get('label_claim', ''),
            'test_method': protocol_data['test_method'],
            'wavelength': protocol_data['wavelength'],
            'specification_range': protocol_data['specification_range'],
            'company_name': protocol_data['company_name'],
            'company_location': protocol_data['company_location'],
            'protocol_number': protocol_data['protocol_number']
        }
        
        # Generate the protocol
        protocol_buffer = analytical_method_verification_service.generate_verification_protocol(
            method_info, selected_params, protocol_data
        )
        
        if protocol_buffer is None:
            flash('Error generating verification protocol. Please try again.', 'error')
            return redirect(url_for('amv_bp.amv_verification_protocol_page'))
        
        # Save protocol to file
        reports_dir = os.path.join(current_app.config.get('REPORTS_FOLDER', 'reports'), 'amv_verification')
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"AMV_Verification_Protocol_{form_data.get('product_name', '').replace(' ', '_')}_{timestamp}.docx"
        output_path = os.path.join(reports_dir, output_filename)
        
        # Save the buffer to file
        with open(output_path, 'wb') as f:
            f.write(protocol_buffer.getvalue())
        
        # 4. Update document with generated file path
        document.generated_doc_url = output_path
        
        # 5. COMMIT TO DATABASE
        db.session.commit()
        
        current_app.logger.info(f"AMV Verification Protocol saved to database. Document ID: {document.id}")
        
        flash('AMV Verification Protocol generated and saved successfully!', 'success')

        # ✅ FIXED: Use the correct filename variable
        return send_file(
            protocol_buffer,
            as_attachment=True,
            download_name=output_filename,  # ✅ This was the fix
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating verification protocol: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Error generating verification protocol. Please try again.', 'error')
        return redirect(url_for('amv_bp.amv_verification_protocol_page'))

# Protocol Generator UI and APIs
@amv_bp.route('/protocol', methods=['GET'])
def protocol_generator_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('protocol_generator.html')

@amv_bp.route('/protocol/api/methods', methods=['GET'])
def protocol_methods():
    methods = [
        {'value': 'uv', 'label': 'UV Spectroscopy'},
        {'value': 'aas', 'label': 'AAS (Atomic Absorption)'},
        {'value': 'hplc', 'label': 'HPLC'},
        {'value': 'uplc', 'label': 'UPLC'},
        {'value': 'gc', 'label': 'GC (Gas Chromatography)'},
        {'value': 'titration', 'label': 'Titration'},
    ]
    return jsonify(methods)

PARAMETERS_BY_METHOD = {
    'uv': [
        'Specificity', 'System Precision', 'Method Precision', 'Intermediate Precision',
        'Linearity', 'Range', 'Recovery'
    ],
    'aas': [
        'Specificity', 'System Precision', 'Method Precision', 'Intermediate Precision',
        'Linearity', 'Range', 'Recovery'
    ],
    'hplc': [
        'Specificity', 'System Suitability', 'System Precision', 'Method Precision',
        'Intermediate Precision', 'Linearity', 'LOD and LOQ', 'LOD and LOQ Precision',
        'Range', 'Recovery', 'Robustness'
    ],
    'uplc': [
        'Specificity', 'System Suitability', 'System Precision', 'Method Precision',
        'Intermediate Precision', 'Linearity', 'LOD and LOQ', 'LOD and LOQ Precision',
        'Range', 'Recovery', 'Robustness'
    ],
    'gc': [
        'Specificity', 'System Suitability', 'System Precision', 'Method Precision',
        'Intermediate Precision', 'Linearity', 'LOD and LOQ', 'LOD and LOQ Precision',
        'Range', 'Recovery', 'Robustness'
    ],
    'titration': [
        'Specificity', 'Method Precision', 'Intermediate Precision', 'Linearity',
        'Range', 'Recovery'
    ],
}

@amv_bp.route('/protocol/api/parameters/<method>', methods=['GET'])
def protocol_parameters(method):
    return jsonify(PARAMETERS_BY_METHOD.get(method, []))

@amv_bp.route('/protocol/api/extract_data', methods=['POST'])
def protocol_extract_data():
    mock_data = {
        'productName': 'Fluorouracil Injection BP',
        'concentration': '50 mg/ml',
        'protocolNumber': 'KPL/AMVN/P/21/001-00',
        'effectiveDate': datetime.now().strftime('%Y-%m-%d'),
        'methodology': 'UV Spectrophotometry',
        'wavelength': '266 nm',
        'acceptanceCriteria': '90.0% - 110.0%',
        'samplePreparation': 'Mix content of five vials, transfer equivalent to 75mg to 200ml flask',
        'company': 'Kwality Pharmaceuticals Limited',
    }
    return jsonify(mock_data)

def _generate_parameter_section(param, data, method):
    pn = data.get('productName', 'Product')
    wl = data.get('wavelength', 'λ')
    acc = data.get('acceptanceCriteria', '90.0% - 110.0%')

    sections = {
        'Specificity': {
            'objective': (
                f"The specificity parameter evaluates the analytical method's ability to unequivocally assess the analyte "
                f"in the presence of components that may be expected to be present, including impurities, degradation products, "
                f"and matrix components. This ensures the analytical response is solely attributable to the target analyte. For {pn}, "
                f"specificity testing demonstrates that blank solutions, placebo preparations, and potential interfering substances do not "
                f"contribute to the absorbance/response at the specified wavelength of {wl}."
            ),
            'procedure': (
                f"Prepare blank using the same diluent system used for sample preparation (e.g., 0.1 M HCl for UV). Measure blank at {wl} to establish baseline. "
                f"Prepare placebo by weighing excipients equivalent to sample formulation without API and process identically to sample. Prepare sample by pooling, transferring an aliquot to the volumetric flask, dissolving with 1 M HCl (if applicable), and diluting as per method. "
                f"Measure absorbance/response sequentially for blank, placebo, and sample, using matched cells/cuvettes and a validated instrument."
            ),
            'acceptance': (
                f"Blank absorbance/response ≤ 0.005 AU (or negligible response); Placebo ≤ 0.010 AU at {wl}; sample shows clear, measurable response significantly above blank/placebo. "
                f"Spectral/peak purity confirms single-component response at {wl} with no secondary peaks/shoulders indicating co-eluting substances."
            ),
            'dataPoints': 3,
        },
        'System Precision': {
            'objective': (
                f"Evaluate inherent variability of the analytical system independent of sample preparation. Demonstrates that the system produces consistent, "
                f"reproducible measurements when the same solution is analyzed repeatedly under identical conditions for {pn}."
            ),
            'procedure': (
                f"Prepare a single working standard solution at the target analytical concentration. Measure absorbance/response at {wl} (where applicable) six times consecutively without re-preparation, rinsing the cell between fills. Maintain constant instrument parameters (bandwidth, scan speed, response time). Record each value to appropriate precision (e.g., 4 decimals for absorbance)."
            ),
            'acceptance': (
                f"RSD of six replicate responses ≤ 1.0%. Individual values within ±2.0% of the mean. Mean response ensures operation within the linear range (e.g., 0.300–0.800 AU for UV). No trending pattern indicative of drift."
            ),
            'dataPoints': 6,
        },
        'Method Precision': {
            'objective': (
                f"Assess repeatability (intra-assay precision) of the complete analytical procedure including preparation, measurement, and calculations when performed "
                f"by a single analyst over a short time. Provides realistic variability for routine QC analysis of {pn}."
            ),
            'procedure': (
                f"Prepare six independent sample preparations following the full method (pool sample if applicable, weigh aliquots, dissolve with 1 M HCl if specified, dilute to volume, perform secondary dilution where required, and measure at {wl} for UV methods). Calculate % of label claim for each preparation."
            ),
            'acceptance': (
                f"RSD of six assay results ≤ 2.0%. All individual results within specification range {acc}. Mean approximates true value (typically 98.0–102.0%). Range (max–min) ≤ 5.0 percentage points. No result deviates more than 3.0% from the mean."
            ),
            'dataPoints': 6,
        },
        'Intermediate Precision': {
            'objective': (
                f"Assess ruggedness by introducing within-lab variations (day, analyst, instrument) while maintaining the same method. Confirms that {pn} results are consistent across minor operational changes."
            ),
            'procedure': (
                f"A second qualified analyst repeats the method on a different validated instrument on a different day, preparing six independent samples identically to method precision. Compute % label claim for each. Pool data (n=12) from method and intermediate precision to compute combined precision."
            ),
            'acceptance': (
                f"RSD for the second set (n=6) ≤ 2.0%. Combined RSD for all twelve results ≤ 2.0%. All results within {acc}. Means between analysts differ by ≤ 2.0 percentage points. Statistical comparison (F-test/t-test) shows no significant difference at 95% confidence."
            ),
            'dataPoints': 12,
        },
        'Linearity': {
            'objective': (
                f"Demonstrate the proportional relationship between concentration and response within a specified range for {pn}, validating quantitative calculations (e.g., Beer–Lambert law for UV)."
            ),
            'procedure': (
                f"Prepare at least five levels (e.g., 50%, 80%, 100%, 120%, 150% of target). Measure response at each level (e.g., absorbance at {wl}). Plot concentration vs response and perform least-squares regression to obtain slope, intercept, correlation (r). Evaluate residuals and confidence intervals for slope/intercept."
            ),
            'acceptance': (
                f"Correlation coefficient r ≥ 0.999 (typical assay criterion). r² ≥ 0.998. Intercept near zero (within ±5% of 100% response) and 95% CI of intercept includes zero. Residuals random; no single residual exceeds 5% of corresponding response. Back-calculated concentrations within ±2.0% of theoretical."
            ),
            'dataPoints': 5,
        },
        'Range': {
            'objective': (
                f"Define interval between upper and lower analyte concentrations for which precision, accuracy, and linearity are acceptable for {pn}."
            ),
            'procedure': (
                f"Verify precision at lower (e.g., 50%) and upper (e.g., 150%) levels with six replicates each. Confirm responses remain within optimal instrument range and consistent with linearity results at 100% level."
            ),
            'acceptance': (
                f"RSD at 50% and 150% levels ≤ 2.0%. Mean response at low level above instrument noise threshold; high level below saturation threshold (e.g., UV ≤ 1.0 AU). Precision scales appropriately with concentration; no individual deviates > 5% from mean."
            ),
            'dataPoints': 12,
        },
        'Recovery': {
            'objective': (
                f"Evaluate accuracy by spiking placebo with known amounts of standard at multiple levels (e.g., 50%, 100%, 150%) and processing through the full method for {pn}."
            ),
            'procedure': (
                f"Prepare triplicates at each level (50%, 100%, 150%) using placebo matrix plus standard, then perform the entire method and calculate % recovery for each. Compute mean and RSD per level and overall."
            ),
            'acceptance': (
                f"Individual recoveries 98.0%–102.0%. Mean per level 98.0%–102.0% with RSD ≤ 2.0%. Overall mean 98.0%–102.0% and overall RSD ≤ 2.0%. 95% CI of overall mean includes 100%."
            ),
            'dataPoints': 9,
        },
        'System Suitability': {
            'objective': (
                f"Confirm chromatographic system performance (HPLC/UPLC/GC) before/during analysis of {pn} via predefined metrics (plates, tailing, resolution, precision)."
            ),
            'procedure': (
                f"Inject standard solution six times under validated conditions. Calculate retention time, theoretical plates, tailing factor, peak area precision, and resolution vs nearest peak (if applicable)."
            ),
            'acceptance': (
                f"Typical criteria: Plates ≥ 2000 (HPLC), ≥ 5000 (UPLC), ≥ 10000 (GC); tailing ≤ 2.0 (HPLC/UPLC) or ≤ 1.5 (GC); resolution ≥ 2.0 to nearest peak; peak area RSD ≤ 2.0%; retention time RSD ≤ 1.0%."
            ),
            'dataPoints': 6,
        },
        'LOD and LOQ': {
            'objective': (
                f"Define the lowest detectable (LOD) and quantifiable (LOQ) concentrations for {pn}, establishing method sensitivity."
            ),
            'procedure': (
                f"Determine by signal-to-noise or standard deviation/slope approach. Prepare very low concentration series; compute S/N for each. Interpolate LOD at S/N≈3 and LOQ at S/N≈10. Verify LOQ with six replicates for precision and accuracy."
            ),
            'acceptance': (
                f"LOD exhibits S/N ≥ 3:1 with identifiable peak/response. LOQ exhibits S/N ≥ 10:1; six replicates at LOQ show RSD ≤ 10% and accuracy 80%–120%."
            ),
            'dataPoints': 18,
        },
        'LOD and LOQ Precision': {
            'objective': (
                f"Demonstrate repeatability at the LOQ (and optionally at LOD for detection success) for {pn}, showing practical capability at trace levels."
            ),
            'procedure': (
                f"Prepare six independent LOQ-level solutions and analyze under validated conditions. Compute mean, SD, RSD, and accuracy vs theoretical LOQ. Optionally assess LOD detection success rate (S/N ≥ 3)."
            ),
            'acceptance': (
                f"LOQ precision: RSD ≤ 10%, individual values within ±20% of mean, mean accuracy 80%–120%, clear peaks with S/N ≥ 10. Optional LOD: ≥ 83% detections (≥ 5/6) with mean S/N > 4."
            ),
            'dataPoints': 6,
        },
        'Robustness': {
            'objective': (
                f"Assess method's insensitivity to small, deliberate variations in parameters (e.g., pH, composition, temperature, flow, wavelength) for {pn}."
            ),
            'procedure': (
                f"Vary one parameter at a time around nominal (e.g., pH ±0.2, flow ±10%, temperature ±5°C, wavelength ±2 nm). For each varied condition, analyze a standard in triplicate and compare system suitability and assay to nominal."
            ),
            'acceptance': (
                f"Assay remains within ±2.0% of nominal across variations; system suitability continues to meet criteria; precision (triplicate RSD) ≤ 2.0%; retention time change ≤ 5%; resolution ≥ 2.0. Identify critical parameters requiring tighter control if criteria not met."
            ),
            'dataPoints': 21,
        },
    }

    return sections.get(param, {
        'objective': f'Detailed evaluation of {param} for {pn}',
        'procedure': f'Standard procedure for {param} assessment',
        'acceptance': f'Standard acceptance criteria for {param}',
        'dataPoints': 6,
    })

def _generate_header(data):
    return {
        'company': data['company'],
        'productName': data['productName'],
        'protocolNumber': data['protocolNumber'],
        'effectiveDate': data['effectiveDate'],
        'title': f"Analytical Method Verification Protocol for {data['productName']}",
    }

@amv_bp.route('/protocol/api/generate_protocol', methods=['POST'])
def protocol_generate():
    payload = request.get_json(silent=True) or {}
    data = payload.get('extractedData') or {}
    params = payload.get('selectedParams') or []
    method = payload.get('selectedMethod') or ''
    if not data or not params:
        return jsonify({'error': 'Missing required data'}), 400
    detailed_objective = (
        f"To establish documented evidence providing a high degree of assurance that the analytical method for {data.get('productName','Product')} "
        f"meets its pre-defined specifications and quality attributes. This verification protocol demonstrates that the analytical procedure is suitable for its intended purpose "
        f"and consistently produces accurate, precise, and reliable results within the specified range. The objective encompasses establishing method performance characteristics "
        f"including specificity, precision at multiple levels, linearity across the working range, accuracy through recovery studies, and robustness under varied conditions. "
        f"Through systematic evaluation of these parameters, this verification ensures the method's capability to quantitatively determine the active pharmaceutical ingredient with appropriate selectivity and sensitivity, "
        f"meeting regulatory requirements and quality standards established by pharmacopeial guidelines and ICH recommendations."
    )
    detailed_scope = (
        f"This verification protocol encompasses the complete analytical methodology for {data.get('productName','Product')} at the concentration of {data.get('concentration','')}. "
        f"The scope includes comprehensive evaluation of all critical method parameters necessary to demonstrate method suitability for routine quality control analysis. "
        f"The verification activities cover sample preparation procedures, instrumental parameters, data analysis methods, and acceptance criteria establishment. "
        f"This protocol applies to the Quality Control laboratory at {data.get('company','Company')} and extends to all personnel involved in performing analytical testing. "
        f"The verification encompasses both intra-laboratory precision and inter-analyst variability assessment. Additionally, the scope includes establishment of working ranges, detection capabilities, and method robustness under normal operational conditions. "
        f"All verification activities are conducted in accordance with current Good Manufacturing Practices (cGMP), ICH Q2(R1) guidelines, and relevant pharmacopeial standards to ensure method reliability and regulatory compliance."
    )
    protocol = {
        'header': _generate_header(data),
        'objective': detailed_objective,
        'scope': detailed_scope,
        'parameters': {},
    }
    for p in params:
        protocol['parameters'][p] = _generate_parameter_section(p, data, method)
    return jsonify({'protocol': protocol})

@amv_bp.route('/protocol/api/download_protocol', methods=['POST'])
def protocol_download():
    payload = request.get_json(silent=True) or {}
    protocol = payload.get('protocol') or {}
    if not protocol:
        return jsonify({'error': 'No protocol data provided'}), 400
    def _format(protocol):
        header = protocol.get('header', {})
        buf = []
        buf.append('ANALYTICAL METHOD VERIFICATION PROTOCOL')
        buf.append(header.get('company',''))
        buf.append(header.get('title',''))
        buf.append(f"Protocol Number: {header.get('protocolNumber','')}")
        buf.append(f"Effective Date: {header.get('effectiveDate','')}")
        buf.append(f"Product Name: {header.get('productName','')}")
        buf.append('')
        buf.append('1. OBJECTIVE')
        buf.append(protocol.get('objective',''))
        buf.append('')
        buf.append('2. SCOPE')
        buf.append(protocol.get('scope',''))
        buf.append('')
        buf.append('3. VERIFICATION PARAMETERS')
        for idx, (name, section) in enumerate(protocol.get('parameters', {}).items(), start=1):
            buf.append('')
            buf.append(f"3.{idx}. {name.upper()}")
            buf.append('')
            buf.append(f"3.{idx}.1. OBJECTIVE")
            buf.append(section.get('objective',''))
            buf.append('')
            buf.append(f"3.{idx}.2. PROCEDURE")
            buf.append(section.get('procedure',''))
            buf.append('')
            buf.append(f"3.{idx}.3. ACCEPTANCE CRITERIA")
            buf.append(section.get('acceptance',''))
            buf.append('')
            buf.append(f"3.{idx}.4. DATA REQUIREMENTS")
            buf.append(f"Number of determinations required: {section.get('dataPoints',0)}")
        buf.append('')
        buf.append('END OF PROTOCOL')
        return "\n".join(buf)
    text = _format(protocol)
    file_obj = io.BytesIO()
    file_obj.write(text.encode('utf-8'))
    file_obj.seek(0)
    product_name = (protocol.get('header', {}).get('productName','Protocol') or 'Protocol').replace(' ', '_')
    filename = f"AMV_Protocol_{product_name}.txt"
    return send_file(file_obj, as_attachment=True, download_name=filename, mimetype='text/plain')

@amv_bp.route('/api/generate-smiles', methods=['POST'])
def generate_smiles():
    """Generate SMILES notation from active ingredient name"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        ingredient_name = data.get('ingredient_name', '').strip()
        
        if not ingredient_name:
            return jsonify({'error': 'Ingredient name is required'}), 400
        
        # Generate SMILES using the service
        chemical_info = smiles_generator.get_chemical_info(ingredient_name)
        
        if chemical_info:
            return jsonify({
                'success': True,
                'ingredient_name': ingredient_name,
                'smiles': chemical_info.get('smiles', ''),
                'molecular_formula': chemical_info.get('molecular_formula', ''),
                'molecular_weight': chemical_info.get('molecular_weight', 0),
                'isomeric_smiles': chemical_info.get('isomeric_smiles', ''),
                'canonical_smiles': chemical_info.get('canonical_smiles', '')
            })
        else:
            # Try to search for alternatives
            alternatives = smiles_generator.search_chemical_alternatives(ingredient_name)
            
            return jsonify({
                'success': False,
                'ingredient_name': ingredient_name,
                'error': 'No chemical information found for this ingredient',
                'alternatives': alternatives or []
            })
            
    except Exception as e:
        current_app.logger.error(f"Error generating SMILES: {str(e)}")
        return jsonify({'error': f'Failed to generate SMILES: {str(e)}'}), 500

@amv_bp.route('/api/generate-structure', methods=['POST'])
def generate_chemical_structure():
    """Generate chemical structure image from SMILES"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        smiles = data.get('smiles', '').strip()
        
        if not smiles:
            return jsonify({'error': 'SMILES notation is required'}), 400
        
        # Import the chemical structure service
        from services.chemical_structure_service import chemical_structure_generator
        
        # Generate structure image
        result = chemical_structure_generator.generate_structure_with_properties(
            smiles, 
            input_type='smiles',
            width=400, 
            height=300
        )
        
        if result['success'] and result['image']:
            # Convert image to base64 for JSON response
            import base64
            image_data = result['image'].getvalue()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return jsonify({
                'success': True,
                'smiles': smiles,
                'image': f"data:image/png;base64,{image_base64}",
                'properties': result.get('properties', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate structure')
            })
            
    except Exception as e:
        current_app.logger.error(f"Error generating chemical structure: {str(e)}")
        return jsonify({'error': f'Failed to generate structure: {str(e)}'}), 500

@amv_bp.route('/extract-method', methods=['POST'])
def extract_method_from_pdf():
    """Extract method parameters from uploaded PDF"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        if 'method_pdf' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['method_pdf']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
        
        # Create upload directory if it doesn't exist
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        
        # Save file
        file.save(filepath)
        
        # Extract data from PDF
        extractor = MethodPDFExtractor(filepath)
        extracted_data = extractor.extract_method_data()
        
        # Clean up file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({
            'success': True,
            'data': extracted_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in PDF extraction: {str(e)}")
        return jsonify({'error': f'PDF extraction failed: {str(e)}'}), 500

@amv_bp.route('/verification/upload', methods=['POST'])
def upload_verification_files():
    """Upload Excel + PDF, process and stream AMV Verification Protocol DOCX"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        if 'excel_file' not in request.files or 'pdf_file' not in request.files:
            return jsonify({'error': 'Both files are required'}), 400

        excel_file = request.files['excel_file']
        pdf_file = request.files['pdf_file']
        if excel_file.filename == '' or pdf_file.filename == '':
            return jsonify({'error': 'No files selected'}), 400

        # Validate extensions
        excel_ext = os.path.splitext(excel_file.filename)[1].lower()
        pdf_ext = os.path.splitext(pdf_file.filename)[1].lower()
        if excel_ext not in ['.xlsx', '.xls']:
            return jsonify({'error': 'Invalid Excel file. Allowed: .xlsx, .xls'}), 400
        if pdf_ext != '.pdf':
            return jsonify({'error': 'Invalid PDF file. Allowed: .pdf'}), 400

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        excel_path = os.path.join(upload_folder, secure_filename(excel_file.filename))
        pdf_path = os.path.join(upload_folder, secure_filename(pdf_file.filename))
        excel_file.save(excel_path)
        pdf_file.save(pdf_path)

        try:
            buffer, method_tag = analytical_method_verification_service.generate_protocol_from_files(excel_path, pdf_path)
        finally:
            # Clean up saved files regardless of success
            try:
                if os.path.exists(excel_path):
                    os.remove(excel_path)
            except Exception:
                pass
            try:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except Exception:
                pass

        if buffer is None:
            return jsonify({'error': 'Failed to process files. Ensure the PDF has extractable text and the Excel contains recognizable sheets like Precision/Linearity/Accuracy.'}), 422

        filename = f"AMV_Protocol_{method_tag}_{datetime.now().strftime('%Y%m%d')}.docx"
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Error generating verification protocol: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f"Server error: {str(e)}"}), 500

@amv_bp.route('/verification/create', methods=['POST'])
def create_amv_verification():
    """Create new AMV Verification document"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        # Create main document
        document = Document(
            user_id=session['user_id'],
            company_id=data.get('company_id'),
            document_type='AMV_VERIFICATION',
            document_number=data.get('protocol_number'),
            title=f"AMV Verification - {data.get('product_name')}",
            status='draft'
        )
        db.session.add(document)
        db.session.flush()  # Get the document ID
        
        # Create AMV Verification details
        amv_verification = AMVVerificationDocument(
            document_id=document.id,
            product_name=data.get('product_name'),
            active_ingredient=data.get('active_ingredient'),
            label_claim=data.get('label_claim'),
            test_method=data.get('test_method'),
            company_name=data.get('company_name'),
            company_location=data.get('company_location'),
            protocol_number=data.get('protocol_number'),
            specification_range=data.get('specification_range'),
            wavelength=data.get('wavelength'),
            molecular_weight=data.get('molecular_weight'),
            molecular_formula=data.get('molecular_formula'),
            smiles=data.get('smiles'),
            prepared_by_name=data.get('prepared_by_name'),
            prepared_by_dept=data.get('prepared_by_dept'),
            reviewed_by_name=data.get('reviewed_by_name'),
            reviewed_by_dept=data.get('reviewed_by_dept')
        )
        
        # Set JSON data
        amv_verification.set_method_parameters(data.get('method_parameters', {}))
        amv_verification.set_selected_equipment(data.get('selected_equipment', []))
        amv_verification.set_selected_glass_materials(data.get('selected_glass_materials', []))
        amv_verification.set_selected_reagents(data.get('selected_reagents', []))
        amv_verification.set_selected_reference(data.get('selected_reference', {}))
        amv_verification.set_validation_parameters(data.get('validation_parameters', []))
        
        db.session.add(amv_verification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'document_id': document.id,
            'message': 'AMV Verification created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@amv_bp.route('/verification/<int:document_id>')
def get_amv_verification(document_id):
    """Get AMV Verification details"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        document = Document.query.filter_by(
            id=document_id, 
            user_id=session['user_id'],
            document_type='AMV_VERIFICATION'
        ).first()
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        amv_verification = document.amv_verification_details
        
        return jsonify({
            'success': True,
            'document': {
                'id': document.id,
                'document_number': document.document_number,
                'title': document.title,
                'status': document.status,
                'created_at': document.created_at.isoformat()
            },
            'amv_verification': {
                'product_name': amv_verification.product_name,
                'active_ingredient': amv_verification.active_ingredient,
                'label_claim': amv_verification.label_claim,
                'test_method': amv_verification.test_method,
                'company_name': amv_verification.company_name,
                'protocol_number': amv_verification.protocol_number,
                'specification_range': amv_verification.specification_range,
                'wavelength': amv_verification.wavelength,
                'molecular_weight': amv_verification.molecular_weight,
                'molecular_formula': amv_verification.molecular_formula,
                'smiles': amv_verification.smiles,
                'method_parameters': amv_verification.get_method_parameters(),
                'selected_equipment': amv_verification.get_selected_equipment(),
                'selected_glass_materials': amv_verification.get_selected_glass_materials(),
                'selected_reagents': amv_verification.get_selected_reagents(),
                'selected_reference': amv_verification.get_selected_reference(),
                'validation_parameters': amv_verification.get_validation_parameters(),
                'prepared_by_name': amv_verification.prepared_by_name,
                'prepared_by_dept': amv_verification.prepared_by_dept,
                'reviewed_by_name': amv_verification.reviewed_by_name,
                'reviewed_by_dept': amv_verification.reviewed_by_dept
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



def get_amv_documents_count(user_id):
    """Get count of AMV documents for a user"""
    return Document.query.filter_by(
        user_id=user_id, 
        document_type='AMV'
    ).count()

def get_amv_verification_count(user_id):
    """Get count of AMV Verification documents for a user"""
    return Document.query.filter_by(
        user_id=user_id, 
        document_type='AMV_VERIFICATION'
    ).count()



@amv_bp.route('/verification/<int:document_id>/download')
def download_verification_protocol(document_id):
    """Download AMV Verification Protocol"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        # Get document and validate ownership
        document = Document.query.filter_by(
            id=document_id, 
            user_id=session['user_id'],
            document_type='AMV_VERIFICATION'
        ).first()
        
        if not document:
            flash('Document not found', 'error')
            return redirect(url_for('dashboard.user_dashboard'))
        
        if not document.generated_doc_url or not os.path.exists(document.generated_doc_url):
            flash('Protocol not generated yet.', 'error')
            return redirect(url_for('amv_bp.view_amv_verification', document_id=document_id))
        
        # Get AMV verification details for filename
        amv_verification = AMVVerificationDocument.query.filter_by(document_id=document_id).first()
        filename = f"AMV_Verification_Protocol_{amv_verification.product_name.replace(' ', '_')}.docx" if amv_verification else "AMV_Verification_Protocol.docx"
        
        return send_file(
            document.generated_doc_url,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error downloading verification protocol: {str(e)}")
        flash(f'Error downloading protocol: {str(e)}', 'error')
        return redirect(url_for('amv_bp.view_amv_verification', document_id=document_id))





@amv_bp.route('/verification/list')
def list_amv_verification_documents():
    """List all AMV Verification documents for the user"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    documents = Document.query.filter_by(
        user_id=user_id, 
        document_type='AMV_VERIFICATION'
    ).order_by(Document.created_at.desc()).all()
    
    return render_template('amv_verification_list.html', documents=documents)


@amv_bp.route('/verification/<int:document_id>')
def view_amv_verification(document_id):
    """View AMV Verification document details"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('dashboard.user_dashboard'))
    
    if document.document_type != 'AMV_VERIFICATION':
        flash('Document not found', 'error')
        return redirect(url_for('dashboard.user_dashboard'))
    
    metadata = {}
    if document.document_metadata:
        try:
            metadata = json.loads(document.document_metadata)
        except:
            metadata = {}
    
    # Get AMV verification details
    amv_verification = AMVVerificationDocument.query.filter_by(document_id=document_id).first()
    
    return render_template('view_amv_verification.html', 
                         document=document, 
                         metadata=metadata, 
                         amv_verification=amv_verification)


