#!/usr/bin/env python3
"""
Redis Cache System Setup and Testing Script

This script initializes the Redis cache system, creates database tables,
runs health checks, and performs basic functionality tests.
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.cache_config import cache_settings, validate_cache_config
from app.services.cache.redis_cache import cache_service, check_cache_health
from app.migrations.cache_migration import initialize_cache_system
from app.services.telemetry.event_tracker import event_tracker


async def test_cache_service():
    """Test basic cache service functionality."""
    print("\n🧪 Testing Cache Service...")
    
    try:
        # Test 1: Basic get/set operations
        print("  Testing basic get/set operations...")
        test_key = "test:basic"
        test_value = {"message": "Hello Cache!", "timestamp": time.time()}
        
        # Set value
        await cache_service.set(test_key, test_value, "test")
        
        # Get value
        retrieved = await cache_service.get(test_key, "test")
        
        if retrieved and retrieved.get("message") == "Hello Cache!":
            print("  ✓ Basic get/set test passed")
        else:
            print("  ✗ Basic get/set test failed")
            return False
        
        # Test 2: TTL functionality
        print("  Testing TTL functionality...")
        ttl_key = "test:ttl"
        await cache_service.set(ttl_key, "temp_data", "test", ttl=1)  # 1 second TTL
        
        # Should be available immediately
        immediate = await cache_service.get(ttl_key, "test")
        if immediate:
            print("  ✓ Immediate access test passed")
        else:
            print("  ✗ Immediate access test failed")
            return False
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should be expired now
        expired = await cache_service.get(ttl_key, "test")
        if not expired:
            print("  ✓ TTL expiration test passed")
        else:
            print("  ✗ TTL expiration test failed")
            return False
        
        # Test 3: Delete operations
        print("  Testing delete operations...")
        delete_key = "test:delete"
        await cache_service.set(delete_key, "data_to_delete", "test")
        
        before_delete = await cache_service.get(delete_key, "test")
        if before_delete:
            await cache_service.delete(delete_key, "test")
            after_delete = await cache_service.get(delete_key, "test")
            
            if not after_delete:
                print("  ✓ Delete operation test passed")
            else:
                print("  ✗ Delete operation test failed")
                return False
        else:
            print("  ✗ Pre-delete check failed")
            return False
        
        # Test 4: Pattern-based operations
        print("  Testing pattern-based operations...")
        await cache_service.set("test:pattern:1", "data1", "test")
        await cache_service.set("test:pattern:2", "data2", "test")
        await cache_service.set("test:pattern:3", "data3", "test")
        
        # Delete pattern
        deleted_count = await cache_service.delete_pattern("test:pattern:*")
        
        if deleted_count >= 3:
            print("  ✓ Pattern delete test passed")
        else:
            print(f"  ✗ Pattern delete test failed (deleted {deleted_count} items)")
            return False
        
        print("  🎉 All cache service tests passed!")
        return True
        
    except Exception as e:
        print(f"  ✗ Cache service test failed: {e}")
        return False


async def test_document_caching():
    """Test document-specific caching features."""
    print("\n📄 Testing Document Caching...")
    
    try:
        # Test document hash caching
        print("  Testing document hash caching...")
        document_hash = "test_doc_hash_12345"
        document_data = {
            "document_id": "doc_123",
            "processed_at": time.time(),
            "confidence": 0.95,
            "fields_count": 15
        }
        
        # Cache document
        success = await cache_service.cache_document_hash(
            document_hash, document_data, "test_tenant"
        )
        
        if not success:
            print("  ✗ Document hash cache failed")
            return False
        
        # Retrieve cached document
        cached = await cache_service.get_cached_document(document_hash, "test_tenant")
        
        if cached and cached.get("document_id") == "doc_123":
            print("  ✓ Document hash cache test passed")
        else:
            print("  ✗ Document hash cache retrieval failed")
            return False
        
        # Test OCR result caching
        print("  Testing OCR result caching...")
        ocr_result = {
            "text": "Sample extracted text",
            "confidence": 0.92,
            "engine": "tesseract",
            "pages": 1
        }
        
        success = await cache_service.cache_ocr_result("doc_123", ocr_result, "test_tenant")
        cached_ocr = await cache_service.get_cached_ocr("doc_123", "test_tenant")
        
        if cached_ocr and cached_ocr.get("text") == "Sample extracted text":
            print("  ✓ OCR result caching test passed")
        else:
            print("  ✗ OCR result caching test failed")
            return False
        
        # Test LLM extraction caching
        print("  Testing LLM extraction caching...")
        llm_result = {
            "fields": {
                "invoice_number": {"value": "12345", "confidence": 0.98},
                "date": {"value": "2024-01-01", "confidence": 0.95},
                "amount": {"value": "100.00", "confidence": 0.97}
            }
        }
        
        success = await cache_service.cache_llm_extraction("doc_123", llm_result, "test_tenant")
        cached_llm = await cache_service.get_cached_llm_extraction("doc_123", "test_tenant")
        
        if cached_llm and cached_llm.get("fields", {}).get("invoice_number"):
            print("  ✓ LLM extraction caching test passed")
        else:
            print("  ✗ LLM extraction caching test failed")
            return False
        
        print("  🎉 All document caching tests passed!")
        return True
        
    except Exception as e:
        print(f"  ✗ Document caching test failed: {e}")
        return False


async def test_performance_monitoring():
    """Test cache performance monitoring."""
    print("\n📊 Testing Performance Monitoring...")
    
    try:
        # Get cache information
        info = await cache_service.get_cache_info()
        print(f"  Cache status: {info.get('status', 'unknown')}")
        
        if info.get("status") in ["healthy", "unknown"]:
            print("  ✓ Cache health check passed")
        else:
            print(f"  ⚠️  Cache health: {info.get('status')}")
        
        # Get performance statistics
        stats = await cache_service.get_performance_stats()
        print(f"  Active metrics keys: {len(stats)}")
        
        # Test with multiple operations to generate stats
        print("  Generating performance metrics...")
        for i in range(10):
            await cache_service.set(f"perf:test:{i}", f"data_{i}", "performance")
            await cache_service.get(f"perf:test:{i}", "performance")
        
        stats_after = await cache_service.get_performance_stats("performance")
        if len(stats_after) > 0:
            print("  ✓ Performance metrics collection test passed")
        else:
            print("  ✗ Performance metrics collection test failed")
            return False
        
        print("  🎉 Performance monitoring tests passed!")
        return True
        
    except Exception as e:
        print(f"  ✗ Performance monitoring test failed: {e}")
        return False


async def test_telemetry_integration():
    """Test telemetry integration."""
    print("\n📡 Testing Telemetry Integration...")
    
    try:
        # Track a cache event
        event_id = event_tracker.track_business_event(
            "cache_test_event",
            {"test_type": "integration_test", "timestamp": time.time()}
        )
        
        if event_id:
            print("  ✓ Telemetry event tracking test passed")
        else:
            print("  ✗ Telemetry event tracking test failed")
            return False
        
        # Get event statistics
        event_stats = event_tracker.get_event_statistics()
        if event_stats.get("total_events", 0) > 0:
            print("  ✓ Telemetry statistics test passed")
        else:
            print("  ✗ Telemetry statistics test failed")
            return False
        
        print("  🎉 Telemetry integration tests passed!")
        return True
        
    except Exception as e:
        print(f"  ✗ Telemetry integration test failed: {e}")
        return False


async def cleanup_test_data():
    """Clean up test data from cache."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        # Clear test-related cache entries
        patterns_to_clear = [
            "test:*",
            "perf:*",
            "doc:*",
            "ocr:*",
            "llm:*"
        ]
        
        total_cleared = 0
        for pattern in patterns_to_clear:
            cleared = await cache_service.delete_pattern(pattern)
            total_cleared += cleared
        
        print(f"  Cleared {total_cleared} test cache entries")
        print("  ✓ Test data cleanup completed")
        return True
        
    except Exception as e:
        print(f"  ✗ Test data cleanup failed: {e}")
        return False


async def main():
    """Main setup and test function."""
    print("🚀 Redis Cache System Setup and Testing")
    print("=" * 50)
    
    # Step 1: Validate configuration
    print("\n🔧 Step 1: Validating Configuration...")
    config_validation = validate_cache_config()
    
    print("Configuration validation:")
    for key, status in config_validation.items():
        status_icon = "✓" if status else "✗"
        print(f"  {status_icon} {key}: {status}")
    
    # Step 2: Initialize database tables
    print("\n🗄️  Step 2: Initializing Database Tables...")
    if initialize_cache_system():
        print("  ✓ Database tables initialized successfully")
    else:
        print("  ✗ Database table initialization failed")
        return False
    
    # Step 3: Initialize cache service
    print("\n⚡ Step 3: Initializing Cache Service...")
    try:
        await cache_service.initialize()
        print("  ✓ Cache service initialized successfully")
    except Exception as e:
        print(f"  ⚠️  Cache service initialization failed: {e}")
        print("     Continuing with tests (Redis may not be running)")
        # Don't return False here - allow tests to continue
    
    # Step 4: Run health check
    print("\n🏥 Step 4: Running Health Check...")
    try:
        health = await check_cache_health()
        print(f"  Cache health: {health.get('status', 'unknown')}")
        
        if health.get('status') == 'healthy':
            print("  ✓ Cache health check passed")
        elif health.get('status') == 'unknown':
            print("  ⚠️  Cache health unknown (Redis may not be running)")
        else:
            print(f"  ⚠️  Cache health degraded: {health.get('status')}")
    except Exception as e:
        print(f"  ⚠️  Health check failed: {e}")
    
    # Step 5: Run functionality tests
    tests_passed = 0
    total_tests = 0
    
    # Test cache service
    total_tests += 1
    if await test_cache_service():
        tests_passed += 1
    
    # Test document caching
    total_tests += 1
    if await test_document_caching():
        tests_passed += 1
    
    # Test performance monitoring
    total_tests += 1
    if await test_performance_monitoring():
        tests_passed += 1
    
    # Test telemetry integration
    total_tests += 1
    if await test_telemetry_integration():
        tests_passed += 1
    
    # Step 6: Cleanup
    await cleanup_test_data()
    
    # Final report
    print("\n" + "=" * 50)
    print("📋 SETUP AND TEST SUMMARY")
    print("=" * 50)
    
    print(f"Configuration validation: {'✓' if all(config_validation.values()) else '✗'}")
    print(f"Database initialization: ✓")
    print(f"Cache service tests: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nRedis caching system is ready for use!")
        print("\nKey features enabled:")
        print("  • Document hash-based caching")
        print("  • OCR result caching")
        print("  • LLM extraction caching")
        print("  • API response caching")
        print("  • Session data caching")
        print("  • Multi-tenant isolation")
        print("  • Performance monitoring")
        print("  • Telemetry integration")
        print("  • Automatic cache cleanup")
        print("  • Cache warming strategies")
    else:
        print(f"\n⚠️  {total_tests - tests_passed} test(s) failed")
        print("Please check the error messages above and ensure Redis is running.")
    
    print(f"\nTo start using the cache system:")
    print(f"  1. Ensure Redis is running on {cache_settings.CONNECTION_CONFIG.REDIS_HOST}:{cache_settings.CONNECTION_CONFIG.REDIS_PORT}")
    print(f"  2. The cache service will automatically initialize on application startup")
    print(f"  3. Use cache decorators on your API endpoints for automatic caching")
    print(f"  4. Document processor now includes automatic caching for identical documents")
    
    return tests_passed == total_tests


if __name__ == "__main__":
    # Run the async main function
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Setup failed with error: {e}")
        sys.exit(1)
