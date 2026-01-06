# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from services.firebase_service import verify_firebase_token, get_user_from_token
from services.cloudinary_service import upload_file
from models import User, Company
from database import db
from utils.helpers import log_activity
import logging

bp = Blueprint('auth', __name__)

@bp.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.user_dashboard'))

    return render_template('index.html',
                         firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
                         firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
                         firebase_app_id=os.environ.get("FIREBASE_APP_ID"))

@bp.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.user_dashboard'))

    return render_template('login.html',
                         firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
                         firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
                         firebase_app_id=os.environ.get("FIREBASE_APP_ID"))

@bp.route('/register')
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard.user_dashboard'))

    return render_template('register.html',
                         firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
                         firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
                         firebase_app_id=os.environ.get("FIREBASE_APP_ID"))

@bp.route('/auth/verify', methods=['POST'])
def verify_auth():
    try:
        data = request.get_json()
        if not data or 'idToken' not in data:
            return jsonify({'error': 'No ID token provided'}), 400

        # Verify Firebase token
        decoded_token = verify_firebase_token(data['idToken'])
        if not decoded_token:
            return jsonify({'error': 'Invalid token'}), 401

        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name', email.split('@')[0])

        # Check if user exists
        user = User.query.filter_by(firebase_uid=firebase_uid).first()

        if not user:
            # Create new user
            user = User(
                firebase_uid=firebase_uid,
                email=email,
                name=name
            )
            db.session.add(user)
            db.session.commit()

            # Create default company for new user
            company = Company(
                user_id=user.id,
                name=f"{name}'s Pharmaceutical Company"
            )
            db.session.add(company)
            db.session.commit()

            log_activity(user.id, 'user_registered', f'New user registered: {email}')

        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Set session
        session['user_id'] = user.id
        session['firebase_uid'] = firebase_uid

        log_activity(user.id, 'user_login', f'User logged in: {email}')

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'is_admin': user.is_admin
            }
        })

    except Exception as e:
        logging.error(f"Auth verification error: {str(e)}")
        return jsonify({'error': 'Authentication failed'}), 500

@bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_activity(session['user_id'], 'user_logout', 'User logged out')

    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.index'))
