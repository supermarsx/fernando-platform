"""
ELK Stack Configuration Management
Handles setup, configuration, and management of the complete ELK stack
"""

import logging
import json
import os
import yaml
import subprocess
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ELKConfig:
    """ELK stack configuration settings"""
    # Elasticsearch configuration
    es_cluster_name: str = "fernando-cluster"
    es_node_name: str = "fernando-node-1"
    es_path_data: str = "/var/lib/elasticsearch"
    es_path_logs: str = "/var/log/elasticsearch"
    es_http_port: int = 9200
    es_transport_port: int = 9300
    es_heap_size: str = "1g"
    es_recovery_settings: Dict[str, Any] = None
    
    # Logstash configuration  
    ls_path_config: str = "/etc/logstash/conf.d"
    ls_path_data: str = "/var/lib/logstash"
    ls_pipeline_workers: int = 2
    ls_pipeline_batch_size: int = 125
    ls_pipeline_batch_delay: int = 50
    ls_queue_type: str = "persisted"
    
    # Kibana configuration
    kb_server_port: int = 5601
    kb_elasticsearch_url: str = "http://localhost:9200"
    kb_index_name: str = ".kibana"
    kb_log_file: str = "/var/log/kibana/kibana.log"
    
    # Security configuration
    enable_security: bool = True
    xpack_security_enabled: bool = True
    xpack_ml_enabled: bool = False
    xpack_watcher_enabled: bool = True
    
    # Performance settings
    number_of_shards: int = 1
    number_of_replicas: int = 1
    refresh_interval: str = "5s"
    max_result_window: int = 10000
    
    def __post_init__(self):
        """Set default recovery settings if not provided"""
        if self.es_recovery_settings is None:
            self.es_recovery_settings = {
                'indices.memory.index_buffer_size': '30%',
                'cluster.routing.allocation.node_concurrent_recoveries': 2,
                'indices.recovery.max_bytes_per_sec': '100mb',
                'indices.recovery.max_concurrent_file_chunks': 2
            }


class ELKConfiguration:
    """Manages ELK stack configuration and deployment"""
    
    def __init__(self, config: ELKConfig = None):
        """
        Initialize ELK configuration manager
        
        Args:
            config: ELK configuration object
        """
        self.config = config or ELKConfig()
        
        # Paths
        self.config_dir = Path("/etc/fernando/elk")
        self.scripts_dir = Path("/opt/fernando/elk/scripts")
        self.templates_dir = Path("/opt/fernando/elk/templates")
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.es_config_files = [
            'elasticsearch.yml',
            'jvm.options',
            'log4j2.properties'
        ]
        
        self.ls_config_files = [
            'logstash.yml',
            'pipelines.yml'
        ]
        
        self.kb_config_files = [
            'kibana.yml'
        ]
    
    def generate_elasticsearch_config(self) -> Dict[str, str]:
        """
        Generate Elasticsearch configuration files
        
        Returns:
            Dictionary mapping filename to content
        """
        configs = {}
        
        # Main Elasticsearch configuration
        elasticsearch_yml = {
            'cluster.name': self.config.es_cluster_name,
            'node.name': self.config.es_node_name,
            'path.data': self.config.es_path_data,
            'path.logs': self.config.es_path_logs,
            'network.host': 'localhost',
            'http.port': self.config.es_http_port,
            'transport.port': self.config.es_transport_port,
            'bootstrap.memory_lock': False,
            'discovery.type': 'single-node',
            'xpack.security.enabled': self.config.xpack_security_enabled,
            'xpack.security.authc.api_key.enabled': self.config.xpack_security_enabled,
            'xpack.monitoring.collection.enabled': True,
            'xpack.watcher.enabled': self.config.xpack_watcher_enabled,
            'logger.level': 'INFO',
            'path.repo': ['/var/lib/elasticsearch/backups'],
            'reindex.remote.whitelist': ['localhost:*']
        }
        
        # Add recovery settings
        elasticsearch_yml.update(self.config.es_recovery_settings)
        
        configs['elasticsearch.yml'] = yaml.dump(elasticsearch_yml, default_flow_style=False)
        
        # JVM Options
        jvm_options = f"""# JVM Options for Elasticsearch
-Xms{self.config.es_heap_size}
-Xmx{self.config.es_heap_size}
-XX:+UseConcMarkSweepGC
-XX:CMSInitiatingOccupancyFraction=75
-XX:+UseCMSInitiatingOccupancyOnly
-XX:+AlwaysPreTouch
-Xss1m
-Djava.awt.headless=true
-Dfile.encoding=UTF-8
-Djna.nosys=true
-XX:-OmitStackTraceInFastThrow
-Dio.netty.noUnsafe=true
-Dio.netty.noKeySetOptimization=true
-Dio.netty.recycler.maxCapacityPerThread=0
-Dlog4j.shutdownHookEnabled=false
-Dlog4j2.disable.jmx=true
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=data
-XX:ErrorFile=logs/hs_err_pid%p.log
-Xlog:gc*,gc+age=trace,safepoint:file=logs/gc.log:utctime,pid,tags:filecount=32,filesize=64m
"""
        configs['jvm.options'] = jvm_options
        
        # Log4j2 Configuration
        log4j2_properties = f"""status = error
dest = err
name = properties_config

appender.console.type = Console
appender.console.name = console
appender.console.layout.type = ConsoleLayout
appender.console.layout.pattern = [%d{{ISO8601}}][%-5p][%-25c] [%{{appHost}}] %m%n

appender.rolling.type = RollingFile
appender.rolling.name = rolling
appender.rolling.fileName = {self.config.es_path_logs}/elasticsearch.log
appender.rolling.filePattern = {self.config.es_path_logs}/elasticsearch-%i.log.gz
appender.rolling.layout.type = ConsoleLayout
appender.rolling.layout.pattern = [%d{{ISO8601}}][%-5p][%-25c] [%{{appHost}}] %m%n

appender.rolling.policies.type = Policies
appender.rolling.policies.size.type = SizeBasedTriggeringPolicy
appender.rolling.policies.size.size = 1GB
appender.rolling.strategy.type = DefaultRolloverStrategy
appender.rolling.strategy.max = 50

rootLogger.level = INFO
rootLogger.appenderRef.console.ref = console
rootLogger.appenderRef.rolling.ref = rolling

logger.index_search_slowlog.level = TRACE, index_search_slowlog_file
logger.index_indexing_slowlog.level = TRACE, index_indexing_slowlog_file
"""
        configs['log4j2.properties'] = log4j2_properties
        
        return configs
    
    def generate_logstash_config(self) -> Dict[str, str]:
        """
        Generate Logstash configuration files
        
        Returns:
            Dictionary mapping filename to content
        """
        configs = {}
        
        # Main Logstash configuration
        logstash_yml = {
            'node.name': 'fernando-logstash',
            'path.data': self.config.ls_path_data,
            'pipeline.workers': self.config.ls_pipeline_workers,
            'pipeline.batch.size': self.config.ls_pipeline_batch_size,
            'pipeline.batch.delay': self.config.ls_pipeline_batch_delay,
            'queue.type': self.config.ls_queue_type,
            'queue.page_capacity': '64mb',
            'queue.max_events': 0,
            'queue.max_events.read': 0,
            'queue.max_written_bytes': '10gb',
            'queue.checkpoint.acks': 1024,
            'queue.checkpoint.writes': 1024,
            'queue.checkpoint.max_events': 0,
            'path.config': self.config.ls_path_config,
            'dead_letter_queue.enable': True,
            'xpack.monitoring.enabled': True,
            'xpack.monitoring.elasticsearch.hosts': self.config.kb_elasticsearch_url,
            'log.level': 'info',
            'http.host': '127.0.0.1',
            'path.logs': '/var/log/logstash'
        }
        
        configs['logstash.yml'] = yaml.dump(logstash_yml, default_flow_style=False)
        
        # Pipelines configuration
        pipelines_yml = f"""# Logstash Pipelines Configuration
# Fernando Application Log Pipelines

- pipeline.id: application-logs
  path.config: "{self.config.ls_path_config}/application.conf"
  queue.type: persisted
  dead_letter_queue.enable: true

- pipeline.id: audit-logs  
  path.config: "{self.config.ls_path_config}/audit.conf"
  queue.type: persisted
  
- pipeline.id: security-logs
  path.config: "{self.config.ls_path_config}/security.conf"
  queue.type: persisted
  dead_letter_queue.enable: true

- pipeline.id: performance-logs
  path.config: "{self.config.ls_path_config}/performance.conf"
  queue.type: persisted

- pipeline.id: compliance-logs
  path.config: "{self.config.ls_path_config}/compliance.conf"
  queue.type: persisted
"""
        configs['pipelines.yml'] = pipelines_yml
        
        return configs
    
    def generate_kibana_config(self) -> Dict[str, str]:
        """
        Generate Kibana configuration files
        
        Returns:
            Dictionary mapping filename to content
        """
        configs = {}
        
        # Main Kibana configuration
        kibana_yml = {
            'server.port': self.config.kb_server_port,
            'server.host': '0.0.0.0',
            'elasticsearch.hosts': self.config.kb_elasticsearch_url,
            'kibana.index': self.config.kb_index_name,
            'logging.appenders': {
                'file': {
                    'type': 'file',
                    'fileName': self.config.kb_log_file,
                    'layout': {
                        'type': 'json'
                    }
                }
            },
            'logging.root': {
                'level': 'info',
                'appenders': ['file']
            },
            'map.regionmap.layers': [],
            'telemetry.enabled': False,
            'telemetry.optIn': False,
            'newsfeed.enabled': False,
            'emails.enabled': False,
            'xpack.security.enabled': self.config.xpack_security_enabled,
            'xpack.encryptedSavedObjects.encryptionKey': 'fernando_encryption_key_32_chars_minimum',
            'xpack.security.encryptionKey': 'fernando_security_key_32_chars_minimum',
            'xpack.security.cookieName': 'sid',
            'xpack.security.sessionTimeout': 86400000,
            'ops.interval': 10000,
            'status.allowAnonymous': False,
            'tilemap.url': None,
            'data.search.aggs.shardDelay.enabled': True,
            'data.search.aggs.shardDelay.delay': 1000
        }
        
        configs['kibana.yml'] = yaml.dump(kibana_yml, default_flow_style=False)
        
        return configs
    
    def write_config_files(self) -> Dict[str, str]:
        """
        Write all configuration files to disk
        
        Returns:
            Dictionary with file paths that were written
        """
        written_files = {}
        
        try:
            # Generate all configurations
            es_configs = self.generate_elasticsearch_config()
            ls_configs = self.generate_logstash_config()
            kb_configs = self.generate_kibana_config()
            
            # Write Elasticsearch configs
            es_dir = self.config_dir / 'elasticsearch'
            es_dir.mkdir(exist_ok=True)
            
            for filename, content in es_configs.items():
                file_path = es_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                written_files[f"elasticsearch/{filename}"] = str(file_path)
                logger.info(f"Written: {file_path}")
            
            # Write Logstash configs
            ls_dir = self.config_dir / 'logstash'
            ls_dir.mkdir(exist_ok=True)
            
            for filename, content in ls_configs.items():
                file_path = ls_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                written_files[f"logstash/{filename}"] = str(file_path)
                logger.info(f"Written: {file_path}")
            
            # Write Kibana configs
            kb_dir = self.config_dir / 'kibana'
            kb_dir.mkdir(exist_ok=True)
            
            for filename, content in kb_configs.items():
                file_path = kb_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                written_files[f"kibana/{filename}"] = str(file_path)
                logger.info(f"Written: {file_path}")
            
            return written_files
            
        except Exception as e:
            logger.error(f"Failed to write config files: {e}")
            raise
    
    def create_systemd_services(self) -> Dict[str, str]:
        """
        Create systemd service files for ELK stack
        
        Returns:
            Dictionary mapping service name to file path
        """
        service_files = {}
        
        try:
            # Elasticsearch service
            es_service = f"""[Unit]
Description=Elasticsearch
Documentation=https://www.elastic.co
Wants=network-online.target
After=network-online.target
ConditionNetwork=true

[Service]
Type=notify
RuntimeDirectory=elasticsearch
PrivateTmp=true
Environment=ES_HOME=/usr/share/elasticsearch
Environment=ES_PATH_CONF=/etc/elasticsearch
Environment=PID_DIR=/var/run/elasticsearch
WorkingDirectory=/usr/share/elasticsearch

ExecStart=/usr/share/elasticsearch/bin/elasticsearch

StandardOutput=null
StandardError=null

LimitNOFILE=65535
LimitNPROC=4096
LimitAS=infinity
LimitMEMLOCK=infinity

TimeoutStopSec=0
KillMode=process
KillSignal=SIGTERM
OOMScoreAdjust=-1000

[Install]
WantedBy=multi-user.target
"""
            
            es_service_path = self.scripts_dir / 'elasticsearch.service'
            with open(es_service_path, 'w') as f:
                f.write(es_service)
            service_files['elasticsearch'] = str(es_service_path)
            
            # Logstash service
            ls_service = f"""[Unit]
Description=Logstash
After=network.target elasticsearch.service

[Service]
Type=simple
User=logstash
Group=logstash
ExecStart=/usr/share/logstash/bin/logstash --path.settings /etc/logstash
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
            
            ls_service_path = self.scripts_dir / 'logstash.service'
            with open(ls_service_path, 'w') as f:
                f.write(ls_service)
            service_files['logstash'] = str(ls_service_path)
            
            # Kibana service
            kb_service = f"""[Unit]
Description=Kibana
Documentation=https://www.elastic.co
Wants=network-online.target
After=network-online.target elasticsearch.service

[Service]
Type=simple
User=kibana
Group=kibana
ExecStart=/usr/share/kibana/bin/kibana --path.config /etc/kibana
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
            
            kb_service_path = self.scripts_dir / 'kibana.service'
            with open(kb_service_path, 'w') as f:
                f.write(kb_service)
            service_files['kibana'] = str(kb_service_path)
            
            return service_files
            
        except Exception as e:
            logger.error(f"Failed to create systemd services: {e}")
            raise
    
    def create_installation_script(self) -> str:
        """Create ELK stack installation script"""
        script_content = '''#!/bin/bash

set -e

echo "Installing ELK Stack for Fernando Platform..."

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Java 11
echo "Installing Java 11..."
sudo apt install -y openjdk-11-jdk
java -version

# Install Elasticsearch
echo "Installing Elasticsearch..."
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-7.x.list
sudo apt update
sudo apt install -y elasticsearch

# Configure Elasticsearch
echo "Configuring Elasticsearch..."
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
sudo systemctl start elasticsearch

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
sleep 30
curl -X GET "localhost:9200/"

# Install Logstash
echo "Installing Logstash..."
sudo apt install -y logstash

# Install Kibana
echo "Installing Kibana..."
sudo apt install -y kibana

# Enable and start services
echo "Starting ELK services..."
sudo systemctl enable logstash
sudo systemctl start logstash
sudo systemctl enable kibana
sudo systemctl start kibana

echo "ELK Stack installation completed!"
echo "Elasticsearch: http://localhost:9200"
echo "Kibana: http://localhost:5601"
'''
        
        script_path = self.scripts_dir / 'install_elk.sh'
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        script_path.chmod(0o755)
        
        return str(script_path)
    
    def create_monitoring_script(self) -> str:
        """Create ELK stack monitoring script"""
        script_content = '''#!/bin/bash

# ELK Stack Health Check Script
echo "=== Fernando ELK Stack Health Check ==="
echo "Date: $(date)"
echo

# Check Elasticsearch
echo "Elasticsearch Status:"
if curl -s http://localhost:9200 > /dev/null; then
    echo "✓ Elasticsearch is running"
    curl -s http://localhost:9200/_cat/health?v | grep -E "(green|yellow|red)"
else
    echo "✗ Elasticsearch is not responding"
fi
echo

# Check Logstash
echo "Logstash Status:"
if pgrep -f logstash > /dev/null; then
    echo "✓ Logstash process is running"
    ps aux | grep logstash | grep -v grep
else
    echo "✗ Logstash is not running"
fi
echo

# Check Kibana
echo "Kibana Status:"
if curl -s http://localhost:5601 > /dev/null; then
    echo "✓ Kibana is running"
else
    echo "✗ Kibana is not responding"
fi
echo

# Check indices
echo "Elasticsearch Indices:"
curl -s http://localhost:9200/_cat/indices?v | grep fernando-logs || echo "No Fernando indices found"
echo

# Disk usage
echo "Disk Usage:"
df -h | grep -E "(elasticsearch|var)"
echo

echo "=== Health Check Complete ==="
'''
        
        script_path = self.scripts_dir / 'health_check.sh'
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        script_path.chmod(0o755)
        
        return str(script_path)
    
    def create_backup_script(self) -> str:
        """Create ELK stack backup script"""
        script_content = '''#!/bin/bash

# ELK Stack Backup Script
BACKUP_DIR="/var/backups/fernando-elk"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting ELK Stack Backup..."

mkdir -p "$BACKUP_DIR"

# Backup Elasticsearch
echo "Backing up Elasticsearch..."
curl -X PUT "localhost:9200/_snapshot/fernando_backup/snapshot_$DATE"
wait

# Backup configuration
echo "Backing up configuration files..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" /etc/elasticsearch /etc/logstash /etc/kibana

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
'''
        
        script_path = self.scripts_dir / 'backup_elk.sh'
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        script_path.chmod(0o755)
        
        return str(script_path)
    
    def deploy_elk_stack(self) -> Dict[str, Any]:
        """
        Deploy complete ELK stack
        
        Returns:
            Deployment results
        """
        results = {
            'success': False,
            'config_files': {},
            'service_files': {},
            'scripts': {},
            'errors': []
        }
        
        try:
            # Write configuration files
            results['config_files'] = self.write_config_files()
            logger.info("Configuration files created")
            
            # Create systemd services
            results['service_files'] = self.create_systemd_services()
            logger.info("Systemd service files created")
            
            # Create scripts
            results['scripts']['install'] = self.create_installation_script()
            results['scripts']['monitor'] = self.create_monitoring_script()
            results['scripts']['backup'] = self.create_backup_script()
            logger.info("Helper scripts created")
            
            results['success'] = True
            logger.info("ELK stack deployment configuration completed")
            
        except Exception as e:
            results['errors'].append(str(e))
            logger.error(f"ELK stack deployment failed: {e}")
        
        return results
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate ELK stack configuration
        
        Returns:
            Validation results
        """
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Validate Elasticsearch config
            es_configs = self.generate_elasticsearch_config()
            for filename, content in es_configs.items():
                if filename == 'elasticsearch.yml':
                    config_data = yaml.safe_load(content)
                    
                    # Basic validation
                    if 'cluster.name' not in config_data:
                        validation_results['warnings'].append("No cluster name specified")
                    
                    if config_data.get('path.data') and not os.path.exists(config_data['path.data']):
                        validation_results['warnings'].append(f"Data directory does not exist: {config_data['path.data']}")
            
            # Validate Logstash config
            ls_configs = self.generate_logstash_config()
            for filename, content in ls_configs.items():
                if filename == 'logstash.yml':
                    config_data = yaml.safe_load(content)
                    
                    if config_data.get('pipeline.workers', 0) < 1:
                        validation_results['errors'].append("Pipeline workers must be at least 1")
            
            # Set validation status
            if validation_results['errors']:
                validation_results['valid'] = False
            
            logger.info("Configuration validation completed")
            
        except Exception as e:
            validation_results['errors'].append(f"Validation failed: {e}")
            validation_results['valid'] = False
        
        return validation_results
    
    def get_system_requirements(self) -> Dict[str, Any]:
        """Get system requirements for ELK stack"""
        return {
            'memory': {
                'minimum': '4GB',
                'recommended': '8GB',
                'elasticsearch_heap': self.config.es_heap_size
            },
            'storage': {
                'minimum': '50GB',
                'elasticsearch_data': self.config.es_path_data,
                'elasticsearch_logs': self.config.es_path_logs,
                'logstash_data': self.config.ls_path_data
            },
            'cpu': {
                'minimum': '2 cores',
                'recommended': '4+ cores',
                'logstash_workers': self.config.ls_pipeline_workers
            },
            'network': {
                'elasticsearch_port': self.config.es_http_port,
                'logstash_port': '5044',
                'kibana_port': self.config.kb_server_port
            },
            'dependencies': [
                'Java 11+',
                'systemd',
                'curl',
                'wget'
            ]
        }
