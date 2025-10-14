# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, session, request, jsonify
from werkzeug.security import generate_password_hash
from models import User
from database import db
from utils.helpers import log_activity

bp = Blueprint('user', __name__)

@bp.route('/user/edit', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    if user.email != email:
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already in use'}), 400

    user.name = name
    user.email = email
    if password:
        user.password_hash = generate_password_hash(password)

    db.session.commit()
    log_activity(user.id, 'profile_updated', 'Updated user profile')

    return jsonify({'success': True, 'message': 'Profile updated successfully'})
