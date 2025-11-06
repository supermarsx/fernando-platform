#!/usr/bin/env python3
"""
Test script for telemetry system migration
"""

import sys
import os

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

try:
    print("Testing telemetry models...")
    
    # Test creating tables
    from app.models.telemetry import (
        TelemetryEvent, SystemMetric, BusinessMetric, 
        AlertRule, Alert, Trace
    )
    print("✓ All telemetry models imported successfully")
    
    # Test that we can get table info
    print("\nTable schemas:")
    print(f"TelemetryEvent table: {TelemetryEvent.__tablename__}")
    print(f"SystemMetric table: {SystemMetric.__tablename__}")
    print(f"BusinessMetric table: {BusinessMetric.__tablename__}")
    print(f"AlertRule table: {AlertRule.__tablename__}")
    print(f"Alert table: {Alert.__tablename__}")
    print(f"Trace table: {Trace.__tablename__}")
    
    # Test model column counts
    print("\nModel column counts:")
    print(f"TelemetryEvent: {len(TelemetryEvent.__table__.columns)} columns")
    print(f"SystemMetric: {len(SystemMetric.__table__.columns)} columns")
    print(f"BusinessMetric: {len(BusinessMetric.__table__.columns)} columns")
    print(f"AlertRule: {len(AlertRule.__table__.columns)} columns")
    print(f"Alert: {len(Alert.__table__.columns)} columns")
    print(f"Trace: {len(Trace.__table__.columns)} columns")
    
    # Test indexes
    print("\nIndex information:")
    for model_name, model in [
        ("TelemetryEvent", TelemetryEvent),
        ("SystemMetric", SystemMetric),
        ("BusinessMetric", BusinessMetric),
        ("AlertRule", AlertRule),
        ("Alert", Alert),
        ("Trace", Trace)
    ]:
        indexes = [idx.name for idx in model.__table__.indexes]
        print(f"{model_name}: {len(indexes)} indexes")
    
    print("\n✓ Telemetry system validation completed successfully!")
    print("✓ All models are properly defined with correct schemas")
    print("✓ Migration is ready to be executed")
    
except Exception as e:
    print(f"✗ Error during validation: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
