"""
Log Collection System

Provides multi-output log collection with ELK integration, log routing, and processing.
"""

from .log_collector import LogCollector
from .elk_integration import ELKIntegration
from .log_router import LogRouter
from .log_processor import LogProcessor
from .log_retention import LogRetentionManager

__all__ = [
    'LogCollector',
    'ELKIntegration',
    'LogRouter',
    'LogProcessor',
    'LogRetentionManager'
]