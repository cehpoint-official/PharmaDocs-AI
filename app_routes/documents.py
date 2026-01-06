# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from models import User, Company, Document, SubBrand
from database import db
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
    """Redirect to AMV creation page since we only support AMV documents currently."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Redirect to AMV creation page
    return redirect(url_for('amv_bp.create_amv_form'))

@bp.route('/create', methods=['POST'])
def create_document_post():
    """Redirect POST requests to AMV creation since we only support AMV documents currently."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Redirect to AMV creation
    return redirect(url_for('amv_bp.create_amv_form'))

@bp.route('/<int:document_id>')
def view_document(document_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
    if not document:
        flash('Document not found.', 'error')
        return redirect(url_for('dashboard.document_history'))

    # Parse metadata JSON here
    metadata = json.loads(document.document_metadata) if document.document_metadata else {}

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
                'excel_url': result.get('excel_url'),
                'cleanup_results': result.get('cleanup_results', {})
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

@bp.route('/<int:document_id>/cleanup-files', methods=['POST'])
def cleanup_document_files(document_id):
    """Manually clean up uploaded files for a document."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        document = Document.query.filter_by(id=document_id, user_id=session['user_id']).first()
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Import cleanup function
        from services.document_service import cleanup_uploaded_files
        
        # Perform cleanup
        cleanup_results = cleanup_uploaded_files(document)
        
        # Update database
        db.session.commit()
        
        log_activity(session['user_id'], 'files_cleaned_up',
                    f'Cleaned up files for document: {document.title}')

        return jsonify({
            'success': True,
            'message': 'Files cleaned up successfully',
            'cleanup_results': cleanup_results
        })

    except Exception as e:
        logging.error(f"File cleanup error: {str(e)}")
        return jsonify({'error': 'Failed to cleanup files'}), 500
