# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from models import User, Company, Document, SubBrand
from app import db
from services.cloudinary_service import upload_file
from services.document_service import generate_document
from utils.helpers import log_activity
from utils.validators import validate_file_type
import json
import logging
from datetime import datetime

bp = Blueprint('documents', __name__, url_prefix='/documents')

@bp.route('/create')
def create_document():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    companies = Company.query.filter_by(user_id=user.id).all()

    # Get sub-brands for all user companies
    sub_brands = []
    for company in companies:
        sub_brands.extend(company.sub_brands)

    return render_template('create_document.html',
                         user=user,
                         companies=companies,
                         sub_brands=sub_brands)

@bp.route('/create', methods=['POST'])
def create_document_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get form data
        document_type = request.form.get('document_type')
        title = request.form.get('title')
        company_id = request.form.get('company_id', type=int)
        document_number = request.form.get('document_number')

        # Validate required fields
        if not all([document_type, title, company_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate company ownership
        company = Company.query.filter_by(id=company_id, user_id=session['user_id']).first()
        if not company:
            return jsonify({'error': 'Invalid company'}), 400

        # Handle file uploads
        stp_file_url = None
        raw_data_url = None

        if 'stp_file' in request.files:
            stp_file = request.files['stp_file']
            if stp_file.filename:
                if not validate_file_type(stp_file.filename, ['doc', 'docx']):
                    return jsonify({'error': 'STP file must be a Word document'}), 400
                stp_file_url = upload_file(stp_file, folder='stp_files')

        if 'raw_data_file' in request.files:
            raw_data_file = request.files['raw_data_file']
            if raw_data_file.filename:
                if not validate_file_type(raw_data_file.filename, ['csv', 'xlsx', 'xls']):
                    return jsonify({'error': 'Raw data file must be CSV or Excel'}), 400
                raw_data_url = upload_file(raw_data_file, folder='raw_data')

        # Create document record
        document = Document(
            user_id=session['user_id'],
            company_id=company_id,
            document_type=document_type,
            document_number=document_number,
            title=title,
            status='draft',
            stp_file_url=stp_file_url,
            raw_data_url=raw_data_url,
            document_metadata=json.dumps(request.form.to_dict())
        )

        db.session.add(document)
        db.session.commit()

        log_activity(session['user_id'], 'document_created',
                    f'Created {document_type} document: {title}')

        return jsonify({
            'success': True,
            'document_id': document.id,
            'redirect_url': url_for('documents.view_document', document_id=document.id)
        })

    except Exception as e:
        logging.error(f"Document creation error: {str(e)}")
        return jsonify({'error': 'Failed to create document'}), 500

@bp.route('/<int:document_id>')
def view_document(document_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('dashboard.document_history'))

    # Parse metadata JSON here
    metadata = json.loads(document.document_metadata) if document.metadata else {}

    return render_template('view_document.html', document=document, metadata=metadata)

@bp.route('/<int:document_id>/generate', methods=['POST'])
def generate_document_api(document_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Get additional parameters from request
        data = request.get_json(silent=True) or {}

        # Generate the document
        result = generate_document(document, data)

        if result['success']:
            # Update document record
            document.generated_doc_url = result.get('doc_url')
            document.generated_excel_url = result.get('excel_url')
            document.status = 'generated'
            document.updated_at = datetime.utcnow()

            db.session.commit()

            log_activity(session['user_id'], 'document_generated',
                        f'Generated document: {document.title}')

            return jsonify({
                'success': True,
                'doc_url': result.get('doc_url'),
                'excel_url': result.get('excel_url')
            })
        else:
            return jsonify({'error': result.get('error', 'Generation failed')}), 500

    except Exception as e:
        logging.error(f"Document generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate document'}), 500

@bp.route('/<int:document_id>/download/<file_type>')
def download_document(document_id, file_type):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('dashboard.document_history'))

    if file_type == 'doc' and document.generated_doc_url:
        # Redirect to Cloudinary URL for download
        return redirect(document.generated_doc_url)
    elif file_type == 'excel' and document.generated_excel_url:
        return redirect(document.generated_excel_url)
    else:
        flash('File not available for download.', 'error')
        return redirect(url_for('documents.view_document', document_id=document_id))

@bp.route('/<int:document_id>/delete', methods=['POST'])
def delete_document(document_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Store title for logging
        title = document.title

        # Delete document
        db.session.delete(document)
        db.session.commit()

        log_activity(session['user_id'], 'document_deleted', f'Deleted document: {title}')

        return jsonify({'success': True})

    except Exception as e:
        logging.error(f"Document deletion error: {str(e)}")
        return jsonify({'error': 'Failed to delete document'}), 500
