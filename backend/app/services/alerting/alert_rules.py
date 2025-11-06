"""
Alert Rules Engine

Evaluates alert rules against various data sources and determines
when alerts should be triggered based on conditions and thresholds.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import statistics

from app.models.alert import AlertRule, AlertStatus, AlertSeverity, AlertType
from app.models.usage import UsageRecord
from app.models.job import Job
from app.models.billing import Subscription, Invoice
from app.models.revenue_operations import RevenueMetric
from app.core.config import settings


logger = logging.getLogger(__name__)


class AlertRuleEngine:
    """
    Engine for evaluating alert rules against various data sources.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._metric_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        
    async def evaluate_rule(self, rule: AlertRule) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single alert rule.
        
        Args:
            rule: AlertRule to evaluate
            
        Returns:
            Evaluation result with triggered state and context
        """
        try:
            # Get metric data based on rule query configuration
            metric_data = await self._get_metric_data(rule)
            
            if metric_data is None:
                return None
            
            # Evaluate the condition
            condition_result = await self._evaluate_condition(rule.condition, metric_data)
            
            # Apply sustained duration logic
            sustained_result = await self._check_sustained_duration(rule, condition_result)
            
            if sustained_result["sustained"]:
                # Check thresholds
                threshold_result = await self._evaluate_thresholds(rule, metric_data)
                
                context = {
                    "metric_data": metric_data,
                    "condition_met": condition_result["met"],
                    "sustained_duration": sustained_result["duration"],
                    "threshold_breach": threshold_result["breached"],
                    "metric_value": threshold_result["current_value"],
                    "threshold_value": threshold_result["threshold"],
                    "labels": threshold_result.get("labels", {}),
                    "source_system": rule.metadata.get("source_system", "rule_engine"),
                    **threshold_result
                }
                
                return {
                    "triggered": threshold_result["breached"],
                    "resolved": condition_result["resolved"],
                    "context": context
                }
            
            return {"triggered": False, "resolved": False}
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            raise
    
    async def _get_metric_data(self, rule: AlertRule) -> Optional[Dict[str, Any]]:
        """
        Get metric data based on rule query configuration.
        
        Args:
            rule: AlertRule with query configuration
            
        Returns:
            Metric data dictionary
        """
        query_config = rule.query_config or {}
        metric_name = query_config.get("metric_name")
        
        if not metric_name:
            return None
        
        # Check cache first
        cache_key = f"{metric_name}:{json.dumps(query_config.get('filters', {}))}"
        cached_data = self._metric_cache.get(cache_key)
        
        if cached_data and (datetime.utcnow() - cached_data["timestamp"]).total_seconds() < self._cache_ttl:
            return cached_data["data"]
        
        # Get data based on metric type
        data_source = query_config.get("data_source", "system")
        
        if data_source == "system":
            metric_data = await self._get_system_metrics(query_config)
        elif data_source == "application":
            metric_data = await self._get_application_metrics(query_config)
        elif data_source == "business":
            metric_data = await self._get_business_metrics(query_config)
        elif data_source == "usage":
            metric_data = await self._get_usage_metrics(query_config)
        elif data_source == "revenue":
            metric_data = await self._get_revenue_metrics(query_config)
        else:
            metric_data = await self._get_custom_metrics(query_config)
        
        # Cache the result
        if metric_data:
            self._metric_cache[cache_key] = {
                "data": metric_data,
                "timestamp": datetime.utcnow()
            }
        
        return metric_data
    
    async def _get_system_metrics(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get system-level metrics (CPU, memory, disk, network).
        
        Args:
            query_config: Query configuration
            
        Returns:
            System metrics data
        """
        metric_name = query_config.get("metric_name")
        filters = query_config.get("filters", {})
        
        # This is a mock implementation - in reality, you'd integrate with
        # system monitoring tools like Prometheus, Datadog, etc.
        
        metrics_data = {
            "cpu_usage": {
                "value": 45.2,
                "timestamp": datetime.utcnow(),
                "labels": {"host": "server1", "region": "us-east-1"}
            },
            "memory_usage": {
                "value": 67.8,
                "timestamp": datetime.utcnow(),
                "labels": {"host": "server1", "region": "us-east-1"}
            },
            "disk_usage": {
                "value": 23.1,
                "timestamp": datetime.utcnow(),
                "labels": {"host": "server1", "device": "/dev/sda1"}
            },
            "network_latency": {
                "value": 125.3,
                "timestamp": datetime.utcnow(),
                "labels": {"host": "server1", "service": "api"}
            },
            "database_connections": {
                "value": 45,
                "timestamp": datetime.utcnow(),
                "labels": {"host": "db-server", "database": "production"}
            }
        }
        
        return metrics_data.get(metric_name, {})
    
    async def _get_application_metrics(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get application-level metrics (error rates, response times, etc.).
        
        Args:
            query_config: Query configuration
            
        Returns:
            Application metrics data
        """
        metric_name = query_config.get("metric_name")
        filters = query_config.get("filters", {})
        
        # Get recent job data for application metrics
        time_window = query_config.get("time_window", 300)  # 5 minutes default
        since = datetime.utcnow() - timedelta(seconds=time_window)
        
        if metric_name == "error_rate":
            # Calculate error rate from recent jobs
            jobs = self.db.query(Job).filter(
                Job.created_at >= since
            ).all()
            
            total_jobs = len(jobs)
            failed_jobs = len([j for j in jobs if j.status == "failed"])
            error_rate = (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            return {
                "value": error_rate,
                "timestamp": datetime.utcnow(),
                "labels": {"service": "document_processor", "endpoint": "process"}
            }
        
        elif metric_name == "response_time":
            # Calculate average response time from jobs
            completed_jobs = self.db.query(Job).filter(
                and_(
                    Job.created_at >= since,
                    Job.status.in_(["completed", "failed"])
                )
            ).all()
            
            if completed_jobs:
                avg_response_time = statistics.mean([
                    (j.finished_at - j.created_at).total_seconds()
                    for j in completed_jobs if j.finished_at
                ])
            else:
                avg_response_time = 0
            
            return {
                "value": avg_response_time,
                "timestamp": datetime.utcnow(),
                "labels": {"service": "api", "endpoint": "process"}
            }
        
        elif metric_name == "throughput":
            # Calculate jobs processed per minute
            jobs_per_minute = len([
                j for j in self.db.query(Job).filter(
                    Job.created_at >= since
                ).all()
            ]) / (time_window / 60)
            
            return {
                "value": jobs_per_minute,
                "timestamp": datetime.utcnow(),
                "labels": {"service": "document_processor"}
            }
        
        return {}
    
    async def _get_business_metrics(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get business-level metrics (revenue, conversion rates, etc.).
        
        Args:
            query_config: Query configuration
            
        Returns:
            Business metrics data
        """
        metric_name = query_config.get("metric_name")
        time_window = query_config.get("time_window", 3600)  # 1 hour default
        since = datetime.utcnow() - timedelta(seconds=time_window)
        
        if metric_name == "revenue_per_hour":
            # Calculate revenue from invoices
            invoices = self.db.query(Invoice).filter(
                and_(
                    Invoice.created_at >= since,
                    Invoice.status == "paid"
                )
            ).all()
            
            revenue_per_hour = sum([inv.amount for inv in invoices]) / (time_window / 3600)
            
            return {
                "value": revenue_per_hour,
                "timestamp": datetime.utcnow(),
                "labels": {"currency": "USD", "period": "hourly"}
            }
        
        elif metric_name == "conversion_rate":
            # Calculate conversion rate (paid invoices / total subscriptions)
            total_subscriptions = self.db.query(Subscription).filter(
                Subscription.created_at >= since
            ).count()
            
            paid_invoices = self.db.query(Invoice).filter(
                and_(
                    Invoice.created_at >= since,
                    Invoice.status == "paid"
                )
            ).count()
            
            conversion_rate = (paid_invoices / total_subscriptions * 100) if total_subscriptions > 0 else 0
            
            return {
                "value": conversion_rate,
                "timestamp": datetime.utcnow(),
                "labels": {"period": "hourly"}
            }
        
        return {}
    
    async def _get_usage_metrics(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get usage-level metrics (API calls, storage usage, etc.).
        
        Args:
            query_config: Query configuration
            
        Returns:
            Usage metrics data
        """
        metric_name = query_config.get("metric_name")
        time_window = query_config.get("time_window", 3600)
        since = datetime.utcnow() - timedelta(seconds=time_window)
        
        if metric_name == "api_calls_per_hour":
            # Count API calls from usage records
            api_calls = self.db.query(UsageRecord).filter(
                and_(
                    UsageRecord.created_at >= since,
                    UsageRecord.record_type == "api_call"
                )
            ).count()
            
            return {
                "value": api_calls / (time_window / 3600),
                "timestamp": datetime.utcnow(),
                "labels": {"service": "api"}
            }
        
        elif metric_name == "storage_usage_gb":
            # Calculate total storage usage
            storage_usage = self.db.query(UsageRecord).filter(
                and_(
                    UsageRecord.created_at >= since,
                    UsageRecord.record_type == "storage"
                )
            ).all()
            
            total_gb = sum([record.quantity for record in storage_usage])
            
            return {
                "value": total_gb,
                "timestamp": datetime.utcnow(),
                "labels": {"unit": "GB"}
            }
        
        return {}
    
    async def _get_revenue_metrics(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get revenue-level metrics.
        
        Args:
            query_config: Query configuration
            
        Returns:
            Revenue metrics data
        """
        metric_name = query_config.get("metric_name")
        time_window = query_config.get("time_window", 86400)  # 24 hours default
        since = datetime.utcnow() - timedelta(seconds=time_window)
        
        # Get revenue metrics from RevenueMetric table
        metrics = self.db.query(RevenueMetric).filter(
            and_(
                RevenueMetric.recorded_at >= since,
                RevenueMetric.metric_name == metric_name
            )
        ).all()
        
        if metrics:
            latest_metric = max(metrics, key=lambda m: m.recorded_at)
            
            return {
                "value": latest_metric.metric_value,
                "timestamp": latest_metric.recorded_at,
                "labels": latest_metric.labels or {}
            }
        
        return {}
    
    async def _get_custom_metrics(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get custom metrics based on query configuration.
        
        Args:
            query_config: Query configuration
            
        Returns:
            Custom metrics data
        """
        # This would handle custom metric queries
        # Implementation depends on specific custom requirements
        
        return {
            "value": 0,
            "timestamp": datetime.utcnow(),
            "labels": {"custom": "metric"}
        }
    
    async def _evaluate_condition(self, condition: Dict[str, Any], metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the alert condition.
        
        Args:
            condition: Alert condition configuration
            metric_data: Metric data to evaluate against
            
        Returns:
            Condition evaluation result
        """
        condition_type = condition.get("type", "threshold")
        
        if condition_type == "threshold":
            return await self._evaluate_threshold_condition(condition, metric_data)
        elif condition_type == "trend":
            return await self._evaluate_trend_condition(condition, metric_data)
        elif condition_type == "pattern":
            return await self._evaluate_pattern_condition(condition, metric_data)
        elif condition_type == "anomaly":
            return await self._evaluate_anomaly_condition(condition, metric_data)
        else:
            return {"met": False, "resolved": False}
    
    async def _evaluate_threshold_condition(self, condition: Dict[str, Any], metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate threshold-based conditions.
        
        Args:
            condition: Threshold condition
            metric_data: Metric data
            
        Returns:
            Evaluation result
        """
        operator = condition.get("operator", "gt")
        value = condition.get("value")
        metric_value = metric_data.get("value")
        
        if metric_value is None or value is None:
            return {"met": False, "resolved": False}
        
        # Evaluate threshold
        if operator == "gt":
            met = metric_value > value
        elif operator == "gte":
            met = metric_value >= value
        elif operator == "lt":
            met = metric_value < value
        elif operator == "lte":
            met = metric_value <= value
        elif operator == "eq":
            met = metric_value == value
        elif operator == "ne":
            met = metric_value != value
        else:
            met = False
        
        return {
            "met": met,
            "resolved": not met,
            "threshold": value,
            "current": metric_value
        }
    
    async def _evaluate_trend_condition(self, condition: Dict[str, Any], metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate trend-based conditions.
        
        Args:
            condition: Trend condition
            metric_data: Metric data
            
        Returns:
            Evaluation result
        """
        # This would analyze trends in metric data
        # For now, return a simple trend evaluation
        
        return {
            "met": False,
            "resolved": False,
            "trend": "stable"
        }
    
    async def _evaluate_pattern_condition(self, condition: Dict[str, Any], metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate pattern-based conditions.
        
        Args:
            condition: Pattern condition
            metric_data: Metric data
            
        Returns:
            Evaluation result
        """
        # This would look for patterns in metric data
        # For now, return a simple pattern evaluation
        
        return {
            "met": False,
            "resolved": False,
            "pattern_match": False
        }
    
    async def _evaluate_anomaly_condition(self, condition: Dict[str, Any], metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate anomaly-based conditions.
        
        Args:
            condition: Anomaly condition
            metric_data: Metric data
            
        Returns:
            Evaluation result
        """
        # This would detect anomalies using statistical methods
        # For now, return a simple anomaly evaluation
        
        return {
            "met": False,
            "resolved": False,
            "anomaly_score": 0.0
        }
    
    async def _check_sustained_duration(self, rule: AlertRule, condition_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if the condition has been sustained for the required duration.
        
        Args:
            rule: AlertRule
            condition_result: Condition evaluation result
            
        Returns:
            Sustained duration result
        """
        if not condition_result["met"]:
            return {"sustained": False, "duration": 0}
        
        # This would track sustained durations for each rule
        # For now, return immediate evaluation
        
        return {
            "sustained": True,
            "duration": rule.sustained_duration
        }
    
    async def _evaluate_thresholds(self, rule: AlertRule, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate thresholds against current metric value.
        
        Args:
            rule: AlertRule
            metric_data: Metric data
            
        Returns:
            Threshold evaluation result
        """
        threshold_config = rule.threshold_config or {}
        current_value = metric_data.get("value")
        labels = metric_data.get("labels", {})
        
        # Determine threshold based on severity
        if rule.severity == AlertSeverity.CRITICAL:
            threshold = threshold_config.get("critical", current_value)
        elif rule.severity == AlertSeverity.HIGH:
            threshold = threshold_config.get("high", threshold_config.get("critical", current_value))
        elif rule.severity == AlertSeverity.MEDIUM:
            threshold = threshold_config.get("medium", threshold_config.get("high", current_value))
        else:
            threshold = threshold_config.get("warning", threshold_config.get("medium", current_value))
        
        # Evaluate against threshold
        operator = threshold_config.get("operator", "gt")
        
        if operator == "gt":
            breached = current_value > threshold
        elif operator == "gte":
            breached = current_value >= threshold
        elif operator == "lt":
            breached = current_value < threshold
        elif operator == "lte":
            breached = current_value <= threshold
        else:
            breached = current_value == threshold
        
        return {
            "breached": breached,
            "current_value": current_value,
            "threshold": threshold,
            "labels": labels,
            "metric_name": rule.query_config.get("metric_name") if rule.query_config else None
        }
    
    def clear_cache(self) -> None:
        """Clear the metric cache."""
        self._metric_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._metric_cache),
            "cache_ttl": self._cache_ttl,
            "cached_metrics": list(self._metric_cache.keys())
        }