"""
Log Processing and Enrichment System

Provides log enrichment, transformation, and analysis capabilities.
"""

import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import threading
import asyncio
import aiohttp
from geopy.geocoders import Nominatim
from geoip2.database import Reader as GeoIPReader
from geoip2.errors import AddressNotFoundError

from app.services.log_collection.log_collector import LogEvent, LogSource, LogSeverity
from app.services.logging.structured_logger import structured_logger


class EnrichmentType(Enum):
    """Types of log enrichment"""
    GEOLOCATION = "geolocation"
    THREAT_INTELLIGENCE = "threat_intelligence"
    USER_CONTEXT = "user_context"
    SYSTEM_CONTEXT = "system_context"
    CORRELATION_ENHANCEMENT = "correlation_enhancement"
    DATA_CLASSIFICATION = "data_classification"
    ANOMALY_DETECTION = "anomaly_detection"
    COMPLIANCE_ANNOTATION = "compliance_annotation"


class TransformationType(Enum):
    """Types of log transformations"""
    FILTER = "filter"
    AGGREGATE = "aggregate"
    SAMPLE = "sample"
    DEDUPLICATE = "deduplicate"
    FORMAT_CONVERT = "format_convert"
    ANONYMIZE = "anonymize"
    MASK_SENSITIVE = "mask_sensitive"
    EXTRACT_FIELDS = "extract_fields"
    NORMALIZE = "normalize"


@dataclass
class ProcessingRule:
    """Individual processing rule definition"""
    rule_id: str
    name: str
    rule_type: Union[EnrichmentType, TransformationType]
    conditions: Dict[str, Any]
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    enrichments: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    ttl: Optional[int] = None
    batch_size: int = 100
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    error_count: int = 0
    
    def should_process(self, log_event: LogEvent) -> bool:
        """Check if rule should process this log event"""
        
        if not self.enabled:
            return False
        
        # Check TTL
        if self.ttl and self.last_executed:
            expiry_time = self.last_executed + timedelta(seconds=self.ttl)
            if datetime.utcnow() > expiry_time:
                return False
        
        # Check conditions
        return self._evaluate_conditions(log_event)
    
    def _evaluate_conditions(self, log_event: LogEvent) -> bool:
        """Evaluate rule conditions against log event"""
        
        conditions = self.conditions
        
        # Source condition
        if 'source' in conditions:
            if log_event.source.value not in conditions['source']:
                return False
        
        # Severity condition
        if 'severity' in conditions:
            if log_event.level.value not in conditions['severity']:
                return False
        
        # Category condition
        if 'category' in conditions:
            if not re.match(conditions['category'], log_event.category):
                return False
        
        # Message pattern condition
        if 'message_pattern' in conditions:
            if not re.search(conditions['message_pattern'], log_event.message):
                return False
        
        # Data field conditions
        if 'data_conditions' in conditions:
            for field_path, field_conditions in conditions['data_conditions'].items():
                field_value = self._get_nested_field(log_event.data, field_path)
                
                if field_conditions.get('required') and field_value is None:
                    return False
                
                if 'equals' in field_conditions and field_value != field_conditions['equals']:
                    return False
                
                if 'pattern' in field_conditions:
                    if not re.search(field_conditions['pattern'], str(field_value)):
                        return False
        
        return True
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value from dictionary"""
        
        if not field_path or not data:
            return None
        
        try:
            keys = field_path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return value
        except Exception:
            return None


class LogProcessor:
    """Enterprise log processing system with enrichment and transformation"""
    
    def __init__(self, 
                 max_enrichment_workers: int = 10,
                 max_transformation_workers: int = 5,
                 geoip_db_path: Optional[str] = None,
                 threat_intel_api_key: Optional[str] = None):
        
        self.processing_rules: Dict[str, ProcessingRule] = {}
        
        # Enrichment services
        self.geoip_reader = None
        if geoip_db_path:
            try:
                self.geoip_reader = GeoIPReader(geoip_db_path)
            except Exception as e:
                structured_logger.warning(
                    f"Failed to initialize GeoIP reader: {str(e)}",
                    geoip_db_path=geoip_db_path
                )
        
        self.geocoder = Nominatim(user_agent="fernando-log-processor")
        
        # External services
        self.threat_intel_api_key = threat_intel_api_key
        
        # Thread pools for parallel processing
        self._enrichment_thread_pool = asyncio.Semaphore(max_enrichment_workers)
        self._transformation_thread_pool = asyncio.Semaphore(max_transformation_workers)
        
        # Caches for performance
        self._geolocation_cache = {}
        self._threat_intel_cache = {}
        self._user_context_cache = {}
        
        # Statistics
        self.stats = {
            'total_logs_processed': 0,
            'total_enrichments': 0,
            'total_transformations': 0,
            'processing_errors': 0,
            'avg_processing_time_ms': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'last_process_time': None
        }
        
        self._lock = threading.Lock()
        
        # Default processing rules
        self._setup_default_rules()
    
    def add_processing_rule(self, rule: ProcessingRule) -> None:
        """Add processing rule"""
        
        self.processing_rules[rule.rule_id] = rule
        
        structured_logger.info(
            f"Added processing rule: {rule.name}",
            rule_id=rule.rule_id,
            rule_type=rule.rule_type.value
        )
    
    def remove_processing_rule(self, rule_id: str) -> None:
        """Remove processing rule"""
        
        if rule_id in self.processing_rules:
            rule = self.processing_rules[rule_id]
            del self.processing_rules[rule_id]
            
            structured_logger.info(
                f"Removed processing rule: {rule.name}",
                rule_id=rule_id
            )
    
    async def process_log(self, log_event: LogEvent) -> LogEvent:
        """Process single log event"""
        
        start_time = datetime.utcnow()
        
        try:
            # Get applicable rules
            applicable_rules = self._get_applicable_rules(log_event)
            
            if not applicable_rules:
                return log_event
            
            # Sort by priority
            applicable_rules.sort(key=lambda r: r.priority, reverse=True)
            
            processed_event = log_event
            
            # Apply transformations first
            for rule in applicable_rules:
                if rule.rule_type in [t for t in TransformationType]:
                    processed_event = await self._apply_transformations(processed_event, rule)
                    rule.execution_count += 1
                    rule.success_count += 1
                    rule.last_executed = datetime.utcnow()
            
            # Apply enrichments
            for rule in applicable_rules:
                if rule.rule_type in [e for e in EnrichmentType]:
                    processed_event = await self._apply_enrichments(processed_event, rule)
                    rule.execution_count += 1
                    rule.success_count += 1
                    rule.last_executed = datetime.utcnow()
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_processing_stats(processing_time)
            
            return processed_event
            
        except Exception as e:
            structured_logger.error(
                f"Error processing log: {str(e)}",
                error=str(e),
                correlation_id=log_event.correlation_id
            )
            
            with self._lock:
                self.stats['processing_errors'] += 1
            
            return log_event
    
    async def process_log_batch(self, log_events: List[LogEvent]) -> List[LogEvent]:
        """Process multiple log events efficiently"""
        
        if not log_events:
            return log_events
        
        # Group events by applicable rules for efficient processing
        grouped_events = {}
        
        for log_event in log_events:
            applicable_rules = self._get_applicable_rules(log_event)
            
            if not applicable_rules:
                # Unprocessed events
                if 'unprocessed' not in grouped_events:
                    grouped_events['unprocessed'] = []
                grouped_events['unprocessed'].append(log_event)
            else:
                # Group by rule combination
                rule_key = ":".join(sorted([rule.rule_id for rule in applicable_rules]))
                if rule_key not in grouped_events:
                    grouped_events[rule_key] = []
                grouped_events[rule_key].append(log_event)
        
        # Process each group
        processed_events = []
        
        for rule_key, events in grouped_events.items():
            if rule_key == 'unprocessed':
                processed_events.extend(events)
            else:
                rule_ids = rule_key.split(":")
                applicable_rules = [self.processing_rules[rule_id] for rule_id in rule_ids if rule_id in self.processing_rules]
                
                # Process events in parallel
                tasks = [self._process_event_with_rules(event, applicable_rules) for event in events]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        structured_logger.error(
                            f"Error processing event in batch: {str(result)}",
                            error=str(result)
                        )
                    else:
                        processed_events.append(result)
        
        return processed_events
    
    async def _process_event_with_rules(self, log_event: LogEvent, rules: List[ProcessingRule]) -> LogEvent:
        """Process event with specific rules"""
        
        processed_event = log_event
        
        # Sort by priority
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Apply transformations
        for rule in rules:
            if rule.rule_type in [t for t in TransformationType]:
                processed_event = await self._apply_transformations(processed_event, rule)
        
        # Apply enrichments
        for rule in rules:
            if rule.rule_type in [e for e in EnrichmentType]:
                processed_event = await self._apply_enrichments(processed_event, rule)
        
        return processed_event
    
    async def _apply_transformations(self, log_event: LogEvent, rule: ProcessingRule) -> LogEvent:
        """Apply transformations to log event"""
        
        for transform in rule.transformations:
            transform_type = transform.get('type')
            
            if transform_type == 'filter':
                log_event = await self._apply_filter_transform(log_event, transform)
            elif transform_type == 'anonymize':
                log_event = await self._apply_anonymize_transform(log_event, transform)
            elif transform_type == 'mask_sensitive':
                log_event = await self._apply_mask_sensitive_transform(log_event, transform)
            elif transform_type == 'extract_fields':
                log_event = await self._apply_extract_fields_transform(log_event, transform)
            elif transform_type == 'normalize':
                log_event = await self._apply_normalize_transform(log_event, transform)
            elif transform_type == 'deduplicate':
                log_event = await self._apply_deduplicate_transform(log_event, transform)
        
        with self._lock:
            self.stats['total_transformations'] += 1
        
        return log_event
    
    async def _apply_enrichments(self, log_event: LogEvent, rule: ProcessingRule) -> LogEvent:
        """Apply enrichments to log event"""
        
        for enrichment in rule.enrichments:
            enrichment_type = enrichment.get('type')
            
            if enrichment_type == 'geolocation':
                log_event = await self._apply_geolocation_enrichment(log_event, enrichment)
            elif enrichment_type == 'threat_intelligence':
                log_event = await self._apply_threat_intel_enrichment(log_event, enrichment)
            elif enrichment_type == 'user_context':
                log_event = await self._apply_user_context_enrichment(log_event, enrichment)
            elif enrichment_type == 'system_context':
                log_event = await self._apply_system_context_enrichment(log_event, enrichment)
            elif enrichment_type == 'correlation_enhancement':
                log_event = await self._apply_correlation_enrichment(log_event, enrichment)
            elif enrichment_type == 'compliance_annotation':
                log_event = await self._apply_compliance_enrichment(log_event, enrichment)
        
        with self._lock:
            self.stats['total_enrichments'] += 1
        
        return log_event
    
    async def _apply_filter_transform(self, log_event: LogEvent, transform: Dict[str, Any]) -> LogEvent:
        """Apply filter transformation"""
        
        # Check if event should be filtered out
        filter_conditions = transform.get('conditions', {})
        
        if 'exclude_patterns' in filter_conditions:
            for pattern in filter_conditions['exclude_patterns']:
                if re.search(pattern, log_event.message):
                    # Mark for filtering - return None to indicate removal
                    log_event._filter_out = True
                    break
        
        return log_event
    
    async def _apply_anonymize_transform(self, log_event: LogEvent, transform: Dict[str, Any]) -> LogEvent:
        """Apply anonymization transformation"""
        
        anonymize_fields = transform.get('fields', [])
        
        for field_path in anonymize_fields:
            field_value = self._get_nested_field(log_event.data, field_path)
            
            if field_value:
                # Hash the value for anonymization
                hashed_value = hashlib.sha256(str(field_value).encode()).hexdigest()[:16]
                self._set_nested_field(log_event.data, field_path, f"ANON_{hashed_value}")
        
        # Anonymize IP addresses in message if configured
        if transform.get('anonymize_ips', True):
            log_event.message = re.sub(
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                '[ANON_IP]',
                log_event.message
            )
        
        return log_event
    
    async def _apply_mask_sensitive_transform(self, log_event: LogEvent, transform: Dict[str, Any]) -> LogEvent:
        """Apply sensitive data masking"""
        
        sensitive_patterns = transform.get('patterns', {})
        
        for pattern_name, pattern in sensitive_patterns.items():
            if pattern_name == 'credit_card':
                # Mask credit card numbers
                log_event.message = re.sub(
                    r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
                    '[CREDIT_CARD_MASKED]',
                    log_event.message
                )
            elif pattern_name == 'ssn':
                # Mask SSN numbers
                log_event.message = re.sub(
                    r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b',
                    '[SSN_MASKED]',
                    log_event.message
                )
            elif pattern_name == 'email':
                # Mask email addresses
                log_event.message = re.sub(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    '[EMAIL_MASKED]',
                    log_event.message
                )
            else:
                # Custom pattern
                log_event.message = re.sub(
                    pattern,
                    '[SENSITIVE_DATA_MASKED]',
                    log_event.message
                )
        
        return log_event
    
    async def _apply_extract_fields_transform(self, log_event: LogEvent, transform: Dict[str, Any]) -> LogEvent:
        """Apply field extraction transformation"""
        
        extract_patterns = transform.get('patterns', {})
        
        for field_name, pattern in extract_patterns.items():
            match = re.search(pattern, log_event.message)
            
            if match:
                extracted_value = match.group(1) if match.groups() else match.group(0)
                log_event.data[f'extracted_{field_name}'] = extracted_value
        
        return log_event
    
    async def _apply_normalize_transform(self, log_event: LogEvent, transform: Dict[str, Any]) -> LogEvent:
        """Apply normalization transformation"""
        
        # Normalize timestamp format
        if transform.get('normalize_timestamps', True):
            # Already in ISO format, but ensure consistency
            log_event.timestamp = log_event.timestamp
        
        # Normalize log levels
        if transform.get('normalize_levels', True):
            level_mapping = transform.get('level_mapping', {})
            if log_event.level.value in level_mapping:
                log_event.level = LogSeverity(level_mapping[log_event.level.value])
        
        # Normalize source names
        if transform.get('normalize_sources', True):
            source_mapping = transform.get('source_mapping', {})
            if log_event.source.value in source_mapping:
                log_event.source = LogSource(source_mapping[log_event.source.value])
        
        return log_event
    
    async def _apply_deduplicate_transform(self, log_event: LogEvent, transform: Dict[str, Any]) -> LogEvent:
        """Apply deduplication transformation"""
        
        # Simple hash-based deduplication within time window
        hash_input = f"{log_event.message}{log_event.source.value}{log_event.level.value}"
        event_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        time_window = transform.get('time_window_seconds', 300)  # 5 minutes default
        
        # Check if similar event recently occurred
        cache_key = f"{log_event.source.value}:{event_hash}"
        if cache_key in self._deduplication_cache:
            last_seen = self._deduplication_cache[cache_key]
            if (datetime.utcnow() - last_seen).total_seconds() < time_window:
                # Mark as duplicate
                log_event._is_duplicate = True
            else:
                # Update cache
                self._deduplication_cache[cache_key] = datetime.utcnow()
        else:
            self._deduplication_cache[cache_key] = datetime.utcnow()
        
        return log_event
    
    async def _apply_geolocation_enrichment(self, log_event: LogEvent, enrichment: Dict[str, Any]) -> LogEvent:
        """Apply geolocation enrichment"""
        
        ip_address = log_event.data.get('ip_address') or log_event.data.get('remote_addr')
        
        if not ip_address:
            return log_event
        
        # Check cache first
        if ip_address in self._geolocation_cache:
            geolocation_data = self._geolocation_cache[ip_address]
            with self._lock:
                self.stats['cache_hits'] += 1
        else:
            geolocation_data = await self._lookup_geolocation(ip_address)
            if geolocation_data:
                self._geolocation_cache[ip_address] = geolocation_data
                with self._lock:
                    self.stats['cache_misses'] += 1
        
        if geolocation_data:
            log_event.data['geolocation'] = geolocation_data
        
        return log_event
    
    async def _lookup_geolocation(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Look up geolocation for IP address"""
        
        geolocation_data = {}
        
        try:
            # Try GeoIP2 database first
            if self.geoip_reader:
                try:
                    response = self.geoip_reader.city(ip_address)
                    geolocation_data = {
                        'country': response.country.name,
                        'country_code': response.country.iso_code,
                        'city': response.city.name,
                        'region': response.subdivisions.most_specific.name,
                        'latitude': float(response.location.latitude),
                        'longitude': float(response.location.longitude),
                        'timezone': response.location.time_zone
                    }
                except AddressNotFoundError:
                    pass
            
            # Fallback to geocoding if no result from GeoIP
            if not geolocation_data and enrichment.get('fallback_to_geocoding', True):
                try:
                    # Use a free geolocation service
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://ip-api.com/json/{ip_address}") as response:
                            if response.status == 200:
                                data = await response.json()
                                if data.get('status') == 'success':
                                    geolocation_data = {
                                        'country': data.get('country'),
                                        'country_code': data.get('countryCode'),
                                        'city': data.get('city'),
                                        'region': data.get('regionName'),
                                        'latitude': data.get('lat'),
                                        'longitude': data.get('lon'),
                                        'timezone': data.get('timezone'),
                                        'isp': data.get('isp')
                                    }
                except Exception:
                    pass
            
            return geolocation_data if geolocation_data else None
            
        except Exception as e:
            structured_logger.warning(
                f"Geolocation lookup failed for {ip_address}: {str(e)}",
                ip_address=ip_address,
                error=str(e)
            )
            return None
    
    async def _apply_threat_intel_enrichment(self, log_event: LogEvent, enrichment: Dict[str, Any]) -> LogEvent:
        """Apply threat intelligence enrichment"""
        
        ip_address = log_event.data.get('ip_address')
        
        if not ip_address or not self.threat_intel_api_key:
            return log_event
        
        # Check cache
        if ip_address in self._threat_intel_cache:
            threat_data = self._threat_intel_cache[ip_address]
            with self._lock:
                self.stats['cache_hits'] += 1
        else:
            threat_data = await self._lookup_threat_intel(ip_address)
            if threat_data:
                self._threat_intel_cache[ip_address] = threat_data
                with self._lock:
                    self.stats['cache_misses'] += 1
        
        if threat_data:
            log_event.data['threat_intelligence'] = threat_data
            log_event.tags.extend(threat_data.get('threat_tags', []))
        
        return log_event
    
    async def _lookup_threat_intel(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Lookup threat intelligence for IP address"""
        
        # This would integrate with threat intelligence services
        # For now, return mock data
        return {
            'threat_score': 0.0,
            'threat_categories': [],
            'threat_tags': [],
            'first_seen': datetime.utcnow().isoformat(),
            'last_seen': datetime.utcnow().isoformat()
        }
    
    async def _apply_user_context_enrichment(self, log_event: LogEvent, enrichment: Dict[str, Any]) -> LogEvent:
        """Apply user context enrichment"""
        
        user_id = log_event.user_id
        
        if not user_id:
            return log_event
        
        # Check cache
        if user_id in self._user_context_cache:
            user_context = self._user_context_cache[user_id]
            with self._lock:
                self.stats['cache_hits'] += 1
        else:
            user_context = await self._lookup_user_context(user_id)
            if user_context:
                self._user_context_cache[user_id] = user_context
                with self._lock:
                    self.stats['cache_misses'] += 1
        
        if user_context:
            log_event.data['user_context'] = user_context
        
        return log_event
    
    async def _lookup_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Lookup user context information"""
        
        # This would lookup user information from user management system
        return {
            'user_type': 'standard',
            'department': 'unknown',
            'risk_level': 'low',
            'last_login': None,
            'permissions': []
        }
    
    async def _apply_system_context_enrichment(self, log_event: LogEvent, enrichment: Dict[str, Any]) -> LogEvent:
        """Apply system context enrichment"""
        
        # Add system information
        log_event.data['system_context'] = {
            'hostname': enrichment.get('hostname'),
            'environment': enrichment.get('environment', 'production'),
            'service_version': enrichment.get('service_version'),
            'deployment_id': enrichment.get('deployment_id')
        }
        
        # Add processing timestamp
        log_event.data['processing_timestamp'] = datetime.utcnow().isoformat()
        
        return log_event
    
    async def _apply_correlation_enrichment(self, log_event: LogEvent, enrichment: Dict[str, Any]) -> LogEvent:
        """Apply correlation enhancement"""
        
        correlation_id = log_event.correlation_id
        
        if correlation_id:
            # Add correlation metadata
            log_event.data['correlation_context'] = {
                'correlation_id': correlation_id,
                'correlation_type': 'request_tracking',
                'trace_depth': log_event.data.get('trace_depth', 0) + 1
            }
        
        return log_event
    
    async def _apply_compliance_enrichment(self, log_event: LogEvent, enrichment: Dict[str, Any]) -> LogEvent:
        """Apply compliance annotation enrichment"""
        
        # Add compliance tags based on log content
        compliance_tags = []
        
        # Check for PII
        if self._contains_pii(log_event.message):
            compliance_tags.append('pii_present')
        
        # Check for financial data
        if re.search(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', log_event.message):
            compliance_tags.append('financial_data')
        
        # Check for audit-relevant content
        if log_event.category in ['audit', 'security', 'compliance']:
            compliance_tags.append('audit_relevant')
        
        if compliance_tags:
            log_event.data['compliance_tags'] = compliance_tags
            log_event.tags.extend(compliance_tags)
        
        return log_event
    
    def _contains_pii(self, text: str) -> bool:
        """Check if text contains personally identifiable information"""
        
        pii_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b',  # SSN
            r'\b\d{10,15}\b',  # Phone number
        ]
        
        for pattern in pii_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value from dictionary using dot notation"""
        
        if not field_path or not data:
            return None
        
        try:
            keys = field_path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return value
        except Exception:
            return None
    
    def _set_nested_field(self, data: Dict[str, Any], field_path: str, value: Any) -> None:
        """Set nested field value in dictionary using dot notation"""
        
        keys = field_path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _get_applicable_rules(self, log_event: LogEvent) -> List[ProcessingRule]:
        """Get rules applicable to log event"""
        
        return [
            rule for rule in self.processing_rules.values()
            if rule.should_process(log_event)
        ]
    
    def _update_processing_stats(self, processing_time: float) -> None:
        """Update processing statistics"""
        
        with self._lock:
            self.stats['total_logs_processed'] += 1
            self.stats['last_process_time'] = datetime.utcnow()
            
            # Update average processing time
            old_avg = self.stats['avg_processing_time_ms']
            count = self.stats['total_logs_processed']
            self.stats['avg_processing_time_ms'] = (old_avg * (count - 1) + processing_time) / count
    
    def _setup_default_rules(self) -> None:
        """Setup default processing rules"""
        
        # PII masking rule
        pii_masking_rule = ProcessingRule(
            rule_id="pii_masking",
            name="PII Masking",
            rule_type=EnrichmentType.DATA_CLASSIFICATION,
            conditions={
                'category': r'.*',  # Apply to all categories
                'data_conditions': {
                    'message': {'pattern': r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}|\b\d{3}[- ]?\d{2}[- ]?\d{4}\b'}
                }
            },
            enrichments=[
                {'type': 'compliance_annotation'}
            ],
            priority=90
        )
        self.processing_rules[pii_masking_rule.rule_id] = pii_masking_rule
        
        # Geolocation enrichment rule
        geolocation_rule = ProcessingRule(
            rule_id="geolocation_enrichment",
            name="Geolocation Enrichment",
            rule_type=EnrichmentType.GEOLOCATION,
            conditions={
                'severity': ['info', 'warning', 'error', 'critical']
            },
            enrichments=[
                {'type': 'geolocation', 'fallback_to_geocoding': True}
            ],
            priority=50
        )
        self.processing_rules[geolocation_rule.rule_id] = geolocation_rule
        
        # User context enrichment rule
        user_context_rule = ProcessingRule(
            rule_id="user_context_enrichment",
            name="User Context Enrichment",
            rule_type=EnrichmentType.USER_CONTEXT,
            conditions={},
            enrichments=[
                {'type': 'user_context'}
            ],
            priority=40
        )
        self.processing_rules[user_context_rule.rule_id] = user_context_rule
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        
        with self._lock:
            stats = self.stats.copy()
            
            # Add rule statistics
            stats['rules'] = {}
            for rule_id, rule in self.processing_rules.items():
                stats['rules'][rule_id] = {
                    'name': rule.name,
                    'type': rule.rule_type.value,
                    'enabled': rule.enabled,
                    'execution_count': rule.execution_count,
                    'success_count': rule.success_count,
                    'error_count': rule.error_count,
                    'success_rate': (rule.success_count / rule.execution_count * 100) if rule.execution_count > 0 else 0,
                    'last_executed': rule.last_executed.isoformat() if rule.last_executed else None
                }
            
            # Add cache statistics
            stats['cache'] = {
                'geolocation_cache_size': len(self._geolocation_cache),
                'threat_intel_cache_size': len(self._threat_intel_cache),
                'user_context_cache_size': len(self._user_context_cache),
                'cache_hit_rate': (self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) * 100) if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0
            }
            
            return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on log processor"""
        
        health_status = {
            'overall_status': 'healthy',
            'processor': 'healthy',
            'rules': {},
            'enrichment_services': {}
        }
        
        # Check enrichment services
        if self.geoip_reader:
            health_status['enrichment_services']['geoip'] = 'healthy'
        else:
            health_status['enrichment_services']['geoip'] = 'unavailable'
        
        if self.threat_intel_api_key:
            health_status['enrichment_services']['threat_intel'] = 'configured'
        else:
            health_status['enrichment_services']['threat_intel'] = 'not_configured'
        
        # Check rule health
        unhealthy_rules = []
        for rule_id, rule in self.processing_rules.items():
            if rule.error_count > rule.success_count and rule.execution_count > 10:
                unhealthy_rules.append(rule_id)
        
        if unhealthy_rules:
            health_status['rules']['unhealthy'] = unhealthy_rules
            health_status['overall_status'] = 'warning'
        
        # Check statistics
        if self.stats['processing_errors'] > 100:
            health_status['overall_status'] = 'critical'
        
        return health_status


# Global log processor instance
log_processor = LogProcessor()