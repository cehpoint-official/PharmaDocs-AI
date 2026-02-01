"""
Process Validation Routes - Enhanced with PharmaDoc AI Integration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from database import db
from models import (
    User, PVP_Template, PVP_Criteria, PVP_Equipment, PVP_Material,
    PVP_Extracted_Stage, PVR_Report, PVR_Data, PVR_Stage_Result,
    PV_Stage_Template
)
from services.process_validation_service import (
    EnhancedPharmaDocAI, 
    EnhancedDocumentParser,
    EnhancedPDFGenerator,
    ProductType,
    ProductInfo,
    Config
)

import logging
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

pv_routes = Blueprint('pv', __name__, url_prefix='/pv')

UPLOAD_FOLDER = 'uploads/pv_documents'
REPORT_FOLDER = 'uploads/pvr_reports'
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, folder=UPLOAD_FOLDER):
    """Save uploaded file with secure filename"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(folder, unique_filename)
        file.save(filepath)
        return filepath, unique_filename
    return None, None
import zipfile
import io
import json
from flask import send_file

@pv_routes.route('/upload_ai', methods=['GET', 'POST'])
def upload_ai_validation():
    """Upload STP and MFR documents for AI-powered validation processing"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('upload_ai_validation.html', 
                             product_types=[pt.value for pt in ProductType],
                             user=user)
    
    # Handle POST - file uploads
    try:
        # Get form data
        product_name = request.form.get('product_name', '').strip()
        dosage_form = request.form.get('dosage_form', '').strip()
        
        if not all([product_name, dosage_form]):
            flash('Product name and dosage form are required', 'error')
            return redirect(request.url)
        
        # Check file uploads
        if 'stp_file' not in request.files or 'mfr_file' not in request.files:
            flash('Both STP and MFR files are required', 'error')
            return redirect(request.url)
        
        stp_file = request.files['stp_file']
        mfr_file = request.files['mfr_file']
        
        if stp_file.filename == '' or mfr_file.filename == '':
            flash('Please select both STP and MFR files', 'error')
            return redirect(request.url)
        
        # Save uploaded files
        stp_path, stp_filename = save_uploaded_file(stp_file)
        mfr_path, mfr_filename = save_uploaded_file(mfr_file)
        
        if not stp_path or not mfr_path:
            flash('Invalid file format. Only PDF and TXT files are allowed', 'error')
            return redirect(request.url)
        
        logger.info(f"Files saved: STP={stp_path}, MFR={mfr_path}")
        logger.info(f"Processing for: {product_name}, {dosage_form}")
        
        # Initialize ENHANCED PharmaDoc AI
        api_key = os.environ.get('GEMINI_API_KEY')
        
        if not api_key:
            flash('⚠️ Gemini API key not configured. Using fallback parsing...', 'warning')
            return redirect(url_for('pv.upload_pvp_fallback', 
                                  product_name=product_name,
                                  dosage_form=dosage_form,
                                  stp_path=stp_path,
                                  mfr_path=mfr_path))
        
        try:
            flash('Processing documents with Enhanced AI... This may take a minute.', 'info')
            logger.info("Initializing Enhanced PharmaDocAI...")
            
            # Use Enhanced PharmaDoc AI
            pharmadoc = EnhancedPharmaDocAI(api_key)
            
            # Process documents with enhanced system
            logger.info("Starting enhanced document processing...")
            results = pharmadoc.process_documents(
                product_name=product_name,
                dosage_form=dosage_form,
                stp_pdf_path=stp_path,
                mfr_pdf_path=mfr_path
            )
            
            logger.info(f"Enhanced AI processing completed.")
            
            # 2. GENERATE ENHANCED PDFS
            pdf_gen = EnhancedPDFGenerator()
            
            # Generate comprehensive PVP PDF
            pvp_pdf_buffer = pdf_gen.generate_pvp(results['pvp'])
            
            # Generate comprehensive PVR PDF
            pvr_pdf_buffer = pdf_gen.generate_pvr(results['pvr'])
            
            # 3. ZIP AND DOWNLOAD
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                
                # Save PVP as PDF
                zf.writestr('Process_Validation_Protocol.pdf', pvp_pdf_buffer.getvalue())
                
                # Save PVR as PDF
                zf.writestr('Process_Validation_Report.pdf', pvr_pdf_buffer.getvalue())
                
                # Save all generated text files if available
                try:
                    # Export all text documents
                    output_dir = tempfile.mkdtemp()
                    pharmadoc.export_results(output_dir)
                    
                    # Add all text files to zip
                    for file_name in os.listdir(output_dir):
                        file_path = os.path.join(output_dir, file_name)
                        if os.path.isfile(file_path):
                            with open(file_path, 'rb') as f:
                                zf.writestr(file_name, f.read())
                except Exception as export_error:
                    logger.warning(f"Could not export text files: {export_error}")
                    # Just add JSON as fallback
                    zf.writestr('validation_data.json', json.dumps(results, indent=4, default=str))
            
            memory_file.seek(0)
            
            # Save to database for history
            try:
                template_name = f"{product_name} - AI Generated {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create PVP template record
                pvp_template = PVP_Template(
                    template_name=template_name,
                    original_filepath=stp_path,
                    user_id=session['user_id'],
                    product_name=product_name,
                    product_type=dosage_form,
                    batch_size=results.get('pvp', {}).get('mfr_summary', {}).get('batch_size', '')
                )
                db.session.add(pvp_template)
                db.session.flush()
                
                # Create PVR report record
                pvr_report = PVR_Report(
                    pvp_template_id=pvp_template.id,
                    user_id=session['user_id'],
                    status='AI Generated',
                    protocol_number=results.get('pvp', {}).get('protocol_number', '')
                )
                db.session.add(pvr_report)
                
                # Save the zip file
                zip_filename = f"{product_name.replace(' ', '_')}_AI_Validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(REPORT_FOLDER, zip_filename)
                
                with open(zip_path, 'wb') as f:
                    f.write(memory_file.getvalue())
                
                pvr_report.pdf_filepath = zip_path
                db.session.commit()
                
                flash(f'✅ Enhanced validation completed! Generated comprehensive documents.', 'success')
                
                return render_template('ai_validation_complete.html',
                                    template=pvp_template,
                                    report=pvr_report,
                                    results=results,
                                    user=user)
                
            except Exception as db_error:
                logger.error(f"Database save error: {db_error}")
                # Still provide download even if DB save fails
                flash('✅ Documents generated! (Note: History not saved due to database error)', 'warning')
            
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'{product_name.replace(" ", "_")}_Enhanced_Validation_Package.zip'
            )
            
        except Exception as ai_error:
            logger.error(f"Enhanced AI processing error: {str(ai_error)}", exc_info=True)
            
            # Try fallback parsing without AI
            flash(f'⚠️ Enhanced AI processing failed: {str(ai_error)[:100]}... Using basic parsing...', 'warning')
            return redirect(url_for('pv.upload_pvp_fallback', 
                                  product_name=product_name,
                                  dosage_form=dosage_form,
                                  stp_path=stp_path,
                                  mfr_path=mfr_path))
        
    except Exception as e:
        logger.error(f"Error in AI validation upload: {str(e)}", exc_info=True)
        flash(f'❌ Error processing validation request: {str(e)}', 'error')
        return redirect(url_for('pv.upload_ai_validation'))

@pv_routes.route('/upload_fallback', methods=['GET', 'POST'])
def upload_pvp_fallback():
    """Fallback upload without AI processing"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        # Get parameters from query string or form
        product_name = request.args.get('product_name', '')
        dosage_form = request.args.get('dosage_form', '')
        stp_path = request.args.get('stp_path', '')
        mfr_path = request.args.get('mfr_path', '')
        template_name = request.args.get('template_name', '')
        
        return render_template('upload_pvp_fallback.html',
                             product_name=product_name,
                             dosage_form=dosage_form,
                             stp_path=stp_path,
                             mfr_path=mfr_path,
                             template_name=template_name,
                             user=user)
    
    # Handle POST - manual data entry
    try:
        template_name = request.form.get('template_name', '').strip()
        product_name = request.form.get('product_name', '').strip()
        dosage_form = request.form.get('dosage_form', '').strip()
        batch_size = request.form.get('batch_size', '').strip()
        
        if not template_name or not product_name or not dosage_form:
            flash('Template name, product name, and dosage form are required', 'error')
            return redirect(request.url)
        
        # Create base template data
        template_data = {
            'template_name': template_name,
            'original_filepath': request.form.get('stp_path', ''),
            'user_id': session['user_id'],
            'product_name': product_name,
            'product_type': dosage_form,
            'batch_size': batch_size
        }
        
        # Add optional fields if they exist
        optional_fields = {
            'stp_filepath': request.form.get('stp_path', ''),
            'mfr_filepath': request.form.get('mfr_path', '')
        }
        
        for field_name, field_value in optional_fields.items():
            if hasattr(PVP_Template, field_name):
                template_data[field_name] = field_value
        
        pvp_template = PVP_Template(**template_data)
        
        db.session.add(pvp_template)
        db.session.flush()
        
        # Rest of your code remains the same...
        # [Keep the existing equipment, materials, stages, criteria code]
        
        db.session.commit()
        
        flash(f'✅ Basic template created for {product_name}. Please add detailed information.', 'success')
        return redirect(url_for('pv.view_pvp_template', template_id=pvp_template.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in fallback upload: {e}", exc_info=True)
        flash(f'Error creating template: {str(e)}', 'error')
        return redirect(url_for('pv.upload_ai_validation'))
@pv_routes.route('/ai_results/<int:template_id>/<int:report_id>')
def view_ai_results(template_id, report_id):
    """View AI-generated validation results"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    template = PVP_Template.query.get_or_404(template_id)
    report = PVR_Report.query.get_or_404(report_id)
    
    # Load AI-extracted data
    extracted_data = {}
    if template.extracted_data:
        try:
            extracted_data = json.loads(template.extracted_data)
        except:
            extracted_data = {}
    
    # Get file paths for downloads
    output_dir = os.path.dirname(report.pdf_filepath) if report.pdf_filepath else ''
    pvp_text_path = os.path.join(output_dir, "Process_Validation_Protocol.txt") if output_dir else ''
    pvr_text_path = os.path.join(output_dir, "Process_Validation_Report.txt") if output_dir else ''
    json_data_path = os.path.join(output_dir, "validation_data.json") if output_dir else ''
    
    return render_template('view_ai_results.html',
                         template=template,
                         report=report,
                         extracted_data=extracted_data,
                         pvp_text_path=pvp_text_path,
                         pvr_text_path=pvr_text_path,
                         json_data_path=json_data_path,
                         user=user)

@pv_routes.route('/download_ai_file/<int:template_id>/<file_type>')
def download_ai_file(template_id, file_type):
    """Download AI-generated files"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    template = PVP_Template.query.get_or_404(template_id)
    
    # Determine file path based on file type
    file_path = None
    filename = f"{template.product_name.replace(' ', '_')}_{file_type}"
    
    if file_type == 'pvp' and hasattr(template, 'extracted_data'):
        try:
            extracted_data = json.loads(template.extracted_data)
            pvp_data = extracted_data.get('pvp', {})
            protocol_no = pvp_data.get('protocol_number', 'PVP').replace('/', '_')
            
            # Generate PVP text file on the fly
            generator = ValidationDocumentGenerator()
            output_dir = tempfile.mkdtemp()
            file_path = os.path.join(output_dir, f"{protocol_no}.txt")
            
            generator.export_pvp_to_text(pvp_data, file_path)
            filename = f"{protocol_no}.txt"
            
        except Exception as e:
            logger.error(f"Error generating PVP file: {e}")
            flash('Error generating PVP file', 'error')
            return redirect(url_for('pv.view_ai_results', template_id=template_id))
    
    elif file_type == 'pvr' and hasattr(template, 'extracted_data'):
        try:
            extracted_data = json.loads(template.extracted_data)
            pvr_data = extracted_data.get('pvr', {})
            pvp_data = extracted_data.get('pvp', {})
            report_no = pvr_data.get('report_number', 'PVR').replace('/', '_')
            
            # Generate PVR text file on the fly
            generator = ValidationDocumentGenerator()
            output_dir = tempfile.mkdtemp()
            file_path = os.path.join(output_dir, f"{report_no}.txt")
            
            batch_results = extracted_data.get('batch_results', [])
            generator.export_pvr_to_text(pvr_data, file_path)
            filename = f"{report_no}.txt"
            
        except Exception as e:
            logger.error(f"Error generating PVR file: {e}")
            flash('Error generating PVR file', 'error')
            return redirect(url_for('pv.view_ai_results', template_id=template_id))
    
    elif file_type == 'json' and template.extracted_data:
        # Create JSON file
        output_dir = tempfile.mkdtemp()
        file_path = os.path.join(output_dir, "validation_data.json")
        with open(file_path, 'w') as f:
            f.write(template.extracted_data)
        filename = "validation_data.json"
    
    if not file_path or not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('pv.view_ai_results', template_id=template_id))
    
    return send_file(file_path, as_attachment=True, download_name=filename)

@pv_routes.route('/api/process_validation', methods=['POST'])
def api_process_validation():
    """API endpoint for processing validation documents"""
    
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        product_name = data.get('product_name')
        dosage_form = data.get('dosage_form')
        stp_path = data.get('stp_path')
        mfr_path = data.get('mfr_path')
        
        if not all([product_name, dosage_form, stp_path, mfr_path]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Initialize PharmaDoc AI
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'API key not configured'}), 500
        
        pharmadoc = PharmaDocAI(api_key)
        
        # Process documents
        results = pharmadoc.process_documents(
            product_name=product_name,
            dosage_form=dosage_form,
            stp_pdf_path=stp_path,
            mfr_pdf_path=mfr_path
        )
        
        return jsonify({
            'status': 'success',
            'data': results,
            'summary': pharmadoc.get_processing_summary()
        })
        
    except Exception as e:
        logger.error(f"API error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Keep existing routes for backward compatibility
@pv_routes.route('/upload', methods=['GET', 'POST'])
def upload_pvp():
    """Legacy upload route - redirect to new AI upload"""
    return redirect(url_for('pv.upload_ai_validation'))

# Other existing routes remain mostly the same...
@pv_routes.route('/templates')
def list_templates():
    """List all uploaded PVP templates"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    templates = PVP_Template.query.filter_by(user_id=session['user_id']).order_by(
        PVP_Template.created_at.desc()
    ).all()
    
    return render_template('pvp_templates_list.html', templates=templates, user=user)

@pv_routes.route('/template/<int:template_id>')
def view_pvp_template(template_id):
    """View PVP template details"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    template = PVP_Template.query.get_or_404(template_id)
    
    # Get all related data
    equipment = PVP_Equipment.query.filter_by(pvp_template_id=template_id).all()
    materials = PVP_Material.query.filter_by(pvp_template_id=template_id).all()
    stages = PVP_Extracted_Stage.query.filter_by(pvp_template_id=template_id).order_by(
        PVP_Extracted_Stage.stage_number
    ).all()
    criteria = PVP_Criteria.query.filter_by(pvp_template_id=template_id).all()
    
    return render_template('view_pvp_template.html',
                         template=template,
                         equipment=equipment,
                         materials=materials,
                         stages=stages,
                         criteria=criteria,
                         user=user)

@pv_routes.route('/generate/<int:template_id>', methods=['GET', 'POST'])
def generate_pvr(template_id):
    """Generate PVR report from PVP template"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    template = PVP_Template.query.get_or_404(template_id)
    
    if request.method == 'GET':
        # Get stages and criteria for form
        stages = PVP_Extracted_Stage.query.filter_by(pvp_template_id=template_id).order_by(
            PVP_Extracted_Stage.stage_number
        ).all()
        criteria = PVP_Criteria.query.filter_by(pvp_template_id=template_id).all()
        return render_template('generate_pvr.html',
                             template=template,
                             stages=stages,
                             criteria=criteria,
                             user=user)
    
    # Handle POST - generate report (existing logic)
    # ... [keep existing generation logic] ...

@pv_routes.route('/report/<int:report_id>')
def view_pvr(report_id):
    """View generated PVR report"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    report = PVR_Report.query.get_or_404(report_id)
    template = report.template
    batch_data = PVR_Data.query.filter_by(pvr_report_id=report_id).all()
    
    # Try to load extracted data if available
    extracted = {}
    if hasattr(report, 'extracted') and report.extracted:
        try:
            extracted = json.loads(report.extracted)
        except:
            extracted = {}
    
    report_payload = {
        "id": report.id,
        "created_at": getattr(report, "created_at", None),
        "status": getattr(report, "status", None),
        "template": template,
        "extracted": extracted,
        "batch_data": batch_data
    }
    
    return render_template(
        "view_pvr.html",
        report=report_payload,
        template=template,
        batch_data=batch_data,
        user=user
    )

# Download routes remain the same
@pv_routes.route('/download/<int:report_id>/pdf')
def download_pvr_pdf(report_id):
    """Download PVR PDF report"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    report = PVR_Report.query.get_or_404(report_id)
    
    if not report.pdf_filepath or not os.path.exists(report.pdf_filepath):
        flash('PDF report not found', 'error')
        return redirect(url_for('pv.view_pvr', report_id=report_id))
    
    return send_file(report.pdf_filepath, as_attachment=True)

@pv_routes.route('/download/<int:report_id>/word')
def download_pvr_word(report_id):
    """Download PVR Word report"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    report = PVR_Report.query.get_or_404(report_id)
    
    if not report.word_filepath or not os.path.exists(report.word_filepath):
        flash('Word report not found', 'error')
        return redirect(url_for('pv.view_pvr', report_id=report_id))
    
    return send_file(report.word_filepath, as_attachment=True)

@pv_routes.route('/dashboard')
def pv_dashboard():
    """Process Validation Dashboard"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    # Get statistics
    templates_count = PVP_Template.query.filter_by(user_id=session['user_id']).count()
    reports_count = PVR_Report.query.filter_by(user_id=session['user_id']).count()
    recent_templates = PVP_Template.query.filter_by(user_id=session['user_id'])\
        .order_by(PVP_Template.created_at.desc()).limit(5).all()
    recent_reports = PVR_Report.query.filter_by(user_id=session['user_id'])\
        .order_by(PVR_Report.created_at.desc()).limit(5).all()
    
    return render_template('pv_dashboard.html',
                         user=user,
                         templates_count=templates_count,
                         reports_count=reports_count,
                         recent_templates=recent_templates,
                         recent_reports=recent_reports)
