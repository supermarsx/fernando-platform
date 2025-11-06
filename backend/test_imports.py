import sys
print("Python executable:", sys.executable)
try:
    import sqlalchemy
    print("✓ SQLAlchemy installed:", sqlalchemy.__version__)
except ImportError as e:
    print("✗ SQLAlchemy NOT installed:", e)
try:
    import fastapi
    print("✓ FastAPI installed:", fastapi.__version__)
except ImportError as e:
    print("✗ FastAPI NOT installed:", e)
try:
    import stripe
    print("✓ Stripe installed:", stripe.version.VERSION)
except ImportError as e:
    print("✗ Stripe NOT installed:", e)
