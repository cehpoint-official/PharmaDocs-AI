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
        # Initialize default counts
        equipment_count = 0
        materials_count = 0
        reagents_count = 0
        references_count = 0
        
        # Get counts from AMV settings database
        try:
            from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
            from sqlalchemy.ext.declarative import declarative_base
            from sqlalchemy.orm import sessionmaker
            import os
            
            # Check if AMV database exists
            amv_db_path = 'amv_company_settings.db'
            if os.path.exists(amv_db_path):
                # Create AMV database session
                amv_engine = create_engine(f'sqlite:///{amv_db_path}')
                AMVBase = declarative_base()
                
                class Equipment(AMVBase):
                    __tablename__ = 'equipment'
                    id = Column(Integer, primary_key=True)
                    company_id = Column(Integer)
                    name = Column(String(200))
                    code = Column(String(100))
                    brand = Column(String(100))
                    verification_frequency = Column(String(200))
                    last_calibration = Column(String(50))
                    next_calibration = Column(String(50))
                    created_at = Column(DateTime, default=datetime.now)
                
                class GlassMaterial(AMVBase):
                    __tablename__ = 'glass_materials'
                    id = Column(Integer, primary_key=True)
                    company_id = Column(Integer)
                    name = Column(String(200))
                    characteristics = Column(String(500))
                    created_at = Column(DateTime, default=datetime.now)
                
                class Reagent(AMVBase):
                    __tablename__ = 'reagents'
                    id = Column(Integer, primary_key=True)
                    company_id = Column(Integer)
                    name = Column(String(200))
                    batch = Column(String(100))
                    expiry_date = Column(String(50))
                    created_at = Column(DateTime, default=datetime.now)
                
                class ReferenceProduct(AMVBase):
                    __tablename__ = 'reference_products'
                    id = Column(Integer, primary_key=True)
                    company_id = Column(Integer)
                    standard_type = Column(String(100))
                    standard_name = Column(String(200))
                    code = Column(String(100))
                    potency = Column(String(50))
                    due_date = Column(String(50))
                    created_at = Column(DateTime, default=datetime.now)
                
                AMVSession = sessionmaker(bind=amv_engine)
                amv_session = AMVSession()
                
                # Get counts for this company from AMV database
                equipment_count = amv_session.query(Equipment).filter_by(company_id=company.id).count()
                materials_count = amv_session.query(GlassMaterial).filter_by(company_id=company.id).count()
                reagents_count = amv_session.query(Reagent).filter_by(company_id=company.id).count()
                references_count = amv_session.query(ReferenceProduct).filter_by(company_id=company.id).count()
                
                amv_session.close()
                
                # Debug logging
                logging.info(f"Company {company.id} counts: Equipment={equipment_count}, Materials={materials_count}, Reagents={reagents_count}, References={references_count}")
            else:
                logging.warning(f"AMV database not found at {amv_db_path}")
                
        except Exception as e:
            # If AMV database is not available, use default counts
            logging.error(f"Error fetching AMV counts for company {company.id}: {str(e)}")
            equipment_count = 0
            materials_count = 0
            reagents_count = 0
            references_count = 0
        
        # Add counts to company object
        company.equipment_count = equipment_count
        company.materials_count = materials_count
        company.reagents_count = reagents_count
        company.references_count = references_count
        
        # Debug logging
        logging.info(f"Company {company.id} final counts: Equipment={equipment_count}, Materials={materials_count}, Reagents={reagents_count}, References={references_count}")
        
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
