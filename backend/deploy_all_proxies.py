#!/bin/bash
"""
Proxy Server Deployment Script

This script deploys all proxy servers for the Fernando platform
to ensure zero API key exposure while maintaining full functionality.

Usage:
    ./deploy_all_proxies.sh [--production] [--health-check]
"""

import os
import sys
import subprocess
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
import httpx
import signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Proxy server configurations
PROXY_SERVERS = {
    "llm": {
        "port": 8000,
        "path": "/workspace/fernando/proxy-servers/llm",
        "name": "LLM Service Proxy"
    },
    "ocr": {
        "port": 8001,
        "path": "/workspace/fernando/proxy-servers/ocr",
        "name": "OCR Service Proxy"
    },
    "toconline": {
        "port": 8002,
        "path": "/workspace/fernando/proxy-servers/toconline",
        "name": "ToConline Document Extraction Proxy"
    },
    "stripe": {
        "port": 8003,
        "path": "/workspace/fernando/proxy-servers/stripe",
        "name": "Stripe Payment Proxy"
    },
    "paypal": {
        "port": 8004,
        "path": "/workspace/fernando/proxy-servers/paypal",
        "name": "PayPal Payment Proxy"
    },
    "coinbase": {
        "port": 8005,
        "path": "/workspace/fernando/proxy-servers/coinbase",
        "name": "Cryptocurrency Payment Proxy"
    },
    "openai": {
        "port": 8006,
        "path": "/workspace/fernando/proxy-servers/openai",
        "name": "OpenAI Direct Proxy"
    }
}

class ProxyServerManager:
    """Manages deployment and lifecycle of proxy servers"""
    
    def __init__(self, production: bool = False):
        self.production = production
        self.processes: Dict[str, subprocess.Popen] = {}
        self.server_status: Dict[str, Dict[str, Any]] = {}
        
    async def deploy_all_servers(self) -> Dict[str, Any]:
        """Deploy all proxy servers"""
        logger.info("🚀 Starting deployment of all proxy servers...")
        
        results = {
            "total_servers": len(PROXY_SERVERS),
            "deployment_started": time.time(),
            "servers": {}
        }
        
        # Start all servers
        for server_name, config in PROXY_SERVERS.items():
            try:
                status = await self._deploy_server(server_name, config)
                results["servers"][server_name] = status
            except Exception as e:
                logger.error(f"Failed to deploy {server_name}: {e}")
                results["servers"][server_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Wait for servers to be ready
        await asyncio.sleep(3)
        
        # Perform health checks
        health_results = await self._check_all_health()
        results["health_checks"] = health_results
        
        # Wait for servers to be fully ready
        await self._wait_for_ready()
        
        results["deployment_completed"] = time.time()
        results["deployment_duration"] = results["deployment_completed"] - results["deployment_started"]
        
        return results
    
    async def _deploy_server(self, server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a single proxy server"""
        try:
            # Check if server directory exists
            server_path = Path(config["path"])
            if not server_path.exists():
                raise FileNotFoundError(f"Server path does not exist: {server_path}")
            
            # Change to server directory
            os.chdir(server_path)
            
            # Determine startup command
            if self.production:
                # Production startup (using Docker or system service)
                if (server_path / "Dockerfile").exists():
                    cmd = ["docker", "build", "-t", f"fernando-{server_name}-proxy", "."]
                    subprocess.run(cmd, check=True)
                    cmd = ["docker", "run", "-d", "-p", f"{config['port']}:8000", 
                           f"fernando-{server_name}-proxy"]
                else:
                    # Use uvicorn for production
                    cmd = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
            else:
                # Development startup
                cmd = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
            
            logger.info(f"Starting {config['name']} on port {config['port']}")
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[server_name] = process
            
            status = {
                "name": config["name"],
                "port": config["port"],
                "pid": process.pid,
                "status": "starting",
                "command": " ".join(cmd)
            }
            
            return status
            
        except Exception as e:
            return {
                "name": config["name"],
                "error": str(e),
                "status": "failed"
            }
    
    async def _check_all_health(self) -> Dict[str, Any]:
        """Check health of all deployed servers"""
        logger.info("🏥 Performing health checks on all proxy servers...")
        
        health_results = {}
        
        async with httpx.AsyncClient() as client:
            tasks = []
            for server_name, config in PROXY_SERVERS.items():
                if server_name in self.processes:
                    task = self._check_server_health(client, server_name, config)
                    tasks.append(task)
            
            # Run all health checks concurrently
            health_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (server_name, config) in enumerate(PROXY_SERVERS.items()):
                if server_name in self.processes:
                    response = health_responses[i]
                    if isinstance(response, Exception):
                        health_results[server_name] = {
                            "status": "unhealthy",
                            "error": str(response),
                            "response_time": None
                        }
                    else:
                        health_results[server_name] = response
                else:
                    health_results[server_name] = {
                        "status": "not_started",
                        "error": "Server not started"
                    }
        
        return health_results
    
    async def _check_server_health(self, client: httpx.AsyncClient, 
                                  server_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of a single server"""
        try:
            start_time = time.time()
            url = f"http://localhost:{config['port']}/health"
            
            response = await client.get(url, timeout=10.0)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "data": health_data
                }
            else:
                return {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "response_time": response_time
                }
                
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "response_time": None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "response_time": None
            }
    
    async def _wait_for_ready(self, max_wait: int = 30) -> bool:
        """Wait for all servers to be ready"""
        logger.info("⏳ Waiting for all servers to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            all_healthy = True
            
            async with httpx.AsyncClient() as client:
                for server_name, config in PROXY_SERVERS.items():
                    if server_name in self.processes:
                        try:
                            url = f"http://localhost:{config['port']}/health"
                            response = await client.get(url, timeout=2.0)
                            if response.status_code != 200:
                                all_healthy = False
                                break
                        except:
                            all_healthy = False
                            break
            
            if all_healthy:
                logger.info("✅ All proxy servers are ready!")
                return True
            
            await asyncio.sleep(1)
        
        logger.warning("⚠️ Timeout waiting for all servers to be ready")
        return False
    
    def stop_all_servers(self):
        """Stop all running proxy servers"""
        logger.info("🛑 Stopping all proxy servers...")
        
        for server_name, process in self.processes.items():
            try:
                logger.info(f"Stopping {server_name} (PID: {process.pid})")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {server_name}")
                    process.kill()
                    
            except Exception as e:
                logger.error(f"Error stopping {server_name}: {e}")
        
        self.processes.clear()
        logger.info("✅ All proxy servers stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all servers"""
        status = {}
        
        for server_name, process in self.processes.items():
            if process.poll() is None:
                status[server_name] = {
                    "status": "running",
                    "pid": process.pid,
                    "uptime": time.time() - process.start_time if hasattr(process, 'start_time') else "unknown"
                }
            else:
                status[server_name] = {
                    "status": "stopped",
                    "pid": process.pid,
                    "return_code": process.returncode
                }
        
        return status


async def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Fernando platform proxy servers")
    parser.add_argument("--production", action="store_true", help="Deploy in production mode")
    parser.add_argument("--health-check", action="store_true", help="Run health checks only")
    parser.add_argument("--stop", action="store_true", help="Stop all running servers")
    
    args = parser.parse_args()
    
    manager = ProxyServerManager(production=args.production)
    
    # Handle stop command
    if args.stop:
        manager.stop_all_servers()
        return
    
    # Run health check only
    if args.health_check:
        results = await manager._check_all_health()
        print(json.dumps(results, indent=2))
        return
    
    # Deploy all servers
    try:
        results = await manager.deploy_all_servers()
        
        # Print results
        print("\n" + "="*50)
        print("🚀 PROXY SERVER DEPLOYMENT RESULTS")
        print("="*50)
        
        print(f"\n📊 Deployment Summary:")
        print(f"   Total Servers: {results['total_servers']}")
        print(f"   Duration: {results['deployment_duration']:.2f} seconds")
        
        print(f"\n🏥 Health Status:")
        for server_name, health in results['health_checks'].items():
            status_icon = "✅" if health['status'] == 'healthy' else "❌"
            print(f"   {status_icon} {server_name}: {health['status']}")
            if health.get('response_time'):
                print(f"      Response Time: {health['response_time']:.3f}s")
        
        # Save deployment report
        report_file = "/workspace/fernando/backend/proxy_deployment_report.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Generate environment configuration
        generate_env_config(results)
        
    except KeyboardInterrupt:
        print("\n🛑 Deployment interrupted by user")
        manager.stop_all_servers()
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        manager.stop_all_servers()
        sys.exit(1)


def generate_env_config(deployment_results: Dict[str, Any]):
    """Generate environment configuration based on deployment"""
    env_config = []
    
    # Add global proxy settings
    env_config.append("# Generated proxy server configuration")
    env_config.append("PROXY_ENABLED=true")
    env_config.append("PROXY_FALLBACK_ENABLED=true")
    env_config.append("")
    
    # Add service-specific configurations
    for server_name, config in PROXY_SERVERS.items():
        health_status = deployment_results['health_checks'].get(server_name, {}).get('status', 'unknown')
        
        if health_status == 'healthy':
            port = config['port']
            endpoint = f"http://localhost:{port}"
            
            # Add service configuration
            service_upper = server_name.upper()
            env_config.append(f"{service_upper}_PROXY_ENDPOINT={endpoint}")
            env_config.append(f"{service_upper}_PROXY_ENABLED=true")
            env_config.append("")
    
    # Add environment file
    env_file = "/workspace/fernando/backend/.env.proxy"
    with open(env_file, 'w') as f:
        f.write("\n".join(env_config))
    
    print(f"📝 Environment configuration saved to: {env_file}")


if __name__ == "__main__":
    asyncio.run(main())