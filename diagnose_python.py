#!/usr/bin/env python3
"""
Quick diagnostic script to find the correct Python environment
"""

import sys
import subprocess

print("="*60)
print("Python Environment Diagnostic")
print("="*60)
print(f"\nCurrent Python: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"\nPython path:")
for p in sys.path:
    print(f"  - {p}")

print("\n" + "="*60)
print("Checking for installed packages:")
print("="*60)

packages = ["sqlalchemy", "fastapi", "uvicorn", "stripe", "requests"]

for package in packages:
    try:
        mod = __import__(package)
        version = getattr(mod, "__version__", "unknown")
        print(f"✓ {package:15} version: {version}")
    except ImportError:
        print(f"✗ {package:15} NOT INSTALLED")

print("\n" + "="*60)
print("Testing pip availability:")
print("="*60)

try:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
        text=True
    )
    print(f"✓ pip available: {result.stdout.strip()}")
except Exception as e:
    print(f"✗ pip not available: {e}")

print("\n" + "="*60)
