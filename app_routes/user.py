# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, session, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from models import User, Subscription, Payment
from database import db
from utils.helpers import log_activity
from services.payment_service import PaymentService, SubscriptionManager

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

@bp.route('/user/status', methods=['GET'])
def user_status():
    """Get user status to determine if subscription popup should be shown."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    show_popup = False
    # Show popup if user is on free plan or subscription has expired.
    if user.subscription_plan == 'free' or \
       (user.subscription_expiry and user.subscription_expiry < datetime.utcnow()):
        show_popup = True

    return jsonify({
        'success': True,
        'show_subscription_popup': show_popup,
        'subscription_plan': user.subscription_plan,
        'subscription_expiry': user.subscription_expiry.isoformat() if user.subscription_expiry else None,
        'name': user.name,
        'email': user.email
    })

@bp.route('/user/subscribe', methods=['POST'])
def subscribe_user():
    """Update user's subscription plan - Legacy endpoint for backward compatibility."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    plan = data.get('plan')

    if not plan or plan not in ['free', 'basic', 'premium']:
        return jsonify({'error': 'Invalid plan selected'}), 400

    # Check subscription limits before allowing action
    limits_check = SubscriptionManager.check_subscription_limits(user, 'upgrade_subscription')
    
    try:
        if plan == 'free':
            # Downgrade to free
            user.subscription_plan = plan
            user.subscription_expiry = None
            user.subscription_status = 'active'
        elif plan in ['basic', 'premium']:
            # For paid plans, redirect to proper payment flow
            return jsonify({
                'success': False, 
                'redirect_to_payment': True,
                'message': f'Please complete payment to upgrade to {plan} plan.',
                'plan': plan
            })

        db.session.commit()
        log_activity(user.id, 'subscription_updated', f'User changed to {plan} plan.')
        return jsonify({'success': True, 'message': f'Successfully changed to the {plan} plan!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/user/usage-stats')
def user_usage_stats():
    """Get user's current usage statistics."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    usage_stats = SubscriptionManager.get_usage_stats(user)
    limits = user.get_plan_limits()

    return jsonify({
        'success': True,
        'usage': usage_stats,
        'limits': limits,
        'subscription_plan': user.subscription_plan,
        'subscription_active': user.is_subscription_active()
    })

@bp.route('/user/check-document-limit')
def check_document_limit():
    """Check if user can create more documents."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    can_create = user.can_create_document()
    limits_info = SubscriptionManager.check_subscription_limits(user, 'create_document')

    return jsonify({
        'success': True,
        'can_create_document': can_create,
        'limits_info': limits_info,
        'current_plan': user.subscription_plan
    })


@bp.route('/user/profile')
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Get current subscription details
    current_subscription = Subscription.query.filter_by(
        user_id=user.id,
        status='active'
    ).first()
    
    # Get usage stats
    usage_stats = SubscriptionManager.get_usage_stats(user)
    limits = user.get_plan_limits()
    
    # Get recent payments
    recent_payments = PaymentService.get_user_payment_history(user, limit=5)
    
    return render_template('profile.html', 
                         user=user, 
                         now=datetime.now(),
                         current_subscription=current_subscription,
                         usage_stats=usage_stats,
                         limits=limits,
                         recent_payments=recent_payments)

@bp.route('/user/subscriptions')
def subscription_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Get subscription and payment history
    subscriptions = PaymentService.get_user_subscription_history(user, limit=20)
    payments = PaymentService.get_user_payment_history(user, limit=20)
    
    # Get usage stats
    usage_stats = SubscriptionManager.get_usage_stats(user)
    
    return render_template('user/subscriptions.html', 
                         user=user,
                         subscriptions=subscriptions,
                         payments=payments,
                         usage_stats=usage_stats)