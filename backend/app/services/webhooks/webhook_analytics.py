"""
Webhook Analytics Service
Handles delivery analytics, performance tracking, and reporting
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session
import logging

from app.models.notifications import WebhookEndpoint, WebhookDelivery, WebhookEvent
from app.services.webhooks.webhook_analytics_queries import WebhookAnalyticsQueries

logger = logging.getLogger(__name__)

class WebhookAnalyticsService:
    """Handles webhook delivery analytics and performance tracking"""
    
    def __init__(self, db: Session):
        self.db = db
        self.queries = WebhookAnalyticsQueries(db)
    
    async def record_delivery(self, delivery: WebhookDelivery):
        """Record delivery event for analytics"""
        
        try:
            # The delivery record is already created by WebhookDeliveryService
            # This method can be used for additional analytics processing
            
            # Update endpoint statistics
            endpoint = self.db.query(WebhookEndpoint).filter(
                WebhookEndpoint.id == delivery.webhook_endpoint_id
            ).first()
            
            if endpoint:
                endpoint.last_delivery_at = datetime.utcnow()
                endpoint.last_delivery_status = delivery.status
                
                # Update success/failure counts
                if delivery.status == 'delivered':
                    endpoint.successful_deliveries_count += 1
                elif delivery.status == 'failed':
                    endpoint.failed_deliveries_count += 1
                
                self.db.commit()
            
            logger.debug(f"Recorded analytics for delivery {delivery.id}")
            
        except Exception as e:
            logger.error(f"Error recording delivery analytics: {e}")
    
    async def get_delivery_metrics(
        self,
        endpoint_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive delivery metrics"""
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Build query conditions
        conditions = [
            WebhookDelivery.created_at >= start_date,
            WebhookDelivery.created_at <= end_date
        ]
        
        if endpoint_id:
            conditions.append(WebhookDelivery.webhook_endpoint_id == endpoint_id)
        
        if event_name:
            conditions.append(WebhookDelivery.event_name == event_name)
        
        # Basic counts
        total_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(*conditions)
        ).scalar() or 0
        
        successful_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(*conditions, WebhookDelivery.status == 'delivered')
        ).scalar() or 0
        
        failed_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(*conditions, WebhookDelivery.status == 'failed')
        ).scalar() or 0
        
        pending_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(*conditions, WebhookDelivery.status == 'pending')
        ).scalar() or 0
        
        # Timeouts and connection errors
        timeout_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(*conditions, WebhookDelivery.status == 'timeout')
        ).scalar() or 0
        
        connection_error_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(*conditions, WebhookDelivery.status == 'connection_error')
        ).scalar() or 0
        
        # Calculate rates
        success_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
        failure_rate = (failed_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
        
        # Performance metrics
        avg_response_time = self.db.query(func.avg(WebhookDelivery.response_time_ms)).filter(
            and_(*conditions, WebhookDelivery.status == 'delivered')
        ).scalar() or 0
        
        min_response_time = self.db.query(func.min(WebhookDelivery.response_time_ms)).filter(
            and_(*conditions, WebhookDelivery.status == 'delivered')
        ).scalar() or 0
        
        max_response_time = self.db.query(func.max(WebhookDelivery.response_time_ms)).filter(
            and_(*conditions, WebhookDelivery.status == 'delivered')
        ).scalar() or 0
        
        # Response time percentiles
        response_time_percentiles = await self._get_response_time_percentiles(conditions)
        
        # Error analysis
        error_distribution = await self._get_error_distribution(conditions)
        
        # Event distribution
        event_distribution = await self._get_event_distribution(conditions)
        
        # Time-based trends
        daily_trends = await self._get_daily_trends(start_date, end_date, conditions)
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_deliveries": total_deliveries,
                "successful_deliveries": successful_deliveries,
                "failed_deliveries": failed_deliveries,
                "pending_deliveries": pending_deliveries,
                "timeout_deliveries": timeout_deliveries,
                "connection_error_deliveries": connection_error_deliveries,
                "success_rate": round(success_rate, 2),
                "failure_rate": round(failure_rate, 2)
            },
            "performance": {
                "average_response_time_ms": round(avg_response_time, 2),
                "min_response_time_ms": min_response_time,
                "max_response_time_ms": max_response_time,
                "response_time_percentiles": response_time_percentiles
            },
            "distribution": {
                "events": event_distribution,
                "errors": error_distribution
            },
            "trends": daily_trends,
            "endpoint_id": endpoint_id,
            "event_name": event_name
        }
    
    async def get_endpoint_performance_ranking(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get performance ranking of endpoints"""
        
        # Get endpoint metrics with performance data
        endpoint_metrics = self.db.query(
            WebhookEndpoint.id,
            WebhookEndpoint.name,
            WebhookEndpoint.url,
            func.count(WebhookDelivery.id).label('total_deliveries'),
            func.sum(func.case([(WebhookDelivery.status == 'delivered', 1)], else_=0)).label('successful_deliveries'),
            func.avg(WebhookDelivery.response_time_ms).label('avg_response_time'),
            func.sum(func.case([(WebhookDelivery.status == 'failed', 1)], else_=0)).label('failed_deliveries')
        ).join(
            WebhookDelivery
        ).filter(
            WebhookDelivery.created_at >= datetime.utcnow() - timedelta(days=30)
        ).group_by(
            WebhookEndpoint.id,
            WebhookEndpoint.name,
            WebhookEndpoint.url
        ).having(
            func.count(WebhookDelivery.id) > 10  # Only endpoints with sufficient activity
        ).all()
        
        rankings = []
        for metric in endpoint_metrics:
            total = metric.total_deliveries or 0
            successful = metric.successful_deliveries or 0
            avg_response = metric.avg_response_time or 0
            
            success_rate = (successful / total * 100) if total > 0 else 0
            
            # Calculate performance score (higher is better)
            performance_score = self._calculate_performance_score(
                success_rate=success_rate,
                avg_response_time=avg_response,
                total_deliveries=total
            )
            
            rankings.append({
                "endpoint_id": metric.id,
                "endpoint_name": metric.name,
                "endpoint_url": metric.url,
                "total_deliveries": total,
                "successful_deliveries": successful,
                "failed_deliveries": metric.failed_deliveries or 0,
                "success_rate": round(success_rate, 2),
                "average_response_time_ms": round(avg_response, 2),
                "performance_score": round(performance_score, 2)
            })
        
        # Sort by performance score (descending)
        rankings.sort(key=lambda x: x["performance_score"], reverse=True)
        
        return rankings[:limit]
    
    async def get_event_analytics(self) -> Dict[str, Any]:
        """Get analytics for all events"""
        
        # Event frequency
        event_counts = self.db.query(
            WebhookDelivery.event_name,
            func.count(WebhookDelivery.id).label('total_count'),
            func.sum(func.case([(WebhookDelivery.status == 'delivered', 1)], else_=0)).label('success_count'),
            func.avg(WebhookDelivery.response_time_ms).label('avg_response_time')
        ).group_by(
            WebhookDelivery.event_name
        ).order_by(
            desc('total_count')
        ).all()
        
        # Calculate statistics per event
        event_analytics = []
        for event_data in event_counts:
            total = event_data.total_count or 0
            successful = event_data.success_count or 0
            avg_response = event_data.avg_response_time or 0
            
            success_rate = (successful / total * 100) if total > 0 else 0
            
            event_analytics.append({
                "event_name": event_data.event_name,
                "total_deliveries": total,
                "successful_deliveries": successful,
                "success_rate": round(success_rate, 2),
                "average_response_time_ms": round(avg_response, 2)
            })
        
        # Recent events (last 7 days)
        recent_events = self.db.query(
            WebhookDelivery.event_name,
            func.count(WebhookDelivery.id).label('recent_count'),
            func.sum(func.case([(WebhookDelivery.status == 'delivered', 1)], else_=0)).label('recent_success_count')
        ).filter(
            WebhookDelivery.created_at >= datetime.utcnow() - timedelta(days=7)
        ).group_by(
            WebhookDelivery.event_name
        ).all()
        
        recent_analytics = {}
        for event_data in recent_events:
            total = event_data.recent_count or 0
            successful = event_data.recent_success_count or 0
            recent_analytics[event_data.event_name] = {
                "recent_deliveries": total,
                "recent_success_rate": round((successful / total * 100), 2) if total > 0 else 0
            }
        
        return {
            "all_time": event_analytics,
            "last_7_days": recent_analytics
        }
    
    async def get_retry_analytics(self) -> Dict[str, Any]:
        """Get analytics on retry behavior"""
        
        # Retry statistics
        retry_stats = self.db.query(
            WebhookDelivery.retry_count,
            func.count(WebhookDelivery.id).label('delivery_count'),
            func.sum(func.case([(WebhookDelivery.status == 'delivered', 1)], else_=0)).label('success_count')
        ).group_by(
            WebhookDelivery.retry_count
        ).order_by(
            WebhookDelivery.retry_count
        ).all()
        
        retry_analysis = []
        for retry_data in retry_stats:
            retry_count = retry_data.retry_count
            total = retry_data.delivery_count or 0
            successful = retry_data.success_count or 0
            success_rate = (successful / total * 100) if total > 0 else 0
            
            retry_analysis.append({
                "retry_count": retry_count,
                "total_deliveries": total,
                "successful_deliveries": successful,
                "success_rate": round(success_rate, 2)
            })
        
        # Total deliveries with retries
        total_with_retries = sum(item["total_deliveries"] for item in retry_analysis if item["retry_count"] > 0)
        
        # Average retries per delivery
        total_deliveries = sum(item["total_deliveries"] for item in retry_analysis)
        total_retries = sum(item["retry_count"] * item["total_deliveries"] for item in retry_analysis)
        avg_retries = (total_retries / total_deliveries) if total_deliveries > 0 else 0
        
        return {
            "retry_distribution": retry_analysis,
            "summary": {
                "total_deliveries": total_deliveries,
                "deliveries_with_retries": total_with_retries,
                "average_retries_per_delivery": round(avg_retries, 2)
            }
        }
    
    async def _get_response_time_percentiles(self, conditions: List) -> Dict[str, float]:
        """Get response time percentiles"""
        
        try:
            # This is a simplified implementation
            # In production, you might want to use window functions or materialized views
            
            delivered_deliveries = self.db.query(WebhookDelivery.response_time_ms).filter(
                and_(*conditions, WebhookDelivery.status == 'delivered', WebhookDelivery.response_time_ms.isnot(None))
            ).order_by(WebhookDelivery.response_time_ms).all()
            
            if not delivered_deliveries:
                return {"50th": 0, "75th": 0, "90th": 0, "95th": 0, "99th": 0}
            
            response_times = [delivery.response_time_ms for delivery in delivered_deliveries]
            n = len(response_times)
            
            def percentile(data, p):
                index = int(p * (n - 1))
                return data[index]
            
            return {
                "50th": round(percentile(response_times, 0.5), 2),
                "75th": round(percentile(response_times, 0.75), 2),
                "90th": round(percentile(response_times, 0.9), 2),
                "95th": round(percentile(response_times, 0.95), 2),
                "99th": round(percentile(response_times, 0.99), 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating percentiles: {e}")
            return {"50th": 0, "75th": 0, "90th": 0, "95th": 0, "99th": 0}
    
    async def _get_error_distribution(self, conditions: List) -> Dict[str, int]:
        """Get distribution of error types"""
        
        error_data = self.db.query(
            WebhookDelivery.status,
            func.count(WebhookDelivery.id).label('count')
        ).filter(
            and_(*conditions, WebhookDelivery.status != 'delivered')
        ).group_by(
            WebhookDelivery.status
        ).all()
        
        return {data.status: data.count for data in error_data}
    
    async def _get_event_distribution(self, conditions: List) -> Dict[str, int]:
        """Get distribution of events"""
        
        event_data = self.db.query(
            WebhookDelivery.event_name,
            func.count(WebhookDelivery.id).label('count')
        ).filter(*conditions).group_by(
            WebhookDelivery.event_name
        ).order_by(
            desc('count')
        ).all()
        
        return {data.event_name: data.count for data in event_data}
    
    async def _get_daily_trends(self, start_date: datetime, end_date: datetime, conditions: List) -> List[Dict[str, Any]]:
        """Get daily trends for deliveries"""
        
        # This is a simplified daily trend calculation
        # In production, you might want to use date_trunc for better performance
        
        days = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            day_conditions = conditions + [
                WebhookDelivery.created_at >= day_start,
                WebhookDelivery.created_at <= day_end
            ]
            
            total = self.db.query(func.count(WebhookDelivery.id)).filter(
                and_(*day_conditions)
            ).scalar() or 0
            
            successful = self.db.query(func.count(WebhookDelivery.id)).filter(
                and_(*day_conditions, WebhookDelivery.status == 'delivered')
            ).scalar() or 0
            
            failed = self.db.query(func.count(WebhookDelivery.id)).filter(
                and_(*day_conditions, WebhookDelivery.status == 'failed')
            ).scalar() or 0
            
            days.append({
                "date": current_date.isoformat(),
                "total_deliveries": total,
                "successful_deliveries": successful,
                "failed_deliveries": failed,
                "success_rate": round((successful / total * 100), 2) if total > 0 else 0
            })
            
            current_date += timedelta(days=1)
        
        return days
    
    def _calculate_performance_score(
        self,
        success_rate: float,
        avg_response_time: float,
        total_deliveries: int
    ) -> float:
        """Calculate overall performance score"""
        
        # Weight components
        success_weight = 0.7
        response_weight = 0.2
        volume_weight = 0.1
        
        # Success rate score (0-100)
        success_score = success_rate
        
        # Response time score (0-100, inversely related to response time)
        if avg_response_time <= 1000:  # <= 1 second
            response_score = 100
        elif avg_response_time >= 10000:  # >= 10 seconds
            response_score = 0
        else:
            response_score = 100 - ((avg_response_time - 1000) / 9000 * 100)
        
        # Volume score (normalize based on sample size)
        min_volume_for_full_score = 100
        if total_deliveries >= min_volume_for_full_score:
            volume_score = 100
        else:
            volume_score = (total_deliveries / min_volume_for_full_score) * 100
        
        # Calculate weighted score
        total_score = (
            success_score * success_weight +
            response_score * response_weight +
            volume_score * volume_weight
        )
        
        return total_score
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time webhook metrics"""
        
        # Current active endpoints
        active_endpoints = self.db.query(func.count(WebhookEndpoint.id)).filter(
            WebhookEndpoint.active == True
        ).scalar() or 0
        
        # Recent deliveries (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            WebhookDelivery.created_at >= one_hour_ago
        ).scalar() or 0
        
        # Recent successful deliveries
        recent_success = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(
                WebhookDelivery.created_at >= one_hour_ago,
                WebhookDelivery.status == 'delivered'
            )
        ).scalar() or 0
        
        # Recent failures
        recent_failures = self.db.query(func.count(WebhookDelivery.id)).filter(
            and_(
                WebhookDelivery.created_at >= one_hour_ago,
                WebhookDelivery.status == 'failed'
            )
        ).scalar() or 0
        
        # Pending deliveries
        pending_deliveries = self.db.query(func.count(WebhookDelivery.id)).filter(
            WebhookDelivery.status == 'pending'
        ).scalar() or 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_endpoints": active_endpoints,
            "recent_deliveries_last_hour": recent_deliveries,
            "recent_success_rate": round((recent_success / recent_deliveries * 100), 2) if recent_deliveries > 0 else 0,
            "recent_failures": recent_failures,
            "pending_deliveries": pending_deliveries,
            "system_status": "healthy" if recent_success > recent_failures else "degraded"
        }