# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, session, redirect, url_for, render_template, request, jsonify
from models import Company, User
from app import db
from utils.helpers import log_activity
from services.cloudinary_service import upload_file
import logging

bp = Blueprint('company', __name__)

@bp.route('/company/profile')
def company_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    companies = Company.query.filter_by(user_id=user.id).all()

    return render_template('company_profile.html', user=user, companies=companies)

@bp.route('/company/create', methods=['POST'])
def create_company():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        name = request.form.get('name')
        address = request.form.get('address')

        if not name:
            return jsonify({'error': 'Company name is required'}), 400

        # Handle logo upload
        logo_url = None
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename:
                logo_url = upload_file(logo_file, folder='company_logos')

        company = Company(
            user_id=session['user_id'],
            name=name,
            address=address,
            logo_url=logo_url
        )

        db.session.add(company)
        db.session.commit()

        log_activity(session['user_id'], 'company_created', f'Created company: {name}')

        return jsonify({'success': True, 'company_id': company.id})

    except Exception as e:
        logging.error(f"Company creation error: {str(e)}")
        return jsonify({'error': 'Failed to create company'}), 500


@bp.route('/company/edit/<int:company_id>', methods=['POST'])
def edit_company(company_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    company = Company.query.get(company_id)
    if not company or company.user_id != session['user_id']:
        return jsonify({'error': 'Company not found or access denied'}), 404

    try:
        name = request.form.get('name')
        address = request.form.get('address')

        if name:
            company.name = name
        if address:
            company.address = address

        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename:
                company.logo_url = upload_file(logo_file, folder='company_logos')

        db.session.commit()

        log_activity(session['user_id'], 'company_edited', f'Edited company: {company.name}')

        return jsonify({'success': True, 'company_id': company.id})

    except Exception as e:
        logging.error(f"Company edit error: {str(e)}")
        return jsonify({'error': 'Failed to edit company'}), 500


@bp.route('/company/get/<int:company_id>')
def get_company(company_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    company = Company.query.get(company_id)
    if not company or company.user_id != session['user_id']:
        return jsonify({'error': 'Company not found'}), 404

    return jsonify({
        'success': True,
        'company': {
            'id': company.id,
            'name': company.name,
            'address': company.address,
            'logo_url': company.logo_url
        }
    })
