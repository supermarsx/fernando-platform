"""
Proxy Service Monitoring and Health Check System

This module provides comprehensive monitoring for all proxy services,
ensuring they are running correctly and providing detailed health metrics.
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class HealthMetrics:
    """Health metrics for a proxy service"""
    service_name: str
    status: str  # healthy, unhealthy, unknown
    response_time: float
    last_check: datetime
    error_count: int
    uptime: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    version: Optional[str] = None

@dataclass
class ProxyMonitoringReport:
    """Complete monitoring report"""
    timestamp: datetime
    total_services: int
    healthy_services: int
    unhealthy_services: int
    metrics: List[HealthMetrics]
    system_info: Dict[str, Any]
    recommendations: List[str]

class ProxyServiceMonitor:
    """Monitor health and performance of all proxy services"""
    
    def __init__(self):
        self.proxy_servers = {
            "llm": {
                "endpoint": settings.LLM_PROXY_ENDPOINT,
                "name": "LLM Service",
                "health_url": "/health"
            },
            "ocr": {
                "endpoint": settings.OCR_PROXY_ENDPOINT,
                "name": "OCR Service",
                "health_url": "/health"
            },
            "toconline": {
                "endpoint": settings.TOCONLINE_PROXY_ENDPOINT,
                "name": "ToConline Service",
                "health_url": "/health"
            },
            "stripe": {
                "endpoint": settings.STRIPE_PROXY_ENDPOINT,
                "name": "Stripe Payment",
                "health_url": "/health"
            },
            "paypal": {
                "endpoint": settings.PAYPAL_PROXY_ENDPOINT,
                "name": "PayPal Payment",
                "health_url": "/health"
            },
            "coinbase": {
                "endpoint": settings.COINBASE_PROXY_ENDPOINT,
                "name": "Cryptocurrency Payment",
                "health_url": "/health"
            },
            "openai": {
                "endpoint": settings.OPENAI_PROXY_ENDPOINT,
                "name": "OpenAI Direct",
                "health_url": "/health"
            }
        }
        
        self.health_history: Dict[str, List[HealthMetrics]] = {}
        self.error_threshold = 5  # Number of consecutive failures before marking unhealthy
        
    async def run_comprehensive_health_check(self) -> ProxyMonitoringReport:
        """Run comprehensive health check on all proxy services"""
        logger.info("🔍 Starting comprehensive proxy service health check...")
        
        start_time = time.time()
        metrics = []
        system_info = await self._get_system_info()
        
        # Check each service
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service_name, config in self.proxy_servers.items():
                try:
                    metric = await self._check_service_health(client, service_name, config)
                    metrics.append(metric)
                    
                    # Add to history
                    if service_name not in self.health_history:
                        self.health_history[service_name] = []
                    self.health_history[service_name].append(metric)
                    
                    # Keep only last 100 metrics per service
                    if len(self.health_history[service_name]) > 100:
                        self.health_history[service_name] = self.health_history[service_name][-100:]
                    
                except Exception as e:
                    logger.error(f"Error checking {service_name}: {e}")
                    metrics.append(HealthMetrics(
                        service_name=service_name,
                        status="error",
                        response_time=0.0,
                        last_check=datetime.utcnow(),
                        error_count=1,
                        details={"error": str(e)}
                    ))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        # Create report
        report = ProxyMonitoringReport(
            timestamp=datetime.utcnow(),
            total_services=len(metrics),
            healthy_services=len([m for m in metrics if m.status == "healthy"]),
            unhealthy_services=len([m for m in metrics if m.status != "healthy"]),
            metrics=metrics,
            system_info=system_info,
            recommendations=recommendations
        )
        
        # Save report
        await self._save_report(report)
        
        duration = time.time() - start_time
        logger.info(f"✅ Health check completed in {duration:.2f} seconds")
        
        return report
    
    async def _check_service_health(self, client: httpx.AsyncClient, 
                                   service_name: str, config: Dict[str, Any]) -> HealthMetrics:
        """Check health of a single service"""
        endpoint = config["endpoint"]
        health_url = config["health_url"]
        full_url = f"{endpoint.rstrip('/')}{health_url}"
        
        start_time = time.time()
        
        try:
            response = await client.get(full_url)
            response_time = time.time() - start_time
            
            # Parse response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    status = "healthy"
                    details = response_data
                    version = response_data.get("version", "unknown")
                    
                    # Check error count from history
                    error_count = self._get_recent_error_count(service_name)
                    
                except json.JSONDecodeError:
                    status = "unhealthy"
                    details = {"error": "Invalid JSON response"}
                    error_count = 1
                    version = "unknown"
            else:
                status = "unhealthy"
                details = {"error": f"HTTP {response.status_code}"}
                response_time = 0.0
                error_count = self._get_recent_error_count(service_name) + 1
                version = "unknown"
            
            # Check if service was down before
            was_unhealthy = False
            if service_name in self.health_history and self.health_history[service_name]:
                last_metric = self.health_history[service_name][-1]
                was_unhealthy = last_metric.status != "healthy"
            
            return HealthMetrics(
                service_name=service_name,
                status=status,
                response_time=response_time,
                last_check=datetime.utcnow(),
                error_count=error_count,
                uptime=self._calculate_uptime(service_name),
                details=details,
                version=version
            )
            
        except asyncio.TimeoutError:
            return HealthMetrics(
                service_name=service_name,
                status="timeout",
                response_time=0.0,
                last_check=datetime.utcnow(),
                error_count=self._get_recent_error_count(service_name) + 1,
                details={"error": "Request timeout"}
            )
        except Exception as e:
            return HealthMetrics(
                service_name=service_name,
                status="error",
                response_time=0.0,
                last_check=datetime.utcnow(),
                error_count=self._get_recent_error_count(service_name) + 1,
                details={"error": str(e)}
            )
    
    def _get_recent_error_count(self, service_name: str) -> int:
        """Get recent error count for a service"""
        if service_name not in self.health_history:
            return 0
        
        # Count errors in last 5 minutes
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_metrics = [
            m for m in self.health_history[service_name]
            if m.last_check > recent_cutoff and m.status != "healthy"
        ]
        
        return len(recent_metrics)
    
    def _calculate_uptime(self, service_name: str) -> Optional[float]:
        """Calculate uptime percentage for a service"""
        if service_name not in self.health_history:
            return None
        
        # Get metrics from last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_metrics = [
            m for m in self.health_history[service_name]
            if m.last_check > cutoff
        ]
        
        if not recent_metrics:
            return None
        
        healthy_count = len([m for m in recent_metrics if m.status == "healthy"])
        return (healthy_count / len(recent_metrics)) * 100
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        import psutil
        
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                "python_version": sys.version,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": f"Could not get system info: {e}"}
    
    def _generate_recommendations(self, metrics: List[HealthMetrics]) -> List[str]:
        """Generate recommendations based on metrics"""
        recommendations = []
        
        # Check for unhealthy services
        unhealthy_services = [m for m in metrics if m.status != "healthy"]
        if unhealthy_services:
            service_names = [m.service_name for m in unhealthy_services]
            recommendations.append(
                f"🔧 {len(unhealthy_services)} services are unhealthy: {', '.join(service_names)}. "
                "Check proxy server logs and restart if necessary."
            )
        
        # Check for slow responses
        slow_services = [m for m in metrics if m.response_time > 2.0]
        if slow_services:
            service_names = [m.service_name for m in slow_services]
            recommendations.append(
                f"⚠️ {len(slow_services)} services have slow response times: {', '.join(service_names)}. "
                "Consider scaling or optimizing these services."
            )
        
        # Check for high error counts
        high_error_services = [m for m in metrics if m.error_count > 3]
        if high_error_services:
            service_names = [m.service_name for m in high_error_services]
            recommendations.append(
                f"🚨 {len(high_error_services)} services have high error rates: {', '.join(service_names)}. "
                "Immediate investigation required."
            )
        
        # Check uptime
        low_uptime_services = [m for m in metrics if m.uptime and m.uptime < 95]
        if low_uptime_services:
            service_names = [m.service_name for m in low_uptime_services]
            recommendations.append(
                f"📉 {len(low_uptime_services)} services have low uptime: {', '.join(service_names)}. "
                "Review stability and infrastructure."
            )
        
        if not recommendations:
            recommendations.append("✅ All proxy services are operating normally.")
        
        return recommendations
    
    async def _save_report(self, report: ProxyMonitoringReport):
        """Save monitoring report to file"""
        try:
            # Ensure reports directory exists
            reports_dir = Path("/workspace/fernando/backend/reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = reports_dir / f"proxy_health_report_{timestamp}.json"
            
            # Convert to JSON-serializable format
            report_dict = asdict(report)
            report_dict["timestamp"] = report.timestamp.isoformat()
            for metric in report_dict["metrics"]:
                metric["last_check"] = metric["last_check"].isoformat()
            
            # Save report
            with open(filename, 'w') as f:
                json.dump(report_dict, f, indent=2)
            
            # Also save as latest report
            latest_filename = reports_dir / "proxy_health_report_latest.json"
            with open(latest_filename, 'w') as f:
                json.dump(report_dict, f, indent=2)
            
            logger.info(f"📄 Monitoring report saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save monitoring report: {e}")
    
    async def continuous_monitoring(self, interval: int = 60, duration: int = 3600):
        """
        Run continuous monitoring for a specified duration
        
        Args:
            interval: Check interval in seconds
            duration: Total monitoring duration in seconds
        """
        logger.info(f"🔄 Starting continuous monitoring for {duration} seconds")
        logger.info(f"Check interval: {interval} seconds")
        
        start_time = time.time()
        check_count = 0
        
        try:
            while time.time() - start_time < duration:
                check_count += 1
                logger.info(f"🔍 Running health check #{check_count}")
                
                # Run health check
                report = await self.run_comprehensive_health_check()
                
                # Print summary
                healthy_count = report.healthy_services
                total_count = report.total_services
                logger.info(
                    f"📊 Health Check #{check_count}: "
                    f"{healthy_count}/{total_count} services healthy"
                )
                
                # Print issues if any
                if report.unhealthy_services > 0:
                    logger.warning("⚠️ Issues detected:")
                    for rec in report.recommendations:
                        logger.warning(f"   {rec}")
                
                # Wait for next check
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Continuous monitoring interrupted by user")
        except Exception as e:
            logger.error(f"❌ Continuous monitoring error: {e}")
        finally:
            end_time = time.time()
            duration_actual = end_time - start_time
            logger.info(
                f"🏁 Continuous monitoring completed. "
                f"Ran {check_count} checks in {duration_actual:.2f} seconds"
            )


# Utility functions
async def quick_health_check() -> Dict[str, Any]:
    """Run a quick health check on all proxy services"""
    monitor = ProxyServiceMonitor()
    report = await monitor.run_comprehensive_health_check()
    
    # Return simplified results
    return {
        "total_services": report.total_services,
        "healthy_services": report.healthy_services,
        "unhealthy_services": report.unhealthy_services,
        "health_percentage": (report.healthy_services / report.total_services) * 100,
        "services": {
            metric.service_name: {
                "status": metric.status,
                "response_time": metric.response_time,
                "error_count": metric.error_count,
                "uptime": metric.uptime
            }
            for metric in report.metrics
        },
        "recommendations": report.recommendations
    }

async def detailed_health_check() -> str:
    """Run detailed health check and return formatted report"""
    monitor = ProxyServiceMonitor()
    report = await monitor.run_comprehensive_health_check()
    
    # Format report
    lines = [
        "=" * 60,
        "🔍 PROXY SERVICE HEALTH CHECK REPORT",
        "=" * 60,
        f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Total Services: {report.total_services}",
        f"Healthy: {report.healthy_services} ✅",
        f"Unhealthy: {report.unhealthy_services} ❌",
        "",
        "📊 SERVICE DETAILS:",
        "-" * 40
    ]
    
    for metric in report.metrics:
        status_icon = "✅" if metric.status == "healthy" else "❌"
        lines.append(f"{status_icon} {metric.service_name}: {metric.status}")
        lines.append(f"   Response Time: {metric.response_time:.3f}s")
        if metric.error_count > 0:
            lines.append(f"   Error Count: {metric.error_count}")
        if metric.uptime is not None:
            lines.append(f"   Uptime: {metric.uptime:.1f}%")
        lines.append("")
    
    lines.extend([
        "🔧 RECOMMENDATIONS:",
        "-" * 40
    ])
    
    for rec in report.recommendations:
        lines.append(f"   {rec}")
    
    lines.extend([
        "",
        "📄 Full report saved to: /workspace/fernando/backend/reports/"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor proxy service health")
    parser.add_argument("--detailed", action="store_true", help="Show detailed report")
    parser.add_argument("--continuous", type=int, help="Run continuous monitoring (seconds)")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    
    args = parser.parse_args()
    
    if args.continuous:
        # Run continuous monitoring
        monitor = ProxyServiceMonitor()
        asyncio.run(monitor.continuous_monitoring(interval=args.interval, duration=args.continuous))
    elif args.detailed:
        # Show detailed report
        report = asyncio.run(detailed_health_check())
        print(report)
    else:
        # Quick health check
        result = asyncio.run(quick_health_check())
        print(json.dumps(result, indent=2))