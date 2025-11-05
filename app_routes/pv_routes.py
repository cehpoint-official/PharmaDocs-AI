# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, send_file, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from database import db
from models import PVP_Template, PVP_Criteria, PVR_Report, PVR_Data, User
from services.pvp_ai_service import extract_pvp_criteria
from services.pvr_generator_service import generate_pvr_pdf

pv_bp = Blueprint('pv_bp', __name__, url_prefix='/pv')

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'pvp_templates')
REPORT_FOLDER = os.path.join(os.getcwd(), 'uploads', 'pvr_reports')

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== ROUTE 1: Upload PVP Template ====================
@pv_bp.route('/upload-template', methods=['GET', 'POST'])
def upload_pvp_template():
    """
    Upload PVP PDF, extract criteria using AI, save to database
    """
    if request.method == 'POST':
        try:
            # Get form data
            pvp_file = request.files.get('pvp_file')
            template_name = request.form.get('template_name', '').strip()
            
            # Get user_id from session
            user_id = session.get('user_id')
            if not user_id:
                flash('Please log in to upload templates.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Validation
            if not pvp_file or not template_name:
                flash('Template name and PDF file are required.', 'danger')
                return redirect(request.url)
            
            if not allowed_file(pvp_file.filename):
                flash('Only PDF files are allowed.', 'danger')
                return redirect(request.url)
            
            # Check for duplicate template name
            existing = PVP_Template.query.filter_by(template_name=template_name).first()
            if existing:
                flash(f'Template "{template_name}" already exists. Please use a different name.', 'danger')
                return redirect(request.url)
            
            # Save file
            filename = secure_filename(pvp_file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            pvp_file.save(filepath)
            
            print(f"✅ PVP file saved: {filepath}")
            
            # Create template record
            new_template = PVP_Template(
                template_name=template_name,
                original_filepath=filepath,
                user_id=user_id
            )
            db.session.add(new_template)
            db.session.commit()
            
            print(f"✅ Template created with ID: {new_template.id}")
            
            # Extract criteria using AI
            print("🤖 Starting AI extraction...")
            extracted_criteria = extract_pvp_criteria(filepath)
            
            print(f"✅ AI extracted {len(extracted_criteria)} criteria")
            
            # Save criteria to database
            for criterion in extracted_criteria:
                new_criterion = PVP_Criteria(
                    pvp_template_id=new_template.id,
                    test_id=criterion['test_id'],
                    test_name=criterion['test_name'],
                    acceptance_criteria=criterion['acceptance_criteria']
                )
                db.session.add(new_criterion)
            
            db.session.commit()
            
            flash(f'✅ Template "{template_name}" uploaded successfully! AI extracted {len(extracted_criteria)} test criteria.', 'success')
            return redirect(url_for('pv_bp.list_templates'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error uploading template: {str(e)}")
            flash(f'Error uploading template: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('upload_pvp.html')


# ==================== ROUTE 2: List PVP Templates ====================
@pv_bp.route('/templates', methods=['GET'])
def list_templates():
    """
    Show all uploaded PVP templates
    """
    templates = PVP_Template.query.order_by(PVP_Template.created_at.desc()).all()
    return render_template('pvp_templates_list.html', templates=templates)


# ==================== ROUTE 3: View Template Criteria ====================
@pv_bp.route('/template/<int:template_id>', methods=['GET'])
def view_template(template_id):
    """
    View a specific template and its extracted criteria
    """
    template = PVP_Template.query.get_or_404(template_id)
    criteria = PVP_Criteria.query.filter_by(pvp_template_id=template_id).all()
    return render_template('view_pvp_template.html', template=template, criteria=criteria)


# ==================== ROUTE 4: Generate PVR Form ====================
@pv_bp.route('/generate-pvr/<int:template_id>', methods=['GET', 'POST'])
def generate_pvr(template_id):
    """
    Form to enter batch data and generate PVR report
    """
    template = PVP_Template.query.get_or_404(template_id)
    criteria = PVP_Criteria.query.filter_by(pvp_template_id=template_id).all()
    
    if request.method == 'POST':
        try:
            user_id = session.get('user_id')
            if not user_id:
                flash('Please log in to generate reports.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Get form data
            product_name = request.form.get('product_name')
            batch_numbers = request.form.getlist('batch_number[]')  # Multiple batches
            
            # Create PVR Report record
            pvr_report = PVR_Report(
                pvp_template_id=template_id,
                user_id=user_id,
                status='Draft'
            )
            db.session.add(pvr_report)
            db.session.commit()
            
            # Save batch data
            for batch_no in batch_numbers:
                for criterion in criteria:
                    test_result = request.form.get(f'result_{criterion.test_id}_{batch_no}')
                    
                    if test_result:
                        pvr_data = PVR_Data(
                            pvr_report_id=pvr_report.id,
                            batch_number=batch_no,
                            test_id=criterion.test_id,
                            test_result=test_result
                        )
                        db.session.add(pvr_data)
            
            db.session.commit()
            
            # Generate PDF
            print("📄 Generating PVR PDF...")
            pdf_path = generate_pvr_pdf(pvr_report.id, product_name, template, criteria)

            print("Generating PVR Word document...")
            from services.pvr_word_generator_service import generate_pvr_word
            word_path = generate_pvr_word(pvr_report.id, product_name, template, criteria)
            
            # Update report with both file paths
            pvr_report.generated_filepath = pdf_path
            pvr_report_word_filepath = word_path 
            pvr_report.status = 'Generated'
            db.session.commit()
            
            flash('✅ PVR Report generated successfully! (PDF & Word)', 'success')
            return redirect(url_for('pv_bp.view_pvr', report_id=pvr_report.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error generating PVR: {str(e)}")
            flash(f'Error generating report: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('generate_pvr.html', template=template, criteria=criteria)


# ==================== ROUTE 5: View PVR Report ====================
@pv_bp.route('/report/<int:report_id>', methods=['GET'])
def view_pvr(report_id):
    """
    View generated PVR report details
    """
    report = PVR_Report.query.get_or_404(report_id)
    return render_template('view_pvr.html', report=report)


# ==================== ROUTE 6: Download PVR PDF ====================
@pv_bp.route('/download/<int:report_id>', methods=['GET'])
def download_pvr(report_id):
    """
    Download PVR PDF file
    """
    report = PVR_Report.query.get_or_404(report_id)
    
    if not report.generated_filepath or not os.path.exists(report.generated_filepath):
        flash('PDF file not found.', 'danger')
        return redirect(url_for('pv_bp.list_templates'))
    
    return send_file(
        report.generated_filepath,
        as_attachment=True,
        download_name=f"PVR_Report_{report.id}.pdf"
    )