import os
import json
import re
import PyPDF2
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, jsonify, session, send_file
from werkzeug.utils import secure_filename
from models import Document, User, Company, AMVDocument
from database import db
from datetime import datetime
from services.cloudinary_service import upload_file
from services.method_extraction_service import method_extraction_service
from services.amv_report_service import AMVReportGenerator, extract_method_from_pdf, process_raw_data_file, calculate_validation_statistics
from services.smiles_service import smiles_generator
from utils.validators import validate_file_type
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database models for company settings
Base = declarative_base()

class Equipment(Base):
    __tablename__ = 'equipment'
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    name = Column(String(200))
    code = Column(String(100))
    brand = Column(String(100))
    verification_frequency = Column(String(200))
    last_calibration = Column(String(50))
    next_calibration = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class GlassMaterial(Base):
    __tablename__ = 'glass_materials'
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    name = Column(String(200))
    characteristics = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

class OtherMaterial(Base):
    __tablename__ = 'other_materials'
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    name = Column(String(200))
    characteristics = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

class Reagent(Base):
    __tablename__ = 'reagents'
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    name = Column(String(200))
    batch = Column(String(100))
    expiry_date = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class ReferenceProduct(Base):
    __tablename__ = 'reference_products'
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    standard_type = Column(String(100))
    standard_name = Column(String(200))
    code = Column(String(100))
    potency = Column(String(50))
    due_date = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

# Initialize database
engine = create_engine('sqlite:///amv_company_settings.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

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
    
    session_db = Session()
    company_id = session.get('user_id', 1)
    
    if request.method == 'POST':
        try:
            # Validate method PDF upload
            if 'method_pdf' not in request.files:
                flash('Method PDF is required. Please upload a method analysis PDF.', 'error')
                return redirect(url_for('amv.create_amv_form'))
            
            method_pdf = request.files['method_pdf']
            if method_pdf.filename == '':
                flash('Method PDF is required. Please select a method analysis PDF file.', 'error')
                return redirect(url_for('amv.create_amv_form'))
            
            if not method_pdf.filename.lower().endswith('.pdf'):
                flash('Please upload a valid PDF file for method analysis.', 'error')
                return redirect(url_for('amv.create_amv_form'))
            
            # Get selected items from database
            selected_equipment_ids = request.form.getlist('selected_equipment')
            selected_glass_ids = request.form.getlist('selected_glass_materials')
            selected_other_ids = request.form.getlist('selected_other_materials')
            selected_reagent_ids = request.form.getlist('selected_reagents')
            selected_reference_id = request.form.get('selected_reference')
            
            # Fetch actual data from database
            equipment_data = []
            for eq_id in selected_equipment_ids:
                equipment = session_db.query(Equipment).filter_by(id=eq_id).first()
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
                glass = session_db.query(GlassMaterial).filter_by(id=gm_id).first()
                if glass:
                    glass_materials.append({
                        'name': glass.name,
                        'characteristics': glass.characteristics
                    })
            
            other_materials = []
            for om_id in selected_other_ids:
                other = session_db.query(OtherMaterial).filter_by(id=om_id).first()
                if other:
                    other_materials.append({
                        'name': other.name,
                        'characteristics': other.characteristics
                    })
            
            reagents = []
            for r_id in selected_reagent_ids:
                reagent = session_db.query(Reagent).filter_by(id=r_id).first()
                if reagent:
                    reagents.append({
                        'name': reagent.name,
                        'batch': reagent.batch,
                        'expiry': reagent.expiry_date
                    })
            
            reference_product = None
            if selected_reference_id:
                ref = session_db.query(ReferenceProduct).filter_by(id=selected_reference_id).first()
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
                'other_materials': other_materials or [],
                'reagents': reagents or [],
                'reference_product': reference_product or {}
            }
            
            # Process method PDF upload
            method_pdf_filename = secure_filename(method_pdf.filename)
            method_pdf_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), method_pdf_filename)
            
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
            # Try multiple approaches to find the company
            company_name = form_data.get('company_name', '')
            company = None
            
            # First try: exact name match
            if company_name:
                company = Company.query.filter_by(name=company_name, user_id=session.get('user_id')).first()
            
            # Second try: if not found, get the first company for this user
            if not company:
                company = Company.query.filter_by(user_id=session.get('user_id')).first()
            
            # Debug logging
            current_app.logger.info(f"Company name from form: '{company_name}'")
            current_app.logger.info(f"Found company: {company}")
            if company:
                current_app.logger.info(f"Company logo URL: {company.logo_url}")
                current_app.logger.info(f"Company address: {company.address}")
            
            company_data = {
                'name': company.name if company else company_name or 'Company',
                'address': company.address if company else '',
                'logo_url': company.logo_url if company else None
            }
            
            current_app.logger.info(f"Company data being passed: {company_data}")
            
            generator = AMVReportGenerator(form_data, company_data=company_data)
            report_path = generator.generate_report(output_path)
            
            session_db.close()
            
            flash('AMV Report generated successfully using mathematical calculations!', 'success')
            return send_file(
                report_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
        except Exception as e:
            session_db.close()
            current_app.logger.error(f"Error generating AMV report: {str(e)}")
            current_app.logger.error(f"Form data: {form_data}")
            flash(f'Error generating report: {str(e)}', 'error')
            return redirect(url_for('amv_bp.create_amv_form'))

    # GET request - load data for selection
    equipment_list = session_db.query(Equipment).filter_by(company_id=company_id).all()
    glass_materials_list = session_db.query(GlassMaterial).filter_by(company_id=company_id).all()
    other_materials_list = session_db.query(OtherMaterial).filter_by(company_id=company_id).all()
    reagents_list = session_db.query(Reagent).filter_by(company_id=company_id).all()
    references_list = session_db.query(ReferenceProduct).filter_by(company_id=company_id).all()
    
    # Get user and companies for dropdown
    user = User.query.get(session.get('user_id'))
    companies = Company.query.filter_by(user_id=session.get('user_id')).all()
    
    session_db.close()
    
    return render_template('create_amv.html',
                         user=user,
                         companies=companies,
                         equipment_list=equipment_list,
                         glass_materials_list=glass_materials_list,
                         other_materials_list=other_materials_list,
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
            'instrument_params': amv_details.get_instrument_params()
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
    """Delete AMV document"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        # Get document and validate ownership
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document or document.document_type != 'AMV':
            flash('Document not found', 'error')
            return redirect(url_for('amv_bp.list_amv_documents'))
        
        # Delete generated file if exists
        if document.generated_doc_url and os.path.exists(document.generated_doc_url):
            os.remove(document.generated_doc_url)
        
        # Delete AMV details
        amv_details = AMVDocument.query.filter_by(document_id=document_id).first()
        if amv_details:
            db.session.delete(amv_details)
        
        # Delete document
        db.session.delete(document)
        db.session.commit()
        
        flash('AMV document deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting AMV document: {str(e)}")
        flash(f'Error deleting document: {str(e)}', 'error')
    
    return redirect(url_for('amv_bp.list_amv_documents'))

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
    
    session_db = Session()
    company_id = session.get('user_id', 1)  # Get from current user session
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            equipment = Equipment(
                company_id=company_id,
                name=request.form.get('name'),
                code=request.form.get('code'),
                brand=request.form.get('brand'),
                verification_frequency=request.form.get('verification_frequency'),
                last_calibration=request.form.get('last_calibration'),
                next_calibration=request.form.get('next_calibration')
            )
            session_db.add(equipment)
            session_db.commit()
            flash('Equipment added successfully!', 'success')
        
        elif action == 'delete':
            equip_id = request.form.get('equipment_id')
            equipment = session_db.query(Equipment).filter_by(id=equip_id).first()
            if equipment:
                session_db.delete(equipment)
                session_db.commit()
                flash('Equipment deleted successfully!', 'success')
    
    equipment_list = session_db.query(Equipment).filter_by(company_id=company_id).all()
    session_db.close()
    
    return render_template('manage_equipment.html', equipment_list=equipment_list)

@amv_bp.route('/settings/materials', methods=['GET', 'POST'])
def manage_materials():
    """Manage glass and other materials"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    session_db = Session()
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
                session_db.add(material)
            elif material_type == 'other':
                material = OtherMaterial(
                    company_id=company_id,
                    name=request.form.get('name'),
                    characteristics=request.form.get('characteristics')
                )
                session_db.add(material)
            session_db.commit()
            flash(f'{material_type.title()} material added successfully!', 'success')
    
    glass_materials = session_db.query(GlassMaterial).filter_by(company_id=company_id).all()
    other_materials = session_db.query(OtherMaterial).filter_by(company_id=company_id).all()
    session_db.close()
    
    return render_template('manage_materials.html', 
                         glass_materials=glass_materials,
                         other_materials=other_materials)

@amv_bp.route('/settings/reagents', methods=['GET', 'POST'])
def manage_reagents():
    """Manage reagents database"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    session_db = Session()
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
            session_db.add(reagent)
            session_db.commit()
            flash('Reagent added successfully!', 'success')
    
    reagents = session_db.query(Reagent).filter_by(company_id=company_id).all()
    session_db.close()
    
    return render_template('manage_reagents.html', reagents=reagents)

@amv_bp.route('/settings/reference-products', methods=['GET', 'POST'])
def manage_reference_products():
    """Manage reference products"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    session_db = Session()
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
            session_db.add(reference)
            session_db.commit()
            flash('Reference product added successfully!', 'success')
    
    references = session_db.query(ReferenceProduct).filter_by(company_id=company_id).all()
    session_db.close()
    
    return render_template('manage_reference_products.html', references=references)

@amv_bp.route('/test-extract', methods=['GET'])
def test_extract_route():
    """Test route to verify routing is working"""
    return jsonify({'success': True, 'message': 'Route is working'})

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