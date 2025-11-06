"""
Log Search Service for Advanced Log Management
Provides full-text search, filtering, and analytics across all log entries
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..elk import ElasticsearchClient

logger = logging.getLogger(__name__)


class SearchOperator(Enum):
    """Search operator types"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class LogLevel(Enum):
    """Log level filter options"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SeverityLevel(Enum):
    """Security severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SearchQuery:
    """Advanced search query configuration"""
    query: str
    indices: List[str]
    fields: List[str] = None
    operators: List[SearchOperator] = None
    filters: Dict[str, Any] = None
    date_range: Tuple[datetime, datetime] = None
    size: int = 100
    from_: int = 0
    sort: List[str] = None
    aggregations: Dict[str, Any] = None
    highlight: bool = True
    timeout: str = "30s"
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []
        if self.operators is None:
            self.operators = []
        if self.filters is None:
            self.filters = {}


@dataclass
class SearchResult:
    """Search result with metadata"""
    total: int
    hits: List[Dict]
    aggregations: Dict = None
    took: int = 0
    timed_out: bool = False
    scroll_id: str = None
    next_scroll_id: str = None
    highlights: Dict = None


class LogSearchService:
    """Advanced log search and analytics service"""
    
    def __init__(self, es_client: ElasticsearchClient):
        """
        Initialize log search service
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        
        # Predefined search templates
        self.search_templates = {
            'error_analysis': self._get_error_analysis_template(),
            'security_incidents': self._get_security_incidents_template(),
            'performance_issues': self._get_performance_issues_template(),
            'user_activity': self._get_user_activity_template(),
            'audit_trail': self._get_audit_trail_template(),
            'compliance_violations': self._get_compliance_violations_template()
        }
        
        # Field mappings for different log types
        self.field_mappings = {
            'application_logs': {
                'text_fields': ['message', 'stack_trace', 'context'],
                'keyword_fields': ['level', 'logger', 'module', 'function'],
                'numeric_fields': ['line_number'],
                'date_fields': ['timestamp'],
                'boolean_fields': [],
                'geo_fields': []
            },
            'audit_logs': {
                'text_fields': ['details', 'user_agent'],
                'keyword_fields': ['event_type', 'action', 'resource', 'user_id', 'user_email', 'risk_level'],
                'numeric_fields': [],
                'date_fields': ['timestamp', 'retention_date'],
                'boolean_fields': ['success', 'compliance_flags'],
                'geo_fields': []
            },
            'security_logs': {
                'text_fields': ['user_agent'],
                'keyword_fields': ['event_type', 'severity', 'protocol', 'method', 'endpoint', 'threat_type'],
                'numeric_fields': ['port', 'status_code', 'threat_score'],
                'date_fields': ['timestamp'],
                'boolean_fields': ['blocked'],
                'geo_fields': ['geoip.location']
            },
            'performance_logs': {
                'text_fields': ['tags', 'dimensions'],
                'keyword_fields': ['metric_name', 'metric_type', 'unit', 'alert_status'],
                'numeric_fields': ['value', 'threshold'],
                'date_fields': ['timestamp'],
                'boolean_fields': [],
                'geo_fields': []
            },
            'compliance_logs': {
                'text_fields': ['evidence', 'findings', 'remediation'],
                'keyword_fields': ['regulation', 'requirement', 'control', 'status', 'severity', 'assessor'],
                'numeric_fields': ['compliance_score'],
                'date_fields': ['timestamp'],
                'boolean_fields': [],
                'geo_fields': []
            }
        }
    
    def _get_error_analysis_template(self) -> Dict:
        """Pre-built template for error analysis"""
        return {
            'name': 'Error Analysis',
            'description': 'Comprehensive error log analysis and trending',
            'query': {
                'bool': {
                    'must': [
                        {'term': {'level': 'ERROR'}}
                    ]
                }
            },
            'aggregations': {
                'errors_by_type': {
                    'terms': {
                        'field': 'logger',
                        'size': 20
                    }
                },
                'error_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1h'
                    }
                },
                'error_trends': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1d'
                    },
                    'aggs': {
                        'error_rate': {
                            'avg': {'field': 'value'}
                        }
                    }
                }
            }
        }
    
    def _get_security_incidents_template(self) -> Dict:
        """Pre-built template for security incident analysis"""
        return {
            'name': 'Security Incidents',
            'description': 'Security event detection and analysis',
            'query': {
                'bool': {
                    'must': [
                        {'terms': {'severity': ['high', 'critical']}}
                    ]
                }
            },
            'aggregations': {
                'threat_sources': {
                    'terms': {
                        'field': 'source_ip',
                        'size': 20
                    }
                },
                'threat_types': {
                    'terms': {
                        'field': 'threat_type',
                        'size': 10
                    }
                },
                'incident_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '15m'
                    }
                }
            }
        }
    
    def _get_performance_issues_template(self) -> Dict:
        """Pre-built template for performance analysis"""
        return {
            'name': 'Performance Issues',
            'description': 'System performance monitoring and analysis',
            'query': {
                'bool': {
                    'must': [
                        {'range': {'value': {'gte': 1000}}}
                    ]
                }
            },
            'aggregations': {
                'slow_operations': {
                    'terms': {
                        'field': 'metric_name',
                        'size': 20
                    }
                },
                'performance_trends': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1h'
                    }
                }
            }
        }
    
    def _get_user_activity_template(self) -> Dict:
        """Pre-built template for user activity analysis"""
        return {
            'name': 'User Activity',
            'description': 'User behavior and activity tracking',
            'query': {'match_all': {}},
            'aggregations': {
                'active_users': {
                    'cardinality': {
                        'field': 'user_id'
                    }
                },
                'user_sessions': {
                    'terms': {
                        'field': 'user_id',
                        'size': 20
                    }
                },
                'activity_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1h'
                    }
                }
            }
        }
    
    def _get_audit_trail_template(self) -> Dict:
        """Pre-built template for audit trail analysis"""
        return {
            'name': 'Audit Trail',
            'description': 'Comprehensive audit trail analysis',
            'query': {'match_all': {}},
            'aggregations': {
                'audit_events': {
                    'terms': {
                        'field': 'event_type',
                        'size': 20
                    }
                },
                'user_audit': {
                    'terms': {
                        'field': 'user_id',
                        'size': 20
                    }
                },
                'audit_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1d'
                    }
                }
            }
        }
    
    def _get_compliance_violations_template(self) -> Dict:
        """Pre-built template for compliance violation analysis"""
        return {
            'name': 'Compliance Violations',
            'description': 'Compliance status and violation tracking',
            'query': {
                'bool': {
                    'must': [
                        {'terms': {'status': ['non_compliant', 'violation']}}
                    ]
                }
            },
            'aggregations': {
                'violations_by_regulation': {
                    'terms': {
                        'field': 'regulation',
                        'size': 20
                    }
                },
                'compliance_score': {
                    'avg': {
                        'field': 'compliance_score'
                    }
                },
                'violation_timeline': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': '1w'
                    }
                }
            }
        }
    
    def create_search_query(self, query: SearchQuery) -> Dict:
        """
        Create Elasticsearch query from search parameters
        
        Args:
            query: Search query configuration
            
        Returns:
            Elasticsearch query DSL
        """
        es_query = {'bool': {'must': []}}
        
        # Full-text search
        if query.query:
            if not query.fields:
                # Search in all text fields
                text_fields = self._get_all_text_fields(query.indices)
                es_query['bool']['must'].append({
                    'multi_match': {
                        'query': query.query,
                        'fields': text_fields,
                        'type': 'best_fields',
                        'fuzziness': 'AUTO'
                    }
                })
            else:
                # Search in specific fields
                es_query['bool']['must'].append({
                    'multi_match': {
                        'query': query.query,
                        'fields': query.fields,
                        'type': 'best_fields',
                        'fuzziness': 'AUTO'
                    }
                })
        
        # Date range filter
        if query.date_range:
            start_time, end_time = query.date_range
            es_query['bool']['must'].append({
                'range': {
                    'timestamp': {
                        'gte': start_time,
                        'lte': end_time
                    }
                }
            })
        
        # Additional filters
        if query.filters:
            for field, value in query.filters.items():
                if isinstance(value, list):
                    es_query['bool']['must'].append({
                        'terms': {field: value}
                    })
                else:
                    es_query['bool']['must'].append({
                        'term': {field: value}
                    })
        
        # Default to match_all if no conditions
        if not es_query['bool']['must']:
            es_query = {'match_all': {}}
        
        return es_query
    
    def _get_all_text_fields(self, indices: List[str]) -> List[str]:
        """Get all text fields for the specified indices"""
        text_fields = []
        
        for index_type in indices:
            mapping = self.field_mappings.get(index_type, {})
            text_fields.extend(mapping.get('text_fields', []))
        
        return text_fields if text_fields else ['*']
    
    def execute_search(self, query: SearchQuery) -> SearchResult:
        """
        Execute advanced search query
        
        Args:
            query: Search query configuration
            
        Returns:
            Search results
        """
        try:
            # Create Elasticsearch query
            es_query = self.create_search_query(query)
            
            # Build search request
            search_body = {
                'query': es_query,
                'size': query.size,
                'from': query.from_,
                'timeout': query.timeout
            }
            
            # Add sorting
            if query.sort:
                search_body['sort'] = [{field: {'order': 'desc'}} for field in query.sort]
            else:
                search_body['sort'] = [{'timestamp': {'order': 'desc'}}]
            
            # Add aggregations
            if query.aggregations:
                search_body['aggs'] = query.aggregations
            
            # Add highlighting
            if query.highlight:
                search_body['highlight'] = {
                    'pre_tags': ['<mark>'],
                    'post_tags': ['</mark>'],
                    'fields': {
                        '*': {}
                    }
                }
            
            # Execute search
            response = self.es_client.advanced_search(
                index_types=query.indices,
                query=search_body,
                aggregations=query.aggregations,
                size=query.size
            )
            
            # Process results
            result = SearchResult(
                total=response['hits']['total']['value'],
                hits=[hit['_source'] for hit in response['hits']['hits']],
                aggregations=response.get('aggregations', {}),
                took=response.get('took', 0),
                timed_out=response.get('timed_out', False)
            )
            
            # Add highlights if available
            if query.highlight and 'hits' in response:
                highlights = {}
                for hit in response['hits']['hits']:
                    if 'highlight' in hit:
                        highlights[hit['_id']] = hit['highlight']
                result.highlights = highlights
            
            logger.info(f"Search executed: {result.total} results found")
            return result
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            raise
    
    def search_by_template(self, template_name: str, parameters: Dict = None) -> SearchResult:
        """
        Execute search using pre-built template
        
        Args:
            template_name: Name of search template
            parameters: Template parameters
            
        Returns:
            Search results
        """
        template = self.search_templates.get(template_name)
        if not template:
            raise ValueError(f"Search template not found: {template_name}")
        
        # Create search query from template
        search_query = SearchQuery(
            query=parameters.get('query', '') if parameters else '',
            indices=parameters.get('indices', ['application_logs']) if parameters else ['application_logs'],
            filters=parameters.get('filters', {}) if parameters else {},
            aggregations=template.get('aggregations'),
            size=parameters.get('size', 100) if parameters else 100
        )
        
        # Execute search
        return self.execute_search(search_query)
    
    def fuzzy_search(self, 
                    query: str, 
                    indices: List[str],
                    fuzziness: str = 'AUTO',
                    similarity: float = 0.6) -> SearchResult:
        """
        Perform fuzzy search with configurable parameters
        
        Args:
            query: Search query
            indices: Indices to search
            fuzziness: Fuzziness level
            similarity: Similarity threshold
            
        Returns:
            Search results
        """
        search_query = SearchQuery(
            query=query,
            indices=indices,
            size=100
        )
        
        # Create fuzzy query
        es_query = {
            'bool': {
                'must': [
                    {
                        'multi_match': {
                            'query': query,
                            'type': 'most_fields',
                            'fuzziness': fuzziness,
                            'operator': 'and'
                        }
                    }
                ]
            }
        }
        
        try:
            response = self.es_client.advanced_search(
                index_types=indices,
                query=es_query,
                size=100
            )
            
            return SearchResult(
                total=response['hits']['total']['value'],
                hits=[hit['_source'] for hit in response['hits']['hits']],
                aggregations=response.get('aggregations', {}),
                took=response.get('took', 0)
            )
            
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            raise
    
    def search_with_patterns(self, 
                           query: str, 
                           patterns: List[str],
                           indices: List[str]) -> SearchResult:
        """
        Search using regex patterns
        
        Args:
            query: Base query
            patterns: List of regex patterns
            indices: Indices to search
            
        Returns:
            Search results
        """
        # Combine patterns into regex
        combined_pattern = '|'.join(f'({pattern})' for pattern in patterns)
        
        search_query = SearchQuery(
            query=query,
            indices=indices,
            size=100
        )
        
        # Create query with regex
        es_query = {
            'bool': {
                'must': [
                    {
                        'query_string': {
                            'query': f'({query}) AND /{combined_pattern}/',
                            'default_field': '*'
                        }
                    }
                ]
            }
        }
        
        try:
            response = self.es_client.advanced_search(
                index_types=indices,
                query=es_query,
                size=100
            )
            
            return SearchResult(
                total=response['hits']['total']['value'],
                hits=[hit['_source'] for hit in response['hits']['hits']],
                aggregations=response.get('aggregations', {}),
                took=response.get('took', 0)
            )
            
        except Exception as e:
            logger.error(f"Pattern search failed: {e}")
            raise
    
    def correlation_search(self, 
                         base_query: Dict,
                         correlation_fields: List[str],
                         indices: List[str]) -> SearchResult:
        """
        Search for correlated events across multiple fields
        
        Args:
            base_query: Base query conditions
            correlation_fields: Fields to correlate
            indices: Indices to search
            
        Returns:
            Search results with correlation analysis
        """
        # Create correlation aggregations
        aggregations = {
            'correlations': {
                'terms': {
                    'field': correlation_fields[0],
                    'size': 50
                },
                'aggs': {
                    'correlation_count': {
                        'terms': {
                            'field': correlation_fields[1] if len(correlation_fields) > 1 else 'user_id',
                            'size': 20
                        }
                    }
                }
            }
        }
        
        try:
            response = self.es_client.advanced_search(
                index_types=indices,
                query=base_query,
                aggregations=aggregations,
                size=100
            )
            
            return SearchResult(
                total=response['hits']['total']['value'],
                hits=[hit['_source'] for hit in response['hits']['hits']],
                aggregations=response.get('aggregations', {}),
                took=response.get('took', 0)
            )
            
        except Exception as e:
            logger.error(f"Correlation search failed: {e}")
            raise
    
    def get_search_suggestions(self, 
                             partial_query: str, 
                             indices: List[str]) -> List[str]:
        """
        Get search suggestions for autocomplete
        
        Args:
            partial_query: Partial query string
            indices: Indices to search
            
        Returns:
            List of suggestions
        """
        try:
            # Create suggest query
            suggest_query = {
                'suggest': {
                    'search_suggestions': {
                        'text': partial_query,
                        'term': {
                            'field': '_all',
                            'size': 10
                        }
                    }
                }
            }
            
            response = self.es_client.advanced_search(
                index_types=indices,
                query=suggest_query,
                size=0  # We only want suggestions
            )
            
            suggestions = []
            if 'suggest' in response:
                for suggestion in response['suggest']['search_suggestions']:
                    for option in suggestion.get('options', []):
                        suggestions.append(option['text'])
            
            return suggestions[:10]  # Limit to 10 suggestions
            
        except Exception as e:
            logger.error(f"Search suggestions failed: {e}")
            return []
    
    def get_field_suggestions(self, 
                            field: str, 
                            indices: List[str],
                            size: int = 20) -> List[str]:
        """
        Get field-specific suggestions (for autocomplete)
        
        Args:
            field: Field to get suggestions for
            indices: Indices to search
            size: Number of suggestions
            
        Returns:
            List of field values
        """
        try:
            # Create terms aggregation
            aggs = {
                'field_suggestions': {
                    'terms': {
                        'field': field,
                        'size': size
                    }
                }
            }
            
            response = self.es_client.advanced_search(
                index_types=indices,
                query={'match_all': {}},
                aggregations=aggs,
                size=0
            )
            
            suggestions = []
            if 'aggregations' in response:
                buckets = response['aggregations']['field_suggestions']['buckets']
                suggestions = [bucket['key'] for bucket in buckets]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Field suggestions failed: {e}")
            return []
    
    def save_search(self, name: str, query: SearchQuery, user_id: str) -> str:
        """
        Save a search query for reuse
        
        Args:
            name: Name for the saved search
            query: Search query to save
            user_id: ID of user saving the search
            
        Returns:
            Saved search ID
        """
        saved_search = {
            'name': name,
            'user_id': user_id,
            'query': {
                'query': query.query,
                'indices': query.indices,
                'fields': query.fields,
                'filters': query.filters,
                'date_range': query.date_range.isoformat() if query.date_range else None,
                'size': query.size,
                'aggregations': query.aggregations
            },
            'created_at': datetime.utcnow(),
            'last_used': datetime.utcnow()
        }
        
        # Index the saved search
        try:
            # This would be indexed to a separate saved_searches index
            # For now, we'll log it
            logger.info(f"Saved search '{name}' for user {user_id}")
            return f"saved_search_{name}_{user_id}"
            
        except Exception as e:
            logger.error(f"Failed to save search: {e}")
            raise
    
    def get_saved_searches(self, user_id: str) -> List[Dict]:
        """
        Get saved searches for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of saved searches
        """
        # This would query the saved_searches index
        # For now, return empty list
        return []
    
    def analyze_query_performance(self, query: SearchQuery) -> Dict:
        """
        Analyze query performance and provide optimization suggestions
        
        Args:
            query: Search query to analyze
            
        Returns:
            Performance analysis results
        """
        analysis = {
            'query_complexity': 0,
            'estimated_time': 'unknown',
            'suggestions': [],
            'field_usage': {},
            'index_usage': []
        }
        
        try:
            # Analyze query complexity
            if query.query:
                analysis['query_complexity'] += 1
            
            if query.filters:
                analysis['query_complexity'] += len(query.filters)
            
            if query.aggregations:
                analysis['query_complexity'] += len(query.aggregations)
            
            # Field usage analysis
            for index in query.indices:
                mapping = self.field_mappings.get(index, {})
                all_fields = []
                for field_type in mapping.values():
                    all_fields.extend(field_type)
                analysis['field_usage'][index] = len(all_fields)
                analysis['index_usage'].append(index)
            
            # Provide suggestions
            if analysis['query_complexity'] > 5:
                analysis['suggestions'].append("Consider reducing query complexity")
            
            if query.size > 1000:
                analysis['suggestions'].append("Consider using pagination for large result sets")
            
            if len(query.indices) > 3:
                analysis['suggestions'].append("Consider narrowing index scope")
            
            # Estimated performance
            if analysis['query_complexity'] <= 2:
                analysis['estimated_time'] = '< 100ms'
            elif analysis['query_complexity'] <= 5:
                analysis['estimated_time'] = '100-500ms'
            else:
                analysis['estimated_time'] = '> 500ms'
            
        except Exception as e:
            logger.error(f"Query performance analysis failed: {e}")
            analysis['suggestions'].append(f"Analysis failed: {e}")
        
        return analysis
