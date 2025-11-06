#!/usr/bin/env python
import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("\nTrying to import modules:")

try:
    import sqlalchemy
    print("✓ sqlalchemy version:", sqlalchemy.__version__)
except ImportError as e:
    print("✗ sqlalchemy:", e)

try:
    import sklearn
    print("✓ scikit-learn version:", sklearn.__version__)
except ImportError as e:
    print("✗ scikit-learn:", e)

try:
    import lightgbm
    print("✓ lightgbm version:", lightgbm.__version__)
except ImportError as e:
    print("✗ lightgbm:", e)

try:
    import numpy
    print("✓ numpy version:", numpy.__version__)
except ImportError as e:
    print("✗ numpy:", e)

try:
    import joblib
    print("✓ joblib version:", joblib.__version__)
except ImportError as e:
    print("✗ joblib:", e)
