"""
Kibana Dashboard Manager for Compliance and Security Visualization
Manages pre-built dashboards and visualizations for log analytics
"""

import logging
import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class KibanaDashboardManager:
    """Manages Kibana dashboards for compliance and security monitoring"""
    
    def __init__(self, 
                 kibana_url: str = "http://localhost:5601",
                 elasticsearch_url: str = "http://localhost:9200",
                 username: str = None,
                 password: str = None):
        """
        Initialize Kibana dashboard manager
        
        Args:
            kibana_url: Kibana server URL
            elasticsearch_url: Elasticsearch URL
            username: Authentication username
            password: Authentication password
        """
        self.kibana_url = kibana_url.rstrip('/')
        self.elasticsearch_url = elasticsearch_url
        self.username = username
        self.password = password
        
        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Auth configuration
        if username and password:
            self.auth = (username, password)
        else:
            self.auth = None
        
        # Pre-built dashboard configurations
        self.dashboard_configs = {
            'security_overview': self._get_security_overview_dashboard(),
            'compliance_status': self._get_compliance_dashboard(),
            'application_monitoring': self._get_application_monitoring_dashboard(),
            'audit_trail': self._get_audit_trail_dashboard(),
            'threat_detection': self._get_threat_detection_dashboard(),
            'performance_analytics': self._get_performance_dashboard(),
            'user_activity': self._get_user_activity_dashboard(),
            'gdpr_compliance': self._get_gdpr_dashboard()
        }
    
    def _get_security_overview_dashboard(self) -> Dict:
        """Security overview dashboard configuration"""
        return {
            'title': 'Fernando Security Overview',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando Security Overview',
                'description': 'Real-time security monitoring and threat detection dashboard',
                'panelsJSON': json.dumps([
                    {
                        'id': 'security-alerts',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'threat-timeline',
                        'type': 'visualization',
                        'gridData': {'x': 6, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'security-events-map',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'security-alerts': {
                    'type': 'pie',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True,
                        'legendPosition': 'right'
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'severity'}}
                    ]
                },
                'threat-timeline': {
                    'type': 'histogram',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                },
                'security-events-map': {
                    'type': 'tile_map',
                    'params': {
                        'mapType': 'Shaded Circle Marker'
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'geohash_grid', 'schema': 'segment', 'params': {'field': 'geoip.location'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-security_logs-*',
            'search_source': '{}'
        }
    
    def _get_compliance_dashboard(self) -> Dict:
        """Compliance status dashboard configuration"""
        return {
            'title': 'Fernando Compliance Dashboard',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando Compliance Dashboard',
                'description': 'Regulatory compliance monitoring and reporting',
                'panelsJSON': json.dumps([
                    {
                        'id': 'compliance-score',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'regulation-status',
                        'type': 'visualization',
                        'gridData': {'x': 4, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'audit-findings',
                        'type': 'visualization',
                        'gridData': {'x': 8, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'compliance-timeline',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'compliance-score': {
                    'type': 'gauge',
                    'params': {
                        'addTooltip': True,
                        'addLegend': False,
                        'type': 'gauge',
                        'gauge': {
                            'alignment': 'vertical',
                            'colorSchema': 'Green to Red',
                            'gaugeColorMode': 'Labels',
                            'labels': {'color': 'black', 'fontSize': '24'},
                            'orientation': 'vertical',
                            'style': {'bgFill': '#000', 'fontSize': 24},
                            'type': 'metric',
                            'useRanges': True,
                            'verticalSplit': False
                        }
                    },
                    'aggs': [
                        {'id': '1', 'type': 'avg', 'schema': 'metric', 'params': {'field': 'compliance_score'}}
                    ]
                },
                'regulation-status': {
                    'type': 'pie',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True,
                        'legendPosition': 'right'
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'regulation'}},
                        {'id': '3', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'status'}}
                    ]
                },
                'audit-findings': {
                    'type': 'bar',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'severity'}}
                    ]
                },
                'compliance-timeline': {
                    'type': 'line',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True,
                        'showCircles': True,
                        'interpolate': 'linear',
                        'scale': 'linear',
                        'drawLinesBetweenPoints': True,
                        'radiusRatio': 9,
                        'missingValues': 'zero',
                        'showTooltip': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'avg', 'schema': 'metric', 'params': {'field': 'compliance_score'}},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-compliance_logs-*',
            'search_source': '{}'
        }
    
    def _get_application_monitoring_dashboard(self) -> Dict:
        """Application monitoring dashboard configuration"""
        return {
            'title': 'Fernando Application Monitoring',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando Application Monitoring',
                'description': 'Application performance and health monitoring',
                'panelsJSON': json.dumps([
                    {
                        'id': 'log-levels',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'error-rate',
                        'type': 'visualization',
                        'gridData': {'x': 6, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'application-metrics',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'log-levels': {
                    'type': 'pie',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'level'}}
                    ]
                },
                'error-rate': {
                    'type': 'area',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                },
                'application-metrics': {
                    'type': 'line',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-application_logs-*',
            'search_source': '{}'
        }
    
    def _get_audit_trail_dashboard(self) -> Dict:
        """Audit trail dashboard configuration"""
        return {
            'title': 'Fernando Audit Trail',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando Audit Trail',
                'description': 'Comprehensive audit trail and user activity tracking',
                'panelsJSON': json.dumps([
                    {
                        'id': 'audit-events',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 8, 'h': 4}
                    },
                    {
                        'id': 'user-activity',
                        'type': 'visualization',
                        'gridData': {'x': 8, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'audit-timeline',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'audit-events': {
                    'type': 'data_table',
                    'params': {
                        'perPage': 10,
                        'showPartialRows': False,
                        'showMetricsAtAllLevels': False,
                        'sort': {'columnIndex': None, 'direction': 'desc'}
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'bucket', 'params': {'field': 'event_type', 'size': 10}},
                        {'id': '3', 'type': 'terms', 'schema': 'bucket', 'params': {'field': 'user_id', 'size': 10}},
                        {'id': '4', 'type': 'date_histogram', 'schema': 'bucket', 'params': {'field': 'timestamp'}}
                    ]
                },
                'user-activity': {
                    'type': 'pie',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'action'}}
                    ]
                },
                'audit-timeline': {
                    'type': 'histogram',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-audit_logs-*',
            'search_source': '{}'
        }
    
    def _get_threat_detection_dashboard(self) -> Dict:
        """Threat detection dashboard configuration"""
        return {
            'title': 'Fernando Threat Detection',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando Threat Detection',
                'description': 'Advanced threat detection and security incident analysis',
                'panelsJSON': json.dumps([
                    {
                        'id': 'threat-severity',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'threat-types',
                        'type': 'visualization',
                        'gridData': {'x': 4, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'threat-intelligence',
                        'type': 'visualization',
                        'gridData': {'x': 8, 'y': 0, 'w': 4, 'h': 4}
                    },
                    {
                        'id': 'threat-timeline',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'threat-severity': {
                    'type': 'pie',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'severity'}}
                    ]
                },
                'threat-types': {
                    'type': 'bar',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'threat_type', 'size': 10}}
                    ]
                },
                'threat-intelligence': {
                    'type': 'heatmap',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'source_ip', 'size': 10}},
                        {'id': '3', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                },
                'threat-timeline': {
                    'type': 'line',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-security_logs-*',
            'search_source': '{}'
        }
    
    def _get_performance_dashboard(self) -> Dict:
        """Performance analytics dashboard configuration"""
        return {
            'title': 'Fernando Performance Analytics',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando Performance Analytics',
                'description': 'System performance monitoring and optimization insights',
                'panelsJSON': json.dumps([
                    {
                        'id': 'performance-metrics',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 12, 'h': 4}
                    },
                    {
                        'id': 'response-time-percentiles',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 6, 'h': 6}
                    },
                    {
                        'id': 'resource-utilization',
                        'type': 'visualization',
                        'gridData': {'x': 6, 'y': 4, 'w': 6, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'performance-metrics': {
                    'type': 'area',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'avg', 'schema': 'metric', 'params': {'field': 'value'}},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'metric_name'}},
                        {'id': '3', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                },
                'response-time-percentiles': {
                    'type': 'line',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'percentiles', 'schema': 'metric', 'params': {'field': 'value', 'percents': [50, 90, 95, 99]}},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                },
                'resource-utilization': {
                    'type': 'gauge',
                    'params': {
                        'addTooltip': True,
                        'addLegend': False,
                        'gauge': {
                            'alignment': 'vertical',
                            'colorSchema': 'Green to Red',
                            'gaugeColorMode': 'None',
                            'labels': {'color': 'black', 'fontSize': 12},
                            'orientation': 'vertical',
                            'style': {'bgFill': '#000', 'fontSize': 12},
                            'type': 'gauge',
                            'useRanges': True,
                            'verticalSplit': False
                        }
                    },
                    'aggs': [
                        {'id': '1', 'type': 'avg', 'schema': 'metric', 'params': {'field': 'value'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-performance_logs-*',
            'search_source': '{}'
        }
    
    def _get_user_activity_dashboard(self) -> Dict:
        """User activity monitoring dashboard configuration"""
        return {
            'title': 'Fernando User Activity',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando User Activity',
                'description': 'User behavior analytics and activity monitoring',
                'panelsJSON': json.dumps([
                    {
                        'id': 'user-actions',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'active-users',
                        'type': 'visualization',
                        'gridData': {'x': 6, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'user-sessions',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'user-actions': {
                    'type': 'pie',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'action'}}
                    ]
                },
                'active-users': {
                    'type': 'metric',
                    'params': {
                        'addTooltip': True,
                        'addLegend': False
                    },
                    'aggs': [
                        {'id': '1', 'type': 'cardinality', 'schema': 'metric', 'params': {'field': 'user_id'}}
                    ]
                },
                'user-sessions': {
                    'type': 'histogram',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}},
                        {'id': '3', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'user_id', 'size': 10}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-user_activity_logs-*',
            'search_source': '{}'
        }
    
    def _get_gdpr_dashboard(self) -> Dict:
        """GDPR compliance dashboard configuration"""
        return {
            'title': 'Fernando GDPR Compliance',
            'type': 'dashboard',
            'dashboard_config': {
                'version': '7.14.0',
                'title': 'Fernando GDPR Compliance',
                'description': 'GDPR compliance monitoring and data protection tracking',
                'panelsJSON': json.dumps([
                    {
                        'id': 'gdpr-metrics',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'data-requests',
                        'type': 'visualization',
                        'gridData': {'x': 6, 'y': 0, 'w': 6, 'h': 4}
                    },
                    {
                        'id': 'gdpr-timeline',
                        'type': 'visualization',
                        'gridData': {'x': 0, 'y': 4, 'w': 12, 'h': 6}
                    }
                ]),
                'optionsJSON': '{}',
                'timeRestore': False,
                'version': 1
            },
            'vis_config': {
                'gdpr-metrics': {
                    'type': 'gauge',
                    'params': {
                        'addTooltip': True,
                        'addLegend': False,
                        'gauge': {
                            'alignment': 'vertical',
                            'colorSchema': 'Green to Red',
                            'gaugeColorMode': 'None',
                            'labels': {'color': 'black', 'fontSize': 24},
                            'orientation': 'vertical',
                            'style': {'bgFill': '#000', 'fontSize': 24},
                            'type': 'gauge',
                            'useRanges': True,
                            'verticalSplit': False
                        }
                    },
                    'aggs': [
                        {'id': '1', 'type': 'avg', 'schema': 'metric', 'params': {'field': 'compliance_score'}}
                    ]
                },
                'data-requests': {
                    'type': 'histogram',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'terms', 'schema': 'segment', 'params': {'field': 'request_type'}},
                        {'id': '3', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                },
                'gdpr-timeline': {
                    'type': 'line',
                    'params': {
                        'addTooltip': True,
                        'addLegend': True
                    },
                    'aggs': [
                        {'id': '1', 'type': 'count', 'schema': 'metric'},
                        {'id': '2', 'type': 'date_histogram', 'schema': 'segment', 'params': {'field': 'timestamp'}}
                    ]
                }
            },
            'index_pattern': 'fernando-logs-compliance_logs-*',
            'search_source': '{"query": {"match": {"regulation": "GDPR"}}}'
        }
    
    def create_dashboard(self, dashboard_id: str, config: Dict = None) -> Dict:
        """
        Create a Kibana dashboard
        
        Args:
            dashboard_id: Unique dashboard identifier
            config: Dashboard configuration (uses default if not provided)
            
        Returns:
            Creation results
        """
        try:
            if config is None:
                config = self.dashboard_configs.get(dashboard_id)
            
            if not config:
                raise ValueError(f"Dashboard configuration not found for: {dashboard_id}")
            
            # Create index pattern first
            index_pattern = self._create_index_pattern(
                config['index_pattern'],
                f"{dashboard_id}_pattern"
            )
            
            # Create visualizations
            vis_ids = []
            for vis_name, vis_config in config.get('vis_config', {}).items():
                vis_id = self._create_visualization(vis_name, vis_config, index_pattern['id'])
                vis_ids.append(vis_id)
            
            # Create dashboard
            dashboard = self._create_kibana_dashboard(config, vis_ids)
            
            logger.info(f"Created dashboard: {dashboard_id}")
            return {
                'success': True,
                'dashboard_id': dashboard_id,
                'dashboard_url': f"{self.kibana_url}/app/dashboards#/view/{dashboard_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to create dashboard {dashboard_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_index_pattern(self, index_pattern: str, pattern_name: str) -> Dict:
        """Create Kibana index pattern"""
        try:
            url = f"{self.kibana_url}/api/saved_objects/index-pattern/{pattern_name}"
            
            data = {
                'attributes': {
                    'title': index_pattern,
                    'timeFieldName': 'timestamp'
                }
            }
            
            response = requests.post(
                url,
                json=data,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to create index pattern: {response.text}")
                
        except Exception as e:
            logger.error(f"Index pattern creation failed: {e}")
            raise
    
    def _create_visualization(self, vis_name: str, vis_config: Dict, index_pattern_id: str) -> str:
        """Create a Kibana visualization"""
        try:
            url = f"{self.kibana_url}/api/saved_objects/visualization/{vis_name}"
            
            data = {
                'attributes': {
                    'title': vis_name,
                    'visState': json.dumps(vis_config),
                    'uiStateJSON': '{}',
                    'kibanaSavedObjectMeta': {
                        'searchSourceJSON': json.dumps({
                            'index': index_pattern_id,
                            'query': {'match_all': {}},
                            'filter': []
                        })
                    }
                }
            }
            
            response = requests.post(
                url,
                json=data,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                return response.json()['id']
            else:
                raise Exception(f"Failed to create visualization: {response.text}")
                
        except Exception as e:
            logger.error(f"Visualization creation failed: {e}")
            raise
    
    def _create_kibana_dashboard(self, config: Dict, vis_ids: List[str]) -> Dict:
        """Create the main Kibana dashboard"""
        try:
            dashboard_id = config['title'].lower().replace(' ', '-')
            url = f"{self.kibana_url}/api/saved_objects/dashboard/{dashboard_id}"
            
            data = {
                'attributes': {
                    'title': config['title'],
                    'description': config.get('description', ''),
                    'panelsJSON': config['dashboard_config']['panelsJSON'],
                    'optionsJSON': config['dashboard_config']['optionsJSON'],
                    'version': config['dashboard_config'].get('version', '1')
                }
            }
            
            response = requests.post(
                url,
                json=data,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to create dashboard: {response.text}")
                
        except Exception as e:
            logger.error(f"Dashboard creation failed: {e}")
            raise
    
    def create_all_dashboards(self) -> Dict:
        """Create all pre-built dashboards"""
        results = {}
        
        for dashboard_id in self.dashboard_configs.keys():
            try:
                result = self.create_dashboard(dashboard_id)
                results[dashboard_id] = result
            except Exception as e:
                results[dashboard_id] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def get_dashboard_list(self) -> List[Dict]:
        """Get list of all dashboards"""
        try:
            url = f"{self.kibana_url}/api/saved_objects/_find"
            
            params = {
                'type': 'dashboard',
                'per_page': 100
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                return response.json().get('saved_objects', [])
            else:
                raise Exception(f"Failed to get dashboard list: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to get dashboard list: {e}")
            return []
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard"""
        try:
            url = f"{self.kibana_url}/api/saved_objects/dashboard/{dashboard_id}"
            
            response = requests.delete(
                url,
                headers=self.headers,
                auth=self.auth
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to delete dashboard {dashboard_id}: {e}")
            return False
    
    def update_dashboard(self, dashboard_id: str, config: Dict) -> bool:
        """Update an existing dashboard"""
        try:
            url = f"{self.kibana_url}/api/saved_objects/dashboard/{dashboard_id}"
            
            data = {
                'attributes': {
                    'title': config['title'],
                    'description': config.get('description', ''),
                    'panelsJSON': config['dashboard_config']['panelsJSON'],
                    'optionsJSON': config['dashboard_config']['optionsJSON']
                }
            }
            
            response = requests.put(
                url,
                json=data,
                headers=self.headers,
                auth=self.auth
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to update dashboard {dashboard_id}: {e}")
            return False
