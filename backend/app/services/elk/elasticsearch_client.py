"""
Elasticsearch Client for Advanced Log Management
Handles all Elasticsearch operations including indexing, searching, and management
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError, RequestError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Advanced Elasticsearch client for enterprise logging"""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 9200,
                 scheme: str = "http",
                 username: str = None,
                 password: str = None,
                 index_prefix: str = "fernando-logs"):
        """
        Initialize Elasticsearch client
        
        Args:
            host: Elasticsearch host
            port: Elasticsearch port
            scheme: Connection scheme (http/https)
            username: Authentication username
            password: Authentication password
            index_prefix: Prefix for all indices
        """
        self.host = host
        self.port = port
        self.scheme = scheme
        self.index_prefix = index_prefix
        
        # Connection configuration
        connection_config = {
            'host': host,
            'port': port,
            'scheme': scheme
        }
        
        if username and password:
            connection_config.update({
                'http_auth': (username, password),
                'use_ssl': scheme == 'https'
            })
        
        self.client = Elasticsearch([connection_config])
        self._verify_connection()
        
        # Index templates and settings
        self.index_templates = {
            'application_logs': self._get_application_log_mapping(),
            'audit_logs': self._get_audit_log_mapping(),
            'security_logs': self._get_security_log_mapping(),
            'performance_logs': self._get_performance_log_mapping(),
            'compliance_logs': self._get_compliance_log_mapping(),
            'user_activity_logs': self._get_user_activity_log_mapping()
        }
        
        # Initialize indices
        self._initialize_indices()
    
    def _verify_connection(self):
        """Verify Elasticsearch connection"""
        try:
            if not self.client.ping():
                raise Exception("Cannot connect to Elasticsearch")
            logger.info("Elasticsearch connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    def _get_application_log_mapping(self) -> Dict:
        """Define application log index mapping"""
        return {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "level": {"type": "keyword"},
                    "logger": {"type": "keyword"},
                    "message": {"type": "text", "analyzer": "standard"},
                    "module": {"type": "keyword"},
                    "function": {"type": "keyword"},
                    "line_number": {"type": "integer"},
                    "stack_trace": {"type": "text"},
                    "context": {"type": "object", "enabled": True},
                    "request_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "session_id": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "version": {"type": "keyword"},
                    "application": {"type": "keyword"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "index.refresh_interval": "5s"
            }
        }
    
    def _get_audit_log_mapping(self) -> Dict:
        """Define audit log index mapping"""
        return {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "action": {"type": "keyword"},
                    "resource": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "user_email": {"type": "keyword"},
                    "ip_address": {"type": "ip"},
                    "user_agent": {"type": "text"},
                    "success": {"type": "boolean"},
                    "details": {"type": "object", "enabled": True},
                    "changes": {"type": "object", "enabled": True},
                    "risk_level": {"type": "keyword"},
                    "compliance_flags": {"type": "keyword"},
                    "retention_date": {"type": "date"},
                    "environment": {"type": "keyword"}
                }
            }
        }
    
    def _get_security_log_mapping(self) -> Dict:
        """Define security log index mapping"""
        return {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "severity": {"type": "keyword"},
                    "source_ip": {"type": "ip"},
                    "target_ip": {"type": "ip"},
                    "user_id": {"type": "keyword"},
                    "user_agent": {"type": "text"},
                    "protocol": {"type": "keyword"},
                    "port": {"type": "integer"},
                    "method": {"type": "keyword"},
                    "endpoint": {"type": "keyword"},
                    "status_code": {"type": "integer"},
                    "blocked": {"type": "boolean"},
                    "threat_type": {"type": "keyword"},
                    "threat_score": {"type": "float"},
                    "geolocation": {"type": "geo_point"},
                    "threat_intelligence": {"type": "object", "enabled": True}
                }
            }
        }
    
    def _get_performance_log_mapping(self) -> Dict:
        """Define performance log index mapping"""
        return {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "metric_name": {"type": "keyword"},
                    "metric_type": {"type": "keyword"},
                    "value": {"type": "float"},
                    "unit": {"type": "keyword"},
                    "tags": {"type": "object", "enabled": True},
                    "dimensions": {"type": "object", "enabled": True},
                    "percentile": {"type": "keyword"},
                    "threshold": {"type": "float"},
                    "alert_status": {"type": "keyword"}
                }
            }
        }
    
    def _get_compliance_log_mapping(self) -> Dict:
        """Define compliance log index mapping"""
        return {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "regulation": {"type": "keyword"},
                    "requirement": {"type": "keyword"},
                    "control": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "evidence": {"type": "object", "enabled": True},
                    "audit_period": {"type": "keyword"},
                    "assessor": {"type": "keyword"},
                    "findings": {"type": "object", "enabled": True},
                    "remediation": {"type": "object", "enabled": True},
                    "severity": {"type": "keyword"},
                    "compliance_score": {"type": "float"}
                }
            }
        }
    
    def _get_user_activity_log_mapping(self) -> Dict:
        """Define user activity log index mapping"""
        return {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "user_id": {"type": "keyword"},
                    "user_email": {"type": "keyword"},
                    "action": {"type": "keyword"},
                    "resource": {"type": "keyword"},
                    "resource_id": {"type": "keyword"},
                    "success": {"type": "boolean"},
                    "response_time": {"type": "float"},
                    "data_volume": {"type": "long"},
                    "session_duration": {"type": "integer"},
                    "ip_address": {"type": "ip"},
                    "device_info": {"type": "object", "enabled": True},
                    "location": {"type": "geo_point"},
                    "compliance_relevance": {"type": "boolean"}
                }
            }
        }
    
    def _initialize_indices(self):
        """Initialize all log indices"""
        for index_name, mapping in self.index_templates.items():
            full_index_name = f"{self.index_prefix}-{index_name}"
            try:
                if not self.client.indices.exists(index=full_index_name):
                    self.client.indices.create(
                        index=full_index_name,
                        body=mapping
                    )
                    logger.info(f"Created index: {full_index_name}")
            except Exception as e:
                logger.error(f"Failed to create index {full_index_name}: {e}")
    
    def index_log(self, index_type: str, document: Dict) -> str:
        """
        Index a log document
        
        Args:
            index_type: Type of log (application_logs, audit_logs, etc.)
            document: Log document to index
            
        Returns:
            Document ID
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_type}"
            
            # Add timestamp if not present
            if 'timestamp' not in document:
                document['timestamp'] = datetime.utcnow()
            
            response = self.client.index(
                index=full_index_name,
                body=document
            )
            
            return response['_id']
            
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            raise
    
    def bulk_index_logs(self, index_type: str, documents: List[Dict]) -> Dict:
        """
        Bulk index multiple log documents
        
        Args:
            index_type: Type of logs
            documents: List of log documents
            
        Returns:
            Bulk operation results
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_type}"
            
            def generate_actions():
                for doc in documents:
                    if 'timestamp' not in doc:
                        doc['timestamp'] = datetime.utcnow()
                    yield {
                        "_index": full_index_name,
                        "_source": doc
                    }
            
            response = helpers.bulk(
                self.client,
                generate_actions(),
                chunk_size=1000,
                request_timeout=30
            )
            
            logger.info(f"Bulk indexed {len(documents)} documents")
            return response
            
        except Exception as e:
            logger.error(f"Failed to bulk index documents: {e}")
            raise
    
    def search_logs(self, 
                   index_type: str, 
                   query: Dict,
                   size: int = 100,
                   from_: int = 0,
                   sort: List[Dict] = None) -> Dict:
        """
        Search logs with advanced query
        
        Args:
            index_type: Type of logs to search
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Starting offset
            sort: Sort configuration
            
        Returns:
            Search results
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_type}"
            
            search_body = {
                'query': query,
                'size': size,
                'from': from_,
                'sort': sort or [{'timestamp': {'order': 'desc'}}]
            }
            
            response = self.client.search(
                index=full_index_name,
                body=search_body
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def advanced_search(self, 
                       index_types: List[str],
                       query: Dict,
                       aggregations: Dict = None,
                       size: int = 100) -> Dict:
        """
        Advanced search across multiple indices with aggregations
        
        Args:
            index_types: List of index types to search
            query: Search query
            aggregations: Aggregation configurations
            size: Result size
            
        Returns:
            Search results with aggregations
        """
        try:
            full_index_names = [f"{self.index_prefix}-{idx}" for idx in index_types]
            
            search_body = {
                'query': query,
                'size': size,
                'aggs': aggregations or {}
            }
            
            response = self.client.search(
                index=','.join(full_index_names),
                body=search_body
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            raise
    
    def get_logs_by_time_range(self,
                              index_type: str,
                              start_time: datetime,
                              end_time: datetime,
                              filters: Dict = None) -> List[Dict]:
        """
        Get logs within a time range
        
        Args:
            index_type: Type of logs
            start_time: Start timestamp
            end_time: End timestamp
            filters: Additional filters to apply
            
        Returns:
            List of log documents
        """
        try:
            query = {
                'bool': {
                    'must': [
                        {
                            'range': {
                                'timestamp': {
                                    'gte': start_time,
                                    'lte': end_time
                                }
                            }
                        }
                    ]
                }
            }
            
            if filters:
                for key, value in filters.items():
                    query['bool']['must'].append({
                        'term': {key: value}
                    })
            
            response = self.search_logs(
                index_type=index_type,
                query=query,
                size=10000
            )
            
            return [hit['_source'] for hit in response['hits']['hits']]
            
        except Exception as e:
            logger.error(f"Failed to get logs by time range: {e}")
            raise
    
    def delete_logs_by_query(self, index_type: str, query: Dict) -> Dict:
        """
        Delete logs matching a query
        
        Args:
            index_type: Type of logs
            query: Query to match documents for deletion
            
        Returns:
            Delete operation results
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_type}"
            
            response = self.client.delete_by_query(
                index=full_index_name,
                body={'query': query}
            )
            
            logger.info(f"Deleted documents matching query")
            return response
            
        except Exception as e:
            logger.error(f"Failed to delete logs: {e}")
            raise
    
    def get_index_stats(self, index_type: str) -> Dict:
        """
        Get statistics for an index
        
        Args:
            index_type: Type of index
            
        Returns:
            Index statistics
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_type}"
            
            response = self.client.indices.stats(index=full_index_name)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise
    
    def create_index_template(self, name: str, template: Dict):
        """
        Create an index template
        
        Args:
            name: Template name
            template: Template configuration
        """
        try:
            self.client.indices.put_template(
                name=name,
                body=template
            )
            logger.info(f"Created index template: {name}")
            
        except Exception as e:
            logger.error(f"Failed to create index template: {e}")
            raise
    
    def setup_data_streams(self):
        """Setup data streams for log management"""
        data_stream_configs = [
            {
                'name': 'application-logs',
                'mapping': self.index_templates['application_logs']
            },
            {
                'name': 'audit-logs', 
                'mapping': self.index_templates['audit_logs']
            },
            {
                'name': 'security-logs',
                'mapping': self.index_templates['security_logs']
            }
        ]
        
        for config in data_stream_configs:
            try:
                self.client.indices.create_data_stream(config['name'])
                logger.info(f"Created data stream: {config['name']}")
            except Exception as e:
                logger.warning(f"Data stream creation failed for {config['name']}: {e}")
    
    def close(self):
        """Close Elasticsearch client connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Elasticsearch client connection closed")
