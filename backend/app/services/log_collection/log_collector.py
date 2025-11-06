"""
Multi-output Log Collection System

Collects logs from various sources and routes them to appropriate destinations.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from queue import Queue, Empty
from dataclasses import dataclass, field
import asyncio
import aiohttp
import redis
from sqlalchemy.orm import Session
from app.models.logging import LogEntry, LogDestination, LogBatch
from app.db.session import SessionLocal
from app.services.logging.structured_logger import structured_logger, LogCategory


class LogSource(Enum):
    """Sources of log data"""
    APPLICATION = "application"
    SYSTEM = "system"
    AUDIT = "audit"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATABASE = "database"
    NETWORK = "network"
    API = "api"
    COMPLIANCE = "compliance"
    FORENSIC = "forensic"


class LogSeverity(Enum):
    """Log severity levels"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DestinationType(Enum):
    """Types of log destinations"""
    FILE = "file"
    DATABASE = "database"
    ELASTICSEARCH = "elasticsearch"
    KAFKA = "kafka"
    REDIS = "redis"
    HTTP_ENDPOINT = "http_endpoint"
    CLOUD_WATCH = "cloud_watch"
    GRAFANA_LOKI = "grafana_loki"
    SPLUNK = "splunk"


@dataclass
class LogEvent:
    """Individual log event structure"""
    timestamp: datetime
    level: LogSeverity
    category: str
    message: str
    source: LogSource
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'category': self.category,
            'message': self.message,
            'source': self.source.value,
            'data': self.data,
            'correlation_id': self.correlation_id,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'session_id': self.session_id,
            'tenant_id': self.tenant_id,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEvent':
        """Create from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            level=LogSeverity(data['level']),
            category=data['category'],
            message=data['message'],
            source=LogSource(data['source']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            user_id=data.get('user_id'),
            request_id=data.get('request_id'),
            session_id=data.get('session_id'),
            tenant_id=data.get('tenant_id'),
            tags=data.get('tags', [])
        )


class LogCollector:
    """Multi-output log collector with buffering and batching"""
    
    def __init__(self, 
                 buffer_size: int = 10000,
                 batch_size: int = 100,
                 batch_timeout: int = 30,
                 redis_url: Optional[str] = None):
        
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.redis_url = redis_url
        
        # Threading components
        self._log_queue = Queue(maxsize=buffer_size)
        self._batch_queue = Queue()
        self._running = False
        self._threads = []
        
        # Redis connection for distributed logging
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                structured_logger.warning(
                    f"Failed to connect to Redis: {str(e)}",
                    redis_url=redis_url
                )
        
        # Log destinations
        self.destinations: Dict[str, Dict[str, Any]] = {}
        self.destination_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            'total_logs_collected': 0,
            'total_logs_processed': 0,
            'total_batches_processed': 0,
            'errors_count': 0,
            'last_processed_time': None,
            'processing_latency_ms': 0.0
        }
        
        self._lock = threading.Lock()
    
    def add_destination(self, 
                       name: str,
                       destination_type: DestinationType,
                       config: Dict[str, Any]) -> None:
        """Add a log destination"""
        
        with self._lock:
            self.destinations[name] = {
                'type': destination_type,
                'config': config,
                'enabled': True,
                'last_error': None,
                'last_success': None,
                'error_count': 0,
                'success_count': 0
            }
            
            # Create appropriate handler
            handler = self._create_destination_handler(destination_type, config)
            self.destination_handlers[name] = handler
            
            structured_logger.info(
                f"Added log destination: {name}",
                destination_type=destination_type.value,
                name=name
            )
    
    def remove_destination(self, name: str) -> None:
        """Remove a log destination"""
        
        with self._lock:
            if name in self.destinations:
                del self.destinations[name]
            
            if name in self.destination_handlers:
                del self.destination_handlers[name]
            
            structured_logger.info(
                f"Removed log destination: {name}",
                name=name
            )
    
    def start(self) -> None:
        """Start the log collector"""
        
        if self._running:
            structured_logger.warning("Log collector is already running")
            return
        
        self._running = True
        
        # Start collector threads
        self._threads.append(threading.Thread(
            target=self._log_collector_worker,
            name="LogCollector-Collector",
            daemon=True
        ))
        
        self._threads.append(threading.Thread(
            target=self._batch_processor_worker,
            name="LogCollector-BatchProcessor",
            daemon=True
        ))
        
        # Start batch distribution threads
        for name in self.destinations:
            self._threads.append(threading.Thread(
                target=self._batch_distributor_worker,
                name=f"LogCollector-Distributor-{name}",
                args=(name,),
                daemon=True
            ))
        
        # Start all threads
        for thread in self._threads:
            thread.start()
        
        structured_logger.info(
            "Log collector started",
            buffer_size=self.buffer_size,
            batch_size=self.batch_size,
            destinations=len(self.destinations)
        )
    
    def stop(self, timeout: int = 30) -> None:
        """Stop the log collector"""
        
        if not self._running:
            return
        
        self._running = False
        
        # Wait for threads to finish
        for thread in self._threads:
            thread.join(timeout=timeout)
        
        # Process remaining logs in queue
        self._process_remaining_logs()
        
        structured_logger.info("Log collector stopped")
    
    def collect_log(self, log_event: LogEvent) -> bool:
        """Collect a log event"""
        
        try:
            self._log_queue.put(log_event, block=False)
            with self._lock:
                self.stats['total_logs_collected'] += 1
            return True
            
        except Exception as e:
            structured_logger.error(
                f"Failed to collect log event: {str(e)}",
                error=str(e),
                category=log_event.category
            )
            return False
    
    def collect_batch(self, log_events: List[LogEvent]) -> int:
        """Collect multiple log events"""
        
        collected = 0
        for log_event in log_events:
            if self.collect_log(log_event):
                collected += 1
        
        return collected
    
    def _create_destination_handler(self, 
                                  destination_type: DestinationType,
                                  config: Dict[str, Any]) -> Callable:
        """Create handler for specific destination type"""
        
        handlers = {
            DestinationType.FILE: self._file_handler,
            DestinationType.DATABASE: self._database_handler,
            DestinationType.ELASTICSEARCH: self._elasticsearch_handler,
            DestinationType.KAFKA: self._kafka_handler,
            DestinationType.REDIS: self._redis_handler,
            DestinationType.HTTP_ENDPOINT: self._http_endpoint_handler,
            DestinationType.CLOUD_WATCH: self._cloud_watch_handler,
            DestinationType.GRAFANA_LOKI: self._grafana_loki_handler,
            DestinationType.SPLUNK: self._splunk_handler
        }
        
        if destination_type not in handlers:
            raise ValueError(f"Unsupported destination type: {destination_type}")
        
        return lambda batch: handlers[destination_type](batch, config)
    
    def _log_collector_worker(self) -> None:
        """Worker thread for collecting logs into batches"""
        
        batch = []
        last_batch_time = time.time()
        
        while self._running:
            try:
                # Get log event with timeout
                try:
                    log_event = self._log_queue.get(timeout=1.0)
                    batch.append(log_event)
                except Empty:
                    # Check if batch timeout reached
                    if batch and (time.time() - last_batch_time) >= self.batch_timeout:
                        self._submit_batch(batch)
                        batch = []
                        last_batch_time = time.time()
                    continue
                
                # Submit batch if size limit reached
                if len(batch) >= self.batch_size:
                    self._submit_batch(batch)
                    batch = []
                    last_batch_time = time.time()
                    
            except Exception as e:
                structured_logger.error(
                    f"Error in log collector worker: {str(e)}",
                    error=str(e)
                )
                time.sleep(1)  # Avoid tight error loops
        
        # Process remaining logs
        if batch:
            self._submit_batch(batch)
    
    def _submit_batch(self, batch: List[LogEvent]) -> None:
        """Submit batch to batch processor"""
        
        try:
            log_batch = LogBatch(
                batch_id=f"batch_{int(time.time() * 1000)}",
                logs=[event.to_dict() for event in batch],
                timestamp=datetime.utcnow(),
                source=batch[0].source.value if batch else "unknown",
                batch_size=len(batch)
            )
            
            self._batch_queue.put(log_batch, block=False)
            
        except Exception as e:
            structured_logger.error(
                f"Failed to submit log batch: {str(e)}",
                error=str(e),
                batch_size=len(batch)
            )
    
    def _batch_processor_worker(self) -> None:
        """Worker thread for processing log batches"""
        
        while self._running:
            try:
                # Get batch with timeout
                log_batch = self._batch_queue.get(timeout=1.0)
                start_time = time.time()
                
                # Distribute to all enabled destinations
                with self._lock:
                    active_destinations = {
                        name: info for name, info in self.destinations.items() 
                        if info['enabled']
                    }
                
                for name, dest_info in active_destinations.items():
                    try:
                        if name in self.destination_handlers:
                            self.destination_handlers[name](log_batch)
                            dest_info['last_success'] = datetime.utcnow()
                            dest_info['success_count'] += 1
                    except Exception as e:
                        dest_info['last_error'] = str(e)
                        dest_info['error_count'] += 1
                        structured_logger.error(
                            f"Failed to send logs to destination {name}: {str(e)}",
                            destination=name,
                            error=str(e)
                        )
                
                # Update statistics
                processing_time = (time.time() - start_time) * 1000
                with self._lock:
                    self.stats['total_logs_processed'] += log_batch.batch_size
                    self.stats['total_batches_processed'] += 1
                    self.stats['last_processed_time'] = datetime.utcnow()
                    self.stats['processing_latency_ms'] = processing_time
                
            except Empty:
                continue
            except Exception as e:
                structured_logger.error(
                    f"Error in batch processor worker: {str(e)}",
                    error=str(e)
                )
                time.sleep(1)
    
    def _batch_distributor_worker(self, destination_name: str) -> None:
        """Worker thread for distributing batches to specific destination"""
        # This is a placeholder for more complex distributed processing
        # In a real implementation, this would handle load balancing and failover
        pass
    
    def _file_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to file destination"""
        
        file_path = config.get('file_path', 'logs/collector.log')
        append_mode = config.get('append_mode', True)
        format_type = config.get('format', 'json')  # json, line, csv
        
        mode = 'a' if append_mode else 'w'
        
        with open(file_path, mode) as f:
            if format_type == 'json':
                for log_dict in batch.logs:
                    f.write(json.dumps(log_dict) + '\n')
            elif format_type == 'line':
                for log_dict in batch.logs:
                    f.write(f"{log_dict['timestamp']} [{log_dict['level']}] {log_dict['message']}\n")
            elif format_type == 'csv':
                # CSV format - write header once
                if not append_mode or f.tell() == 0:
                    import csv
                    writer = csv.DictWriter(f, fieldnames=log_dict.keys())
                    writer.writeheader()
                
                import csv
                writer = csv.DictWriter(f, fieldnames=batch.logs[0].keys())
                writer.writerows(batch.logs)
    
    def _database_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to database destination"""
        
        db: Session = SessionLocal()
        try:
            log_entries = []
            for log_dict in batch.logs:
                log_entry = LogEntry(
                    timestamp=datetime.fromisoformat(log_dict['timestamp']),
                    level=log_dict['level'],
                    category=log_dict['category'],
                    message=log_dict['message'],
                    source=log_dict['source'],
                    data=log_dict.get('data', {}),
                    correlation_id=log_dict.get('correlation_id'),
                    user_id=log_dict.get('user_id'),
                    request_id=log_dict.get('request_id'),
                    session_id=log_dict.get('session_id'),
                    tenant_id=log_dict.get('tenant_id'),
                    tags=log_dict.get('tags', [])
                )
                log_entries.append(log_entry)
            
            db.add_all(log_entries)
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def _elasticsearch_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to Elasticsearch destination"""
        
        import requests
        
        es_url = config.get('elasticsearch_url', 'http://localhost:9200')
        index_pattern = config.get('index_pattern', 'fernando-logs-{YYYY.MM.dd}')
        
        # Prepare bulk request
        bulk_body = ""
        for log_dict in batch.logs:
            # Add index action
            index_name = index_pattern.replace('{YYYY.MM.dd}', 
                                             datetime.fromisoformat(log_dict['timestamp']).strftime('%Y.%m.%d'))
            bulk_body += f'{{"index": {{"_index": "{index_name}", "_id": "{log_dict.get("correlation_id", "")}"}}}}\n'
            bulk_body += json.dumps(log_dict) + '\n'
        
        try:
            response = requests.post(
                f"{es_url}/_bulk",
                data=bulk_body.encode(),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Elasticsearch bulk request failed: {response.status_code}")
                
        except Exception as e:
            structured_logger.error(
                f"Elasticsearch write failed: {str(e)}",
                error=str(e),
                batch_size=batch.batch_size
            )
            raise
    
    def _kafka_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to Kafka destination"""
        
        try:
            from kafka import KafkaProducer
            
            bootstrap_servers = config.get('bootstrap_servers', ['localhost:9092'])
            topic = config.get('topic', 'fernando-logs')
            
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            for log_dict in batch.logs:
                producer.send(topic, log_dict)
            
            producer.flush()
            
        except ImportError:
            raise Exception("kafka-python not installed")
        except Exception as e:
            structured_logger.error(
                f"Kafka write failed: {str(e)}",
                error=str(e)
            )
            raise
    
    def _redis_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to Redis destination"""
        
        if not self.redis_client:
            raise Exception("Redis client not initialized")
        
        redis_key = config.get('redis_key', 'fernando:logs')
        list_name = config.get('list_name', 'logs')
        
        # Store logs in Redis list
        for log_dict in batch.logs:
            self.redis_client.lpush(
                f"{redis_key}:{list_name}",
                json.dumps(log_dict)
            )
        
        # Set expiration
        if config.get('expire_seconds'):
            self.redis_client.expire(
                f"{redis_key}:{list_name}",
                config['expire_seconds']
            )
    
    def _http_endpoint_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to HTTP endpoint destination"""
        
        endpoint_url = config.get('url')
        if not endpoint_url:
            raise Exception("HTTP endpoint URL not configured")
        
        # Use asyncio for async HTTP requests
        async def send_http_batch():
            async with aiohttp.ClientSession() as session:
                payload = {
                    'batch_id': batch.batch_id,
                    'timestamp': batch.timestamp.isoformat(),
                    'logs': batch.logs
                }
                
                try:
                    async with session.post(
                        endpoint_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status >= 400:
                            raise Exception(f"HTTP error: {response.status}")
                except Exception as e:
                    structured_logger.error(
                        f"HTTP endpoint send failed: {str(e)}",
                        endpoint=endpoint_url,
                        error=str(e)
                    )
                    raise
        
        # Run async function in executor to avoid blocking
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_http_batch())
        finally:
            loop.close()
    
    def _cloud_watch_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to AWS CloudWatch"""
        
        try:
            import boto3
            
            log_group = config.get('log_group', '/fernando/logs')
            log_stream = config.get('log_stream', 'default')
            
            # Convert logs to CloudWatch format
            log_events = []
            for log_dict in batch.logs:
                log_events.append({
                    'timestamp': int(datetime.fromisoformat(log_dict['timestamp']).timestamp() * 1000),
                    'message': json.dumps(log_dict)
                })
            
            # Send to CloudWatch
            client = boto3.client('logs')
            client.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=log_events
            )
            
        except ImportError:
            raise Exception("boto3 not installed")
        except Exception as e:
            structured_logger.error(
                f"CloudWatch send failed: {str(e)}",
                error=str(e)
            )
            raise
    
    def _grafana_loki_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to Grafana Loki"""
        
        loki_url = config.get('loki_url', 'http://localhost:3100')
        
        # Convert logs to Loki format
        streams = {}
        for log_dict in batch.logs:
            # Group logs by labels
            labels = {
                'level': log_dict['level'],
                'category': log_dict['category'],
                'source': log_dict['source']
            }
            
            if log_dict.get('tenant_id'):
                labels['tenant'] = log_dict['tenant_id']
            
            label_str = json.dumps(labels, sort_keys=True)
            
            if label_str not in streams:
                streams[label_str] = {
                    'stream': labels,
                    'values': []
                }
            
            streams[label_str]['values'].append([
                str(int(datetime.fromisoformat(log_dict['timestamp']).timestamp() * 1e9)),
                log_dict['message']
            ])
        
        try:
            import requests
            
            response = requests.post(
                f"{loki_url}/loki/api/v1/push",
                json={'streams': list(streams.values())},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code != 204:
                raise Exception(f"Loki push failed: {response.status_code}")
                
        except Exception as e:
            structured_logger.error(
                f"Loki send failed: {str(e)}",
                error=str(e)
            )
            raise
    
    def _splunk_handler(self, batch: LogBatch, config: Dict[str, Any]) -> None:
        """Handle logs to Splunk"""
        
        try:
            import requests
            
            splunk_url = config.get('splunk_url')
            splunk_token = config.get('splunk_token')
            
            if not splunk_url or not splunk_token:
                raise Exception("Splunk URL or token not configured")
            
            headers = {
                'Authorization': f'Splunk {splunk_token}',
                'Content-Type': 'application/json'
            }
            
            # Send logs individually (Splunk HTTP Event Collector format)
            for log_dict in batch.logs:
                payload = {
                    'time': datetime.fromisoformat(log_dict['timestamp']).timestamp(),
                    'host': log_dict.get('source', 'fernando'),
                    'source': 'fernando-logger',
                    'sourcetype': 'json',
                    'event': log_dict
                }
                
                response = requests.post(
                    f"{splunk_url}/services/collector",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code != 200:
                    structured_logger.warning(
                        f"Splunk send failed for event: {response.status_code}",
                        event_id=log_dict.get('correlation_id')
                    )
            
        except Exception as e:
            structured_logger.error(
                f"Splunk send failed: {str(e)}",
                error=str(e)
            )
            raise
    
    def _process_remaining_logs(self) -> None:
        """Process any remaining logs in the queue"""
        
        remaining_logs = []
        
        # Get all remaining logs from queue
        while not self._log_queue.empty():
            try:
                log_event = self._log_queue.get(block=False)
                remaining_logs.append(log_event)
            except Empty:
                break
        
        if remaining_logs:
            # Create final batch
            final_batch = LogBatch(
                batch_id=f"final_batch_{int(time.time() * 1000)}",
                logs=[event.to_dict() for event in remaining_logs],
                timestamp=datetime.utcnow(),
                source="collector_shutdown",
                batch_size=len(remaining_logs)
            )
            
            # Process the final batch
            try:
                for name, dest_info in self.destinations.items():
                    if dest_info['enabled'] and name in self.destination_handlers:
                        self.destination_handlers[name](final_batch)
            except Exception as e:
                structured_logger.error(
                    f"Error processing final logs: {str(e)}",
                    error=str(e),
                    remaining_logs_count=len(remaining_logs)
                )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get log collector statistics"""
        
        with self._lock:
            stats = self.stats.copy()
            
            # Add destination statistics
            stats['destinations'] = {}
            for name, info in self.destinations.items():
                stats['destinations'][name] = {
                    'type': info['type'].value,
                    'enabled': info['enabled'],
                    'last_error': info['last_error'],
                    'last_success': info['last_success'].isoformat() if info['last_success'] else None,
                    'error_count': info['error_count'],
                    'success_count': info['success_count']
                }
            
            stats['queue_size'] = self._log_queue.qsize()
            stats['batch_queue_size'] = self._batch_queue.qsize()
            stats['is_running'] = self._running
            
            return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on log collector"""
        
        stats = self.get_statistics()
        
        health_status = {
            'overall_status': 'healthy',
            'components': {}
        }
        
        # Check queue health
        if stats['queue_size'] > (self.buffer_size * 0.9):
            health_status['overall_status'] = 'warning'
            health_status['components']['log_queue'] = 'high_usage'
        else:
            health_status['components']['log_queue'] = 'healthy'
        
        # Check batch queue health
        if stats['batch_queue_size'] > 1000:
            health_status['overall_status'] = 'warning'
            health_status['components']['batch_queue'] = 'high_usage'
        else:
            health_status['components']['batch_queue'] = 'healthy'
        
        # Check destination health
        for name, dest_info in stats['destinations'].items():
            if dest_info['error_count'] > dest_info['success_count']:
                health_status['components'][f'destination_{name}'] = 'unhealthy'
                health_status['overall_status'] = 'critical'
            elif dest_info['last_error'] and \
                 (datetime.utcnow() - datetime.fromisoformat(dest_info['last_success'])).seconds > 300:
                health_status['components'][f'destination_{name}'] = 'stale'
                if health_status['overall_status'] == 'healthy':
                    health_status['overall_status'] = 'warning'
            else:
                health_status['components'][f'destination_{name}'] = 'healthy'
        
        return health_status


# Global log collector instance
log_collector = LogCollector()