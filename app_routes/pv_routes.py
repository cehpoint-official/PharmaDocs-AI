# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

"""
Process Validation Routes - Enhanced with comprehensive extraction
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, session

from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime
from database import db
from models import (
    PVP_Template, PVP_Criteria, PVP_Equipment, PVP_Material, 
    PVP_Extracted_Stage, PVR_Report, PVR_Data, PVR_Stage_Result,
    PV_Stage_Template
)
from services.enhanced_pvp_extraction_service import EnhancedPVPExtractor
from services.comprehensive_pvr_generator import ComprehensivePVRGenerator
from services.comprehensive_pvr_word_generator import ComprehensivePVRWordGenerator
import logging

logger = logging.getLogger(__name__)

pv_routes = Blueprint('pv', __name__, url_prefix='/pv')

UPLOAD_FOLDER = 'uploads/pvp'
REPORT_FOLDER = 'uploads/pvr_reports'

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


@pv_routes.route('/upload', methods=['GET', 'POST'])
def upload_pvp():
    """Upload and extract PVP document"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('upload_pvp.html')
    
    # Handle POST - file upload
    if 'pvp_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(request.url)
    
    file = request.files['pvp_file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(request.url)
    
    if not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed', 'error')
        return redirect(request.url)
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        logger.info(f"PVP uploaded: {filepath}")
        
        # Extract data using AI
        flash('Extracting data from PVP... This may take a minute.', 'info')
        extractor = EnhancedPVPExtractor(filepath)
        extracted_data = extractor.extract_all()
        
        # Create PVP Template record
        product_name = extracted_data['product_info'].get('product_name', 'Unknown Product')
        product_type = extracted_data['product_type']
        batch_size = extracted_data['product_info'].get('batch_size', '')
        
        pvp_template = PVP_Template(
            product_name=product_name,
            product_type=product_type,
            batch_size=batch_size,
            filepath=filepath,
            user_id=session['user_id']
        )
        db.session.add(pvp_template)
        db.session.flush()  # Get ID
        
        # Save equipment
        equipment_count = 0
        for eq_data in extracted_data.get('equipment', []):
            equipment = PVP_Equipment(
                pvp_template_id=pvp_template.id,
                equipment_name=eq_data.get('equipment_name', ''),
                equipment_id=eq_data.get('equipment_id', ''),
                location=eq_data.get('location', ''),
                calibration_status=eq_data.get('calibration_status', 'Valid')
            )
            db.session.add(equipment)
            equipment_count += 1
        
        # Save materials
        material_count = 0
        for mat_data in extracted_data.get('materials', []):
            material = PVP_Material(
                pvp_template_id=pvp_template.id,
                material_type=mat_data.get('material_type', 'Excipient'),
                material_name=mat_data.get('material_name', ''),
                specification=mat_data.get('specification', ''),
                quantity=mat_data.get('quantity', '')
            )
            db.session.add(material)
            material_count += 1
        
        # Save extracted stages
        stage_count = 0
        for stage_data in extracted_data.get('stages', []):
            # Try to find matching template
            stage_template = PV_Stage_Template.query.filter_by(
                product_type=product_type,
                stage_number=stage_data.get('stage_number', 0)
            ).first()
            
            stage = PVP_Extracted_Stage(
                pvp_template_id=pvp_template.id,
                stage_template_id=stage_template.id if stage_template else None,
                stage_number=stage_data.get('stage_number', 0),
                stage_name=stage_data.get('stage_name', ''),
                equipment_used=stage_data.get('equipment_used', ''),
                specific_parameters=stage_data.get('parameters', ''),
                acceptance_criteria=stage_data.get('acceptance_criteria', '')
            )
            db.session.add(stage)
            stage_count += 1
        
        # Save test criteria
        criteria_count = 0
        for crit_data in extracted_data.get('test_criteria', []):
            criteria = PVP_Criteria(
                pvp_template_id=pvp_template.id,
                test_id=crit_data.get('test_id', ''),
                test_name=crit_data.get('test_name', ''),
                acceptance_criteria=crit_data.get('acceptance_criteria', '')
            )
            db.session.add(criteria)
            criteria_count += 1
        
        db.session.commit()
        
        flash(f'✅ PVP uploaded successfully!', 'success')
        flash(f'✅ Extracted: {equipment_count} equipment, {material_count} materials, {stage_count} stages, {criteria_count} test criteria', 'info')
        
        return redirect(url_for('pv.view_pvp_template', template_id=pvp_template.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing PVP: {e}", exc_info=True)
        flash(f'Error processing PVP: {str(e)}', 'error')
        return redirect(url_for('pv.upload_pvp'))


@pv_routes.route('/templates')
def list_templates():
    """List all uploaded PVP templates"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    templates = PVP_Template.query.filter_by(user_id=session['user_id']).order_by(
        PVP_Template.created_at.desc()
    ).all()
    
    return render_template('pvp_templates_list.html', templates=templates)


@pv_routes.route('/template/<int:template_id>')
def view_pvp_template(template_id):
    """View PVP template details"""
    
    if 'user_id' not in session:
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
                         criteria=criteria)


@pv_routes.route('/generate/<int:template_id>', methods=['GET', 'POST'])
def generate_pvr(template_id):
    """Generate PVR report from PVP template"""
    
    if 'user_id' not in session:
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
                             criteria=criteria)
    
    # Handle POST - generate report
    try:
        # Get batch data from form
        batch_numbers = request.form.getlist('batch_number[]')
        
        if not batch_numbers or len(batch_numbers) < 3:
            flash('Please enter data for at least 3 batches', 'error')
            return redirect(request.url)
        
        # Create PVR Report
        pvr_report = PVR_Report(
            pvp_template_id=template_id,
            user_id=session['user_id'],
            status='Generated'
        )
        db.session.add(pvr_report)
        db.session.flush()
        
        # Save batch data
        criteria = PVP_Criteria.query.filter_by(pvp_template_id=template_id).all()
        
        for batch_num in batch_numbers:
            for criterion in criteria:
                test_result_key = f'result_{criterion.test_id}_{batch_num}'
                test_result = request.form.get(test_result_key, '')
                
                if test_result:
                    pvr_data = PVR_Data(
                        pvr_report_id=pvr_report.id,
                        batch_number=batch_num,
                        test_id=criterion.test_id,
                        test_result=test_result
                    )
                    db.session.add(pvr_data)
        
        db.session.commit()
        
        # Prepare batch data for generators
        batch_data = []
        for batch_num in batch_numbers:
            batch_info = {'batch_number': batch_num, 'test_results': {}}
            for criterion in criteria:
                test_result_key = f'result_{criterion.test_id}_{batch_num}'
                batch_info['test_results'][criterion.test_name] = request.form.get(test_result_key, '')
            batch_data.append(batch_info)
        
        # Generate PDF report file path
        safe_product_name = re.sub(r'[<>:"/\\|?*]', '_', template.product_name).replace(' ', '_')
        pdf_filename = f"PVR_{safe_product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(REPORT_FOLDER, pdf_filename)

        # Generate Word report file path
        word_filename = f"PVR_{safe_product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        word_path = os.path.join(REPORT_FOLDER, word_filename)
        
        # Generate PDF and Word reports using comprehensive generators
        pdf_generator = ComprehensivePVRGenerator(template, batch_data)
        pdf_path = pdf_generator.generate_pdf(pdf_path)
        
        word_generator = ComprehensivePVRWordGenerator()
        word_path = word_generator.generate_comprehensive_pvr_word(pvr_report.id, REPORT_FOLDER)
        
        # Update report with file paths
        pvr_report.pdf_filepath = pdf_path
        pvr_report.word_filepath = word_path
        pvr_report.conclusion = 'Pass'  # TODO: Auto-calculate
        db.session.commit()
        
        flash('✅ PVR Report generated successfully!', 'success')
        return redirect(url_for('pv.view_pvr', report_id=pvr_report.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating PVR: {e}", exc_info=True)
        flash(f'Error generating PVR: {str(e)}', 'error')
        return redirect(request.url)


@pv_routes.route('/report/<int:report_id>')
def view_pvr(report_id):
    """View generated PVR report"""
    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    report = PVR_Report.query.get_or_404(report_id)
    template = report.pvp_template
    batch_data = PVR_Data.query.filter_by(pvr_report_id=report_id).all()
    
    return render_template('view_pvr.html',
                         report=report,
                         template=template,
                         batch_data=batch_data)


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