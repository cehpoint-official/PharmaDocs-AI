# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import razorpay
import logging
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models import User, Subscription, Payment, SubscriptionPlan
from database import db
from utils.helpers import log_activity

class RazorpayService:
    """Service for handling all payment operations with Razorpay (India)"""
    
    def __init__(self):
        self.client = razorpay.Client(
            auth=(
                os.environ.get('RAZORPAY_KEY_ID'),
                os.environ.get('RAZORPAY_KEY_SECRET')
            )
        )
    
    def create_customer(self, user: User) -> Optional[str]:
        """Create a Razorpay customer for the user"""
        try:
            customer_data = {
                'name': user.name,
                'email': user.email,
                'contact': user.phone if hasattr(user, 'phone') and user.phone else '',
                'notes': {
                    'user_id': str(user.id),
                    'system': 'PharmaDocs'
                }
            }
            
            customer = self.client.customer.create(customer_data)
            
            # Update user with Razorpay customer ID
            user.razorpay_customer_id = customer['id']
            db.session.commit()
            
            log_activity(user.id, 'razorpay_customer_created', f'Razorpay customer created: {customer["id"]}')
            return customer['id']
            
        except Exception as e:
            logging.error(f"Error creating Razorpay customer: {str(e)}")
            return None
    
    def get_or_create_customer(self, user: User) -> Optional[str]:
        """Get existing customer ID or create new customer"""
        if hasattr(user, 'razorpay_customer_id') and user.razorpay_customer_id:
            return user.razorpay_customer_id
        return self.create_customer(user)
    
    def create_order(self, user: User, amount: int, currency: str = 'INR', 
                     description: str = None, metadata: Dict[str, Any] = None) -> Optional[Dict]:
        """Create a Razorpay order for payment"""
        try:
            order_data = {
                'amount': amount,  # Amount in paise (1 INR = 100 paise)
                'currency': currency,
                'receipt': f'order_{user.id}_{int(datetime.now().timestamp())}',
                'notes': metadata or {}
            }
            
            if description:
                order_data['notes']['description'] = description
            
            order = self.client.order.create(order_data)
            
            # Record payment in database
            payment = Payment(
                user_id=user.id,
                razorpay_order_id=order['id'],
                amount=amount,
                currency=currency,
                status='created',
                description=description,
                metadata=str(metadata) if metadata else None
            )
            db.session.add(payment)
            db.session.commit()
            
            log_activity(user.id, 'razorpay_order_created', f'Order created: {order["id"]}')
            return order
            
        except Exception as e:
            logging.error(f"Error creating Razorpay order: {str(e)}")
            return None
    
    def verify_payment_signature(self, razorpay_order_id: str, razorpay_payment_id: str, 
                                razorpay_signature: str) -> bool:
        """Verify Razorpay payment signature"""
        try:
            # Create signature string
            body = razorpay_order_id + "|" + razorpay_payment_id
            
            # Generate expected signature
            expected_signature = hmac.new(
                key=os.environ.get('RAZORPAY_KEY_SECRET').encode(),
                msg=body.encode(),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, razorpay_signature)
            
        except Exception as e:
            logging.error(f"Error verifying payment signature: {str(e)}")
            return False
    
    def create_subscription(self, user: User, plan_name: str, trial_days: int = 0) -> Optional[Dict]:
        """Create a subscription for the user"""
        try:
            customer_id = self.get_or_create_customer(user)
            if not customer_id:
                return None
            
            # Get plan details
            plan_amounts = {
                'basic': int(os.environ.get('BASIC_PLAN_AMOUNT', 49900)),
                'premium': int(os.environ.get('PREMIUM_PLAN_AMOUNT', 149900))
            }
            
            if plan_name not in plan_amounts:
                return None
            
            amount = plan_amounts[plan_name]
            
            # Create Razorpay plan first
            plan_data = {
                'period': 'monthly',
                'interval': 1,
                'item': {
                    'name': f'PharmaDocs {plan_name.title()} Plan',
                    'description': f'{plan_name.title()} subscription plan for PharmaDocs',
                    'amount': amount,
                    'currency': 'INR'
                },
                'notes': {
                    'plan_name': plan_name,
                    'system': 'PharmaDocs'
                }
            }
            
            razorpay_plan = self.client.plan.create(plan_data)
            
            # Create subscription
            subscription_data = {
                'plan_id': razorpay_plan['id'],
                'customer_id': customer_id,
                'quantity': 1,
                'total_count': 12,  # 12 months
                'notes': {
                    'user_id': str(user.id),
                    'plan_name': plan_name
                }
            }
            
            # Add trial period if specified
            if trial_days > 0:
                trial_end = datetime.now() + timedelta(days=trial_days)
                subscription_data['start_at'] = int(trial_end.timestamp())
            
            subscription = self.client.subscription.create(subscription_data)
            
            # Record subscription in database
            db_subscription = Subscription(
                user_id=user.id,
                razorpay_subscription_id=subscription['id'],
                razorpay_plan_id=razorpay_plan['id'],
                plan_name=plan_name,
                status=subscription['status'],
                current_period_start=datetime.fromtimestamp(subscription['current_start']) if subscription.get('current_start') else datetime.now(),
                current_period_end=datetime.fromtimestamp(subscription['current_end']) if subscription.get('current_end') else datetime.now() + timedelta(days=30)
            )
            
            db.session.add(db_subscription)
            
            # Update user subscription
            user.subscription_plan = plan_name
            user.subscription_expiry = db_subscription.current_period_end
            user.subscription_status = subscription['status']
            
            db.session.commit()
            
            log_activity(user.id, 'subscription_created', f'Subscription created: {subscription["id"]}')
            
            return {
                'subscription_id': subscription['id'],
                'plan_id': razorpay_plan['id'],
                'status': subscription['status'],
                'short_url': subscription.get('short_url')
            }
            
        except Exception as e:
            logging.error(f"Error creating subscription: {str(e)}")
            return None
    
    def cancel_subscription(self, user: User, cancel_at_cycle_end: bool = True) -> bool:
        """Cancel user's subscription"""
        try:
            # Get active subscription
            subscription = Subscription.query.filter_by(
                user_id=user.id, 
                status='active'
            ).first()
            
            if not subscription or not subscription.razorpay_subscription_id:
                return False
            
            # Cancel in Razorpay
            cancel_data = {'cancel_at_cycle_end': cancel_at_cycle_end}
            razorpay_subscription = self.client.subscription.cancel(
                subscription.razorpay_subscription_id, 
                cancel_data
            )
            
            # Update database
            subscription.cancel_at_period_end = cancel_at_cycle_end
            subscription.status = razorpay_subscription['status']
            
            if not cancel_at_cycle_end:
                subscription.canceled_at = datetime.now()
                user.subscription_plan = 'free'
                user.subscription_expiry = None
                user.subscription_status = 'canceled'
            
            db.session.commit()
            
            log_activity(user.id, 'subscription_canceled', f'Subscription canceled: {subscription.razorpay_subscription_id}')
            return True
            
        except Exception as e:
            logging.error(f"Error canceling subscription: {str(e)}")
            return False
    
    def handle_webhook_payment_captured(self, payment_data: Dict[str, Any]) -> bool:
        """Handle successful payment webhook"""
        try:
            order_id = payment_data.get('order_id')
            payment_id = payment_data.get('id')
            
            # Find payment in database
            payment = Payment.query.filter_by(
                razorpay_order_id=order_id
            ).first()
            
            if payment:
                payment.status = 'captured'
                payment.razorpay_payment_id = payment_id
                
                # Add additional payment details
                payment.payment_method = payment_data.get('method', 'unknown')
                payment.metadata = str(payment_data)
                
                db.session.commit()
                log_activity(payment.user_id, 'payment_captured', f'Payment captured: {payment_id}')
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error handling payment captured webhook: {str(e)}")
            return False
    
    def handle_webhook_subscription_charged(self, subscription_data: Dict[str, Any]) -> bool:
        """Handle subscription charge webhook"""
        try:
            subscription_id = subscription_data.get('subscription_id')
            payment_data = subscription_data.get('payment', {})
            
            # Find subscription in database
            subscription = Subscription.query.filter_by(
                razorpay_subscription_id=subscription_id
            ).first()
            
            if subscription:
                # Record payment
                payment = Payment(
                    user_id=subscription.user_id,
                    subscription_id=subscription.id,
                    razorpay_payment_id=payment_data.get('id'),
                    amount=payment_data.get('amount', 0),
                    currency=payment_data.get('currency', 'INR'),
                    status='captured',
                    description=f"Recurring payment for {subscription.plan_name} plan",
                    payment_method=payment_data.get('method'),
                    metadata=str(subscription_data)
                )
                db.session.add(payment)
                db.session.commit()
                
                log_activity(subscription.user_id, 'subscription_charged', 
                           f'Subscription charged: {subscription_id}')
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error handling subscription charged webhook: {str(e)}")
            return False
    
    def get_payment_link(self, user: User, amount: int, plan_name: str) -> Optional[str]:
        """Create payment link for one-time payments"""
        try:
            payment_link_data = {
                'amount': amount,
                'currency': 'INR',
                'accept_partial': False,
                'description': f'PharmaDocs {plan_name.title()} Plan Subscription',
                'customer': {
                    'name': user.name,
                    'email': user.email,
                    'contact': user.phone if hasattr(user, 'phone') and user.phone else ''
                },
                'notify': {
                    'sms': True,
                    'email': True
                },
                'reminder_enable': True,
                'notes': {
                    'user_id': str(user.id),
                    'plan_name': plan_name,
                    'system': 'PharmaDocs'
                },
                'callback_url': f"{os.environ.get('BASE_URL', 'http://localhost:5000')}/subscription/payment-success",
                'callback_method': 'get'
            }
            
            payment_link = self.client.payment_link.create(payment_link_data)
            
            log_activity(user.id, 'payment_link_created', f'Payment link created: {payment_link["id"]}')
            return payment_link['short_url']
            
        except Exception as e:
            logging.error(f"Error creating payment link: {str(e)}")
            return None

class IndianPaymentGatewayManager:
    """Manager for multiple Indian payment gateways"""
    
    def __init__(self):
        self.razorpay = RazorpayService()
        self.primary_gateway = 'razorpay'
    
    def create_order(self, user: User, amount: int, plan_name: str, gateway: str = None) -> Optional[Dict]:
        """Create order with specified or primary gateway"""
        gateway = gateway or self.primary_gateway
        
        if gateway == 'razorpay':
            return self.razorpay.create_order(
                user=user,
                amount=amount,
                description=f'PharmaDocs {plan_name.title()} Plan',
                metadata={'plan_name': plan_name}
            )
        
        # Add other gateways here (Paytm, Instamojo, etc.)
        return None
    
    def get_payment_link(self, user: User, amount: int, plan_name: str) -> Optional[str]:
        """Get payment link for the user"""
        return self.razorpay.get_payment_link(user, amount, plan_name)
    
    def verify_payment(self, gateway_data: Dict[str, Any]) -> bool:
        """Verify payment based on gateway"""
        if 'razorpay_order_id' in gateway_data:
            return self.razorpay.verify_payment_signature(
                gateway_data['razorpay_order_id'],
                gateway_data['razorpay_payment_id'],
                gateway_data['razorpay_signature']
            )
        
        return False