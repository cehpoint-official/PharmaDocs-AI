# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from models import User, Company, Document, ActivityLog
from database import db
from utils.helpers import log_activity
from sqlalchemy import desc
import logging

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if user.is_admin:
        return redirect(url_for('admin.dashboard'))

    # Get user's companies
    companies = Company.query.filter_by(user_id=user.id).all()

    # Get recent documents
    recent_documents = (
        Document.query.filter_by(user_id=user.id)
        .order_by(desc(Document.updated_at))
        .limit(5).all()
    )

    # Get document statistics (now includes Compatibility)
    doc_stats = {
        'total': Document.query.filter_by(user_id=user.id).count(),
        'amv': Document.query.filter_by(user_id=user.id, document_type='AMV').count(),
        'pv': Document.query.filter_by(user_id=user.id, document_type='PV').count(),
        'stability': Document.query.filter_by(user_id=user.id, document_type='Stability').count(),
        'degradation': Document.query.filter_by(user_id=user.id, document_type='Degradation').count(),
        'compatibility': Document.query.filter_by(user_id=user.id, document_type='Compatibility').count()
    }

    # Log dashboard access
    log_activity(user.id, 'dashboard_accessed', 'User accessed dashboard')

    return render_template(
        'dashboard.html',
        user=user,
        companies=companies,
        recent_documents=recent_documents,
        doc_stats=doc_stats
    )


@bp.route('/documents')
def document_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    page = request.args.get('page', 1, type=int)
    per_page = 10

    documents = Document.query.filter_by(user_id=user.id)\
                             .order_by(desc(Document.updated_at))\
                             .paginate(page=page, per_page=per_page, error_out=False)

    companies = Company.query.filter_by(user_id=user.id).all()

    return render_template('document_history.html',
                         user=user,
                         documents=documents,
                         companies=companies)

@bp.route('/stats')
def dashboard_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']

    try:
        # Document statistics
        total_docs = Document.query.filter_by(user_id=user_id).count()
        completed_docs = Document.query.filter_by(user_id=user_id, status='completed').count()
        draft_docs = Document.query.filter_by(user_id=user_id, status='draft').count()

        # Monthly document creation
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_docs = Document.query.filter(
            Document.user_id == user_id,
            Document.created_at >= thirty_days_ago
        ).count()

        # Document type distribution
        doc_types = db.session.query(
            Document.document_type,
            db.func.count(Document.id).label('count')
        ).filter_by(user_id=user_id).group_by(Document.document_type).all()

        type_distribution = {doc_type: count for doc_type, count in doc_types}

        return jsonify({
            'total_documents': total_docs,
            'completed_documents': completed_docs,
            'draft_documents': draft_docs,
            'recent_documents': recent_docs,
            'type_distribution': type_distribution
        })

    except Exception as e:
        logging.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500
