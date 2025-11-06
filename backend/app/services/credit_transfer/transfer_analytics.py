"""
Transfer Analytics Service

Transfer pattern analysis and insights generation.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import statistics
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models.credits import (
    CreditTransfer, CreditTransferStatus, CreditTransferPermission,
    CreditPermissionType, User, Organization, CreditBalance
)
from app.services.credits.credit_analytics import CreditAnalyticsService
from app.services.credits.credit_manager import CreditManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class TransferAnalyticsService:
    """
    Service for analyzing credit transfer patterns and generating insights
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics_service = CreditAnalyticsService(db)
        self.credit_manager = CreditManager(db)
    
    def get_transfer_statistics(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive transfer statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Build base query
            query = self.db.query(CreditTransfer).filter(
                CreditTransfer.created_at >= start_date
            )
            
            if user_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_user_id == user_id,
                        CreditTransfer.to_user_id == user_id
                    )
                )
            
            if organization_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_organization_id == organization_id,
                        CreditTransfer.to_organization_id == organization_id
                    )
                )
            
            transfers = query.all()
            
            # Calculate statistics
            total_transfers = len(transfers)
            completed_transfers = len([t for t in transfers if t.status == CreditTransferStatus.COMPLETED])
            failed_transfers = len([t for t in transfers if t.status == CreditTransferStatus.FAILED])
            pending_transfers = len([t for t in transfers if t.status in [CreditTransferStatus.PENDING, CreditTransferStatus.PENDING_APPROVAL]])
            
            # Calculate volumes
            total_volume = sum(t.amount for t in transfers if t.status == CreditTransferStatus.COMPLETED)
            total_volume_decimal = Decimal(str(total_volume))
            
            # Calculate average transfer size
            avg_transfer_size = total_volume_decimal / completed_transfers if completed_transfers > 0 else Decimal('0')
            
            # Calculate success rate
            success_rate = (completed_transfers / total_transfers * 100) if total_transfers > 0 else 0
            
            # Get status distribution
            status_distribution = {}
            for status in CreditTransferStatus:
                count = len([t for t in transfers if t.status == status])
                if count > 0:
                    status_distribution[status.value] = count
            
            # Calculate daily/weekly patterns
            time_patterns = self._analyze_time_patterns(transfers)
            
            # Calculate top users by transfer volume
            top_users = self._get_top_transfer_users(transfers, user_id, organization_id)
            
            return {
                "overview": {
                    "total_transfers": total_transfers,
                    "completed_transfers": completed_transfers,
                    "failed_transfers": failed_transfers,
                    "pending_transfers": pending_transfers,
                    "success_rate": round(success_rate, 2),
                    "total_volume": float(total_volume_decimal),
                    "average_transfer_size": float(avg_transfer_size),
                    "period_days": days
                },
                "status_distribution": status_distribution,
                "time_patterns": time_patterns,
                "top_users": top_users
            }
            
        except Exception as e:
            logger.error(f"Error getting transfer statistics: {str(e)}")
            return {}
    
    def analyze_transfer_patterns(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze transfer patterns and trends
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get transfer data
            query = self.db.query(CreditTransfer).filter(
                CreditTransfer.created_at >= start_date
            )
            
            if user_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_user_id == user_id,
                        CreditTransfer.to_user_id == user_id
                    )
                )
            
            if organization_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_organization_id == organization_id,
                        CreditTransfer.to_organization_id == organization_id
                    )
                )
            
            transfers = query.order_by(desc(CreditTransfer.created_at)).all()
            
            # Analyze patterns
            volume_trend = self._analyze_volume_trend(transfers)
            frequency_pattern = self._analyze_frequency_pattern(transfers)
            size_pattern = self._analyze_transfer_size_pattern(transfers)
            approval_pattern = self._analyze_approval_pattern(transfers)
            
            # Identify anomalies
            anomalies = self._identify_transfer_anomalies(transfers)
            
            # Calculate correlations
            correlations = self._calculate_transfer_correlations(transfers)
            
            return {
                "volume_trend": volume_trend,
                "frequency_pattern": frequency_pattern,
                "size_pattern": size_pattern,
                "approval_pattern": approval_pattern,
                "anomalies": anomalies,
                "correlations": correlations,
                "analysis_period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error analyzing transfer patterns: {str(e)}")
            return {}
    
    def get_user_transfer_profile(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed transfer profile for a user
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get user's transfer history
            sent_transfers = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.from_user_id == user_id,
                    CreditTransfer.created_at >= start_date
                )
            ).all()
            
            received_transfers = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.to_user_id == user_id,
                    CreditTransfer.created_at >= start_date
                )
            ).all()
            
            # Calculate user metrics
            profile = {
                "user_id": user_id,
                "period_days": days,
                "sent_transfers": {
                    "count": len(sent_transfers),
                    "total_amount": sum(t.amount for t in sent_transfers if t.status == CreditTransferStatus.COMPLETED),
                    "success_rate": self._calculate_success_rate(sent_transfers),
                    "average_amount": self._calculate_average_amount(sent_transfers),
                    "most_common_recipients": self._get_most_common_recipients(sent_transfers),
                    "peak_hours": self._get_peak_activity_hours(sent_transfers)
                },
                "received_transfers": {
                    "count": len(received_transfers),
                    "total_amount": sum(t.amount for t in received_transfers if t.status == CreditTransferStatus.COMPLETED),
                    "success_rate": self._calculate_success_rate(received_transfers),
                    "average_amount": self._calculate_average_amount(received_transfers),
                    "most_common_senders": self._get_most_common_senders(received_transfers),
                    "peak_hours": self._get_peak_activity_hours(received_transfers)
                }
            }
            
            # Calculate balance impact
            balance_impact = self._calculate_balance_impact(user_id, sent_transfers, received_transfers)
            profile["balance_impact"] = balance_impact
            
            # Get transfer permissions
            permissions = self._get_user_transfer_permissions(user_id, organization_id)
            profile["permissions"] = permissions
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user transfer profile: {str(e)}")
            return {}
    
    def generate_transfer_insights(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights about transfer behavior
        """
        try:
            # Get comprehensive data
            statistics = self.get_transfer_statistics(user_id, organization_id, days)
            patterns = self.analyze_transfer_patterns(user_id, organization_id, days)
            
            insights = {
                "data_quality_score": self._calculate_data_quality_score(statistics, patterns),
                "behavioral_insights": self._generate_behavioral_insights(statistics, patterns),
                "efficiency_insights": self._generate_efficiency_insights(statistics, patterns),
                "recommendations": self._generate_transfer_recommendations(statistics, patterns),
                "risk_assessment": self._assess_transfer_risks(statistics, patterns),
                "optimization_suggestions": self._suggest_optimizations(statistics, patterns)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating transfer insights: {str(e)}")
            return {}
    
    def predict_transfer_behavior(
        self,
        user_id: int,
        days: int = 30,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Predict future transfer behavior based on historical data
        """
        try:
            # Get historical data for prediction (longer period for better patterns)
            historical_days = days * 3
            start_date = datetime.utcnow() - timedelta(days=historical_days)
            
            # Get user's transfer history
            sent_transfers = self.db.query(CreditTransfer).filter(
                and_(
                    CreditTransfer.from_user_id == user_id,
                    CreditTransfer.created_at >= start_date
                )
            ).all()
            
            # Analyze historical patterns
            volume_forecast = self._forecast_transfer_volume(sent_transfers, days)
            frequency_forecast = self._forecast_transfer_frequency(sent_transfers, days)
            size_forecast = self._forecast_transfer_size(sent_transfers, days)
            
            # Calculate prediction confidence
            confidence_score = self._calculate_prediction_confidence(sent_transfers)
            
            # Identify seasonal patterns
            seasonal_patterns = self._identify_seasonal_patterns(sent_transfers)
            
            return {
                "predicted_volume": volume_forecast,
                "predicted_frequency": frequency_forecast,
                "predicted_size": size_forecast,
                "confidence_score": confidence_score,
                "seasonal_patterns": seasonal_patterns,
                "forecast_period_days": days,
                "data_period_days": historical_days
            }
            
        except Exception as e:
            logger.error(f"Error predicting transfer behavior: {str(e)}")
            return {}
    
    def detect_transfer_fraud(
        self,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Detect potential fraudulent transfer patterns
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent transfers
            query = self.db.query(CreditTransfer).filter(
                CreditTransfer.created_at >= start_date
            )
            
            if user_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_user_id == user_id,
                        CreditTransfer.to_user_id == user_id
                    )
                )
            
            if organization_id:
                query = query.filter(
                    or_(
                        CreditTransfer.from_organization_id == organization_id,
                        CreditTransfer.to_organization_id == organization_id
                    )
                )
            
            transfers = query.all()
            
            # Run fraud detection algorithms
            fraud_indicators = []
            
            # Check for unusual volume spikes
            volume_spikes = self._detect_volume_spikes(transfers)
            if volume_spikes:
                fraud_indicators.extend(volume_spikes)
            
            # Check for unusual timing patterns
            timing_anomalies = self._detect_timing_anomalies(transfers)
            if timing_anomalies:
                fraud_indicators.extend(timing_anomalies)
            
            # Check for circular transfers
            circular_transfers = self._detect_circular_transfers(transfers)
            if circular_transfers:
                fraud_indicators.extend(circular_transfers)
            
            # Check for unusual recipient patterns
            recipient_anomalies = self._detect_recipient_anomalies(transfers)
            if recipient_anomalies:
                fraud_indicators.extend(recipient_anomalies)
            
            # Calculate risk scores
            for indicator in fraud_indicators:
                indicator["risk_score"] = self._calculate_fraud_risk_score(indicator)
            
            return fraud_indicators
            
        except Exception as e:
            logger.error(f"Error detecting transfer fraud: {str(e)}")
            return []
    
    def _analyze_time_patterns(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Analyze temporal patterns in transfers
        """
        try:
            # Group transfers by hour of day
            hourly_counts = defaultdict(int)
            hourly_volumes = defaultdict(Decimal)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    hour = transfer.created_at.hour
                    hourly_counts[hour] += 1
                    hourly_volumes[hour] += transfer.amount
            
            # Group transfers by day of week
            daily_counts = defaultdict(int)
            daily_volumes = defaultdict(Decimal)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    day = transfer.created_at.weekday()  # 0 = Monday
                    daily_counts[day] += 1
                    daily_volumes[day] += transfer.amount
            
            # Find peak hours and days
            peak_hour = max(hourly_counts.keys(), key=lambda h: hourly_counts[h]) if hourly_counts else 0
            peak_day = max(daily_counts.keys(), key=lambda d: daily_counts[d]) if daily_counts else 0
            
            return {
                "hourly_distribution": dict(hourly_counts),
                "hourly_volume": {k: float(v) for k, v in hourly_volumes.items()},
                "daily_distribution": dict(daily_counts),
                "daily_volume": {k: float(v) for k, v in daily_volumes.items()},
                "peak_hour": peak_hour,
                "peak_day": peak_day
            }
            
        except Exception as e:
            logger.error(f"Error analyzing time patterns: {str(e)}")
            return {}
    
    def _get_top_transfer_users(
        self,
        transfers: List[CreditTransfer],
        filter_user_id: Optional[int],
        organization_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Get top users by transfer activity
        """
        try:
            # Count outbound transfers
            outbound_counts = defaultdict(int)
            outbound_volumes = defaultdict(Decimal)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    outbound_counts[transfer.from_user_id] += 1
                    outbound_volumes[transfer.from_user_id] += transfer.amount
            
            # Count inbound transfers
            inbound_counts = defaultdict(int)
            inbound_volumes = defaultdict(Decimal)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    inbound_counts[transfer.to_user_id] += 1
                    inbound_volumes[transfer.to_user_id] += transfer.amount
            
            # Get top users
            top_senders = sorted(
                outbound_counts.keys(),
                key=lambda uid: (outbound_counts[uid], outbound_volumes[uid]),
                reverse=True
            )[:10]
            
            top_receivers = sorted(
                inbound_counts.keys(),
                key=lambda uid: (inbound_counts[uid], inbound_volumes[uid]),
                reverse=True
            )[:10]
            
            return {
                "top_senders": [
                    {
                        "user_id": uid,
                        "transfer_count": outbound_counts[uid],
                        "total_volume": float(outbound_volumes[uid])
                    }
                    for uid in top_senders
                ],
                "top_receivers": [
                    {
                        "user_id": uid,
                        "transfer_count": inbound_counts[uid],
                        "total_volume": float(inbound_volumes[uid])
                    }
                    for uid in top_receivers
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting top transfer users: {str(e)}")
            return {"top_senders": [], "top_receivers": []}
    
    def _analyze_volume_trend(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Analyze transfer volume trends over time
        """
        try:
            # Group by date
            daily_volumes = defaultdict(Decimal)
            daily_counts = defaultdict(int)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    date_key = transfer.created_at.date()
                    daily_volumes[date_key] += transfer.amount
                    daily_counts[date_key] += 1
            
            # Calculate trend
            if len(daily_volumes) < 2:
                return {"trend": "insufficient_data", "growth_rate": 0}
            
            # Simple linear trend calculation
            dates = sorted(daily_volumes.keys())
            volumes = [daily_volumes[date] for date in dates]
            
            # Calculate growth rate
            first_volume = volumes[0]
            last_volume = volumes[-1]
            if first_volume > 0:
                growth_rate = ((last_volume - first_volume) / first_volume) * 100
            else:
                growth_rate = 0
            
            # Determine trend direction
            if growth_rate > 5:
                trend = "increasing"
            elif growth_rate < -5:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return {
                "trend": trend,
                "growth_rate": round(growth_rate, 2),
                "daily_volumes": {str(k): float(v) for k, v in daily_volumes.items()},
                "daily_counts": {str(k): v for k, v in daily_counts.items()}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume trend: {str(e)}")
            return {"trend": "error", "growth_rate": 0}
    
    def _analyze_frequency_pattern(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Analyze transfer frequency patterns
        """
        try:
            # Count transfers per day
            daily_frequencies = defaultdict(int)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    date_key = transfer.created_at.date()
                    daily_frequencies[date_key] += 1
            
            if not daily_frequencies:
                return {"pattern": "no_transfers"}
            
            frequencies = list(daily_frequencies.values())
            avg_frequency = statistics.mean(frequencies)
            median_frequency = statistics.median(frequencies)
            
            # Identify pattern type
            if avg_frequency < 1:
                pattern = "sporadic"
            elif avg_frequency <= 3:
                pattern = "regular"
            else:
                pattern = "frequent"
            
            return {
                "pattern": pattern,
                "average_frequency": round(avg_frequency, 2),
                "median_frequency": median_frequency,
                "max_daily_frequency": max(frequencies),
                "days_with_transfers": len(frequencies)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing frequency pattern: {str(e)}")
            return {"pattern": "error"}
    
    def _analyze_transfer_size_pattern(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Analyze transfer size patterns
        """
        try:
            completed_transfers = [t for t in transfers if t.status == CreditTransferStatus.COMPLETED]
            
            if not completed_transfers:
                return {"pattern": "no_completed_transfers"}
            
            amounts = [t.amount for t in completed_transfers]
            avg_amount = statistics.mean(amounts)
            median_amount = statistics.median(amounts)
            std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            # Identify size pattern
            if len(set(amounts)) == 1:
                pattern = "consistent"
            elif std_dev / avg_amount < 0.5:
                pattern = "similar_sizes"
            else:
                pattern = "variable_sizes"
            
            return {
                "pattern": pattern,
                "average_amount": float(avg_amount),
                "median_amount": float(median_amount),
                "standard_deviation": float(std_dev),
                "min_amount": float(min(amounts)),
                "max_amount": float(max(amounts)),
                "total_amount": float(sum(amounts))
            }
            
        except Exception as e:
            logger.error(f"Error analyzing transfer size pattern: {str(e)}")
            return {"pattern": "error"}
    
    def _analyze_approval_pattern(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Analyze approval patterns in transfers
        """
        try:
            pending_approvals = [t for t in transfers if t.status == CreditTransferStatus.PENDING_APPROVAL]
            approved_transfers = [t for t in transfers if t.status == CreditTransferStatus.APPROVED]
            rejected_transfers = [t for t in transfers if t.status == CreditTransferStatus.REJECTED]
            
            total_pending_approvals = len(pending_approvals) + len(approved_transfers) + len(rejected_transfers)
            
            if total_pending_approvals == 0:
                return {"pattern": "no_approvals_required"}
            
            approval_rate = len(approved_transfers) / total_pending_approvals * 100
            rejection_rate = len(rejected_transfers) / total_pending_approvals * 100
            
            # Calculate average approval time
            approval_times = []
            for transfer in approved_transfers:
                if transfer.approved_at:
                    approval_time = (transfer.approved_at - transfer.created_at).total_seconds() / 3600
                    approval_times.append(approval_time)
            
            avg_approval_time = statistics.mean(approval_times) if approval_times else 0
            
            return {
                "pattern": "approval_required" if total_pending_approvals > 0 else "no_approval_required",
                "total_approvals_required": total_pending_approvals,
                "approval_rate": round(approval_rate, 2),
                "rejection_rate": round(rejection_rate, 2),
                "average_approval_time_hours": round(avg_approval_time, 2),
                "pending_approvals": len(pending_approvals),
                "approved_transfers": len(approved_transfers),
                "rejected_transfers": len(rejected_transfers)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing approval pattern: {str(e)}")
            return {"pattern": "error"}
    
    def _identify_transfer_anomalies(self, transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Identify anomalous transfer patterns
        """
        anomalies = []
        
        try:
            # Check for unusually large transfers
            completed_transfers = [t for t in transfers if t.status == CreditTransferStatus.COMPLETED]
            if completed_transfers:
                amounts = [t.amount for t in completed_transfers]
                avg_amount = statistics.mean(amounts)
                threshold = avg_amount * 3  # 3x average as anomaly threshold
                
                large_transfers = [t for t in completed_transfers if t.amount > threshold]
                for transfer in large_transfers:
                    anomalies.append({
                        "type": "unusually_large_transfer",
                        "transfer_id": transfer.id,
                        "amount": float(transfer.amount),
                        "threshold": float(threshold),
                        "severity": "high" if transfer.amount > avg_amount * 5 else "medium"
                    })
            
            # Check for rapid succession transfers
            sorted_transfers = sorted(completed_transfers, key=lambda t: t.created_at)
            for i in range(len(sorted_transfers) - 1):
                current = sorted_transfers[i]
                next_transfer = sorted_transfers[i + 1]
                
                time_diff = (next_transfer.created_at - current.created_at).total_seconds() / 60  # minutes
                if time_diff < 5 and current.from_user_id == next_transfer.from_user_id:  # Within 5 minutes
                    anomalies.append({
                        "type": "rapid_succession_transfers",
                        "transfer_ids": [current.id, next_transfer.id],
                        "time_difference_minutes": round(time_diff, 2),
                        "from_user_id": current.from_user_id,
                        "severity": "medium"
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error identifying anomalies: {str(e)}")
            return anomalies
    
    def _calculate_transfer_correlations(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Calculate correlations between different transfer metrics
        """
        try:
            # This is a simplified correlation analysis
            # In a real implementation, you might use statistical libraries
            
            completed_transfers = [t for t in transfers if t.status == CreditTransferStatus.COMPLETED]
            
            if len(completed_transfers) < 2:
                return {"correlations": "insufficient_data"}
            
            # Correlation between transfer size and time of day
            amounts = [float(t.amount) for t in completed_transfers]
            hours = [t.created_at.hour for t in completed_transfers]
            
            # Simple correlation calculation
            if len(amounts) > 1 and len(hours) > 1:
                correlation = self._calculate_simple_correlation(amounts, hours)
            else:
                correlation = 0
            
            return {
                "size_time_correlation": correlation,
                "analysis_note": "Simplified correlation analysis"
            }
            
        except Exception as e:
            logger.error(f"Error calculating correlations: {str(e)}")
            return {"correlations": "error"}
    
    def _calculate_simple_correlation(self, x: List[float], y: List[float]) -> float:
        """
        Calculate simple Pearson correlation coefficient
        """
        try:
            if len(x) != len(y) or len(x) < 2:
                return 0
            
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            sum_y2 = sum(y[i] ** 2 for i in range(n))
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
            
            if denominator == 0:
                return 0
            
            return numerator / denominator
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {str(e)}")
            return 0
    
    def _calculate_success_rate(self, transfers: List[CreditTransfer]) -> float:
        """
        Calculate success rate for transfers
        """
        try:
            if not transfers:
                return 0.0
            
            completed = len([t for t in transfers if t.status == CreditTransferStatus.COMPLETED])
            return (completed / len(transfers)) * 100
            
        except Exception as e:
            logger.error(f"Error calculating success rate: {str(e)}")
            return 0.0
    
    def _calculate_average_amount(self, transfers: List[CreditTransfer]) -> float:
        """
        Calculate average transfer amount
        """
        try:
            completed_transfers = [t for t in transfers if t.status == CreditTransferStatus.COMPLETED]
            if not completed_transfers:
                return 0.0
            
            amounts = [float(t.amount) for t in completed_transfers]
            return sum(amounts) / len(amounts)
            
        except Exception as e:
            logger.error(f"Error calculating average amount: {str(e)}")
            return 0.0
    
    def _get_most_common_recipients(self, sent_transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Get most common recipients from sent transfers
        """
        try:
            recipient_counts = defaultdict(int)
            
            for transfer in sent_transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    recipient_counts[transfer.to_user_id] += 1
            
            # Sort by count
            sorted_recipients = sorted(
                recipient_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return [
                {"user_id": uid, "transfer_count": count}
                for uid, count in sorted_recipients
            ]
            
        except Exception as e:
            logger.error(f"Error getting common recipients: {str(e)}")
            return []
    
    def _get_most_common_senders(self, received_transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Get most common senders from received transfers
        """
        try:
            sender_counts = defaultdict(int)
            
            for transfer in received_transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    sender_counts[transfer.from_user_id] += 1
            
            # Sort by count
            sorted_senders = sorted(
                sender_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return [
                {"user_id": uid, "transfer_count": count}
                for uid, count in sorted_senders
            ]
            
        except Exception as e:
            logger.error(f"Error getting common senders: {str(e)}")
            return []
    
    def _get_peak_activity_hours(self, transfers: List[CreditTransfer]) -> Dict[str, int]:
        """
        Get peak activity hours for transfers
        """
        try:
            hourly_counts = defaultdict(int)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    hour = transfer.created_at.hour
                    hourly_counts[hour] += 1
            
            # Return the 3 most active hours
            sorted_hours = sorted(
                hourly_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            return dict(sorted_hours)
            
        except Exception as e:
            logger.error(f"Error getting peak hours: {str(e)}")
            return {}
    
    def _calculate_balance_impact(
        self,
        user_id: int,
        sent_transfers: List[CreditTransfer],
        received_transfers: List[CreditTransfer]
    ) -> Dict[str, float]:
        """
        Calculate net balance impact from transfers
        """
        try:
            sent_volume = sum(
                t.amount for t in sent_transfers 
                if t.status == CreditTransferStatus.COMPLETED
            )
            
            received_volume = sum(
                t.amount for t in received_transfers
                if t.status == CreditTransferStatus.COMPLETED
            )
            
            net_impact = received_volume - sent_volume
            
            return {
                "total_sent": float(sent_volume),
                "total_received": float(received_volume),
                "net_impact": float(net_impact)
            }
            
        except Exception as e:
            logger.error(f"Error calculating balance impact: {str(e)}")
            return {"total_sent": 0, "total_received": 0, "net_impact": 0}
    
    def _get_user_transfer_permissions(
        self,
        user_id: int,
        organization_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Get user's transfer permissions
        """
        try:
            query = self.db.query(CreditTransferPermission).filter(
                or_(
                    CreditTransferPermission.from_user_id == user_id,
                    CreditTransferPermission.to_user_id == user_id
                )
            )
            
            if organization_id:
                query = query.filter(
                    or_(
                        CreditTransferPermission.from_organization_id == organization_id,
                        CreditTransferPermission.to_organization_id == organization_id,
                        CreditTransferPermission.from_organization_id.is_(None),
                        CreditTransferPermission.to_organization_id.is_(None)
                    )
                )
            
            permissions = query.filter(CreditTransferPermission.is_active == True).all()
            
            return [
                {
                    "id": p.id,
                    "permission_type": p.permission_type,
                    "from_user_id": p.from_user_id,
                    "to_user_id": p.to_user_id,
                    "max_amount": float(p.max_amount) if p.max_amount else None,
                    "created_at": p.created_at.isoformat()
                }
                for p in permissions
            ]
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return []
    
    def _generate_behavioral_insights(
        self,
        statistics: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Generate behavioral insights from statistics and patterns
        """
        insights = []
        
        try:
            overview = statistics.get("overview", {})
            volume_trend = patterns.get("volume_trend", {})
            frequency_pattern = patterns.get("frequency_pattern", {})
            
            # Volume trend insights
            if volume_trend.get("trend") == "increasing":
                insights.append("Transfer volume is showing an upward trend, indicating increased activity.")
            elif volume_trend.get("trend") == "decreasing":
                insights.append("Transfer volume is declining, which may indicate reduced usage or migration to other payment methods.")
            
            # Success rate insights
            success_rate = overview.get("success_rate", 0)
            if success_rate > 90:
                insights.append("Very high transfer success rate indicates well-optimized processes.")
            elif success_rate < 70:
                insights.append("Low transfer success rate suggests potential issues requiring investigation.")
            
            # Frequency pattern insights
            if frequency_pattern.get("pattern") == "frequent":
                insights.append("High transfer frequency suggests active user engagement or business operations.")
            elif frequency_pattern.get("pattern") == "sporadic":
                insights.append("Sporadic transfer pattern may indicate irregular business needs or manual processes.")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating behavioral insights: {str(e)}")
            return ["Error generating insights"]
    
    def _generate_efficiency_insights(
        self,
        statistics: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Generate efficiency insights
        """
        insights = []
        
        try:
            overview = statistics.get("overview", {})
            approval_pattern = patterns.get("approval_pattern", {})
            
            # Approval efficiency
            avg_approval_time = approval_pattern.get("average_approval_time_hours", 0)
            if avg_approval_time > 24:
                insights.append("Long approval times may indicate bottlenecks in the approval process.")
            elif avg_approval_time < 2:
                insights.append("Fast approval times indicate efficient approval workflows.")
            
            # Transfer size efficiency
            avg_transfer_size = overview.get("average_transfer_size", 0)
            if avg_transfer_size > 0:
                insights.append(f"Average transfer size of {avg_transfer_size} credits indicates appropriate transaction sizing.")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating efficiency insights: {str(e)}")
            return ["Error generating insights"]
    
    def _generate_transfer_recommendations(
        self,
        statistics: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable recommendations
        """
        recommendations = []
        
        try:
            overview = statistics.get("overview", {})
            success_rate = overview.get("success_rate", 0)
            
            # Success rate recommendations
            if success_rate < 80:
                recommendations.append("Consider implementing automatic transfer validation to improve success rates.")
            
            # Volume recommendations
            total_transfers = overview.get("total_transfers", 0)
            if total_transfers > 100:
                recommendations.append("High volume detected. Consider implementing batch processing for improved efficiency.")
            
            # Frequency recommendations
            frequency_pattern = patterns.get("frequency_pattern", {})
            if frequency_pattern.get("pattern") == "sporadic":
                recommendations.append("Consider setting up scheduled transfers for regular payment patterns.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    def _assess_transfer_risks(
        self,
        statistics: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess transfer-related risks
        """
        try:
            risks = []
            risk_level = "low"
            
            overview = statistics.get("overview", {})
            success_rate = overview.get("success_rate", 100)
            anomalies = patterns.get("anomalies", [])
            
            # Failure rate risk
            failure_rate = 100 - success_rate
            if failure_rate > 20:
                risks.append("High failure rate indicates potential technical or process issues.")
                risk_level = "high"
            elif failure_rate > 10:
                risks.append("Moderate failure rate may indicate occasional issues.")
                risk_level = "medium"
            
            # Anomaly risk
            if len(anomalies) > 5:
                risks.append("Multiple anomalous patterns detected, indicating potential irregular behavior.")
                risk_level = max(risk_level, "medium")
            
            # Volume risk
            total_volume = overview.get("total_volume", 0)
            if total_volume > 100000:  # High volume threshold
                risks.append("High transaction volume requires enhanced monitoring and controls.")
                risk_level = max(risk_level, "medium")
            
            return {
                "risk_level": risk_level,
                "risk_factors": risks,
                "risk_score": self._calculate_overall_risk_score(failure_rate, len(anomalies), total_volume)
            }
            
        except Exception as e:
            logger.error(f"Error assessing risks: {str(e)}")
            return {"risk_level": "unknown", "risk_factors": [], "risk_score": 0}
    
    def _calculate_overall_risk_score(
        self,
        failure_rate: float,
        anomaly_count: int,
        total_volume: float
    ) -> float:
        """
        Calculate overall risk score (0-100)
        """
        try:
            # Simple risk scoring algorithm
            score = 0
            
            # Failure rate contribution (0-40 points)
            score += min(failure_rate * 2, 40)
            
            # Anomaly contribution (0-30 points)
            score += min(anomaly_count * 5, 30)
            
            # Volume contribution (0-30 points)
            volume_score = min(total_volume / 10000, 30)  # 10k credits = 30 points
            score += volume_score
            
            return min(score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0
    
    def _suggest_optimizations(
        self,
        statistics: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> List[str]:
        """
        Suggest system optimizations
        """
        suggestions = []
        
        try:
            # Based on patterns, suggest optimizations
            frequency_pattern = patterns.get("frequency_pattern", {})
            
            if frequency_pattern.get("pattern") == "frequent":
                suggestions.append("Implement automated scheduling for frequent transfers to improve user experience.")
            
            volume_trend = patterns.get("volume_trend", {})
            if volume_trend.get("trend") == "increasing":
                suggestions.append("Consider implementing pagination and caching for better performance with growing transfer volumes.")
            
            approval_pattern = patterns.get("approval_pattern", {})
            avg_approval_time = approval_pattern.get("average_approval_time_hours", 0)
            if avg_approval_time > 12:
                suggestions.append("Implement notification reminders for pending approvals to reduce approval times.")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting optimizations: {str(e)}")
            return ["Error generating suggestions"]
    
    def _calculate_data_quality_score(
        self,
        statistics: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> float:
        """
        Calculate data quality score for analytics
        """
        try:
            score = 100.0
            
            overview = statistics.get("overview", {})
            total_transfers = overview.get("total_transfers", 0)
            
            # Reduce score for insufficient data
            if total_transfers < 10:
                score -= 30
            elif total_transfers < 50:
                score -= 15
            
            # Reduce score for incomplete patterns
            if not patterns.get("volume_trend", {}).get("trend"):
                score -= 20
            
            if not patterns.get("frequency_pattern", {}).get("pattern"):
                score -= 20
            
            return max(score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating data quality score: {str(e)}")
            return 0
    
    def _forecast_transfer_volume(
        self,
        transfers: List[CreditTransfer],
        forecast_days: int
    ) -> Dict[str, Any]:
        """
        Simple volume forecasting based on historical patterns
        """
        try:
            if len(transfers) < 7:
                return {"forecast": "insufficient_data"}
            
            # Group by day and calculate daily volumes
            daily_volumes = defaultdict(Decimal)
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    date_key = transfer.created_at.date()
                    daily_volumes[date_key] += transfer.amount
            
            if len(daily_volumes) < 3:
                return {"forecast": "insufficient_data"}
            
            volumes = list(daily_volumes.values())
            avg_daily_volume = statistics.mean(volumes)
            
            # Simple forecast: average daily volume * forecast days
            forecasted_volume = avg_daily_volume * forecast_days
            
            return {
                "forecasted_total_volume": float(forecasted_volume),
                "average_daily_volume": float(avg_daily_volume),
                "forecast_days": forecast_days,
                "confidence": "medium"
            }
            
        except Exception as e:
            logger.error(f"Error forecasting volume: {str(e)}")
            return {"forecast": "error"}
    
    def _forecast_transfer_frequency(
        self,
        transfers: List[CreditTransfer],
        forecast_days: int
    ) -> Dict[str, Any]:
        """
        Simple frequency forecasting
        """
        try:
            if len(transfers) < 7:
                return {"forecast": "insufficient_data"}
            
            # Calculate daily transfer counts
            daily_counts = defaultdict(int)
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    date_key = transfer.created_at.date()
                    daily_counts[date_key] += 1
            
            if len(daily_counts) < 3:
                return {"forecast": "insufficient_data"}
            
            counts = list(daily_counts.values())
            avg_daily_frequency = statistics.mean(counts)
            
            forecasted_frequency = avg_daily_frequency * forecast_days
            
            return {
                "forecasted_total_transfers": int(forecasted_frequency),
                "average_daily_frequency": round(avg_daily_frequency, 2),
                "forecast_days": forecast_days,
                "confidence": "medium"
            }
            
        except Exception as e:
            logger.error(f"Error forecasting frequency: {str(e)}")
            return {"forecast": "error"}
    
    def _forecast_transfer_size(
        self,
        transfers: List[CreditTransfer],
        forecast_days: int
    ) -> Dict[str, Any]:
        """
        Simple transfer size forecasting
        """
        try:
            completed_transfers = [t for t in transfers if t.status == CreditTransferStatus.COMPLETED]
            
            if len(completed_transfers) < 10:
                return {"forecast": "insufficient_data"}
            
            amounts = [t.amount for t in completed_transfers]
            avg_amount = statistics.mean(amounts)
            median_amount = statistics.median(amounts)
            
            return {
                "forecasted_average_amount": float(avg_amount),
                "forecasted_median_amount": float(median_amount),
                "forecast_basis": "historical_average",
                "sample_size": len(completed_transfers),
                "confidence": "medium"
            }
            
        except Exception as e:
            logger.error(f"Error forecasting transfer size: {str(e)}")
            return {"forecast": "error"}
    
    def _calculate_prediction_confidence(self, transfers: List[CreditTransfer]) -> float:
        """
        Calculate confidence score for predictions
        """
        try:
            if len(transfers) < 7:
                return 0.3  # Low confidence
            elif len(transfers) < 30:
                return 0.6  # Medium confidence
            else:
                return 0.8  # High confidence
                
        except Exception as e:
            logger.error(f"Error calculating prediction confidence: {str(e)}")
            return 0.0
    
    def _identify_seasonal_patterns(self, transfers: List[CreditTransfer]) -> Dict[str, Any]:
        """
        Identify seasonal patterns in transfers
        """
        try:
            if len(transfers) < 30:  # Need sufficient data
                return {"pattern": "insufficient_data"}
            
            # Group transfers by day of week
            dow_volumes = defaultdict(Decimal)
            dow_counts = defaultdict(int)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    dow = transfer.created_at.weekday()  # 0 = Monday
                    dow_volumes[dow] += transfer.amount
                    dow_counts[dow] += 1
            
            # Find peak day
            peak_dow = max(dow_counts.keys(), key=lambda d: dow_counts[d]) if dow_counts else 0
            dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            return {
                "peak_day": dow_names[peak_dow],
                "day_of_week_volumes": {dow_names[d]: float(v) for d, v in dow_volumes.items()},
                "day_of_week_counts": {dow_names[d]: v for d, v in dow_counts.items()},
                "pattern": "weekly_pattern_detected" if len(set(dow_counts.values())) > 1 else "no_pattern"
            }
            
        except Exception as e:
            logger.error(f"Error identifying seasonal patterns: {str(e)}")
            return {"pattern": "error"}
    
    def _detect_volume_spikes(self, transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Detect unusual volume spikes
        """
        spikes = []
        
        try:
            # Group by day
            daily_volumes = defaultdict(Decimal)
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    date_key = transfer.created_at.date()
                    daily_volumes[date_key] += transfer.amount
            
            if len(daily_volumes) < 7:
                return spikes
            
            volumes = list(daily_volumes.values())
            avg_volume = statistics.mean(volumes)
            std_dev = statistics.stdev(volumes) if len(volumes) > 1 else 0
            
            spike_threshold = avg_volume + (2 * std_dev)  # 2 standard deviations
            
            for date, volume in daily_volumes.items():
                if volume > spike_threshold:
                    spikes.append({
                        "type": "volume_spike",
                        "date": str(date),
                        "volume": float(volume),
                        "threshold": float(spike_threshold),
                        "severity": "high" if volume > spike_threshold * 1.5 else "medium"
                    })
            
            return spikes
            
        except Exception as e:
            logger.error(f"Error detecting volume spikes: {str(e)}")
            return spikes
    
    def _detect_timing_anomalies(self, transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Detect unusual timing patterns
        """
        anomalies = []
        
        try:
            # Check for transfers at unusual hours
            off_hours_transfers = []
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    hour = transfer.created_at.hour
                    if hour < 6 or hour > 22:  # Outside 6 AM - 10 PM
                        off_hours_transfers.append(transfer)
            
            if len(off_hours_transfers) > len(transfers) * 0.3:  # More than 30% off-hours
                anomalies.append({
                    "type": "unusual_timing",
                    "description": "High percentage of off-hours transfers detected",
                    "off_hours_count": len(off_hours_transfers),
                    "total_count": len(transfers),
                    "percentage": round(len(off_hours_transfers) / len(transfers) * 100, 2),
                    "severity": "high" if len(off_hours_transfers) > len(transfers) * 0.5 else "medium"
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting timing anomalies: {str(e)}")
            return anomalies
    
    def _detect_circular_transfers(self, transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Detect potential circular transfer patterns (potential fraud)
        """
        circular_patterns = []
        
        try:
            # Create a mapping of transfer pairs
            transfer_pairs = defaultdict(list)
            
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    pair = (transfer.from_user_id, transfer.to_user_id)
                    transfer_pairs[pair].append(transfer)
            
            # Check for reciprocal transfers
            for pair, pair_transfers in transfer_pairs.items():
                reverse_pair = (pair[1], pair[0])
                reverse_transfers = transfer_pairs.get(reverse_pair, [])
                
                # If there are transfers in both directions
                if reverse_transfers and len(pair_transfers) > 0:
                    # This could indicate a circular pattern
                    total_amount = sum(t.amount for t in pair_transfers) + sum(t.amount for t in reverse_transfers)
                    
                    circular_patterns.append({
                        "type": "circular_transfer",
                        "user_pair": list(pair),
                        "total_amount": float(total_amount),
                        "transfer_count": len(pair_transfers) + len(reverse_transfers),
                        "severity": "medium"
                    })
            
            return circular_patterns
            
        except Exception as e:
            logger.error(f"Error detecting circular transfers: {str(e)}")
            return circular_patterns
    
    def _detect_recipient_anomalies(self, transfers: List[CreditTransfer]) -> List[Dict[str, Any]]:
        """
        Detect unusual recipient patterns
        """
        anomalies = []
        
        try:
            # Check for new recipients
            recipient_first_time = defaultdict(list)
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    recipient_first_time[transfer.to_user_id].append(transfer.created_at)
            
            # Find users with many new recipients
            user_new_recipients = defaultdict(int)
            for transfer in transfers:
                if transfer.status == CreditTransferStatus.COMPLETED:
                    # Check if this is a first-time recipient
                    first_times = recipient_first_time[transfer.to_user_id]
                    if transfer.created_at == min(first_times):
                        user_new_recipients[transfer.from_user_id] += 1
            
            # Flag users with unusual numbers of new recipients
            for user_id, new_recipient_count in user_new_recipients.items():
                if new_recipient_count > 5:  # Threshold for "many new recipients"
                    anomalies.append({
                        "type": "many_new_recipients",
                        "user_id": user_id,
                        "new_recipient_count": new_recipient_count,
                        "severity": "medium" if new_recipient_count < 10 else "high"
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting recipient anomalies: {str(e)}")
            return anomalies
    
    def _calculate_fraud_risk_score(self, indicator: Dict[str, Any]) -> float:
        """
        Calculate fraud risk score for an indicator
        """
        try:
            base_score = 0
            indicator_type = indicator.get("type", "")
            
            if indicator_type == "volume_spike":
                base_score = 70
            elif indicator_type == "unusual_timing":
                base_score = 60
            elif indicator_type == "circular_transfer":
                base_score = 80
            elif indicator_type == "many_new_recipients":
                base_score = 65
            else:
                base_score = 50
            
            # Adjust based on severity
            severity = indicator.get("severity", "medium")
            if severity == "high":
                base_score += 20
            elif severity == "low":
                base_score -= 10
            
            return min(base_score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating fraud risk score: {str(e)}")
            return 50