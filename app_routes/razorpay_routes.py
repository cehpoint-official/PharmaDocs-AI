# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import json
import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from datetime import datetime, timedelta
from models import User, Subscription, Payment, SubscriptionPlan
from database import db
from services.razorpay_service import RazorpayService, IndianPaymentGatewayManager
from utils.helpers import log_activity

bp = Blueprint('razorpay', __name__, url_prefix='/razorpay')

# Initialize Razorpay service
razorpay_service = RazorpayService()
payment_manager = IndianPaymentGatewayManager()

@bp.route('/plans')
def subscription_plans():
    """Display available subscription plans with Indian pricing"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Indian pricing plans
    plans = [
        {
            'name': 'free',
            'display_name': 'Free',
            'price': 0,
            'currency': 'INR',
            'features': ['5 Documents/month', '100MB Storage', 'Email Support', 'Basic Reports'],
            'popular': False
        },
        {
            'name': 'basic',
            'display_name': 'Basic',
            'price': int(os.environ.get('BASIC_PLAN_AMOUNT', 49900)) / 100,  # Convert paise to rupees
            'currency': 'INR',
            'features': ['50 Documents/month', '1GB Storage', 'Priority Support', 'Advanced Reports', 'PDF Export'],
            'popular': True
        },
        {
            'name': 'premium',
            'display_name': 'Premium',
            'price': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 149900)) / 100,  # Convert paise to rupees
            'currency': 'INR',
            'features': ['Unlimited Documents', '10GB Storage', 'Phone Support', 'All Reports', 'API Access', 'Custom Templates'],
            'popular': False
        }
    ]
    
    return render_template('subscription/razorpay_plans.html', 
                         user=user, 
                         plans=plans,
                         razorpay_key_id=os.environ.get('RAZORPAY_KEY_ID'),
                         now=datetime.now())

@bp.route('/create-order', methods=['POST'])
def create_order():
    """Create a Razorpay order for payment"""
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
            'basic': int(os.environ.get('BASIC_PLAN_AMOUNT', 49900)),
            'premium': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 149900))
        }
        
        if plan not in amount_mapping:
            return jsonify({'error': 'Invalid plan'}), 400
        
        amount = amount_mapping[plan]
        
        # Check if Razorpay credentials are configured
        razorpay_key_id = os.environ.get('RAZORPAY_KEY_ID')
        razorpay_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
        
        if not razorpay_key_id or not razorpay_key_secret:
            return jsonify({
                'error': 'Razorpay credentials not configured',
                'message': 'Please add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to your .env file to enable payments.',
                'setup_required': True
            }), 400

        order = payment_manager.create_order(
            user=user,
            amount=amount,
            plan_name=plan
        )
        
        if order:
            return jsonify({
                'success': True,
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key': razorpay_key_id
            })
        else:
            return jsonify({'error': 'Failed to create order. Please check your Razorpay configuration.'}), 500
    
    except Exception as e:
        logging.error(f"Error creating order: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Verify payment and update subscription"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        # Verify payment signature
        is_valid = payment_manager.verify_payment(data)
        
        if not is_valid:
            return jsonify({'error': 'Payment verification failed'}), 400
        
        # Update payment status
        payment = Payment.query.filter_by(
            razorpay_order_id=data['razorpay_order_id']
        ).first()
        
        if payment:
            payment.status = 'captured'
            payment.razorpay_payment_id = data['razorpay_payment_id']
            
            # Update user subscription based on payment
            user = User.query.get(payment.user_id)
            if user and payment.metadata:
                try:
                    try:
                        metadata = eval(payment.metadata) if isinstance(payment.metadata, str) else payment.metadata
                        plan_name = metadata.get('plan_name')
                    except:
                        # If metadata parsing fails, get plan from payment description
                        if 'basic' in payment.description.lower():
                            plan_name = 'basic'
                        elif 'premium' in payment.description.lower():
                            plan_name = 'premium'
                        else:
                            plan_name = 'basic'  # default
                    
                    if plan_name:
                        user.subscription_plan = plan_name
                        user.subscription_status = 'active'
                        user.subscription_expiry = datetime.now() + timedelta(days=30)
                        
                        # Create subscription record
                        subscription = Subscription(
                            user_id=user.id,
                            plan_name=plan_name,
                            status='active',
                            current_period_start=datetime.now(),
                            current_period_end=user.subscription_expiry
                        )
                        db.session.add(subscription)
                        payment.subscription_id = subscription.id
                        
                except Exception as e:
                    logging.error(f"Error parsing metadata: {str(e)}")
            
            db.session.commit()
            log_activity(payment.user_id, 'payment_verified', f'Payment verified: {data["razorpay_payment_id"]}')
            
            return jsonify({'success': True, 'message': 'Payment verified successfully'})
        
        return jsonify({'error': 'Payment record not found'}), 404
    
    except Exception as e:
        logging.error(f"Error verifying payment: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/payment-link', methods=['POST'])
def create_payment_link():
    """Create a payment link for easy payments"""
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
            'basic': int(os.environ.get('BASIC_PLAN_AMOUNT', 49900)),
            'premium': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 149900))
        }
        
        if plan not in amount_mapping:
            return jsonify({'error': 'Invalid plan'}), 400
        
        amount = amount_mapping[plan]
        
        payment_link = payment_manager.get_payment_link(user, amount, plan)
        
        if payment_link:
            return jsonify({
                'success': True,
                'payment_link': payment_link,
                'message': 'Payment link created successfully'
            })
        else:
            return jsonify({'error': 'Failed to create payment link'}), 500
    
    except Exception as e:
        logging.error(f"Error creating payment link: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/payment-success')
def payment_success():
    """Handle successful payment callback"""
    payment_id = request.args.get('razorpay_payment_id')
    payment_link_id = request.args.get('razorpay_payment_link_id')
    
    if payment_id:
        # Log successful payment
        if 'user_id' in session:
            log_activity(session['user_id'], 'payment_success_callback', f'Payment success: {payment_id}')
        
        return render_template('subscription/payment_success.html', 
                             payment_id=payment_id,
                             payment_link_id=payment_link_id)
    
    return redirect(url_for('razorpay.subscription_plans'))

@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Razorpay webhooks"""
    try:
        # Verify webhook signature (optional but recommended)
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET')
        
        if webhook_secret and webhook_signature:
            # Verify webhook signature
            import hmac
            import hashlib
            
            body = request.get_data()
            expected_signature = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_signature, webhook_signature):
                logging.warning("Invalid webhook signature")
                return jsonify({'error': 'Invalid signature'}), 400
        
        event = request.get_json()
        event_type = event.get('event')
        
        if event_type == 'payment.captured':
            razorpay_service.handle_webhook_payment_captured(event['payload']['payment']['entity'])
        
        elif event_type == 'subscription.charged':
            razorpay_service.handle_webhook_subscription_charged(event['payload'])
        
        elif event_type == 'subscription.completed':
            # Handle subscription completion
            subscription_data = event['payload']['subscription']['entity']
            subscription = Subscription.query.filter_by(
                razorpay_subscription_id=subscription_data['id']
            ).first()
            
            if subscription:
                subscription.status = 'completed'
                db.session.commit()
                log_activity(subscription.user_id, 'subscription_completed', 
                           f'Subscription completed: {subscription_data["id"]}')
        
        elif event_type == 'subscription.cancelled':
            # Handle subscription cancellation
            subscription_data = event['payload']['subscription']['entity']
            subscription = Subscription.query.filter_by(
                razorpay_subscription_id=subscription_data['id']
            ).first()
            
            if subscription:
                subscription.status = 'cancelled'
                subscription.canceled_at = datetime.now()
                
                # Downgrade user to free plan
                user = User.query.get(subscription.user_id)
                if user:
                    user.subscription_plan = 'free'
                    user.subscription_status = 'canceled'
                    user.subscription_expiry = None
                
                db.session.commit()
                log_activity(subscription.user_id, 'subscription_cancelled', 
                           f'Subscription cancelled: {subscription_data["id"]}')
        
        else:
            logging.info(f"Unhandled webhook event: {event_type}")
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        logging.error(f"Webhook processing error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@bp.route('/subscription-status')
def subscription_status():
    """Get current subscription status for Indian users"""
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
    
    # Calculate usage stats (you can reuse the existing logic)
    from services.payment_service import SubscriptionManager
    usage_stats = SubscriptionManager.get_usage_stats(user)
    
    # Convert amounts to INR
    plan_amounts = {
        'basic': int(os.environ.get('BASIC_PLAN_AMOUNT', 49900)) / 100,
        'premium': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 149900)) / 100
    }
    
    return jsonify({
        'success': True,
        'subscription_plan': user.subscription_plan,
        'subscription_status': user.subscription_status,
        'subscription_expiry': user.subscription_expiry.isoformat() if user.subscription_expiry else None,
        'is_active': user.is_subscription_active(),
        'limits': user.get_plan_limits(),
        'usage': usage_stats,
        'currency': 'INR',
        'plan_amounts': plan_amounts,
        'trial_active': current_subscription.is_trial() if current_subscription else False,
        'days_until_expiry': current_subscription.days_until_expiry() if current_subscription else None
    })

@bp.route('/cancel-subscription', methods=['POST'])
def cancel_subscription():
    """Cancel subscription for Indian users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        cancel_immediately = data.get('cancel_immediately', False)
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        success = razorpay_service.cancel_subscription(
            user=user,
            cancel_at_cycle_end=not cancel_immediately
        )
        
        if success:
            message = "Subscription canceled immediately." if cancel_immediately else "Subscription will be canceled at the end of the current period."
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': 'Failed to cancel subscription'}), 500
    
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500