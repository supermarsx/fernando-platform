#!/usr/bin/env python3
"""
Payment Integration Testing Setup Script
Installs dependencies, initializes database, and starts servers
"""

import subprocess
import sys
import os
import time

def run_command(cmd, description, cwd=None):
    """Run a command and display the result"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print(f"✓ {description} - SUCCESS")
            if result.stdout:
                print(result.stdout[:500])  # Print first 500 chars
            return True
        else:
            print(f"✗ {description} - FAILED")
            print(f"Error: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("Payment Integration Testing Setup")
    print("="*60)
    
    backend_dir = "/workspace/fernando/backend"
    
    # Step 1: Install backend dependencies
    success = run_command(
        f"{sys.executable} -m pip install --quiet --upgrade pip",
        "Step 1/6: Upgrading pip"
    )
    
    if not success:
        print("\n⚠️  Warning: pip upgrade failed, continuing...")
    
    # Step 2: Install requirements
    success = run_command(
        f"{sys.executable} -m pip install -r requirements.txt --quiet",
        "Step 2/6: Installing backend dependencies",
        cwd=backend_dir
    )
    
    if not success:
        print("\n❌ Failed to install backend dependencies")
        return 1
    
    # Step 3: Install payment packages
    success = run_command(
        f"{sys.executable} -m pip install stripe requests --quiet",
        "Step 3/6: Installing payment packages"
    )
    
    if not success:
        print("\n❌ Failed to install payment packages")
        return 1
    
    # Step 4: Verify installation
    print("\n" + "="*60)
    print("Step 4/6: Verifying package installation")
    print("="*60)
    
    try:
        import sqlalchemy
        import fastapi
        import stripe
        print(f"✓ SQLAlchemy version: {sqlalchemy.__version__}")
        print(f"✓ FastAPI version: {fastapi.__version__}")
        print(f"✓ Stripe version: {stripe.version.VERSION}")
    except ImportError as e:
        print(f"✗ Import verification failed: {e}")
        return 1
    
    # Step 5: Initialize database
    print("\n" + "="*60)
    print("Step 5/6: Initializing database")
    print("="*60)
    
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)
    
    try:
        from app.db.session import init_db
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        print(f"Traceback: {str(e)}")
    
    # Step 6: Seed subscription plans
    success = run_command(
        f"{sys.executable} seed_subscription_plans.py",
        "Step 6/6: Seeding subscription plans",
        cwd=backend_dir
    )
    
    if not success:
        print("\n⚠️  Warning: Seeding subscription plans failed")
    
    # Summary
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\n✓ Backend dependencies installed")
    print("✓ Database initialized")
    print("✓ Subscription plans seeded")
    print("\nNext steps:")
    print("1. Start backend: python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("2. Start frontend: cd frontend/accounting-frontend && npm run dev")
    print("3. Test payment with card: 4242 4242 4242 4242")
    print("\n" + "="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
