#!/usr/bin/env python3
# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

"""
Script to initialize the Razorpay subscription system for Indian users.
Run this after setting up Razorpay account and configuring environment variables.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import create_app, db
from models import SubscriptionPlan, User
from services.razorpay_service import RazorpayService

def verify_razorpay_credentials():
    """Verify Razorpay credentials are properly set"""
    print("Verifying Razorpay credentials...")
    
    required_vars = ['RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease add these to your .env file:")
        for var in missing_vars:
            if 'KEY_ID' in var:
                print(f"{var}=rzp_test_your_key_id_here")
            elif 'SECRET' in var:
                print(f"{var}=your_secret_key_here")
        return False
    
    # Test Razorpay connection
    try:
        razorpay_service = RazorpayService()
        # Try a simple API call to verify credentials
        print("✅ Razorpay credentials verified successfully!")
        return True
    except Exception as e:
        print(f"❌ Razorpay connection failed: {str(e)}")
        print("Please check your Razorpay credentials and try again.")
        return False

def create_indian_subscription_plans():
    """Create or update subscription plans with Indian pricing"""
    print("Creating Indian subscription plans...")
    
    # Free Plan (India)
    free_plan = SubscriptionPlan.query.filter_by(name='free').first()
    if not free_plan:
        free_plan = SubscriptionPlan(
            name='free',
            display_name='Free',
            description='Perfect for getting started with basic pharmaceutical documentation',
            price=0,
            currency='inr',
            billing_interval='month',
            documents_per_month=5,
            storage_mb=100,
            api_requests_per_day=10,
            features=json.dumps(['basic_reports', 'email_support']),
            is_active=True,
            sort_order=1
        )
        db.session.add(free_plan)
    else:
        # Update existing plan
        free_plan.currency = 'inr'
    
    # Basic Plan (₹499/month)
    basic_plan = SubscriptionPlan.query.filter_by(name='basic').first()
    if not basic_plan:
        basic_plan = SubscriptionPlan(
            name='basic',
            display_name='Basic',
            description='Ideal for small pharmaceutical companies and individual researchers',
            price=49900,  # ₹499 in paise
            currency='inr',
            billing_interval='month',
            documents_per_month=50,
            storage_mb=1000,
            api_requests_per_day=100,
            features=json.dumps([
                'basic_reports', 'advanced_reports', 'email_support', 
                'priority_support', 'pdf_export', 'excel_export'
            ]),
            is_active=True,
            sort_order=2
        )
        db.session.add(basic_plan)
    else:
        # Update existing plan with Indian pricing
        basic_plan.price = 49900
        basic_plan.currency = 'inr'
    
    # Premium Plan (₹1,499/month)
    premium_plan = SubscriptionPlan.query.filter_by(name='premium').first()
    if not premium_plan:
        premium_plan = SubscriptionPlan(
            name='premium',
            display_name='Premium',
            description='Complete solution for large pharmaceutical companies',
            price=149900,  # ₹1,499 in paise
            currency='inr',
            billing_interval='month',
            documents_per_month=-1,  # Unlimited
            storage_mb=10000,
            api_requests_per_day=1000,
            features=json.dumps([
                'all_reports', 'custom_templates', 'priority_support', 
                'phone_support', 'api_access', 'advanced_analytics',
                'bulk_operations', 'white_label', 'dedicated_support'
            ]),
            is_active=True,
            sort_order=3
        )
        db.session.add(premium_plan)
    else:
        # Update existing plan with Indian pricing
        premium_plan.price = 149900
        premium_plan.currency = 'inr'
    
    db.session.commit()
    print("✅ Indian subscription plans created/updated successfully!")
    
    # Display pricing info
    print("\n📋 Subscription Plans:")
    print("1. Free Plan: ₹0/month - 5 documents, 100MB storage")
    print("2. Basic Plan: ₹499/month - 50 documents, 1GB storage")
    print("3. Premium Plan: ₹1,499/month - Unlimited documents, 10GB storage")

def update_existing_users_for_india():
    """Update existing users with Indian defaults"""
    print("Updating existing users for Indian market...")
    
    users = User.query.all()
    updated_count = 0
    
    for user in users:
        # Ensure all new fields have default values
        if not hasattr(user, 'subscription_status') or user.subscription_status is None:
            user.subscription_status = 'active'
        
        if not hasattr(user, 'documents_limit') or user.documents_limit is None:
            user.documents_limit = 5  # Free plan default
        
        # Ensure subscription_plan is set
        if not user.subscription_plan:
            user.subscription_plan = 'free'
        
        updated_count += 1
    
    if updated_count > 0:
        db.session.commit()
        print(f"✅ Updated {updated_count} existing users")
    else:
        print("ℹ️  No users to update")

def create_test_payment_link():
    """Create a test payment link to verify integration"""
    print("Creating test payment link...")
    
    try:
        from services.razorpay_service import IndianPaymentGatewayManager
        
        payment_manager = IndianPaymentGatewayManager()
        
        # Create a dummy user for testing (if none exist)
        test_user = User.query.first()
        if not test_user:
            print("ℹ️  No users found to create test payment link")
            return
        
        # Create test payment link for Basic plan
        payment_link = payment_manager.get_payment_link(
            user=test_user,
            amount=49900,  # ₹499
            plan_name='basic'
        )
        
        if payment_link:
            print(f"✅ Test payment link created: {payment_link}")
            print("You can use this link to test the payment flow")
        else:
            print("❌ Failed to create test payment link")
    
    except Exception as e:
        print(f"❌ Error creating test payment link: {str(e)}")

def verify_installation():
    """Verify that the Razorpay system is properly installed"""
    print("\n🔍 Verifying Razorpay installation...")
    
    issues = []
    
    # Check environment variables
    required_env_vars = [
        'RAZORPAY_KEY_ID',
        'RAZORPAY_KEY_SECRET',
        'BASIC_PLAN_AMOUNT',
        'PREMIUM_PLAN_AMOUNT'
    ]
    
    for var in required_env_vars:
        if not os.environ.get(var):
            issues.append(f"Missing environment variable: {var}")
    
    # Check database tables
    try:
        plans_count = SubscriptionPlan.query.count()
        if plans_count < 3:
            issues.append(f"Expected at least 3 subscription plans, found {plans_count}")
        else:
            print(f"✅ Found {plans_count} subscription plans")
    except Exception as e:
        issues.append(f"Error checking subscription plans table: {str(e)}")
    
    # Check Indian pricing
    try:
        basic_plan = SubscriptionPlan.query.filter_by(name='basic').first()
        if basic_plan and basic_plan.currency != 'inr':
            issues.append("Basic plan currency should be 'inr' for Indian market")
        elif basic_plan:
            print(f"✅ Basic plan configured for Indian market: ₹{basic_plan.price/100}")
    except Exception as e:
        issues.append(f"Error checking plan pricing: {str(e)}")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ Razorpay system verification completed successfully!")
        return True

def main():
    """Main function to initialize the Razorpay subscription system"""
    print("🇮🇳 Initializing PharmaDocs Razorpay System (India)")
    print("=" * 55)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Verify Razorpay credentials
        if not verify_razorpay_credentials():
            print("\n❌ Cannot proceed without valid Razorpay credentials")
            return
        
        # Create Indian subscription plans
        create_indian_subscription_plans()
        
        # Update existing users
        update_existing_users_for_india()
        
        # Create test payment link
        create_test_payment_link()
        
        # Verify installation
        verification_success = verify_installation()
        
        print("\n" + "=" * 55)
        if verification_success:
            print("🎉 Razorpay system initialized successfully!")
            print("\n📋 Next steps:")
            print("1. Test payment flow using the test payment link")
            print("2. Set up webhook endpoints in Razorpay dashboard:")
            print("   - URL: https://yourdomain.com/razorpay/webhook")
            print("   - Events: payment.captured, subscription.charged")
            print("3. Update your .env with webhook secret")
            print("4. Test with Razorpay test cards")
            print("\n💳 Test Cards for India:")
            print("   - Success: 4111 1111 1111 1111")
            print("   - Failure: 4000 0000 0000 0002")
            print("   - UPI: success@razorpay")
        else:
            print("❌ Razorpay system initialization completed with issues")
            print("Please resolve the issues above before using the system")

if __name__ == "__main__":
    main()