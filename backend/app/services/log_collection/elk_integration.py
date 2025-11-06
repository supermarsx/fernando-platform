"""
ELK Stack Integration for Log Aggregation

Provides comprehensive integration with Elasticsearch, Logstash, and Kibana for enterprise log management.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session
from app.models.logging import ELKConfiguration, LogIndexTemplate, SearchQuery
from app.db.session import SessionLocal
from app.services.logging.structured_logger import structured_logger


class IndexPattern(Enum):
    """Predefined index patterns for different log types"""
    APPLICATION_LOGS = "fernando-app-{YYYY.MM.dd}"
    AUDIT_LOGS = "fernando-audit-{YYYY.MM.dd}"
    SECURITY_LOGS = "fernando-security-{YYYY.MM.dd}"
    COMPLIANCE_LOGS = "fernando-compliance-{YYYY.MM.dd}"
    FORENSIC_LOGS = "fernando-forensic-{YYYY.MM.dd}"
    PERFORMANCE_LOGS = "fernando-perf-{YYYY.MM.dd}"
    ERROR_LOGS = "fernando-error-{YYYY.MM.dd}"


class AggregationType(Enum):
    """Elasticsearch aggregation types"""
    TERMS = "terms"
    DATE_HISTOGRAM = "date_histogram"
    AVERAGE = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    RANGE = "range"
    HISTOGRAM = "histogram"


class ESQueryType(Enum):
    """Elasticsearch query types"""
    MATCH = "match"
    MATCH_ALL = "match_all"
    TERM = "term"
    TERMS = "terms"
    RANGE = "range"
    BOOL = "bool"
    EXISTS = "exists"
    WILDCARD = "wildcard"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"


@dataclass
class SearchResult:
    """Search result from Elasticsearch"""
    total_hits: int
    hits: List[Dict[str, Any]]
    aggregations: Optional[Dict[str, Any]]
    took_ms: float
    index: str


@dataclass
class ELKIndex:
    """ELK index information"""
    name: str
    health: str
    status: str
    docs_count: int
    docs_deleted: int
    store_size: str
    creation_date: datetime
    template_name: Optional[str] = None


class ELKIntegration:
    """Enterprise ELK stack integration for log aggregation and analysis"""
    
    def __init__(self, 
                 elasticsearch_url: str,
                 kibana_url: Optional[str] = None,
                 logstash_url: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 api_key: Optional[str] = None):
        
        self.elasticsearch_url = elasticsearch_url.rstrip('/')
        self.kibana_url = kibana_url.rstrip('/') if kibana_url else None
        self.logstash_url = logstash_url.rstrip('/') if logstash_url else None
        
        # Authentication
        self.auth = None
        if api_key:
            self.auth = HTTPBasicAuth(api_key, '')
        elif username and password:
            self.auth = HTTPBasicAuth(username, password)
        
        # Connection session
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth
        
        # Headers
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Index templates and configurations
        self.index_templates = {}
        self.index_lifecycle_policies = {}
        
        # Threading for background operations
        self._background_threads = []
        self._running = False
        
        # Statistics
        self.stats = {
            'total_searches': 0,
            'total_ingested': 0,
            'search_errors': 0,
            'ingest_errors': 0,
            'avg_search_time_ms': 0.0,
            'last_ingest_time': None,
            'cluster_health': 'unknown'
        }
        
        self._lock = threading.Lock()
    
    def initialize(self) -> bool:
        """Initialize ELK integration"""
        
        try:
            # Test Elasticsearch connection
            if not self._test_connection():
                structured_logger.error("Failed to connect to Elasticsearch")
                return False
            
            # Initialize index templates
            self._initialize_index_templates()
            
            # Initialize index lifecycle management
            self._initialize_index_lifecycle()
            
            # Setup Kibana dashboards (if available)
            if self.kibana_url:
                self._setup_kibana_dashboards()
            
            structured_logger.info(
                "ELK integration initialized successfully",
                elasticsearch_url=self.elasticsearch_url,
                kibana_url=self.kibana_url
            )
            
            return True
            
        except Exception as e:
            structured_logger.error(
                f"Failed to initialize ELK integration: {str(e)}",
                error=str(e)
            )
            return False
    
    def start_background_monitoring(self) -> None:
        """Start background monitoring and maintenance"""
        
        if self._running:
            return
        
        self._running = True
        
        # Start cluster health monitoring
        self._background_threads.append(threading.Thread(
            target=self._cluster_health_monitor,
            name="ELK-HealthMonitor",
            daemon=True
        ))
        
        # Start index lifecycle monitoring
        self._background_threads.append(threading.Thread(
            target=self._index_lifecycle_monitor,
            name="ELK-LifecycleMonitor",
            daemon=True
        ))
        
        # Start statistics collector
        self._background_threads.append(threading.Thread(
            target=self._statistics_collector,
            name="ELK-StatsCollector",
            daemon=True
        ))
        
        # Start all threads
        for thread in self._background_threads:
            thread.start()
        
        structured_logger.info("ELK background monitoring started")
    
    def stop_background_monitoring(self) -> None:
        """Stop background monitoring"""
        
        self._running = False
        
        for thread in self._background_threads:
            thread.join(timeout=5)
        
        structured_logger.info("ELK background monitoring stopped")
    
    def create_index_template(self, 
                            template_name: str,
                            index_pattern: str,
                            mappings: Dict[str, Any],
                            settings: Optional[Dict[str, Any]] = None) -> bool:
        """Create Elasticsearch index template"""
        
        try:
            template_data = {
                "index_patterns": [index_pattern],
                "mappings": mappings,
                "settings": settings or {}
            }
            
            response = requests.put(
                f"{self.elasticsearch_url}/_index_template/{template_name}",
                json=template_data,
                headers=self.headers,
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                structured_logger.info(
                    f"Created index template: {template_name}",
                    template_name=template_name,
                    index_pattern=index_pattern
                )
                return True
            else:
                structured_logger.error(
                    f"Failed to create index template: {response.status_code}",
                    template_name=template_name,
                    response=response.text
                )
                return False
                
        except Exception as e:
            structured_logger.error(
                f"Error creating index template: {str(e)}",
                template_name=template_name,
                error=str(e)
            )
            return False
    
    def ingest_logs(self, 
                   index_pattern: IndexPattern,
                   logs: List[Dict[str, Any]],
                   bulk_size: int = 1000) -> bool:
        """Ingest logs into Elasticsearch using bulk API"""
        
        try:
            total_ingested = 0
            total_batches = (len(logs) + bulk_size - 1) // bulk_size
            
            for i in range(0, len(logs), bulk_size):
                batch = logs[i:i + bulk_size]
                
                if self._bulk_ingest(index_pattern, batch):
                    total_ingested += len(batch)
                else:
                    structured_logger.error(
                        f"Bulk ingest failed for batch {i//bulk_size + 1}",
                        batch_size=len(batch),
                        total_batches=total_batches
                    )
                    return False
            
            with self._lock:
                self.stats['total_ingested'] += total_ingested
                self.stats['last_ingest_time'] = datetime.utcnow()
            
            structured_logger.info(
                f"Successfully ingested {total_ingested} logs",
                index_pattern=index_pattern.value,
                total_ingested=total_ingested,
                total_batches=total_batches
            )
            
            return True
            
        except Exception as e:
            structured_logger.error(
                f"Error ingesting logs: {str(e)}",
                error=str(e),
                index_pattern=index_pattern.value
            )
            with self._lock:
                self.stats['ingest_errors'] += 1
            return False
    
    def search_logs(self, 
                   index_pattern: str,
                   query: Dict[str, Any],
                   size: int = 1000,
                   from_offset: int = 0,
                   sort: Optional[List[str]] = None) -> SearchResult:
        """Search logs in Elasticsearch"""
        
        try:
            search_body = {
                "query": query,
                "size": size,
                "from": from_offset,
                "sort": sort or ["@timestamp:desc"]
            }
            
            response = requests.post(
                f"{self.elasticsearch_url}/{index_pattern}/_search",
                json=search_body,
                headers=self.headers,
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                search_result = SearchResult(
                    total_hits=result['hits']['total']['value'],
                    hits=[hit['_source'] for hit in result['hits']['hits']],
                    aggregations=result.get('aggregations'),
                    took_ms=result['took'],
                    index=index_pattern
                )
                
                with self._lock:
                    self.stats['total_searches'] += 1
                    # Update average search time
                    old_avg = self.stats['avg_search_time_ms']
                    count = self.stats['total_searches']
                    self.stats['avg_search_time_ms'] = (old_avg * (count - 1) + result['took']) / count
                
                return search_result
            else:
                structured_logger.error(
                    f"Elasticsearch search failed: {response.status_code}",
                    index_pattern=index_pattern,
                    query=query,
                    response=response.text
                )
                with self._lock:
                    self.stats['search_errors'] += 1
                raise Exception(f"Search failed with status {response.status_code}")
                
        except Exception as e:
            structured_logger.error(
                f"Error searching logs: {str(e)}",
                error=str(e),
                index_pattern=index_pattern,
                query=query
            )
            with self._lock:
                self.stats['search_errors'] += 1
            raise
    
    def advanced_search(self, 
                       index_pattern: str,
                       bool_queries: List[Dict[str, Any]],
                       aggregations: Optional[List[Dict[str, Any]]] = None,
                       size: int = 1000) -> SearchResult:
        """Perform advanced search with boolean queries and aggregations"""
        
        try:
            query = {
                "bool": {
                    "must": bool_queries
                }
            }
            
            search_body = {
                "query": query,
                "size": size
            }
            
            if aggregations:
                search_body["aggs"] = {}
                for agg in aggregations:
                    search_body["aggs"][agg['name']] = agg['aggregation']
            
            return self.search_logs(index_pattern, search_body, size)
            
        except Exception as e:
            structured_logger.error(
                f"Error in advanced search: {str(e)}",
                index_pattern=index_pattern,
                error=str(e)
            )
            raise
    
    def create_visualization(self,
                           viz_name: str,
                           index_pattern: str,
                           visualization_type: str,
                           query: Dict[str, Any],
                           agg_config: Dict[str, Any]) -> bool:
        """Create Kibana visualization"""
        
        if not self.kibana_url:
            structured_logger.warning("Kibana URL not configured")
            return False
        
        try:
            viz_config = {
                "attributes": {
                    "title": viz_name,
                    "visState": {
                        "type": visualization_type,
                        "params": agg_config
                    },
                    "uiStateJSON": {},
                    "kibanaSavedObjectMeta": {
                        "searchSourceJSON": json.dumps({
                            "index": index_pattern,
                            "query": query
                        })
                    }
                }
            }
            
            response = requests.post(
                f"{self.kibana_url}/api/saved_objects/visualization",
                json=viz_config,
                headers=self.headers,
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                structured_logger.info(
                    f"Created Kibana visualization: {viz_name}",
                    viz_name=viz_name,
                    index_pattern=index_pattern
                )
                return True
            else:
                structured_logger.error(
                    f"Failed to create Kibana visualization: {response.status_code}",
                    viz_name=viz_name,
                    response=response.text
                )
                return False
                
        except Exception as e:
            structured_logger.error(
                f"Error creating Kibana visualization: {str(e)}",
                viz_name=viz_name,
                error=str(e)
            )
            return False
    
    def create_dashboard(self,
                        dashboard_name: str,
                        visualizations: List[str],
                        index_pattern: str = None) -> bool:
        """Create Kibana dashboard"""
        
        if not self.kibana_url:
            structured_logger.warning("Kibana URL not configured")
            return False
        
        try:
            dashboard_config = {
                "attributes": {
                    "title": dashboard_name,
                    "visState": json.dumps({"Panels": []}),
                    "kibanaSavedObjectMeta": {
                        "searchSourceJSON": json.dumps({
                            "index": index_pattern,
                            "query": {"query": "", "language": "lucene"}
                        })
                    },
                    "optionsJSON": json.dumps({"darkTheme": False})
                }
            }
            
            response = requests.post(
                f"{self.kibana_url}/api/saved_objects/dashboard",
                json=dashboard_config,
                headers=self.headers,
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                dashboard_id = response.json()['id']
                
                # Add visualizations to dashboard
                for viz_id in visualizations:
                    self._add_visualization_to_dashboard(dashboard_id, viz_id)
                
                structured_logger.info(
                    f"Created Kibana dashboard: {dashboard_name}",
                    dashboard_name=dashboard_name,
                    dashboard_id=dashboard_id
                )
                return True
            else:
                structured_logger.error(
                    f"Failed to create Kibana dashboard: {response.status_code}",
                    dashboard_name=dashboard_name,
                    response=response.text
                )
                return False
                
        except Exception as e:
            structured_logger.error(
                f"Error creating Kibana dashboard: {str(e)}",
                dashboard_name=dashboard_name,
                error=str(e)
            )
            return False
    
    def get_cluster_health(self) -> Dict[str, Any]:
        """Get Elasticsearch cluster health"""
        
        try:
            response = requests.get(
                f"{self.elasticsearch_url}/_cluster/health",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 200:
                health_data = response.json()
                with self._lock:
                    self.stats['cluster_health'] = health_data.get('status', 'unknown')
                return health_data
            else:
                structured_logger.error(
                    f"Failed to get cluster health: {response.status_code}",
                    response=response.text
                )
                return {}
                
        except Exception as e:
            structured_logger.error(
                f"Error getting cluster health: {str(e)}",
                error=str(e)
            )
            return {}
    
    def get_indices_info(self) -> List[ELKIndex]:
        """Get information about all indices"""
        
        try:
            response = requests.get(
                f"{self.elasticsearch_url}/_cat/indices?v",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 200:
                indices = []
                for line in response.text.strip().split('\n')[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 8:
                        indices.append(ELKIndex(
                            name=parts[2],
                            health=parts[0],
                            status=parts[1],
                            docs_count=int(parts[7]) if parts[7] != '-' else 0,
                            docs_deleted=int(parts[8]) if len(parts) > 8 and parts[8] != '-' else 0,
                            store_size=parts[10] if len(parts) > 10 else 'unknown',
                            creation_date=datetime.utcnow(),  # Would need to parse from API
                            template_name=None
                        ))
                return indices
            else:
                structured_logger.error(
                    f"Failed to get indices info: {response.status_code}",
                    response=response.text
                )
                return []
                
        except Exception as e:
            structured_logger.error(
                f"Error getting indices info: {str(e)}",
                error=str(e)
            )
            return []
    
    def delete_old_indices(self, index_pattern: str, days_to_keep: int = 30) -> int:
        """Delete indices older than specified days"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            date_str = cutoff_date.strftime('%Y.%m.%d')
            
            # Find indices to delete
            indices_info = self.get_indices_info()
            indices_to_delete = [
                idx.name for idx in indices_info 
                if index_pattern.replace('*', '') in idx.name and 
                   date_str in idx.name
            ]
            
            deleted_count = 0
            for index_name in indices_to_delete:
                response = requests.delete(
                    f"{self.elasticsearch_url}/{index_name}",
                    headers=self.headers,
                    auth=self.auth,
                    timeout=30
                )
                
                if response.status_code == 200:
                    deleted_count += 1
                    structured_logger.info(
                        f"Deleted old index: {index_name}",
                        index_name=index_name,
                        cutoff_date=date_str
                    )
                else:
                    structured_logger.error(
                        f"Failed to delete index {index_name}: {response.status_code}",
                        index_name=index_name
                    )
            
            return deleted_count
            
        except Exception as e:
            structured_logger.error(
                f"Error deleting old indices: {str(e)}",
                error=str(e),
                index_pattern=index_pattern
            )
            return 0
    
    def _test_connection(self) -> bool:
        """Test connection to Elasticsearch"""
        
        try:
            response = requests.get(
                f"{self.elasticsearch_url}/",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _initialize_index_templates(self) -> None:
        """Initialize default index templates"""
        
        # Common mappings for all log indices
        common_mapping = {
            "properties": {
                "@timestamp": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_millis"
                },
                "level": {"type": "keyword"},
                "category": {"type": "keyword"},
                "source": {"type": "keyword"},
                "message": {"type": "text", "analyzer": "standard"},
                "correlation_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "request_id": {"type": "keyword"},
                "session_id": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "data": {"type": "object", "enabled": True}
            }
        }
        
        # Create templates for different log types
        templates = {
            "fernando-app-logs": {
                "pattern": IndexPattern.APPLICATION_LOGS.value,
                "mapping": common_mapping
            },
            "fernando-audit-logs": {
                "pattern": IndexPattern.AUDIT_LOGS.value,
                "mapping": common_mapping
            },
            "fernando-security-logs": {
                "pattern": IndexPattern.SECURITY_LOGS.value,
                "mapping": common_mapping
            },
            "fernando-compliance-logs": {
                "pattern": IndexPattern.COMPLIANCE_LOGS.value,
                "mapping": common_mapping
            },
            "fernando-forensic-logs": {
                "pattern": IndexPattern.FORENSIC_LOGS.value,
                "mapping": common_mapping
            }
        }
        
        for template_name, config in templates.items():
            self.create_index_template(template_name, config["pattern"], config["mapping"])
    
    def _initialize_index_lifecycle(self) -> None:
        """Initialize index lifecycle management"""
        
        # This would create ILM policies for automatic index rollover and deletion
        # Implementation depends on ELK version and configuration
        pass
    
    def _setup_kibana_dashboards(self) -> None:
        """Setup Kibana dashboards and visualizations"""
        
        try:
            # Create main application logs dashboard
            self.create_dashboard(
                "Fernando Application Logs",
                ["log-levels", "log-categories", "error-timeline"],
                IndexPattern.APPLICATION_LOGS.value
            )
            
            # Create security dashboard
            self.create_dashboard(
                "Fernando Security Logs",
                ["security-events", "failed-logins", "suspicious-activity"],
                IndexPattern.SECURITY_LOGS.value
            )
            
            # Create compliance dashboard
            self.create_dashboard(
                "Fernando Compliance Logs",
                ["gdpr-events", "sox-controls", "compliance-status"],
                IndexPattern.COMPLIANCE_LOGS.value
            )
            
        except Exception as e:
            structured_logger.warning(
                f"Failed to setup Kibana dashboards: {str(e)}",
                error=str(e)
            )
    
    def _bulk_ingest(self, index_pattern: IndexPattern, logs: List[Dict[str, Any]]) -> bool:
        """Perform bulk ingestion of logs"""
        
        try:
            # Prepare bulk request body
            bulk_body = ""
            current_date = datetime.utcnow().strftime('%Y.%m.%d')
            index_name = index_pattern.value.replace('{YYYY.MM.dd}', current_date)
            
            for log in logs:
                # Add index action
                bulk_body += f'{{"index": {{"_index": "{index_name}"}}}}\n'
                
                # Add document with @timestamp
                log_doc = log.copy()
                if 'timestamp' not in log_doc:
                    log_doc['@timestamp'] = datetime.utcnow().isoformat()
                elif 'timestamp' in log_doc:
                    log_doc['@timestamp'] = log_doc.pop('timestamp')
                
                bulk_body += json.dumps(log_doc) + '\n'
            
            response = requests.post(
                f"{self.elasticsearch_url}/_bulk",
                data=bulk_body.encode(),
                headers=self.headers,
                auth=self.auth,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('errors', True):
                    structured_logger.warning(
                        f"Bulk ingest had errors: {result.get('items', [])}",
                        error_count=len([item for item in result.get('items', []) 
                                       if item.get('index', {}).get('error')])
                    )
                    return False
                
                return True
            else:
                structured_logger.error(
                    f"Bulk ingest failed: {response.status_code}",
                    response=response.text
                )
                return False
                
        except Exception as e:
            structured_logger.error(
                f"Error in bulk ingest: {str(e)}",
                error=str(e)
            )
            return False
    
    def _add_visualization_to_dashboard(self, dashboard_id: str, viz_id: str) -> bool:
        """Add visualization to existing dashboard"""
        
        # This would implement the logic to add visualizations to dashboards
        # Implementation depends on Kibana API specifics
        return True
    
    def _cluster_health_monitor(self) -> None:
        """Background thread for monitoring cluster health"""
        
        while self._running:
            try:
                self.get_cluster_health()
                time.sleep(60)  # Check every minute
            except Exception as e:
                structured_logger.error(
                    f"Error in cluster health monitor: {str(e)}",
                    error=str(e)
                )
                time.sleep(60)
    
    def _index_lifecycle_monitor(self) -> None:
        """Background thread for index lifecycle management"""
        
        while self._running:
            try:
                # Delete old indices periodically
                self.delete_old_indices("fernando-app-*", days_to_keep=30)
                self.delete_old_indices("fernando-audit-*", days_to_keep=2555)  # 7 years
                self.delete_old_indices("fernando-security-*", days_to_keep=2555)  # 7 years
                
                time.sleep(3600)  # Check every hour
            except Exception as e:
                structured_logger.error(
                    f"Error in index lifecycle monitor: {str(e)}",
                    error=str(e)
                )
                time.sleep(3600)
    
    def _statistics_collector(self) -> None:
        """Background thread for collecting statistics"""
        
        while self._running:
            try:
                # Update statistics
                self.stats['timestamp'] = datetime.utcnow().isoformat()
                
                # Log statistics periodically
                structured_logger.info(
                    "ELK Statistics",
                    **self.stats
                )
                
                time.sleep(300)  # Every 5 minutes
            except Exception as e:
                structured_logger.error(
                    f"Error in statistics collector: {str(e)}",
                    error=str(e)
                )
                time.sleep(300)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ELK integration statistics"""
        
        with self._lock:
            return self.stats.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on ELK integration"""
        
        health_status = {
            'overall_status': 'healthy',
            'elasticsearch': 'unknown',
            'kibana': 'unknown',
            'cluster_health': self.stats.get('cluster_health', 'unknown'),
            'statistics': self.get_statistics()
        }
        
        # Check Elasticsearch connectivity
        try:
            if self._test_connection():
                health_status['elasticsearch'] = 'healthy'
                
                # Check cluster health
                cluster_health = self.get_cluster_health()
                if cluster_health:
                    status = cluster_health.get('status', 'unknown')
                    if status == 'red':
                        health_status['overall_status'] = 'critical'
                        health_status['cluster_health'] = 'red'
                    elif status == 'yellow':
                        health_status['overall_status'] = 'warning'
                        health_status['cluster_health'] = 'yellow'
            else:
                health_status['elasticsearch'] = 'unhealthy'
                health_status['overall_status'] = 'critical'
        except Exception as e:
            health_status['elasticsearch'] = f'error: {str(e)}'
            health_status['overall_status'] = 'critical'
        
        # Check Kibana connectivity
        if self.kibana_url:
            try:
                response = requests.get(
                    f"{self.kibana_url}/api/status",
                    headers=self.headers,
                    auth=self.auth,
                    timeout=10
                )
                health_status['kibana'] = 'healthy' if response.status_code == 200 else 'unhealthy'
            except Exception:
                health_status['kibana'] = 'unhealthy'
                if health_status['overall_status'] == 'healthy':
                    health_status['overall_status'] = 'warning'
        
        return health_status


# Global ELK integration instance
elk_integration = None