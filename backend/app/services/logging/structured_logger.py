"""
Structured Logger Implementation

Provides JSON-formatted logging with correlation IDs for enterprise-grade log management.
"""

import json
import logging
import uuid
import time
import threading
from datetime import datetime
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar
from functools import wraps
from enum import Enum
import traceback
from .log_formatter import LogFormatter


class LogLevel(Enum):
    """Enhanced log levels for structured logging"""
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    TRACE = 5


class LogCategory(Enum):
    """Log categories for structured routing"""
    SYSTEM = "system"
    AUDIT = "audit"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    COMPLIANCE = "compliance"
    USER_ACTION = "user_action"
    API_CALL = "api_call"
    DATA_ACCESS = "data_access"
    ERROR = "error"
    WARNING = "warning"
    DEBUG = "debug"


# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class CorrelationContext:
    """Context manager for correlation ID management"""
    
    def __init__(self, correlation_id: Optional[str] = None, 
                 user_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 request_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.request_id = request_id
        self._original_context = {}
    
    def __enter__(self):
        # Store original context
        self._original_context = {
            'correlation_id': correlation_id_var.get(),
            'user_id': user_id_var.get(),
            'session_id': session_id_var.get(),
            'request_id': request_id_var.get()
        }
        
        # Set new context
        correlation_id_var.set(self.correlation_id)
        user_id_var.set(self.user_id)
        session_id_var.set(self.session_id)
        request_id_var.set(self.request_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        correlation_id_var.set(self._original_context['correlation_id'])
        user_id_var.set(self._original_context['user_id'])
        session_id_var.set(self._original_context['session_id'])
        request_id_var.set(self._original_context['request_id'])


class StructuredLogger:
    """Enterprise-grade structured logger with correlation tracking"""
    
    def __init__(self, name: str = "fernando.structured", 
                 log_level: Union[int, LogLevel] = LogLevel.INFO):
        self.logger = logging.getLogger(name)
        self.log_level = LogLevel(log_level) if isinstance(log_level, int) else log_level
        self._setup_logger()
        
        # Performance tracking
        self._local = threading.local()
        self._operation_start_times = {}
    
    def _setup_logger(self):
        """Configure logger with structured formatting"""
        if not self.logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(LogFormatter())
            self.logger.addHandler(console_handler)
            
            # File handler for structured logs
            file_handler = logging.FileHandler('logs/structured.log')
            file_handler.setFormatter(LogFormatter())
            self.logger.addHandler(file_handler)
        
        self.logger.setLevel(self.log_level.value)
        self.logger.propagate = False
    
    def _get_log_context(self, **kwargs) -> Dict[str, Any]:
        """Extract structured context for logging"""
        context = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlation_id': correlation_id_var.get(),
            'user_id': user_id_var.get(),
            'session_id': session_id_var.get(),
            'request_id': request_id_var.get(),
            'thread_id': threading.get_ident(),
            'process_id': __import__('os').getpid()
        }
        
        # Add custom context
        context.update(kwargs)
        
        return context
    
    def _log(self, level: LogLevel, category: LogCategory, message: str, 
             error: Optional[Exception] = None, **kwargs) -> None:
        """Internal logging method"""
        log_data = self._get_log_context(**kwargs)
        log_data.update({
            'level': level.name,
            'category': category.value,
            'message': message
        })
        
        if error:
            log_data.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_traceback': traceback.format_exc()
            })
        
        # Log at appropriate level
        log_func = getattr(self.logger, level.name.lower())
        log_func(json.dumps(log_data, default=str))
    
    def debug(self, message: str, category: LogCategory = LogCategory.DEBUG, **kwargs) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, category, message, **kwargs)
    
    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, category, message, **kwargs)
    
    def warning(self, message: str, category: LogCategory = LogCategory.WARNING, 
               error: Optional[Exception] = None, **kwargs) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, category, message, error, **kwargs)
    
    def error(self, message: str, category: LogCategory = LogCategory.ERROR,
             error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, category, message, error, **kwargs)
    
    def critical(self, message: str, category: LogCategory = LogCategory.ERROR,
                error: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message"""
        self._log(LogLevel.CRITICAL, category, message, error, **kwargs)
    
    def audit(self, message: str, **kwargs) -> None:
        """Log audit message"""
        self._log(LogLevel.INFO, LogCategory.AUDIT, message, **kwargs)
    
    def security(self, message: str, **kwargs) -> None:
        """Log security message"""
        self._log(LogLevel.INFO, LogCategory.SECURITY, message, **kwargs)
    
    def performance(self, message: str, **kwargs) -> None:
        """Log performance message"""
        self._log(LogLevel.INFO, LogCategory.PERFORMANCE, message, **kwargs)
    
    def business(self, message: str, **kwargs) -> None:
        """Log business event"""
        self._log(LogLevel.INFO, LogCategory.BUSINESS, message, **kwargs)
    
    def compliance(self, message: str, **kwargs) -> None:
        """Log compliance message"""
        self._log(LogLevel.INFO, LogCategory.COMPLIANCE, message, **kwargs)
    
    def data_access(self, message: str, resource: Optional[str] = None, 
                   action: Optional[str] = None, **kwargs) -> None:
        """Log data access event"""
        log_data = kwargs.copy()
        if resource:
            log_data['resource'] = resource
        if action:
            log_data['action'] = action
        self._log(LogLevel.INFO, LogCategory.DATA_ACCESS, message, **log_data)
    
    def api_call(self, method: str, endpoint: str, status_code: Optional[int] = None,
                response_time: Optional[float] = None, **kwargs) -> None:
        """Log API call"""
        log_data = kwargs.copy()
        log_data.update({
            'api_method': method,
            'api_endpoint': endpoint,
            'status_code': status_code,
            'response_time_ms': response_time
        })
        self._log(LogLevel.INFO, LogCategory.API_CALL, 
                 f"API call: {method} {endpoint}", **log_data)
    
    def user_action(self, action: str, resource: Optional[str] = None, **kwargs) -> None:
        """Log user action"""
        log_data = kwargs.copy()
        log_data['user_action'] = action
        if resource:
            log_data['resource'] = resource
        self._log(LogLevel.INFO, LogCategory.USER_ACTION, f"User action: {action}", **log_data)
    
    def with_context(self, **context) -> 'StructuredLogger':
        """Create logger with additional context"""
        logger = StructuredLogger(self.logger.name, self.log_level.value)
        # Store additional context for this logger instance
        logger._local.context = getattr(self._local, 'context', {}) | context
        return logger
    
    def start_operation(self, operation_name: str, **kwargs) -> str:
        """Start timing an operation"""
        operation_id = str(uuid.uuid4())
        self._operation_start_times[operation_id] = time.time()
        
        self.debug(f"Started operation: {operation_name}",
                  operation_id=operation_id,
                  operation_name=operation_name,
                  **kwargs)
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, **kwargs) -> float:
        """End timing an operation and log duration"""
        if operation_id not in self._operation_start_times:
            self.warning(f"Operation ID {operation_id} not found", 
                        operation_id=operation_id)
            return 0.0
        
        duration = time.time() - self._operation_start_times[operation_id]
        self.performance(f"Completed operation", 
                        operation_id=operation_id,
                        duration_ms=duration * 1000,
                        success=success,
                        **kwargs)
        
        del self._operation_start_times[operation_id]
        return duration
    
    def operation_timer(self, operation_name: str, **kwargs):
        """Context manager for timing operations"""
        return OperationTimer(self, operation_name, **kwargs)


class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, logger: StructuredLogger, operation_name: str, **kwargs):
        self.logger = logger
        self.operation_name = operation_name
        self.context = kwargs
        self.operation_id = None
    
    def __enter__(self):
        self.operation_id = self.logger.start_operation(
            self.operation_name, **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        if not success:
            self.logger.error(f"Operation {self.operation_name} failed",
                            operation_id=self.operation_id,
                            error=str(exc_val),
                            **self.context)
        self.logger.end_operation(self.operation_id, success, **self.context)


def structured_log(level: LogLevel = LogLevel.INFO, 
                  category: LogCategory = LogCategory.SYSTEM,
                  **context):
    """Decorator for automatic structured logging of function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger(f"{func.__module__}.{func.__name__}")
            
            with logger.operation_timer(f"function_call:{func.__name__}"):
                logger.debug(f"Calling function {func.__name__}",
                           function=func.__name__,
                           args_count=len(args),
                           kwargs=kwargs)
                
                try:
                    result = func(*args, **kwargs)
                    logger.debug(f"Function {func.__name__} completed successfully",
                               function=func.__name__,
                               result_type=type(result).__name__)
                    return result
                except Exception as e:
                    logger.error(f"Function {func.__name__} failed",
                               function=func.__name__,
                               error=str(e))
                    raise
        
        return wrapper
    return decorator


# Global structured logger instance
structured_logger = StructuredLogger()


# Context management functions
def set_correlation_context(correlation_id: Optional[str] = None,
                          user_id: Optional[str] = None,
                          session_id: Optional[str] = None,
                          request_id: Optional[str] = None) -> CorrelationContext:
    """Set correlation context for current execution"""
    return CorrelationContext(correlation_id, user_id, session_id, request_id)


def get_correlation_context() -> Dict[str, Optional[str]]:
    """Get current correlation context"""
    return {
        'correlation_id': correlation_id_var.get(),
        'user_id': user_id_var.get(),
        'session_id': session_id_var.get(),
        'request_id': request_id_var.get()
    }