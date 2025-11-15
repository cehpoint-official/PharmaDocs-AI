# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import stripe
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models import User, Subscription, Payment, SubscriptionPlan, Document
from database import db
from utils.helpers import log_activity

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class PaymentService:
    """Service for handling all payment operations with Stripe"""
    
    @staticmethod
    def create_customer(user: User) -> Optional[str]:
        """Create a Stripe customer for the user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={
                    'user_id': str(user.id),
                    'system': 'PharmaDocs'
                }
            )
            
            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            db.session.commit()
            
            log_activity(user.id, 'stripe_customer_created', f'Stripe customer created: {customer.id}')
            return customer.id
            
        except stripe.error.StripeError as e:
            logging.error(f"Error creating Stripe customer: {str(e)}")
            return None
    
    @staticmethod
    def get_or_create_customer(user: User) -> Optional[str]:
        """Get existing customer ID or create new customer"""
        if user.stripe_customer_id:
            return user.stripe_customer_id
        return PaymentService.create_customer(user)
    
    @staticmethod
    def create_payment_intent(user: User, amount: int, currency: str = 'usd', 
                            description: str = None, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Create a payment intent for one-time payment"""
        try:
            customer_id = PaymentService.get_or_create_customer(user)
            if not customer_id:
                return None
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                description=description or f"Payment for {user.name}",
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                }
            )
            
            # Record payment in database
            payment = Payment(
                user_id=user.id,
                stripe_payment_intent_id=payment_intent.id,
                amount=amount,
                currency=currency,
                status='pending',
                description=description,
                metadata=payment_intent.metadata
            )
            db.session.add(payment)
            db.session.commit()
            
            log_activity(user.id, 'payment_intent_created', f'Payment intent created: {payment_intent.id}')
            return payment_intent.client_secret
            
        except stripe.error.StripeError as e:
            logging.error(f"Error creating payment intent: {str(e)}")
            return None
    
    @staticmethod
    def create_subscription(user: User, price_id: str, trial_days: int = 0) -> Optional[Dict[str, Any]]:
        """Create a subscription for the user"""
        try:
            customer_id = PaymentService.get_or_create_customer(user)
            if not customer_id:
                return None
            
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'payment_settings': {'save_default_payment_method': 'on_subscription'},
                'expand': ['latest_invoice.payment_intent'],
                'metadata': {
                    'user_id': str(user.id),
                    'system': 'PharmaDocs'
                }
            }
            
            # Add trial period if specified
            if trial_days > 0:
                subscription_params['trial_period_days'] = trial_days
            
            subscription = stripe.Subscription.create(**subscription_params)
            
            # Get plan information from price
            price = stripe.Price.retrieve(price_id)
            plan_name = PaymentService.get_plan_name_from_price_id(price_id)
            
            # Record subscription in database
            db_subscription = Subscription(
                user_id=user.id,
                stripe_subscription_id=subscription.id,
                plan_name=plan_name,
                status=subscription.status,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end)
            )
            
            # Add trial information if applicable
            if hasattr(subscription, 'trial_start') and subscription.trial_start:
                db_subscription.trial_start = datetime.fromtimestamp(subscription.trial_start)
                db_subscription.trial_end = datetime.fromtimestamp(subscription.trial_end)
            
            db.session.add(db_subscription)
            
            # Update user subscription
            user.subscription_plan = plan_name
            user.subscription_expiry = db_subscription.current_period_end
            user.subscription_status = subscription.status
            
            db.session.commit()
            
            log_activity(user.id, 'subscription_created', f'Subscription created: {subscription.id}')
            
            return {
                'subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice.payment_intent else None,
                'status': subscription.status
            }
            
        except stripe.error.StripeError as e:
            logging.error(f"Error creating subscription: {str(e)}")
            return None
    
    @staticmethod
    def cancel_subscription(user: User, cancel_at_period_end: bool = True) -> bool:
        """Cancel user's subscription"""
        try:
            # Get active subscription
            subscription = Subscription.query.filter_by(
                user_id=user.id, 
                status='active'
            ).first()
            
            if not subscription or not subscription.stripe_subscription_id:
                return False
            
            # Cancel in Stripe
            if cancel_at_period_end:
                stripe_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            else:
                stripe_subscription = stripe.Subscription.delete(
                    subscription.stripe_subscription_id
                )
            
            # Update database
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.status = stripe_subscription.status
            
            if not cancel_at_period_end:
                subscription.canceled_at = datetime.now()
                user.subscription_plan = 'free'
                user.subscription_expiry = None
                user.subscription_status = 'canceled'
            
            db.session.commit()
            
            log_activity(user.id, 'subscription_canceled', f'Subscription canceled: {subscription.stripe_subscription_id}')
            return True
            
        except stripe.error.StripeError as e:
            logging.error(f"Error canceling subscription: {str(e)}")
            return False
    
    @staticmethod
    def get_plan_name_from_price_id(price_id: str) -> str:
        """Get plan name from Stripe price ID"""
        plan_mappings = {
            os.environ.get('BASIC_PLAN_PRICE_ID'): 'basic',
            os.environ.get('PREMIUM_PLAN_PRICE_ID'): 'premium'
        }
        return plan_mappings.get(price_id, 'free')
    
    @staticmethod
    def handle_webhook_payment_succeeded(payment_intent_data: Dict[str, Any]) -> bool:
        """Handle successful payment webhook"""
        try:
            payment_intent_id = payment_intent_data['id']
            
            # Find payment in database
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if payment:
                payment.status = 'succeeded'
                payment.stripe_charge_id = payment_intent_data.get('charges', {}).get('data', [{}])[0].get('id')
                payment.receipt_url = payment_intent_data.get('charges', {}).get('data', [{}])[0].get('receipt_url')
                
                db.session.commit()
                log_activity(payment.user_id, 'payment_succeeded', f'Payment completed: {payment_intent_id}')
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error handling payment succeeded webhook: {str(e)}")
            return False
    
    @staticmethod
    def handle_webhook_subscription_updated(subscription_data: Dict[str, Any]) -> bool:
        """Handle subscription update webhook"""
        try:
            stripe_subscription_id = subscription_data['id']
            
            # Find subscription in database
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=stripe_subscription_id
            ).first()
            
            if subscription:
                # Update subscription details
                subscription.status = subscription_data['status']
                subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
                subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
                subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
                
                # Update user details
                user = User.query.get(subscription.user_id)
                if user:
                    user.subscription_status = subscription_data['status']
                    user.subscription_expiry = subscription.current_period_end
                    
                    # If subscription is canceled or past_due, downgrade to free
                    if subscription_data['status'] in ['canceled', 'unpaid']:
                        user.subscription_plan = 'free'
                        user.subscription_expiry = None
                
                db.session.commit()
                log_activity(subscription.user_id, 'subscription_updated', f'Subscription updated: {stripe_subscription_id}')
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error handling subscription updated webhook: {str(e)}")
            return False
    
    @staticmethod
    def get_subscription_plans() -> list:
        """Get all available subscription plans"""
        return SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.sort_order).all()
    
    @staticmethod
    def get_user_payment_history(user: User, limit: int = 10) -> list:
        """Get user's payment history"""
        return Payment.query.filter_by(user_id=user.id).order_by(Payment.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_subscription_history(user: User, limit: int = 10) -> list:
        """Get user's subscription history"""
        return Subscription.query.filter_by(user_id=user.id).order_by(Subscription.created_at.desc()).limit(limit).all()

class SubscriptionManager:
    """Manager for subscription-related operations"""
    
    @staticmethod
    def check_subscription_limits(user: User, action: str) -> Dict[str, Any]:
        """Check if user can perform action based on subscription limits"""
        limits = user.get_plan_limits()
        result = {
            'allowed': True,
            'message': '',
            'upgrade_required': False,
            'current_plan': user.subscription_plan
        }
        
        if action == 'create_document':
            if not user.can_create_document():
                result.update({
                    'allowed': False,
                    'message': f"Document limit reached for {user.subscription_plan} plan. Upgrade to create more documents.",
                    'upgrade_required': True
                })
        
        elif action == 'api_request':
            # Check daily API limit (would need to implement tracking)
            pass
        
        elif action == 'storage_upload':
            # Check storage limit (would need to implement tracking)
            pass
        
        return result
    
    @staticmethod
    def get_usage_stats(user: User) -> Dict[str, Any]:
        """Get current usage statistics for the user"""
        from datetime import datetime
        from sqlalchemy import extract
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Count documents created this month
        monthly_docs = Document.query.filter(
            Document.user_id == user.id,
            extract('month', Document.created_at) == current_month,
            extract('year', Document.created_at) == current_year
        ).count()
        
        limits = user.get_plan_limits()
        
        return {
            'documents': {
                'used': monthly_docs,
                'limit': limits['documents_per_month'],
                'percentage': (monthly_docs / limits['documents_per_month'] * 100) if limits['documents_per_month'] > 0 else 0
            },
            'storage': {
                'used_mb': 0,  # Would need to implement file size tracking
                'limit_mb': limits['storage_mb'],
                'percentage': 0
            },
            'api_requests': {
                'used_today': 0,  # Would need to implement API usage tracking
                'limit_daily': limits['api_requests_per_day'],
                'percentage': 0
            }
        }