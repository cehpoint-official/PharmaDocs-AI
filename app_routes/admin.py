# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from models import User, Company, Document, ActivityLog
from app import db
from utils.helpers import log_activity
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import logging

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('dashboard.user_dashboard'))

    # Get statistics
    total_users = User.query.count()
    total_companies = Company.query.count()
    total_documents = Document.query.count()

    # Recent activity
    recent_activities = ActivityLog.query.order_by(desc(ActivityLog.timestamp)).limit(10).all()

    # Users registered in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users = User.query.filter(User.created_at >= thirty_days_ago).count()

    # Documents created in last 30 days
    new_documents = Document.query.filter(Document.created_at >= thirty_days_ago).count()

    # Document type distribution
    doc_types = db.session.query(
        Document.document_type,
        func.count(Document.id).label('count')
    ).group_by(Document.document_type).all()

    log_activity(user.id, 'admin_dashboard_accessed', 'Admin accessed dashboard')

    return render_template('admin_dashboard.html',
                         user=user,
                         total_users=total_users,
                         total_companies=total_companies,
                         total_documents=total_documents,
                         new_users=new_users,
                         new_documents=new_documents,
                         recent_activities=recent_activities,
                         doc_types=doc_types)

@bp.route('/users')
def manage_users():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('dashboard.user_dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 20

    users = User.query.order_by(desc(User.created_at))\
                     .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin_users.html', user=user, users=users)

@bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
def toggle_admin(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    try:
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404

        # Prevent self-demotion
        if target_user.id == admin_user.id:
            return jsonify({'error': 'Cannot modify your own admin status'}), 400

        target_user.is_admin = not target_user.is_admin
        db.session.commit()

        action = 'promoted to admin' if target_user.is_admin else 'removed from admin'
        log_activity(admin_user.id, 'user_admin_toggle',
                    f'User {target_user.email} {action}')

        return jsonify({'success': True, 'is_admin': target_user.is_admin})

    except Exception as e:
        logging.error(f"Admin toggle error: {str(e)}")
        return jsonify({'error': 'Failed to update user status'}), 500

@bp.route('/documents')
def manage_documents():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('dashboard.user_dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 20

    documents = Document.query.order_by(desc(Document.created_at))\
                             .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin_documents.html', user=user, documents=documents)

@bp.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('dashboard.user_dashboard'))

    try:
        # User registration trends (last 12 months)
        user_trends = []
        for i in range(12):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=31)
            count = User.query.filter(
                User.created_at >= month_start,
                User.created_at < month_end
            ).count()
            user_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })

        # Document generation trends
        doc_trends = []
        for i in range(12):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=31)
            count = Document.query.filter(
                Document.created_at >= month_start,
                Document.created_at < month_end
            ).count()
            doc_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })

        return jsonify({
            'user_trends': list(reversed(user_trends)),
            'document_trends': list(reversed(doc_trends))
        })

    except Exception as e:
        logging.error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500
