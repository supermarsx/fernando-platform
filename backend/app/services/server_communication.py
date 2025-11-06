"""
Inter-Server Communication System

This module handles communication between Client Server and Supplier Server instances,
including API integration, server registration, data synchronization, and security.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import uuid
import json
import asyncio
import aiohttp
from urllib.parse import urljoin
import jwt
import hashlib

from ..core.server_architecture import ServerType, server_architecture
from ..core.config import settings
from ..core.telemetry import telemetry_tracker
from ..models.server_architecture import ServerCommunicationLog, ServerRegistration, SyncJob


class CommunicationStatus(str, Enum):
    """Communication status enumeration"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"


class SyncStatus(str, Enum):
    """Synchronization status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Message type enumeration"""
    HEARTBEAT = "heartbeat"
    REGISTRATION = "registration"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    LICENSE_CHECK = "license_check"
    METRICS_REPORT = "metrics_report"
    ERROR_NOTIFICATION = "error_notification"


@dataclass
class ServerEndpoint:
    """Server endpoint configuration"""
    name: str
    url: str
    method: str = "POST"
    requires_auth: bool = True
    timeout: int = 30
    retry_count: int = 3
    auth_header: str = "Authorization"
    content_type: str = "application/json"


@dataclass
class CommunicationMessage:
    """Communication message structure"""
    id: str
    message_type: MessageType
    source_server_id: str
    target_server_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: CommunicationStatus = CommunicationStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class SecurityManager:
    """
    Security manager for inter-server communication
    """
    
    def __init__(self, server_id: str, secret_key: str):
        self.server_id = server_id
        self.secret_key = secret_key
        
    def generate_token(self, target_server_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token for server-to-server authentication"""
        payload = {
            'iss': self.server_id,
            'aud': target_server_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'server_id': self.server_id
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def validate_token(self, token: str, expected_issuer: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check issuer
            if payload.get('iss') != expected_issuer:
                return None
            
            # Check expiration
            if datetime.utcfromtimestamp(payload.get('exp', 0)) < datetime.utcnow():
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    def generate_message_hash(self, message: Dict[str, Any]) -> str:
        """Generate hash for message integrity verification"""
        message_str = json.dumps(message, sort_keys=True)
        return hashlib.sha256(message_str.encode()).hexdigest()
    
    def sign_message(self, message: Dict[str, Any]) -> str:
        """Sign message with HMAC"""
        message_str = json.dumps(message, sort_keys=True)
        return hashlib.sha256((message_str + self.secret_key).encode()).hexdigest()


class APIIntegration:
    """
    API integration manager for inter-server communication
    """
    
    def __init__(self, base_url: str, server_id: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.server_id = server_id
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, endpoint: ServerEndpoint, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to server endpoint"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        url = urljoin(self.base_url, endpoint.url)
        
        # Add authentication headers
        headers = {
            'Content-Type': endpoint.content_type,
            'X-Server-ID': self.server_id,
            'X-Message-ID': str(uuid.uuid4()),
            endpoint.auth_header: f"Bearer {self.auth_token}"
        }
        
        # Add digital signature for security
        security_manager = SecurityManager(self.server_id, settings.SECRET_KEY)
        signature = security_manager.sign_message(data)
        headers['X-Message-Signature'] = signature
        
        try:
            async with self.session.request(
                endpoint.method,
                url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
            ) as response:
                
                response_data = await response.json()
                
                if response.status >= 200 and response.status < 300:
                    return {
                        'success': True,
                        'status_code': response.status,
                        'data': response_data,
                        'headers': dict(response.headers)
                    }
                else:
                    raise aiohttp.ClientError(f"HTTP {response.status}: {response_data}")
                    
        except asyncio.TimeoutError:
            raise aiohttp.ClientError(f"Request timeout after {endpoint.timeout} seconds")
        except Exception as e:
            raise aiohttp.ClientError(f"Request failed: {str(e)}")


class ServerDiscovery:
    """
    Server discovery and registration management
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._known_servers: Dict[str, Dict[str, Any]] = {}
        self._discovery_urls: List[str] = []
        
    def register_discovery_url(self, url: str):
        """Register a server discovery URL"""
        if url not in self._discovery_urls:
            self._discovery_urls.append(url)
            self.logger.info(f"Registered discovery URL: {url}")
    
    async def discover_servers(self) -> List[Dict[str, Any]]:
        """Discover available servers through discovery service"""
        discovered_servers = []
        
        for discovery_url in self._discovery_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(discovery_url, timeout=10) as response:
                        if response.status == 200:
                            servers_data = await response.json()
                            discovered_servers.extend(servers_data.get('servers', []))
                            
            except Exception as e:
                self.logger.warning(f"Failed to discover servers from {discovery_url}: {str(e)}")
        
        # Cache discovered servers
        for server in discovered_servers:
            self._known_servers[server['server_id']] = server
        
        return discovered_servers
    
    def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a known server"""
        return self._known_servers.get(server_id)
    
    def list_known_servers(self) -> List[Dict[str, Any]]:
        """List all known servers"""
        return list(self._known_servers.values())
    
    def remove_server(self, server_id: str):
        """Remove server from known servers"""
        if server_id in self._known_servers:
            del self._known_servers[server_id]
            self.logger.info(f"Removed server from known list: {server_id}")


class DataSynchronization:
    """
    Data synchronization between servers
    """
    
    def __init__(self, server_id: str):
        self.server_id = server_id
        self.logger = logging.getLogger(__name__)
        self._sync_jobs: Dict[str, SyncJob] = {}
        
    async def create_sync_job(self, target_server_id: str, 
                            sync_type: str, data: Dict[str, Any]) -> str:
        """Create a new synchronization job"""
        job_id = str(uuid.uuid4())
        
        sync_job = SyncJob(
            id=job_id,
            source_server_id=self.server_id,
            target_server_id=target_server_id,
            sync_type=sync_type,
            data=data,
            status=SyncStatus.SCHEDULED,
            created_at=datetime.utcnow(),
            scheduled_at=datetime.utcnow()
        )
        
        # Save to database
        db = self._get_db()
        db.add(sync_job)
        db.commit()
        
        self._sync_jobs[job_id] = sync_job
        
        # Start sync job asynchronously
        asyncio.create_task(self._execute_sync_job(job_id))
        
        self.logger.info(f"Created sync job {job_id} to {target_server_id}")
        return job_id
    
    async def _execute_sync_job(self, job_id: str):
        """Execute synchronization job"""
        try:
            job = self._sync_jobs[job_id]
            if not job:
                return
            
            job.status = SyncStatus.IN_PROGRESS
            job.started_at = datetime.utcnow()
            
            # Get target server info
            discovery = ServerDiscovery()
            target_info = discovery.get_server_info(job.target_server_id)
            
            if not target_info:
                raise ValueError(f"Target server {job.target_server_id} not found")
            
            # Prepare sync data
            sync_data = {
                'job_id': job_id,
                'source_server_id': self.server_id,
                'sync_type': job.sync_type,
                'data': job.data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send to target server
            async with APIIntegration(
                target_info['api_url'],
                self.server_id,
                self._generate_auth_token()
            ) as api:
                
                endpoint = ServerEndpoint(
                    name="sync_data",
                    url="/api/sync/receive",
                    method="POST"
                )
                
                result = await api.make_request(endpoint, sync_data)
                
                if result['success']:
                    job.status = SyncStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    job.result = result['data']
                    
                    # Track telemetry
                    telemetry_tracker.track_event('sync_completed', {
                        'job_id': job_id,
                        'source_server': self.server_id,
                        'target_server': job.target_server_id,
                        'sync_type': job.sync_type,
                        'server_type': server_architecture.get_current_server_type()
                    })
                else:
                    raise Exception("Sync operation failed")
            
            # Update database
            db = self._get_db()
            db.merge(job)
            db.commit()
            
            self.logger.info(f"Completed sync job {job_id}")
            
        except Exception as e:
            job = self._sync_jobs.get(job_id)
            if job:
                job.status = SyncStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                
                # Update database
                db = self._get_db()
                db.merge(job)
                db.commit()
                
                self.logger.error(f"Failed sync job {job_id}: {str(e)}")
    
    def get_sync_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get synchronization job status"""
        job = self._sync_jobs.get(job_id)
        if not job:
            # Try to get from database
            db = self._get_db()
            job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
        
        if job:
            return {
                'id': job.id,
                'source_server_id': job.source_server_id,
                'target_server_id': job.target_server_id,
                'sync_type': job.sync_type,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'result': job.result,
                'error_message': job.error_message
            }
        
        return None
    
    def list_sync_jobs(self, status: Optional[SyncStatus] = None) -> List[Dict[str, Any]]:
        """List synchronization jobs"""
        db = self._get_db()
        query = db.query(SyncJob)
        
        if status:
            query = query.filter(SyncJob.status == status)
        
        jobs = query.order_by(SyncJob.created_at.desc()).all()
        
        return [self.get_sync_job_status(job.id) for job in jobs]
    
    def _generate_auth_token(self) -> str:
        """Generate authentication token for API calls"""
        security_manager = SecurityManager(self.server_id, settings.SECRET_KEY)
        return security_manager.generate_token("target_server")
    
    def _get_db(self):
        """Get database session"""
        from ..core.database import get_db
        return next(get_db())


class CommunicationMonitor:
    """
    Communication monitoring and error handling
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._message_queue: List[CommunicationMessage] = []
        self._retry_delays = [1, 5, 15, 30, 60]  # seconds
        
    def queue_message(self, message: CommunicationMessage):
        """Queue message for sending"""
        self._message_queue.append(message)
        self.logger.debug(f"Queued message {message.id} for {message.target_server_id}")
    
    async def process_message_queue(self):
        """Process queued messages"""
        if not self._message_queue:
            return
        
        messages_to_process = self._message_queue[:]
        self._message_queue.clear()
        
        for message in messages_to_process:
            try:
                await self._send_message(message)
            except Exception as e:
                self.logger.error(f"Failed to process message {message.id}: {str(e)}")
    
    async def _send_message(self, message: CommunicationMessage):
        """Send individual message"""
        try:
            # Get target server info
            discovery = ServerDiscovery()
            target_info = discovery.get_server_info(message.target_server_id)
            
            if not target_info:
                raise ValueError(f"Target server {message.target_server_id} not found")
            
            # Prepare message data
            message_data = {
                'message_id': message.id,
                'message_type': message.message_type.value,
                'source_server_id': message.source_server_id,
                'payload': message.payload,
                'timestamp': message.timestamp.isoformat()
            }
            
            # Send message
            async with APIIntegration(
                target_info['api_url'],
                message.source_server_id,
                self._generate_auth_token(message.target_server_id)
            ) as api:
                
                endpoint = ServerEndpoint(
                    name="send_message",
                    url="/api/communication/receive",
                    method="POST"
                )
                
                result = await api.make_request(endpoint, message_data)
                
                if result['success']:
                    message.status = CommunicationStatus.SUCCESS
                    message.response = result['data']
                    
                    # Log successful communication
                    self._log_communication(message, result['data'])
                    
                    # Track telemetry
                    telemetry_tracker.track_event('message_sent_successfully', {
                        'message_id': message.id,
                        'message_type': message.message_type.value,
                        'target_server': message.target_server_id,
                        'server_type': server_architecture.get_current_server_type()
                    })
                else:
                    raise Exception("Message sending failed")
                    
        except Exception as e:
            message.attempts += 1
            message.error_message = str(e)
            
            # Retry if under max attempts
            if message.attempts < message.max_attempts:
                message.status = CommunicationStatus.RETRY
                
                # Re-queue with delay
                delay = self._retry_delays[min(message.attempts - 1, len(self._retry_delays) - 1)]
                await asyncio.sleep(delay)
                self.queue_message(message)
                
                self.logger.warning(f"Retrying message {message.id} (attempt {message.attempts})")
            else:
                message.status = CommunicationStatus.FAILED
                self.logger.error(f"Failed to send message {message.id} after {message.attempts} attempts")
            
            # Log failed communication
            self._log_communication(message, None, str(e))
    
    def _log_communication(self, message: CommunicationMessage, 
                          response: Optional[Dict[str, Any]], error: Optional[str] = None):
        """Log communication to database"""
        try:
            from ..core.database import get_db
            
            log_entry = ServerCommunicationLog(
                id=str(uuid.uuid4()),
                message_id=message.id,
                source_server_id=message.source_server_id,
                target_server_id=message.target_server_id,
                message_type=message.message_type.value,
                status=message.status.value,
                payload=message.payload,
                response=response,
                error_message=error,
                timestamp=datetime.utcnow()
            )
            
            db = next(get_db())
            db.add(log_entry)
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log communication: {str(e)}")
    
    def _generate_auth_token(self, target_server_id: str) -> str:
        """Generate authentication token for specific target"""
        security_manager = SecurityManager(
            server_architecture.get_server_info()['server_id'], 
            settings.SECRET_KEY
        )
        return security_manager.generate_token(target_server_id)
    
    def get_communication_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get communication logs"""
        try:
            from ..core.database import get_db
            
            db = next(get_db())
            logs = db.query(ServerCommunicationLog).order_by(
                ServerCommunicationLog.timestamp.desc()
            ).limit(limit).all()
            
            return [{
                'id': log.id,
                'message_id': log.message_id,
                'source_server_id': log.source_server_id,
                'target_server_id': log.target_server_id,
                'message_type': log.message_type,
                'status': log.status,
                'timestamp': log.timestamp.isoformat(),
                'error_message': log.error_message
            } for log in logs]
            
        except Exception as e:
            self.logger.error(f"Error getting communication logs: {str(e)}")
            return []


class InterServerCommunication:
    """
    Main inter-server communication manager
    """
    
    def __init__(self, server_id: str, server_type: ServerType):
        self.server_id = server_id
        self.server_type = server_type
        self.security_manager = SecurityManager(server_id, settings.SECRET_KEY)
        self.discovery = ServerDiscovery()
        self.synchronization = DataSynchronization(server_id)
        self.monitor = CommunicationMonitor()
        self.logger = logging.getLogger(__name__)
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background communication tasks"""
        # Start message queue processor
        asyncio.create_task(self._message_processor_loop())
        
        # Start heartbeat sender (for client servers)
        if self.server_type == ServerType.CLIENT:
            asyncio.create_task(self._heartbeat_loop())
        
        # Start sync scheduler
        asyncio.create_task(self._sync_scheduler_loop())
    
    async def _message_processor_loop(self):
        """Background task to process message queue"""
        while True:
            try:
                await self.monitor.process_message_queue()
                await asyncio.sleep(1)  # Process every second
            except Exception as e:
                self.logger.error(f"Error in message processor: {str(e)}")
                await asyncio.sleep(5)
    
    async def _heartbeat_loop(self):
        """Background task to send heartbeats to supplier"""
        while True:
            try:
                if self.server_type == ServerType.CLIENT:
                    await self.send_heartbeat()
                await asyncio.sleep(30)  # Every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {str(e)}")
                await asyncio.sleep(30)
    
    async def _sync_scheduler_loop(self):
        """Background task to schedule synchronizations"""
        while True:
            try:
                # Schedule periodic sync (every 5 minutes)
                await self.schedule_periodic_sync()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in sync scheduler: {str(e)}")
                await asyncio.sleep(300)
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to supplier server"""
        try:
            # Get supplier server info
            supplier_info = self._get_supplier_server_info()
            if not supplier_info:
                return False
            
            heartbeat_data = {
                'server_id': self.server_id,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'active',
                'metrics': self._get_server_metrics(),
                'version': settings.APP_VERSION
            }
            
            message = CommunicationMessage(
                id=str(uuid.uuid4()),
                message_type=MessageType.HEARTBEAT,
                source_server_id=self.server_id,
                target_server_id=supplier_info['server_id'],
                payload=heartbeat_data
            )
            
            self.monitor.queue_message(message)
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {str(e)}")
            return False
    
    async def register_with_supplier(self, supplier_url: str) -> bool:
        """Register with supplier server"""
        try:
            # Get supplier server info
            supplier_info = {'server_id': 'supplier', 'api_url': supplier_url}
            
            registration_data = {
                'server_id': self.server_id,
                'server_type': self.server_type.value,
                'registration_token': self._generate_registration_token(),
                'api_url': f"http://localhost:{settings.port}",
                'capabilities': server_architecture.get_available_features(),
                'metadata': {
                    'version': settings.APP_VERSION,
                    'hostname': settings.host,
                    'features': server_architecture.get_available_features()
                }
            }
            
            message = CommunicationMessage(
                id=str(uuid.uuid4()),
                message_type=MessageType.REGISTRATION,
                source_server_id=self.server_id,
                target_server_id=supplier_info['server_id'],
                payload=registration_data
            )
            
            self.monitor.queue_message(message)
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering with supplier: {str(e)}")
            return False
    
    async def request_license_check(self, license_id: str) -> Dict[str, Any]:
        """Request license validation from supplier"""
        try:
            supplier_info = self._get_supplier_server_info()
            if not supplier_info:
                return {'success': False, 'error': 'Supplier server not found'}
            
            request_data = {
                'license_id': license_id,
                'server_id': self.server_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            message = CommunicationMessage(
                id=str(uuid.uuid4()),
                message_type=MessageType.LICENSE_CHECK,
                source_server_id=self.server_id,
                target_server_id=supplier_info['server_id'],
                payload=request_data
            )
            
            # Wait for response (simplified - in real implementation would use async response)
            self.monitor.queue_message(message)
            
            # Return pending status
            return {'success': True, 'status': 'pending', 'message_id': message.id}
            
        except Exception as e:
            self.logger.error(f"Error requesting license check: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def schedule_periodic_sync(self):
        """Schedule periodic data synchronization"""
        try:
            supplier_info = self._get_supplier_server_info()
            if not supplier_info:
                return
            
            # Prepare sync data based on server type
            if self.server_type == ServerType.CLIENT:
                sync_data = self._prepare_client_sync_data()
            else:
                sync_data = self._prepare_supplier_sync_data()
            
            await self.synchronization.create_sync_job(
                supplier_info['server_id'],
                'periodic_sync',
                sync_data
            )
            
        except Exception as e:
            self.logger.error(f"Error scheduling periodic sync: {str(e)}")
    
    def _get_supplier_server_info(self) -> Optional[Dict[str, Any]]:
        """Get supplier server information"""
        # In a real implementation, this would query the database or service registry
        return {'server_id': 'supplier', 'api_url': settings.supplier_server_url}
    
    def _get_server_metrics(self) -> Dict[str, Any]:
        """Get current server metrics"""
        server_info = server_architecture.get_server_info()
        return {
            'uptime': server_info.get('uptime', 0) if server_info else 0,
            'features_enabled': len(server_info.get('available_features', [])) if server_info else 0,
            'status': server_info.get('status', 'unknown') if server_info else 'unknown'
        }
    
    def _generate_registration_token(self) -> str:
        """Generate registration token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _prepare_client_sync_data(self) -> Dict[str, Any]:
        """Prepare client server sync data"""
        # Get client server data
        from .client_server import client_server_api
        
        return {
            'server_type': 'client',
            'metrics': self._get_server_metrics(),
            'customers_count': len(client_server_api.customer_management._customer_metrics),
            'sync_timestamp': datetime.utcnow().isoformat()
        }
    
    def _prepare_supplier_sync_data(self) -> Dict[str, Any]:
        """Prepare supplier server sync data"""
        # Get supplier server data
        from .supplier_server import supplier_server_api
        
        return {
            'server_type': 'supplier',
            'metrics': self._get_server_metrics(),
            'client_servers_count': len(supplier_server_api.client_mgmt.list_client_servers()),
            'sync_timestamp': datetime.utcnow().isoformat()
        }
    
    def get_communication_status(self) -> Dict[str, Any]:
        """Get overall communication status"""
        logs = self.monitor.get_communication_logs(10)
        sync_jobs = self.synchronization.list_sync_jobs()
        
        return {
            'server_id': self.server_id,
            'server_type': self.server_type,
            'recent_messages': len([log for log in logs if log['status'] == 'success']),
            'failed_messages': len([log for log in logs if log['status'] == 'failed']),
            'active_sync_jobs': len([job for job in sync_jobs if job['status'] in ['scheduled', 'in_progress']]),
            'queued_messages': len(self.monitor._message_queue),
            'last_heartbeat': datetime.utcnow().isoformat()
        }


# Global instances will be initialized based on server type
inter_server_communication: Optional[InterServerCommunication] = None


def initialize_inter_server_communication(server_id: str, server_type: ServerType):
    """Initialize inter-server communication system"""
    global inter_server_communication
    inter_server_communication = InterServerCommunication(server_id, server_type)
    return inter_server_communication


def get_inter_server_communication() -> InterServerCommunication:
    """Get inter-server communication instance"""
    if not inter_server_communication:
        raise RuntimeError("Inter-server communication not initialized")
    return inter_server_communication