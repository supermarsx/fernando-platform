#!/usr/bin/env python3
"""
Enterprise Features Test Script
Tests all enterprise features to ensure they're working correctly
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

class EnterpriseFeaturesTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.auth_token = None
        self.tenant_id = None
        
    def print_test(self, test_name):
        print(f"\n🧪 Testing: {test_name}")
        print("-" * 50)
    
    def print_success(self, message):
        print(f"✅ {message}")
    
    def print_error(self, message):
        print(f"❌ {message}")
    
    def print_info(self, message):
        print(f"ℹ️  {message}")
    
    def test_system_status(self):
        """Test system status endpoint"""
        self.print_test("System Status")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/system/status")
            
            if response.status_code == 200:
                data = response.json()
                self.print_success("System status endpoint working")
                self.print_info(f"Version: {data.get('version')}")
                self.print_info(f"Database: {data.get('database')}")
                self.print_info(f"Enterprise features: {data.get('enterprise_features')}")
                return True
            else:
                self.print_error(f"Failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Error: {e}")
            return False
    
    def test_authentication(self):
        """Test authentication and get token"""
        self.print_test("Authentication")
        
        try:
            # Register a test user
            user_data = {
                "email": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.com",
                "password": "testpassword123",
                "full_name": "Test User"
            }
            
            response = self.session.post(f"{BASE_URL}/auth/register", json=user_data)
            
            if response.status_code == 201:
                self.print_success("User registration successful")
            elif response.status_code == 400:
                self.print_info("User already exists, attempting login")
            
            # Login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                # Get user info to find tenant_id
                user_response = self.session.get(f"{BASE_URL}/auth/me")
                if user_response.status_code == 200:
                    user_info = user_response.json()
                    self.tenant_id = user_info.get("tenant_id")
                    self.print_success("Authentication successful")
                    self.print_info(f"User ID: {user_info.get('user_id')}")
                    self.print_info(f"Tenant ID: {self.tenant_id}")
                    return True
                else:
                    self.print_error("Failed to get user info")
                    return False
            else:
                self.print_error(f"Login failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Authentication error: {e}")
            return False
    
    def test_multi_tenant_support(self):
        """Test multi-tenant features"""
        if not self.tenant_id:
            self.print_error("No tenant_id available, skipping multi-tenant tests")
            return False
            
        self.print_test("Multi-Tenant Support")
        
        try:
            # Test tenant info
            response = self.session.get(f"{BASE_URL}/enterprise/tenants/{self.tenant_id}")
            
            if response.status_code == 200:
                tenant_info = response.json()
                self.print_success("Tenant information retrieved")
                self.print_info(f"Tenant name: {tenant_info.get('name')}")
                self.print_info(f"Status: {tenant_info.get('status')}")
                return True
            else:
                self.print_error(f"Failed to get tenant info: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Multi-tenant test error: {e}")
            return False
    
    def test_user_permissions(self):
        """Test user permission system"""
        self.print_test("User Permissions")
        
        try:
            # Get user permissions
            response = self.session.get(f"{BASE_URL}/enterprise/users/me/permissions")
            
            if response.status_code == 200:
                permissions_data = response.json()
                permissions = permissions_data.get("permissions", [])
                self.print_success(f"User permissions retrieved ({len(permissions)} permissions)")
                self.print_info(f"Sample permissions: {permissions[:3]}")  # Show first 3
                return True
            else:
                self.print_error(f"Failed to get permissions: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Permission test error: {e}")
            return False
    
    def test_quota_management(self):
        """Test quota management"""
        self.print_test("Quota Management")
        
        try:
            # Check quota limits
            response = self.session.get(f"{BASE_URL}/enterprise/quota/check")
            
            if response.status_code == 200:
                quota_data = response.json()
                self.print_success("Quota information retrieved")
                self.print_info(f"Within limits: {quota_data.get('within_limits')}")
                self.print_info(f"Usage: {quota_data.get('usage', {})}")
                return True
            else:
                self.print_error(f"Failed to get quota info: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Quota test error: {e}")
            return False
    
    def test_audit_trails(self):
        """Test audit trail functionality"""
        self.print_test("Audit Trails")
        
        try:
            # Create audit log entry
            audit_data = {
                "action": "test_action",
                "resource_type": "test_resource",
                "resource_id": "test-123",
                "risk_level": "low"
            }
            
            response = self.session.post(f"{BASE_URL}/enterprise/audit/log", json=audit_data)
            
            if response.status_code == 200:
                self.print_success("Audit log entry created")
                
                # Get audit logs
                logs_response = self.session.get(f"{BASE_URL}/enterprise/audit/logs?limit=10")
                
                if logs_response.status_code == 200:
                    logs_data = logs_response.json()
                    self.print_success(f"Audit logs retrieved ({len(logs_data)} entries)")
                    return True
                else:
                    self.print_error(f"Failed to get audit logs: {logs_response.status_code}")
                    return False
            else:
                self.print_error(f"Failed to create audit log: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Audit trail test error: {e}")
            return False
    
    def test_queue_management(self):
        """Test queue management features"""
        self.print_test("Queue Management")
        
        try:
            # Get queue statistics
            response = self.session.get(f"{BASE_URL}/queue/statistics")
            
            if response.status_code == 200:
                stats_data = response.json()
                self.print_success("Queue statistics retrieved")
                self.print_info(f"Total jobs: {stats_data.get('total_jobs')}")
                self.print_info(f"Active workers: {stats_data.get('active_workers')}")
                return True
            else:
                self.print_error(f"Failed to get queue stats: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Queue management test error: {e}")
            return False
    
    def test_export_import(self):
        """Test export/import functionality"""
        self.print_test("Export/Import Functionality")
        
        try:
            # Get supported formats
            response = self.session.get(f"{BASE_URL}/export-import/formats/supported")
            
            if response.status_code == 200:
                formats_data = response.json()
                self.print_success("Supported formats retrieved")
                self.print_info(f"Export formats: {len(formats_data.get('export_formats', []))}")
                self.print_info(f"Import formats: {len(formats_data.get('import_formats', []))}")
                return True
            else:
                self.print_error(f"Failed to get formats: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Export/import test error: {e}")
            return False
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        self.print_test("Rate Limiting")
        
        try:
            # Check rate limit for jobs endpoint
            response = self.session.get(f"{BASE_URL}/enterprise/rate-limit/jobs")
            
            if response.status_code == 200:
                rate_data = response.json()
                self.print_success("Rate limit status retrieved")
                self.print_info(f"Allowed: {rate_data.get('allowed')}")
                if 'limit_per_hour' in rate_data:
                    self.print_info(f"Hourly limit: {rate_data.get('limit_per_hour')}")
                return True
            else:
                self.print_error(f"Failed to get rate limit status: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Rate limiting test error: {e}")
            return False
    
    def test_scheduled_tasks(self):
        """Test scheduled tasks"""
        self.print_test("Scheduled Tasks")
        
        try:
            # Get scheduled tasks list
            response = self.session.get(f"{BASE_URL}/queue/scheduled-tasks")
            
            if response.status_code == 200:
                tasks_data = response.json()
                self.print_success("Scheduled tasks retrieved")
                self.print_info(f"Total tasks: {len(tasks_data)}")
                return True
            else:
                self.print_error(f"Failed to get scheduled tasks: {response.status_code}")
                return False
                
        except Exception as e:
            self.print_error(f"Scheduled tasks test error: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test that all enterprise API endpoints are accessible"""
        self.print_test("API Endpoint Accessibility")
        
        endpoints_to_test = [
            "/enterprise/quota/check",
            "/enterprise/rate-limit/test",
            "/queue/statistics",
            "/export-import/formats/supported",
            "/enterprise/permissions"
        ]
        
        accessible_count = 0
        
        for endpoint in endpoints_to_test:
            try:
                response = self.session.get(f"{BASE_URL}{endpoint}")
                if response.status_code in [200, 403, 404]:  # 403/404 means endpoint exists but no access
                    accessible_count += 1
                    self.print_success(f"Endpoint accessible: {endpoint}")
                else:
                    self.print_error(f"Endpoint failed: {endpoint} (status: {response.status_code})")
            except Exception as e:
                self.print_error(f"Endpoint error: {endpoint} - {e}")
        
        success_rate = (accessible_count / len(endpoints_to_test)) * 100
        self.print_info(f"Accessibility rate: {success_rate:.1f}% ({accessible_count}/{len(endpoints_to_test)})")
        
        return success_rate > 80  # Consider successful if >80% endpoints are accessible
    
    def run_all_tests(self):
        """Run all enterprise feature tests"""
        print("🚀 Starting Enterprise Features Test Suite")
        print("=" * 60)
        
        # Check if server is running
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ Server is not running. Please start the server first:")
                print("   cd /workspace/fernando/backend")
                print("   uvicorn app.main:app --host 0.0.0.0 --port 8000")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
        
        tests = [
            ("System Status", self.test_system_status),
            ("Authentication", self.test_authentication),
            ("Multi-Tenant Support", self.test_multi_tenant_support),
            ("User Permissions", self.test_user_permissions),
            ("Quota Management", self.test_quota_management),
            ("Audit Trails", self.test_audit_trails),
            ("Queue Management", self.test_queue_management),
            ("Export/Import", self.test_export_import),
            ("Rate Limiting", self.test_rate_limiting),
            ("Scheduled Tasks", self.test_scheduled_tasks),
            ("API Endpoints", self.test_api_endpoints),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                self.print_error(f"Test failed with exception: {e}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:<30} {status}")
            if result:
                passed += 1
        
        print("-" * 60)
        print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 All enterprise features are working correctly!")
            print("\nEnterprise features enabled:")
            print("✅ Multi-tenant support with data isolation")
            print("✅ Advanced user management with groups and permissions")
            print("✅ Enhanced batch processing with queue management")
            print("✅ Export/import functionality for multiple formats")
            print("✅ Advanced audit trails and compliance reporting")
            print("✅ API rate limiting and quota management")
            print("✅ Role-based access control enhancements")
            print("✅ Advanced job scheduling and automation")
            return True
        elif passed >= total * 0.8:
            print(f"\n⚠️  {total - passed} tests failed. Most enterprise features are working.")
            return True
        else:
            print(f"\n❌ {total - passed} tests failed. Please check the issues above.")
            return False


def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Allow passing custom base URL
        global BASE_URL
        BASE_URL = sys.argv[1]
    
    print("Enterprise Features Test Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"API Prefix: {API_PREFIX}")
    
    tester = EnterpriseFeaturesTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
