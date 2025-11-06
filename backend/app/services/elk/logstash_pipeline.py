"""
Logstash Pipeline Management for Advanced Log Processing
Handles log transformation, enrichment, and routing through configurable pipelines
"""

import json
import logging
import os
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LogstashPipeline:
    """Manages Logstash pipelines for log processing and transformation"""
    
    def __init__(self, 
                 logstash_home: str = "/opt/logstash",
                 config_path: str = "/etc/logstash/conf.d",
                 pipeline_config: str = None):
        """
        Initialize Logstash pipeline manager
        
        Args:
            logstash_home: Logstash installation directory
            config_path: Configuration files directory
            pipeline_config: Custom pipeline configuration
        """
        self.logstash_home = logstash_home
        self.config_path = config_path
        self.pipeline_config = pipeline_config or self._get_default_pipeline_config()
        
        # Ensure config directory exists
        Path(self.config_path).mkdir(parents=True, exist_ok=True)
        
        # Pipeline definitions
        self.pipelines = {
            'application_logs': self._get_application_log_pipeline(),
            'audit_logs': self._get_audit_log_pipeline(),
            'security_logs': self._get_security_log_pipeline(),
            'performance_logs': self._get_performance_log_pipeline(),
            'compliance_logs': self._get_compliance_log_pipeline()
        }
    
    def _get_default_pipeline_config(self) -> Dict:
        """Get default Logstash pipeline configuration"""
        return {
            'pipeline.workers': 2,
            'pipeline.batch.size': 125,
            'pipeline.batch.delay': 50,
            'queue.type': 'persisted',
            'dead_letter_queue.enable': True
        }
    
    def _get_application_log_pipeline(self) -> Dict:
        """Pipeline configuration for application logs"""
        return {
            'pipeline_id': 'application-logs',
            'pipeline': '''input {
                file {
                    path => "/var/log/fernando/application.log"
                    start_position => "beginning"
                    sincedb_path => "/dev/null"
                    codec => "json"
                    type => "application"
                }
            }
            
            filter {
                # Parse application log fields
                if [type] == "application" {
                    date {
                        match => ["timestamp", "ISO8601"]
                    }
                    
                    # Add environment information
                if ![environment] {
                        mutate {
                            add_field => { "environment" => "production" }
                        }
                    }
                    
                    # Parse error details
                    if [level] == "ERROR" {
                        grok {
                            match => { 
                                "message" => "%{TIMESTAMP_ISO8601:log_timestamp} %{LOGLEVEL:level} %{DATA:logger} - %{GREEDYDATA:message}"
                            }
                        }
                        
                        # Extract stack trace
                        if [message] =~ /^[\w\W]*?Traceback.*$/ {
                            mutate {
                                add_tag => ["has_stack_trace"]
                            }
                        }
                    }
                    
                    # Enrich with host information
                    mutate {
                        add_field => { 
                            "hostname" => "%{[@metadata][hostname]}"
                            "pipeline_version" => "1.0"
                        }
                    }
                }
            }
            
            output {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "fernando-logs-application_logs-%{+YYYY.MM.dd}"
                    template_name => "application_logs"
                }
            }'''
        }
    
    def _get_audit_log_pipeline(self) -> Dict:
        """Pipeline configuration for audit logs"""
        return {
            'pipeline_id': 'audit-logs',
            'pipeline': '''input {
                http {
                    port => 8080
                    type => "audit"
                }
                
                kafka {
                    bootstrap_servers => "localhost:9092"
                    topics => ["audit-logs"]
                    type => "audit"
                }
            }
            
            filter {
                # Process audit events
                if [type] == "audit" {
                    # Validate audit event structure
                    if ![event_type] {
                        mutate { 
                            add_field => { "event_type" => "unknown" }
                        }
                    }
                    
                    # Calculate risk score
                    if [severity] == "high" {
                        mutate {
                            add_field => { "risk_score" => "9.0" }
                        }
                    } else if [severity] == "medium" {
                        mutate {
                            add_field => { "risk_score" => "5.0" }
                        }
                    } else {
                        mutate {
                            add_field => { "risk_score" => "1.0" }
                        }
                    }
                    
                    # Add compliance flags
                    if [event_type] in ["login_failure", "privilege_escalation", "data_access"] {
                        mutate {
                            add_field => { "compliance_flag" => true }
                        }
                    }
                    
                    # GeoIP enrichment for IP addresses
                    if [ip_address] {
                        geoip {
                            source => "ip_address"
                            target => "geoip"
                        }
                    }
                    
                    # Add audit metadata
                    mutate {
                        add_field => {
                            "audit_id" => "%{[@timestamp]}-%{user_id}"
                            "compliance_status" => "pending"
                        }
                    }
                }
            }
            
            output {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "fernando-logs-audit_logs-%{+YYYY.MM.dd}"
                    template_name => "audit_logs"
                }
            }'''
        }
    
    def _get_security_log_pipeline(self) -> Dict:
        """Pipeline configuration for security logs"""
        return {
            'pipeline_id': 'security-logs',
            'pipeline': '''input {
                beats {
                    port => 5044
                    type => "security"
                }
                
                udp {
                    port => 514
                    codec => json
                    type => "security"
                }
            }
            
            filter {
                # Process security events
                if [type] == "security" {
                    # Threat scoring
                    if [event_type] in ["intrusion_attempt", "malware", "ddos"] {
                        mutate {
                            add_field => { "threat_severity" => "critical" }
                        }
                    }
                    
                    # Extract IOC indicators
                    if [message] {
                        grok {
                            match => {
                                "message" => "IP:%{IP:threat_ip}"
                            }
                        }
                    }
                    
                    # Correlation with threat intelligence
                    if [threat_ip] {
                        mutate {
                            add_field => { "requires_investigation" => true }
                        }
                    }
                    
                    # Add security metadata
                    mutate {
                        add_field => {
                            "incident_id" => "%{@timestamp}-%{source_ip}"
                            "detection_engine" => "logstash"
                        }
                    }
                }
            }
            
            output {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "fernando-logs-security_logs-%{+YYYY.MM.dd}"
                    template_name => "security_logs"
                }
                
                # Also send critical alerts to immediate notification
                if [threat_severity] == "critical" {
                    http {
                        url => "http://localhost:9000/alerts"
                        http_method => "post"
                        content_type => "application/json"
                        mapping => {
                            "severity" => "critical"
                            "message" => "Security threat detected: %{event_type}"
                        }
                    }
                }
            }'''
        }
    
    def _get_performance_log_pipeline(self) -> Dict:
        """Pipeline configuration for performance logs"""
        return {
            'pipeline_id': 'performance-logs',
            'pipeline': '''input {
                http {
                    port => 8081
                    type => "performance"
                }
            }
            
            filter {
                # Process performance metrics
                if [type] == "performance" {
                    # Metric validation
                    if ![value] {
                        mutate {
                            add_field => { "value" => 0 }
                        }
                    }
                    
                    # Threshold checking
                    if [metric_name] == "response_time" and [value] > 1000 {
                        mutate {
                            add_field => { "threshold_exceeded" => true }
                        }
                    }
                    
                    # Add percentiles for aggregation
                    if [metric_name] in ["response_time", "memory_usage"] {
                        aggregate {
                            task_id => "%{metric_name}"
                            code => "
                                map['count'] ||= 0;
                                map['sum'] ||= 0;
                                map['values'] ||= [];
                                
                                map['count'] += 1;
                                map['sum'] += event.get('value');
                                map['values'] << event.get('value');
                            "
                            push_map_as_event_on_timeout => true
                            timeout => 60
                        }
                    }
                }
            }
            
            output {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "fernando-logs-performance_logs-%{+YYYY.MM.dd}"
                    template_name => "performance_logs"
                }
            }'''
        }
    
    def _get_compliance_log_pipeline(self) -> Dict:
        """Pipeline configuration for compliance logs"""
        return {
            'pipeline_id': 'compliance-logs',
            'pipeline': '''input {
                http {
                    port => 8082
                    type => "compliance"
                }
            }
            
            filter {
                # Process compliance events
                if [type] == "compliance" {
                    # Compliance scoring
                    if ![compliance_score] {
                        if [status] == "compliant" {
                            mutate {
                                add_field => { "compliance_score" => 100 }
                            }
                        } else if [status] == "non_compliant" {
                            mutate {
                                add_field => { "compliance_score" => 0 }
                            }
                        } else {
                            mutate {
                                add_field => { "compliance_score" => 50 }
                            }
                        }
                    }
                    
                    # Data retention marking
                    if [regulation] == "GDPR" {
                        mutate {
                            add_field => { "retention_years" => 7 }
                        }
                    } else if [regulation] == "SOX" {
                        mutate {
                            add_field => { "retention_years" => 6 }
                        }
                    }
                    
                    # Audit trail completeness
                    if ![evidence] {
                        mutate {
                            add_field => { "audit_complete" => false }
                        }
                    } else {
                        mutate {
                            add_field => { "audit_complete" => true }
                        }
                    }
                }
            }
            
            output {
                elasticsearch {
                    hosts => ["localhost:9200"]
                    index => "fernando-logs-compliance_logs-%{+YYYY.MM.dd}"
                    template_name => "compliance_logs"
                }
            }'''
        }
    
    def create_pipeline_config(self, pipeline_id: str, config: Dict) -> str:
        """
        Create a Logstash pipeline configuration file
        
        Args:
            pipeline_id: Unique pipeline identifier
            config: Pipeline configuration dictionary
            
        Returns:
            Path to created configuration file
        """
        try:
            config_file = Path(self.config_path) / f"{pipeline_id}.conf"
            
            # Generate configuration content
            config_content = self._generate_config_content(config)
            
            # Write configuration file
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Created pipeline configuration: {config_file}")
            return str(config_file)
            
        except Exception as e:
            logger.error(f"Failed to create pipeline config: {e}")
            raise
    
    def _generate_config_content(self, config: Dict) -> str:
        """Generate Logstash configuration file content"""
        if 'pipeline' in config:
            return config['pipeline']
        else:
            # Generate from components
            input_section = config.get('input', 'input { stdin { } }')
            filter_section = config.get('filter', '')
            output_section = config.get('output', 'output { stdout { } }')
            
            return f"{input_section}\n\n{filter_section}\n\n{output_section}"
    
    def create_pipelines(self):
        """Create all defined pipeline configurations"""
        for pipeline_id, pipeline_config in self.pipelines.items():
            self.create_pipeline_config(pipeline_id, pipeline_config)
    
    def validate_pipeline(self, pipeline_file: str) -> Dict:
        """
        Validate a Logstash pipeline configuration
        
        Args:
            pipeline_file: Path to pipeline configuration file
            
        Returns:
            Validation results
        """
        try:
            # Test pipeline configuration
            cmd = [
                os.path.join(self.logstash_home, 'bin', 'logstash'),
                '--configtest',
                f'--path.config={pipeline_file}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'valid': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except Exception as e:
            logger.error(f"Pipeline validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def start_pipeline(self, pipeline_id: str) -> bool:
        """
        Start a Logstash pipeline
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Success status
        """
        try:
            config_file = Path(self.config_path) / f"{pipeline_id}.conf"
            
            if not config_file.exists():
                raise FileNotFoundError(f"Pipeline config not found: {config_file}")
            
            # Start Logstash with specific pipeline
            cmd = [
                os.path.join(self.logstash_home, 'bin', 'logstash'),
                '--path.config', str(config_file)
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Started pipeline: {pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pipeline {pipeline_id}: {e}")
            return False
    
    def stop_pipeline(self, pipeline_id: str):
        """Stop a running pipeline"""
        try:
            # This would need proper process management
            # For now, just log the attempt
            logger.info(f"Requested stop for pipeline: {pipeline_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop pipeline {pipeline_id}: {e}")
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict:
        """
        Get pipeline status information
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            Pipeline status information
        """
        try:
            config_file = Path(self.config_path) / f"{pipeline_id}.conf"
            
            status = {
                'pipeline_id': pipeline_id,
                'config_exists': config_file.exists(),
                'config_path': str(config_file),
                'created_at': datetime.fromtimestamp(config_file.stat().st_mtime) if config_file.exists() else None
            }
            
            # Validate configuration
            if config_file.exists():
                validation = self.validate_pipeline(str(config_file))
                status['validation'] = validation
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {'error': str(e)}
    
    def create_multi_pipeline_config(self) -> str:
        """Create master pipeline configuration for multiple pipelines"""
        master_config = '''# Master Logstash Pipeline Configuration
# This file orchestrates multiple log processing pipelines

# Pipeline configuration
pipeline.id: main
path.config: /etc/logstash/conf.d/

# Pipeline settings
pipeline.workers: 4
pipeline.batch.size: 1000
pipeline.batch.delay: 20

# Queue configuration
queue.type: persisted
path.queue: /var/lib/logstash/queue
path.dead_letter_queue: /var/lib/logstash/dead_letter_queue

# Dead letter queue settings
dead_letter_queue.enable: true

# Monitoring
xpack.monitoring.enabled: true
'''
        
        config_file = Path(self.config_path) / 'logstash.yml'
        
        with open(config_file, 'w') as f:
            f.write(master_config)
        
        logger.info(f"Created master pipeline config: {config_file}")
        return str(config_file)
    
    def setup_log_shippers(self) -> Dict:
        """Setup configuration for log shippers (Filebeat, etc.)"""
        shipper_configs = {
            'filebeat': '''filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/fernando/*.log
  fields:
    service: fernando
  fields_under_root: true

output.logstash:
  hosts: ["localhost:5044"]

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644''',
            
            'metricbeat': '''metricbeat.modules:
- module: system
  metricsets:
    - cpu
    - memory
    - network
    - process
  enabled: true
  period: 10s

output.logstash:
  hosts: ["localhost:5044"]

logging.level: info'''
        }
        
        configs_created = {}
        for shipper, config in shipper_configs.items():
            config_file = Path(self.config_path) / f"{shipper}.yml"
            
            with open(config_file, 'w') as f:
                f.write(config)
            
            configs_created[shipper] = str(config_file)
        
        return configs_created
