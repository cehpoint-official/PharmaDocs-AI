#!/usr/bin/env python3
# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

"""
Script to initialize the subscription system with default plans and settings.
Run this after setting up Stripe and migrating the database.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import create_app, db
from models import SubscriptionPlan, User
import stripe

def setup_stripe_products():
    """Create products and prices in Stripe"""
    print("Setting up Stripe products and prices...")
    
    try:
        # Initialize Stripe
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            print("Warning: STRIPE_SECRET_KEY not found in environment variables")
            return None, None
        
        # Create Basic Plan Product
        basic_product = stripe.Product.create(
            name="PharmaDocs Basic Plan",
            description="Basic pharmaceutical documentation plan with 50 documents per month",
            metadata={
                'plan_name': 'basic',
                'system': 'PharmaDocs'
            }
        )
        
        basic_price = stripe.Price.create(
            product=basic_product.id,
            unit_amount=999,  # $9.99 in cents
            currency='usd',
            recurring={'interval': 'month'},
            metadata={
                'plan_name': 'basic',
                'system': 'PharmaDocs'
            }
        )
        
        # Create Premium Plan Product
        premium_product = stripe.Product.create(
            name="PharmaDocs Premium Plan",
            description="Premium pharmaceutical documentation plan with unlimited documents",
            metadata={
                'plan_name': 'premium',
                'system': 'PharmaDocs'
            }
        )
        
        premium_price = stripe.Price.create(
            product=premium_product.id,
            unit_amount=2999,  # $29.99 in cents
            currency='usd',
            recurring={'interval': 'month'},
            metadata={
                'plan_name': 'premium',
                'system': 'PharmaDocs'
            }
        )
        
        print(f"Created Stripe products and prices:")
        print(f"Basic Plan Price ID: {basic_price.id}")
        print(f"Premium Plan Price ID: {premium_price.id}")
        print("\nAdd these to your .env file:")
        print(f"BASIC_PLAN_PRICE_ID={basic_price.id}")
        print(f"PREMIUM_PLAN_PRICE_ID={premium_price.id}")
        
        return basic_price.id, premium_price.id
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return None, None
    except Exception as e:
        print(f"Error setting up Stripe: {str(e)}")
        return None, None

def create_subscription_plans(basic_price_id=None, premium_price_id=None):
    """Create or update subscription plans in the database"""
    print("Creating subscription plans in database...")
    
    # Free Plan
    free_plan = SubscriptionPlan.query.filter_by(name='free').first()
    if not free_plan:
        free_plan = SubscriptionPlan(
            name='free',
            display_name='Free',
            description='Perfect for getting started with basic pharmaceutical documentation',
            price=0,
            currency='usd',
            billing_interval='month',
            stripe_price_id=None,
            documents_per_month=5,
            storage_mb=100,
            api_requests_per_day=10,
            features=json.dumps(['basic_reports', 'email_support']),
            is_active=True,
            sort_order=1
        )
        db.session.add(free_plan)
    
    # Basic Plan
    basic_plan = SubscriptionPlan.query.filter_by(name='basic').first()
    if not basic_plan:
        basic_plan = SubscriptionPlan(
            name='basic',
            display_name='Basic',
            description='Ideal for small pharmaceutical companies and individual researchers',
            price=999,
            currency='usd',
            billing_interval='month',
            stripe_price_id=basic_price_id,
            documents_per_month=50,
            storage_mb=1000,
            api_requests_per_day=100,
            features=json.dumps(['basic_reports', 'advanced_reports', 'email_support', 'priority_support', 'pdf_export']),
            is_active=True,
            sort_order=2
        )
        db.session.add(basic_plan)
    else:
        # Update existing plan with Stripe price ID
        if basic_price_id:
            basic_plan.stripe_price_id = basic_price_id
    
    # Premium Plan
    premium_plan = SubscriptionPlan.query.filter_by(name='premium').first()
    if not premium_plan:
        premium_plan = SubscriptionPlan(
            name='premium',
            display_name='Premium',
            description='Complete solution for large pharmaceutical companies',
            price=2999,
            currency='usd',
            billing_interval='month',
            stripe_price_id=premium_price_id,
            documents_per_month=-1,  # Unlimited
            storage_mb=10000,
            api_requests_per_day=1000,
            features=json.dumps([
                'all_reports', 'custom_templates', 'priority_support', 
                'phone_support', 'api_access', 'advanced_analytics',
                'bulk_export', 'white_label'
            ]),
            is_active=True,
            sort_order=3
        )
        db.session.add(premium_plan)
    else:
        # Update existing plan with Stripe price ID
        if premium_price_id:
            premium_plan.stripe_price_id = premium_price_id
    
    db.session.commit()
    print("Subscription plans created/updated successfully!")

def update_existing_users():
    """Update existing users with default subscription settings"""
    print("Updating existing users...")
    
    users = User.query.all()
    updated_count = 0
    
    for user in users:
        # Set default values for new fields if they don't exist
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
        print(f"Updated {updated_count} existing users with subscription defaults")
    else:
        print("No users to update")

def verify_installation():
    """Verify that the subscription system is properly installed"""
    print("\nVerifying installation...")
    
    issues = []
    
    # Check environment variables
    required_env_vars = [
        'STRIPE_PUBLISHABLE_KEY',
        'STRIPE_SECRET_KEY',
        'STRIPE_WEBHOOK_SECRET'
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
            print(f"✓ Found {plans_count} subscription plans")
    except Exception as e:
        issues.append(f"Error checking subscription plans table: {str(e)}")
    
    # Check Stripe connection
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if stripe.api_key:
            stripe.Account.retrieve()
            print("✓ Stripe connection successful")
        else:
            issues.append("Cannot test Stripe connection without STRIPE_SECRET_KEY")
    except Exception as e:
        issues.append(f"Stripe connection failed: {str(e)}")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n✅ Subscription system verification completed successfully!")
        return True

def main():
    """Main function to initialize the subscription system"""
    print("🚀 Initializing PharmaDocs Subscription System")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Set up Stripe products and prices
        basic_price_id, premium_price_id = setup_stripe_products()
        
        # Create subscription plans in database
        create_subscription_plans(basic_price_id, premium_price_id)
        
        # Update existing users
        update_existing_users()
        
        # Verify installation
        verification_success = verify_installation()
        
        print("\n" + "=" * 50)
        if verification_success:
            print("🎉 Subscription system initialized successfully!")
            print("\nNext steps:")
            print("1. Update your .env file with the Stripe price IDs shown above")
            print("2. Set up webhook endpoints in your Stripe dashboard")
            print("3. Test the subscription flow with Stripe test cards")
            print("4. Configure your subscription plans in the admin panel")
        else:
            print("❌ Subscription system initialization completed with issues")
            print("Please resolve the issues above before using the subscription system")

if __name__ == "__main__":
    main()