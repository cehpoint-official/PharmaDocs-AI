# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, session, redirect, url_for, render_template, request, jsonify
from models import Company, User
from database import db
from utils.helpers import log_activity
from services.cloudinary_service import upload_file
from datetime import datetime
import logging

bp = Blueprint('company', __name__)

@bp.route('/company/profile')
def company_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    companies = Company.query.filter_by(user_id=user.id).all()
    # Get counts for each company's management items
    companies_with_counts = []
    for company in companies:
        # Get counts using SQLAlchemy relationships
        try:
            equipment_count = len(company.equipment_list)
            materials_count = len(company.glass_materials_list) + len(company.other_materials_list)
            reagents_count = len(company.reagents_list)
            references_count = len(company.reference_products_list)
        except Exception as e:
            logging.error(f"Error fetching relationship counts for company {company.id}: {str(e)}")
            equipment_count = 0
            materials_count = 0
            reagents_count = 0
            references_count = 0
        
        # Add counts to company object
        company.equipment_count = equipment_count
        company.material_count = materials_count # Template expects material_count
        company.reagent_count = reagents_count   # Template expects reagent_count
        company.reference_count = references_count
        
        companies_with_counts.append(company)

    return render_template('company_profile.html', user=user, companies=companies_with_counts)

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
        glass_materials = request.form.get('glass_materials')

        if name:
            company.name = name
        if address:
            company.address = address
        if glass_materials:
            company.glass_materials = glass_materials

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

@bp.route('/subbrand/create', methods=['POST'])
def create_subbrand():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        company_id = request.form.get('company_id')
        name = request.form.get('name')

        if not name or not company_id:
            return jsonify({'error': 'Name and Company ID are required'}), 400

        from models import SubBrand
        sub_brand = SubBrand(
            company_id=company_id,
            name=name
        )

        db.session.add(sub_brand)
        db.session.commit()

        log_activity(session['user_id'], 'sub_brand_created', f'Created sub-brand {name} for company {company_id}')
        return jsonify({'success': True})

    except Exception as e:
        logging.error(f"Sub-brand creation error: {str(e)}")
        return jsonify({'error': 'Failed to create sub-brand'}), 500
