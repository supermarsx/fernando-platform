"""
Custom Log Formatting and Serialization

Provides configurable log formatters for different output targets and compliance requirements.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from io import StringIO
import hashlib
import secrets


class LogFormatter:
    """Base log formatter for structured JSON logging"""
    
    def __init__(self, include_stack_trace: bool = True,
                 include_thread_info: bool = True,
                 include_process_info: bool = True):
        self.include_stack_trace = include_stack_trace
        self.include_thread_info = include_thread_info
        self.include_process_info = include_process_info
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add thread information
        if self.include_thread_info:
            log_entry['thread_id'] = record.thread
            log_entry['thread_name'] = record.threadName
        
        # Add process information
        if self.include_process_info:
            log_entry['process_id'] = record.process
            log_entry['process_name'] = record.processName
        
        # Add stack trace for errors
        if record.exc_info and self.include_stack_trace:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.format_exception(record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'process', 'processName', 'message']:
                try:
                    # Attempt to serialize the value
                    json.dumps(value, default=str)
                    extra_fields[key] = value
                except (TypeError, ValueError):
                    # Skip values that can't be serialized
                    extra_fields[key] = str(value)
        
        if extra_fields:
            log_entry.update(extra_fields)
        
        return json.dumps(log_entry, default=str)
    
    def format_exception(self, exc_info) -> str:
        """Format exception info as string"""
        return ''.join(logging.traceback.format_exception(*exc_info))


class CompactLogFormatter(LogFormatter):
    """Compact log formatter for high-volume scenarios"""
    
    def __init__(self):
        super().__init__(include_stack_trace=False, 
                        include_thread_info=False, 
                        include_process_info=False)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in compact JSON"""
        log_entry = {
            't': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'l': record.levelname,
            'm': record.getMessage(),
            'f': f"{record.module}.{record.funcName}:{record.lineno}",
        }
        
        # Add basic exception info
        if record.exc_info:
            log_entry['e'] = {
                't': record.exc_info[0].__name__,
                'm': str(record.exc_info[1])
            }
        
        # Add essential extra fields only
        for key, value in record.__dict__.items():
            if key in ['correlation_id', 'user_id', 'request_id', 'operation_id']:
                log_entry[key[0]] = value  # Use single character keys for compactness
        
        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(LogFormatter):
    """Human-readable formatter for console output"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format"""
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        level_colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[41m'  # Red background
        }
        reset_color = '\033[0m'
        
        color = level_colors.get(record.levelname, '')
        reset = reset_color if color else ''
        
        formatted = f"{color}[{timestamp}] {record.levelname:8} {record.module}.{record.funcName}:{record.lineno} - {record.getMessage()}{reset}"
        
        # Add exception info
        if record.exc_info:
            formatted += "\n" + ''.join(logging.traceback.format_exception(*record.exc_info))
        
        return formatted


class ComplianceLogFormatter(LogFormatter):
    """Log formatter designed for regulatory compliance"""
    
    def __init__(self, include_pii_encryption: bool = True,
                 include_data_lineage: bool = True,
                 include_access_control: bool = True):
        super().__init__()
        self.include_pii_encryption = include_pii_encryption
        self.include_data_lineage = include_data_lineage
        self.include_access_control = include_access_control
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for compliance requirements"""
        # Base log entry
        log_entry = super().format(record)
        parsed = json.loads(log_entry)
        
        # Add compliance-specific fields
        if self.include_access_control:
            parsed.update({
                'access_control': {
                    'authenticated': getattr(record, 'authenticated', False),
                    'user_permissions': getattr(record, 'user_permissions', []),
                    'resource_permissions': getattr(record, 'resource_permissions', []),
                }
            })
        
        # Add data lineage information
        if self.include_data_lineage:
            parsed.update({
                'data_lineage': {
                    'source_system': getattr(record, 'source_system', None),
                    'data_classification': getattr(record, 'data_classification', None),
                    'sensitive_data_types': getattr(record, 'sensitive_data_types', []),
                }
            })
        
        # Encrypt PII if enabled
        if self.include_pii_encryption:
            self._encrypt_pii_fields(parsed)
        
        # Add compliance metadata
        parsed['compliance_metadata'] = {
            'log_integrity_hash': self._calculate_integrity_hash(parsed),
            'compliance_version': '1.0',
            'regulation_standards': getattr(record, 'regulation_standards', ['GDPR', 'SOX']),
        }
        
        return json.dumps(parsed, default=str)
    
    def _encrypt_pii_fields(self, log_entry: Dict[str, Any]):
        """Encrypt or mask PII fields in log entry"""
        pii_fields = ['email', 'phone', 'ssn', 'credit_card', 'user_name']
        
        for key, value in log_entry.items():
            if key.lower() in [field.lower() for field in pii_fields]:
                if isinstance(value, str):
                    # Hash sensitive values
                    log_entry[key] = hashlib.sha256(value.encode()).hexdigest()[:16]
            elif key == 'metadata' and isinstance(value, dict):
                # Check metadata for PII
                self._encrypt_pii_fields(value)
    
    def _calculate_integrity_hash(self, log_entry: Dict[str, Any]) -> str:
        """Calculate integrity hash for log entry"""
        # Remove integrity hash if present to avoid circular dependency
        temp_entry = log_entry.copy()
        if 'compliance_metadata' in temp_entry:
            temp_entry['compliance_metadata'] = temp_entry['compliance_metadata'].copy()
            if 'log_integrity_hash' in temp_entry['compliance_metadata']:
                del temp_entry['compliance_metadata']['log_integrity_hash']
        
        content = json.dumps(temp_entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()


class ForensicLogFormatter(LogFormatter):
    """Specialized formatter for forensic investigation logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for forensic analysis"""
        # Start with base compliance formatter
        log_entry = json.loads(super().format(record))
        
        # Add forensic-specific information
        forensic_data = {
            'forensic_metadata': {
                'event_id': getattr(record, 'event_id', None),
                'investigation_case': getattr(record, 'investigation_case', None),
                'chain_of_custody': getattr(record, 'chain_of_custody', []),
                'evidence_integrity': getattr(record, 'evidence_integrity', False),
                'forensic_timeline': getattr(record, 'forensic_timeline', []),
            },
            'security_context': {
                'ip_address': self._mask_ip(getattr(record, 'ip_address', None)),
                'user_agent': getattr(record, 'user_agent', None),
                'session_fingerprint': getattr(record, 'session_fingerprint', None),
                'threat_indicators': getattr(record, 'threat_indicators', []),
            },
            'investigation_data': {
                'suspicious_patterns': getattr(record, 'suspicious_patterns', []),
                'anomaly_score': getattr(record, 'anomaly_score', 0.0),
                'investigation_tags': getattr(record, 'investigation_tags', []),
            }
        }
        
        log_entry.update(forensic_data)
        
        # Add tamper-evident hash
        log_entry['forensic_integrity'] = {
            'hash': self._calculate_integrity_hash(log_entry),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'validator': 'forensic_system_v1.0'
        }
        
        return json.dumps(log_entry, default=str)
    
    def _mask_ip(self, ip_address: Optional[str]) -> Optional[str]:
        """Mask IP address for privacy in forensic logs"""
        if not ip_address:
            return None
        
        # For IPv4: mask last octet
        if '.' in ip_address:
            parts = ip_address.split('.')
            if len(parts) == 4:
                return '.'.join(parts[:3] + ['***'])
        
        # For IPv6: mask last part
        if ':' in ip_address:
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return ':'.join(parts[:3] + ['***'])
        
        return '***'
    
    def _calculate_integrity_hash(self, log_entry: Dict[str, Any]) -> str:
        """Calculate tamper-evident hash for forensic logs"""
        # Remove forensic integrity to avoid circular dependency
        temp_entry = log_entry.copy()
        if 'forensic_integrity' in temp_entry:
            del temp_entry['forensic_integrity']
        
        content = json.dumps(temp_entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()


class StructuredLogHandler(logging.Handler):
    """Custom log handler that can switch between formatters dynamically"""
    
    def __init__(self, formatter_type: str = 'json', **formatter_kwargs):
        super().__init__()
        self.set_formatter_type(formatter_type, **formatter_kwargs)
    
    def set_formatter_type(self, formatter_type: str, **kwargs):
        """Change formatter type dynamically"""
        formatters = {
            'json': lambda: LogFormatter(**kwargs),
            'compact': lambda: CompactLogFormatter(**kwargs),
            'human': lambda: HumanReadableFormatter(**kwargs),
            'compliance': lambda: ComplianceLogFormatter(**kwargs),
            'forensic': lambda: ForensicLogFormatter(**kwargs),
        }
        
        if formatter_type not in formatters:
            raise ValueError(f"Unknown formatter type: {formatter_type}")
        
        self.setFormatter(formatters[formatter_type]())


class LogSerializer:
    """Utility class for log serialization and deserialization"""
    
    @staticmethod
    def serialize_log_entry(data: Dict[str, Any], format_type: str = 'json') -> str:
        """Serialize log entry to specified format"""
        if format_type == 'json':
            return json.dumps(data, default=str)
        elif format_type == 'csv':
            return LogSerializer._to_csv(data)
        elif format_type == 'xml':
            return LogSerializer._to_xml(data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    @staticmethod
    def deserialize_log_entry(log_string: str, format_type: str = 'json') -> Dict[str, Any]:
        """Deserialize log entry from specified format"""
        if format_type == 'json':
            return json.loads(log_string)
        elif format_type == 'csv':
            return LogSerializer._from_csv(log_string)
        elif format_type == 'xml':
            return LogSerializer._from_xml(log_string)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    @staticmethod
    def _to_csv(data: Dict[str, Any]) -> str:
        """Convert log entry to CSV format"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data.keys())
        writer.writeheader()
        writer.writerow({k: str(v) for k, v in data.items()})
        return output.getvalue()
    
    @staticmethod
    def _from_csv(csv_string: str) -> Dict[str, Any]:
        """Convert CSV to log entry"""
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(csv_string))
        return next(reader)
    
    @staticmethod
    def _to_xml(data: Dict[str, Any]) -> str:
        """Convert log entry to XML format"""
        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<log_entry>')
        
        for key, value in data.items():
            xml.append(f'  <{key}><![CDATA[{value}]]></{key}>')
        
        xml.append('</log_entry>')
        return '\n'.join(xml)
    
    @staticmethod
    def _from_xml(xml_string: str) -> Dict[str, Any]:
        """Convert XML to log entry"""
        # Simple XML parser - in production, use a proper XML parser
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(xml_string)
        return {child.tag: child.text for child in root}