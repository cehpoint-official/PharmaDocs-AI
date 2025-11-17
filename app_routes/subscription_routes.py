# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import stripe
import json
import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from datetime import datetime
from models import User, Subscription, Payment, SubscriptionPlan
from database import db
from services.payment_service import PaymentService, SubscriptionManager
from utils.helpers import log_activity

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

bp = Blueprint('subscription', __name__, url_prefix='/subscription')

@bp.route('/plans')
def subscription_plans():
    """Display available subscription plans"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    plans = PaymentService.get_subscription_plans()
    usage_stats = SubscriptionManager.get_usage_stats(user)
    
    return render_template('subscription/plans.html', 
                         user=user, 
                         plans=plans, 
                         usage_stats=usage_stats,
                         stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY'),
                         now=datetime.now())

@bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """Create a payment intent for subscription"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        plan = data.get('plan')
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get plan details
        amount_mapping = {
            'basic': int(os.environ.get('BASIC_PLAN_AMOUNT', 999)),
            'premium': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 2999))
        }
        
        if plan not in amount_mapping:
            return jsonify({'error': 'Invalid plan'}), 400
        
        amount = amount_mapping[plan]
        
        client_secret = PaymentService.create_payment_intent(
            user=user,
            amount=amount,
            description=f"Subscription to {plan.title()} Plan",
            metadata={'plan': plan, 'user_id': str(user.id)}
        )
        
        if client_secret:
            return jsonify({'client_secret': client_secret})
        else:
            return jsonify({'error': 'Failed to create payment intent'}), 500
    
    except Exception as e:
        logging.error(f"Error creating payment intent: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/create-subscription', methods=['POST'])
def create_subscription():
    """Create a subscription with Stripe"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        plan = data.get('plan')
        trial_days = data.get('trial_days', 0)
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # For Razorpay, redirect to Razorpay routes
        return jsonify({
            'success': False,
            'redirect_to_razorpay': True,
            'message': 'Redirecting to Indian payment gateway...',
            'redirect_url': '/razorpay/plans'
        })
        
        if result:
            return jsonify({
                'success': True,
                'subscription_id': result['subscription_id'],
                'client_secret': result['client_secret'],
                'status': result['status']
            })
        else:
            return jsonify({'error': 'Failed to create subscription'}), 500
    
    except Exception as e:
        logging.error(f"Error creating subscription: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel user's subscription"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        cancel_immediately = data.get('cancel_immediately', False)
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        success = PaymentService.cancel_subscription(
            user=user,
            cancel_at_period_end=not cancel_immediately
        )
        
        if success:
            message = "Subscription canceled immediately." if cancel_immediately else "Subscription will be canceled at the end of the current period."
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': 'Failed to cancel subscription'}), 500
    
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/history')
def subscription_history():
    """Display subscription and payment history"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    subscriptions = PaymentService.get_user_subscription_history(user, limit=20)
    payments = PaymentService.get_user_payment_history(user, limit=20)
    
    return render_template('subscription/history.html',
                         user=user,
                         subscriptions=subscriptions,
                         payments=payments)

@bp.route('/status')
def subscription_status():
    """Get current subscription status"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get current subscription
    current_subscription = Subscription.query.filter_by(
        user_id=user.id,
        status='active'
    ).first()
    
    usage_stats = SubscriptionManager.get_usage_stats(user)
    
    return jsonify({
        'success': True,
        'subscription_plan': user.subscription_plan,
        'subscription_status': user.subscription_status,
        'subscription_expiry': user.subscription_expiry.isoformat() if user.subscription_expiry else None,
        'is_active': user.is_subscription_active(),
        'limits': user.get_plan_limits(),
        'usage': usage_stats,
        'trial_active': current_subscription.is_trial() if current_subscription else False,
        'days_until_expiry': current_subscription.days_until_expiry() if current_subscription else None
    })

@bp.route('/check-limits', methods=['POST'])
def check_limits():
    """Check if user can perform an action based on subscription limits"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        action = data.get('action')
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        result = SubscriptionManager.check_subscription_limits(user, action)
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"Error checking limits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        logging.error(f"Invalid payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    try:
        if event['type'] == 'payment_intent.succeeded':
            PaymentService.handle_webhook_payment_succeeded(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.updated':
            PaymentService.handle_webhook_subscription_updated(event['data']['object'])
        
        elif event['type'] == 'customer.subscription.deleted':
            PaymentService.handle_webhook_subscription_updated(event['data']['object'])
        
        elif event['type'] == 'invoice.payment_succeeded':
            # Handle successful recurring payment
            invoice_data = event['data']['object']
            subscription_id = invoice_data.get('subscription')
            
            if subscription_id:
                subscription = Subscription.query.filter_by(
                    stripe_subscription_id=subscription_id
                ).first()
                
                if subscription:
                    # Record payment
                    payment = Payment(
                        user_id=subscription.user_id,
                        subscription_id=subscription.id,
                        amount=invoice_data['amount_paid'],
                        currency=invoice_data['currency'],
                        status='succeeded',
                        description=f"Recurring payment for {subscription.plan_name} plan",
                        receipt_url=invoice_data.get('hosted_invoice_url')
                    )
                    db.session.add(payment)
                    db.session.commit()
                    
                    log_activity(subscription.user_id, 'recurring_payment_success', 
                               f'Recurring payment successful: {invoice_data["id"]}')
        
        elif event['type'] == 'invoice.payment_failed':
            # Handle failed payment
            invoice_data = event['data']['object']
            subscription_id = invoice_data.get('subscription')
            
            if subscription_id:
                subscription = Subscription.query.filter_by(
                    stripe_subscription_id=subscription_id
                ).first()
                
                if subscription:
                    log_activity(subscription.user_id, 'payment_failed', 
                               f'Payment failed for subscription: {subscription_id}')
        
        else:
            logging.info(f"Unhandled event type: {event['type']}")
    
    except Exception as e:
        logging.error(f"Error handling webhook: {str(e)}")
        return jsonify({'error': 'Webhook handler failed'}), 500
    
    return jsonify({'success': True})

@bp.route('/upgrade-popup-data')
def upgrade_popup_data():
    """Get data for upgrade popup"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    plans = [
        {
            'name': 'basic',
            'display_name': 'Basic',
            'price': int(os.environ.get('BASIC_PLAN_AMOUNT', 999)) / 100,
            'features': ['50 Documents/month', '1GB Storage', 'Email Support', 'Basic Reports']
        },
        {
            'name': 'premium',
            'display_name': 'Premium',
            'price': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 2999)) / 100,
            'features': ['Unlimited Documents', '10GB Storage', 'Priority Support', 'Advanced Reports', 'API Access']
        }
    ]
    
    usage_stats = SubscriptionManager.get_usage_stats(user)
    
    return jsonify({
        'success': True,
        'current_plan': user.subscription_plan,
        'plans': plans,
        'usage': usage_stats,
        'stripe_publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY')
    })