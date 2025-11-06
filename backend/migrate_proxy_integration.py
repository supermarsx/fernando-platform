#!/usr/bin/env python3
"""
Proxy Integration Migration Script

This script helps migrate from direct API calls to proxy-based architecture
in the Fernando platform, ensuring zero API key exposure.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.proxy import (
    ProxyClient, RequestBuilder, ResponseHandler, AuthHandler,
    get_proxy_client
)
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyMigrationManager:
    """Manages the migration to proxy-based architecture"""
    
    def __init__(self):
        self.migration_status = {}
        self.service_configs = {
            "llm": {
                "old_patterns": ["import openai", "openai.ChatCompletion", "OPENAI_API_KEY"],
                "new_patterns": ["from app.services.llm_service import get_llm_service"],
                "files_to_check": ["app/services/llm_service.py", "app/api/extractions.py"]
            },
            "ocr": {
                "old_patterns": ["import requests", "requests.post.*vision", "OCR_API_KEY"],
                "new_patterns": ["from app.services.ocr_service import get_ocr_service"],
                "files_to_check": ["app/services/ocr_service.py", "app/api/extractions.py"]
            },
            "stripe": {
                "old_patterns": ["import stripe", "stripe.api_key", "STRIPE_SECRET_KEY"],
                "new_patterns": ["from app.services.stripe_service import StripeService"],
                "files_to_check": ["app/services/stripe_service.py", "app/api/payments.py"]
            },
            "paypal": {
                "old_patterns": ["import requests", "requests.post.*paypal", "PAYPAL_CLIENT"],
                "new_patterns": ["from app.services.paypal_service import PayPalService"],
                "files_to_check": ["app/services/paypal_service.py", "app/api/payments.py"]
            },
            "coinbase": {
                "old_patterns": ["import requests", "requests.post.*coinbase", "COINBASE_"],
                "new_patterns": ["from app.services.cryptocurrency_service import CryptocurrencyService"],
                "files_to_check": ["app/services/cryptocurrency_service.py", "app/api/payments.py"]
            }
        }
    
    async def run_migration_check(self) -> Dict[str, Any]:
        """Run complete migration check"""
        logger.info("Starting proxy integration migration check...")
        
        results = {
            "environment_check": await self.check_environment_setup(),
            "service_configurations": await self.check_service_configurations(),
            "proxy_servers_status": await self.check_proxy_servers(),
            "code_analysis": await self.analyze_code_changes(),
            "migration_readiness": self.assess_migration_readiness()
        }
        
        return results
    
    async def check_environment_setup(self) -> Dict[str, Any]:
        """Check if environment is properly configured for proxy migration"""
        logger.info("Checking environment setup...")
        
        required_vars = [
            "PROXY_ENABLED",
            "LLM_PROXY_ENDPOINT", 
            "OCR_PROXY_ENDPOINT",
            "STRIPE_PROXY_ENDPOINT",
            "PAYPAL_PROXY_ENDPOINT",
            "COINBASE_PROXY_ENDPOINT"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        return {
            "configured": len(missing_vars) == 0,
            "missing_variables": missing_vars,
            "total_required": len(required_vars),
            "total_configured": len(required_vars) - len(missing_vars)
        }
    
    async def check_service_configurations(self) -> Dict[str, Any]:
        """Check proxy client configurations for each service"""
        logger.info("Checking service configurations...")
        
        try:
            client = get_proxy_client()
            status = await get_all_services_status()
            
            configured_services = []
            failed_services = []
            
            for service, service_status in status.items():
                if service_status.get("configured", False):
                    configured_services.append(service)
                else:
                    failed_services.append(service)
            
            return {
                "total_services": len(status),
                "configured_services": len(configured_services),
                "failed_services": len(failed_services),
                "services": status,
                "ready_for_migration": len(failed_services) == 0
            }
            
        except Exception as e:
            logger.error(f"Error checking service configurations: {e}")
            return {
                "error": str(e),
                "ready_for_migration": False
            }
    
    async def check_proxy_servers(self) -> Dict[str, Any]:
        """Check if proxy servers are running and healthy"""
        logger.info("Checking proxy servers...")
        
        import httpx
        
        proxy_endpoints = {
            "llm": os.getenv("LLM_PROXY_ENDPOINT", "http://localhost:8000"),
            "ocr": os.getenv("OCR_PROXY_ENDPOINT", "http://localhost:8001"),
            "toconline": os.getenv("TOCONLINE_PROXY_ENDPOINT", "http://localhost:8002"),
            "stripe": os.getenv("STRIPE_PROXY_ENDPOINT", "http://localhost:8003"),
            "paypal": os.getenv("PAYPAL_PROXY_ENDPOINT", "http://localhost:8004"),
            "coinbase": os.getenv("COINBASE_PROXY_ENDPOINT", "http://localhost:8005"),
            "openai": os.getenv("OPENAI_PROXY_ENDPOINT", "http://localhost:8006")
        }
        
        server_status = {}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service, endpoint in proxy_endpoints.items():
                try:
                    response = await client.get(f"{endpoint}/health")
                    if response.status_code == 200:
                        server_status[service] = {
                            "status": "healthy",
                            "endpoint": endpoint,
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    else:
                        server_status[service] = {
                            "status": "unhealthy",
                            "endpoint": endpoint,
                            "status_code": response.status_code
                        }
                except Exception as e:
                    server_status[service] = {
                        "status": "unreachable",
                        "endpoint": endpoint,
                        "error": str(e)
                    }
        
        healthy_count = sum(1 for s in server_status.values() if s["status"] == "healthy")
        
        return {
            "total_servers": len(proxy_endpoints),
            "healthy_servers": healthy_count,
            "servers": server_status,
            "all_servers_healthy": healthy_count == len(proxy_endpoints)
        }
    
    async def analyze_code_changes(self) -> Dict[str, Any]:
        """Analyze what code changes are needed"""
        logger.info("Analyzing code changes...")
        
        analysis = {
            "services_analyzed": [],
            "changes_needed": {},
            "migration_steps": []
        }
        
        for service, config in self.service_configs.items():
            service_analysis = await self.analyze_service_migration(service, config)
            analysis["services_analyzed"].append(service)
            analysis["changes_needed"][service] = service_analysis
        
        # Generate migration steps
        analysis["migration_steps"] = self.generate_migration_steps()
        
        return analysis
    
    async def analyze_service_migration(self, service: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze migration requirements for a specific service"""
        
        project_root = Path(__file__).parent
        files_checked = 0
        patterns_found = 0
        migrations_needed = []
        
        for file_pattern in config["files_to_check"]:
            file_path = project_root / file_pattern
            if file_path.exists():
                files_checked += 1
                content = file_path.read_text()
                
                # Check for old patterns
                for pattern in config["old_patterns"]:
                    if pattern in content:
                        patterns_found += 1
                        migrations_needed.append(f"Replace '{pattern}' with proxy usage in {file_path}")
        
        # Check if service is already using proxy
        proxy_usage_found = False
        for pattern in config["new_patterns"]:
            if pattern in content:
                proxy_usage_found = True
                break
        
        return {
            "files_checked": files_checked,
            "patterns_found": patterns_found,
            "proxy_already_used": proxy_usage_found,
            "migration_needed": patterns_found > 0 and not proxy_usage_found,
            "specific_migrations": migrations_needed,
            "status": "ready" if proxy_usage_found else "needs_migration"
        }
    
    def generate_migration_steps(self) -> List[str]:
        """Generate step-by-step migration instructions"""
        
        steps = [
            "1. Environment Setup:",
            "   - Set PROXY_ENABLED=true in environment",
            "   - Configure proxy server endpoints",
            "   - Remove client-side API keys from .env files",
            "",
            "2. Service Migration:",
            "   - Update service imports to use proxy-enabled versions",
            "   - Replace direct API calls with proxy methods",
            "   - Update error handling to use proxy response format",
            "",
            "3. Testing:",
            "   - Run integration tests with proxy servers",
            "   - Verify all functionality works with proxy",
            "   - Test fallback mechanisms",
            "",
            "4. Production Deployment:",
            "   - Deploy proxy servers to production",
            "   - Update production environment variables",
            "   - Monitor proxy server health",
            "",
            "5. Security Validation:",
            "   - Verify no API keys are exposed to clients",
            "   - Test authentication flow",
            "   - Validate circuit breaker functionality"
        ]
        
        return steps
    
    def assess_migration_readiness(self) -> Dict[str, Any]:
        """Assess overall migration readiness"""
        
        return {
            "ready": True,  # Will be calculated based on other checks
            "priority": "high",
            "estimated_effort": "2-4 hours",
            "risk_level": "low",
            "rollback_plan": "Disable PROXY_ENABLED to revert to direct calls"
        }
    
    async def generate_migration_report(self) -> str:
        """Generate comprehensive migration report"""
        
        results = await self.run_migration_check()
        
        report = f"""
# Proxy Integration Migration Report

Generated: {asyncio.get_event_loop().time()}

## Environment Status
- Environment Setup: {"✅ Ready" if results["environment_check"]["configured"] else "❌ Needs Configuration"}
- Missing Variables: {', '.join(results["environment_check"]["missing_variables"])}

## Service Configuration Status
- Services Configured: {results["service_configurations"].get("configured_services", 0)}/{results["service_configurations"].get("total_services", 0)}
- Migration Ready: {"✅ Yes" if results["service_configurations"].get("ready_for_migration") else "❌ No"}

## Proxy Server Health
- Healthy Servers: {results["proxy_servers_status"].get("healthy_servers", 0)}/{results["proxy_servers_status"].get("total_servers", 0)}
- All Servers Healthy: {"✅ Yes" if results["proxy_servers_status"].get("all_servers_healthy") else "❌ No"}

## Code Analysis Summary
"""
        
        for service, analysis in results["code_analysis"]["changes_needed"].items():
            status_icon = "✅" if analysis["status"] == "ready" else "⚠️"
            report += f"\n### {service.title()} Service: {status_icon}\n"
            report += f"- Files Checked: {analysis['files_checked']}\n"
            report += f"- Status: {analysis['status']}\n"
            if analysis["specific_migrations"]:
                report += f"- Actions Needed: {len(analysis['specific_migrations'])}\n"
        
        report += "\n## Migration Steps\n"
        for step in results["code_analysis"]["migration_steps"]:
            report += f"{step}\n"
        
        return report


async def main():
    """Main migration script entry point"""
    
    print("🔄 Proxy Integration Migration Manager")
    print("=====================================\n")
    
    manager = ProxyMigrationManager()
    
    try:
        # Run migration check
        report = await manager.generate_migration_report()
        
        # Print report
        print(report)
        
        # Save report to file
        with open("proxy_migration_report.md", "w") as f:
            f.write(report)
        
        print(f"\n📄 Migration report saved to: proxy_migration_report.md")
        
        # Optional: Run automated migration if everything is ready
        print("\n🤔 Would you like to run automated migration? (y/n)")
        choice = input().lower().strip()
        
        if choice in ['y', 'yes']:
            print("🚀 Running automated migration...")
            await run_automated_migration()
        
    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        print(f"❌ Migration check failed: {e}")
        sys.exit(1)


async def run_automated_migration():
    """Run automated migration steps"""
    
    print("⚠️  Automated migration not yet implemented.")
    print("Please follow the manual steps in the migration report.")
    print("\nManual migration steps:")
    print("1. Update environment variables")
    print("2. Modify service imports and method calls")
    print("3. Test with proxy servers")
    print("4. Deploy to production")


if __name__ == "__main__":
    asyncio.run(main())