#!/bin/bash
# Setup script for billing system integration
# This script initializes the billing database tables and seeds subscription plans

echo "============================================================"
echo "Billing System Setup Script"
echo "============================================================"
echo ""

cd "$(dirname "$0")"

echo "Step 1: Checking Python environment..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }

echo ""
echo "Step 2: Initializing billing database tables..."
echo "This will create all necessary billing tables via SQLAlchemy"

# Create a simple script to initialize the database
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from app.db.session import init_db

print("Initializing database with billing tables...")
try:
    init_db()
    print("✓ Database tables created successfully")
except Exception as e:
    print(f"✗ Error creating tables: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "Error: Failed to initialize database tables"
    exit 1
fi

echo ""
echo "Step 3: Seeding subscription plans..."
python3 seed_subscription_plans.py

if [ $? -ne 0 ]; then
    echo "Warning: Seeding subscription plans encountered an error"
    echo "You may need to run this manually: python3 seed_subscription_plans.py"
else
    echo "✓ Subscription plans seeded successfully"
fi

echo ""
echo "============================================================"
echo "Billing System Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Start/restart the backend server: uvicorn app.main:app --reload"
echo "2. Access billing at: http://localhost:3000/billing"
echo "3. Access admin billing analytics at: http://localhost:3000/admin/billing-analytics"
echo ""
echo "Subscription Plans Created:"
echo "  • Basic Plan: €29/month"
echo "  • Professional Plan: €99/month"
echo "  • Enterprise Plan: €299/month"
echo ""
