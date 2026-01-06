# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from functools import wraps
from flask import session, request, jsonify, redirect, url_for, flash
from models import User
from services.payment_service import SubscriptionManager
import logging

def subscription_required(action='general'):
    """Decorator to check subscription limits for specific actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
                return redirect(url_for('auth.login'))
            
            user = User.query.get(session['user_id'])
            if not user:
                session.clear()
                if request.is_json:
                    return jsonify({'error': 'User not found', 'redirect': '/login'}), 401
                return redirect(url_for('auth.login'))
            
            # Check if subscription is active
            if not user.is_subscription_active():
                if request.is_json:
                    return jsonify({
                        'error': 'Subscription inactive',
                        'message': 'Your subscription has expired. Please renew to continue using premium features.',
                        'redirect': '/subscription/plans'
                    }), 403
                flash('Your subscription has expired. Please renew to continue using premium features.', 'error')
                return redirect(url_for('subscription.subscription_plans'))
            
            # Check specific action limits
            limits_check = SubscriptionManager.check_subscription_limits(user, action)
            
            if not limits_check['allowed']:
                if request.is_json:
                    return jsonify({
                        'error': 'Limit exceeded',
                        'message': limits_check['message'],
                        'upgrade_required': limits_check['upgrade_required'],
                        'current_plan': limits_check['current_plan'],
                        'redirect': '/subscription/plans' if limits_check['upgrade_required'] else None
                    }), 403
                
                flash(limits_check['message'], 'warning')
                if limits_check['upgrade_required']:
                    return redirect(url_for('subscription.subscription_plans'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_document_creation_limit():
    """Middleware function to check document creation limits"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login'))
            
            user = User.query.get(session['user_id'])
            if not user:
                if request.is_json:
                    return jsonify({'error': 'User not found'}), 401
                return redirect(url_for('auth.login'))
            
            # Check if user can create more documents
            if not user.can_create_document():
                limits = user.get_plan_limits()
                message = f"You have reached your monthly limit of {limits['documents_per_month']} documents. Upgrade your plan to create more documents."
                
                if request.is_json:
                    return jsonify({
                        'error': 'Document limit exceeded',
                        'message': message,
                        'upgrade_required': True,
                        'current_plan': user.subscription_plan,
                        'limits': limits
                    }), 403
                
                flash(message, 'warning')
                return redirect(url_for('subscription.subscription_plans'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to check if user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.user_dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def premium_feature_required(f):
    """Decorator to check if user has access to premium features"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            if request.is_json:
                return jsonify({'error': 'User not found'}), 401
            return redirect(url_for('auth.login'))
        
        if user.subscription_plan not in ['basic', 'premium'] or not user.is_subscription_active():
            message = 'This feature requires a Basic or Premium subscription.'
            if request.is_json:
                return jsonify({
                    'error': 'Premium feature',
                    'message': message,
                    'upgrade_required': True,
                    'current_plan': user.subscription_plan
                }), 403
            
            flash(message, 'info')
            return redirect(url_for('subscription.subscription_plans'))
        
        return f(*args, **kwargs)
    return decorated_function

def api_rate_limit_check(f):
    """Decorator to check API rate limits"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Check API rate limits
        limits_check = SubscriptionManager.check_subscription_limits(user, 'api_request')
        
        if not limits_check['allowed']:
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': limits_check['message'],
                'upgrade_required': limits_check['upgrade_required'],
                'current_plan': limits_check['current_plan']
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function

class SubscriptionMiddleware:
    """Main subscription middleware class"""
    
    @staticmethod
    def check_feature_access(user, feature):
        """Check if user has access to a specific feature"""
        if not user or not user.is_subscription_active():
            return False
        
        limits = user.get_plan_limits()
        features = limits.get('features', [])
        
        return feature in features
    
    @staticmethod
    def get_usage_warning(user):
        """Get usage warning message if user is approaching limits"""
        if not user:
            return None
        
        usage_stats = SubscriptionManager.get_usage_stats(user)
        warnings = []
        
        # Check document usage
        doc_usage = usage_stats['documents']
        if doc_usage['limit'] > 0 and doc_usage['percentage'] >= 80:
            warnings.append(f"You've used {doc_usage['used']}/{doc_usage['limit']} documents this month ({doc_usage['percentage']:.0f}%)")
        
        # Check storage usage
        storage_usage = usage_stats['storage']
        if storage_usage['percentage'] >= 80:
            warnings.append(f"You've used {storage_usage['percentage']:.0f}% of your storage limit")
        
        # Check API usage
        api_usage = usage_stats['api_requests']
        if api_usage['percentage'] >= 80:
            warnings.append(f"You've used {api_usage['percentage']:.0f}% of your daily API requests")
        
        return warnings if warnings else None
    
    @staticmethod
    def log_feature_usage(user, feature, details=None):
        """Log feature usage for analytics"""
        try:
            from utils.helpers import log_activity
            log_activity(
                user.id, 
                f'feature_used_{feature}', 
                details or f'User used {feature} feature'
            )
        except Exception as e:
            logging.error(f"Error logging feature usage: {str(e)}")

def inject_subscription_context():
    """Template context processor to inject subscription-related data"""
    def utility_processor():
        context = {}
        
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                context.update({
                    'user_limits': user.get_plan_limits(),
                    'user_usage': SubscriptionManager.get_usage_stats(user),
                    'subscription_warnings': SubscriptionMiddleware.get_usage_warning(user),
                    'is_subscription_active': user.is_subscription_active()
                })
        
        return context
    
    return utility_processor