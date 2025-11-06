#!/usr/bin/env python3
"""
Seed script to create default subscription plans for the billing system.
Creates three plans: Basic (€29/month), Professional (€99/month), Enterprise (€299/month)
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal
from app.models.billing import SubscriptionPlan, BillingCycle
from app.models.license import LicenseTier
from sqlalchemy.exc import IntegrityError


def seed_subscription_plans():
    """Seed default subscription plans into the database"""
    db = SessionLocal()
    
    try:
        # First, ensure we have license tiers (Basic, Professional, Enterprise)
        # These should already exist from the licensing system
        basic_tier = db.query(LicenseTier).filter(LicenseTier.tier_name == "Basic").first()
        professional_tier = db.query(LicenseTier).filter(LicenseTier.tier_name == "Professional").first()
        enterprise_tier = db.query(LicenseTier).filter(LicenseTier.tier_name == "Enterprise").first()
        
        if not basic_tier or not professional_tier or not enterprise_tier:
            print("⚠️  Warning: License tiers not found. Please ensure licensing system is initialized first.")
            print("   Expected tiers: Basic, Professional, Enterprise")
            return
        
        # Define subscription plans
        plans = [
            {
                "plan_name": "Basic Plan",
                "description": "Perfect for small businesses and freelancers",
                "tier_id": basic_tier.tier_id,
                "base_price": Decimal("29.00"),
                "currency": "EUR",
                "billing_cycle": BillingCycle.MONTHLY,
                "trial_days": 14,
                "is_active": True,
                "features": {
                    "max_users": 3,
                    "max_documents_per_month": 100,
                    "max_api_calls_per_month": 1000,
                    "support": "email",
                    "retention_days": 90,
                    "features": [
                        "OCR document processing",
                        "Basic invoice extraction",
                        "Email support",
                        "90-day data retention"
                    ]
                },
                "usage_limits": {
                    "documents": 100,
                    "api_calls": 1000,
                    "storage_gb": 5
                }
            },
            {
                "plan_name": "Professional Plan",
                "description": "Ideal for growing businesses with advanced needs",
                "tier_id": professional_tier.tier_id,
                "base_price": Decimal("99.00"),
                "currency": "EUR",
                "billing_cycle": BillingCycle.MONTHLY,
                "trial_days": 14,
                "is_active": True,
                "features": {
                    "max_users": 10,
                    "max_documents_per_month": 500,
                    "max_api_calls_per_month": 10000,
                    "support": "priority",
                    "retention_days": 365,
                    "features": [
                        "Advanced OCR processing",
                        "AI-powered extraction",
                        "Batch processing",
                        "Priority support",
                        "1-year data retention",
                        "API access",
                        "Custom workflows"
                    ]
                },
                "usage_limits": {
                    "documents": 500,
                    "api_calls": 10000,
                    "storage_gb": 50
                }
            },
            {
                "plan_name": "Enterprise Plan",
                "description": "For large organizations requiring unlimited scale",
                "tier_id": enterprise_tier.tier_id,
                "base_price": Decimal("299.00"),
                "currency": "EUR",
                "billing_cycle": BillingCycle.MONTHLY,
                "trial_days": 30,
                "is_active": True,
                "features": {
                    "max_users": -1,  # Unlimited
                    "max_documents_per_month": -1,  # Unlimited
                    "max_api_calls_per_month": -1,  # Unlimited
                    "support": "dedicated",
                    "retention_days": -1,  # Unlimited
                    "features": [
                        "Everything in Professional",
                        "Unlimited users and documents",
                        "Dedicated account manager",
                        "24/7 phone support",
                        "Unlimited data retention",
                        "Custom integrations",
                        "SLA guarantee",
                        "Advanced analytics",
                        "Multi-tenant support",
                        "White-label options"
                    ]
                },
                "usage_limits": {
                    "documents": -1,  # Unlimited
                    "api_calls": -1,  # Unlimited
                    "storage_gb": -1  # Unlimited
                }
            }
        ]
        
        # Create or update subscription plans
        created_count = 0
        updated_count = 0
        
        for plan_data in plans:
            # Check if plan already exists
            existing_plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_name == plan_data["plan_name"]
            ).first()
            
            if existing_plan:
                # Update existing plan
                for key, value in plan_data.items():
                    setattr(existing_plan, key, value)
                updated_count += 1
                print(f"✓ Updated: {plan_data['plan_name']} - €{plan_data['base_price']}/month")
            else:
                # Create new plan
                new_plan = SubscriptionPlan(**plan_data)
                db.add(new_plan)
                created_count += 1
                print(f"✓ Created: {plan_data['plan_name']} - €{plan_data['base_price']}/month")
        
        # Commit changes
        db.commit()
        
        print("\n" + "="*60)
        print(f"Subscription Plans Seeding Complete!")
        print(f"  Created: {created_count} plans")
        print(f"  Updated: {updated_count} plans")
        print(f"  Total Active Plans: {db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).count()}")
        print("="*60)
        
        # Display all active plans
        print("\nActive Subscription Plans:")
        active_plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
        for plan in active_plans:
            print(f"\n  {plan.plan_name}")
            print(f"    Price: €{plan.base_price}/{plan.billing_cycle.value}")
            print(f"    Trial: {plan.trial_days} days")
            print(f"    Description: {plan.description}")
        
    except IntegrityError as e:
        db.rollback()
        print(f"❌ Error: Database integrity error - {e}")
        print("   This usually means the plan already exists or there's a constraint violation.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding subscription plans: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting subscription plans seeding...")
    print("="*60)
    seed_subscription_plans()
