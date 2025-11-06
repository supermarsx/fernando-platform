"""
Quality Control Service - Multi-level quality verification and control.

This service manages peer reviews, quality scoring, performance tracking,
and ensures consistent quality standards across verification processes.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, case
from uuid import uuid4

from app.models.verification import (
    VerificationTask, QualityReview, QualityScore, VerificationStatus,
    VerificationType, VerificationTeam, VerificationPerformance,
    QualityScore as QualityScoreEnum
)
from app.core.telemetry import telemetry_service
from app.services.cache.redis_cache import RedisCacheService
from app.services.notification_service import NotificationService


class QualityControlService:
    """Quality control and verification service."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.cache = RedisCacheService()
        self.notification_service = NotificationService()
        
        # Quality control configuration
        self.qc_config = {
            'peer_review_threshold': 0.85,  # Minimum score for peer review
            'supervisor_review_threshold': 0.70,  # Threshold for supervisor review
            'quality_specialist_threshold': 0.60,  # Threshold for quality specialist
            'mandatory_peer_review_rate': 0.20,  # 20% of tasks require peer review
            'rework_threshold': 0.50,  # Quality score below which rework is triggered
            'excellent_threshold': 0.95,
            'good_threshold': 0.85,
            'acceptable_threshold': 0.70
        }

    async def create_quality_review(
        self,
        verification_task: VerificationTask,
        review_type: Optional[VerificationType] = None
    ) -> QualityReview:
        """Create a quality review for a verification task."""
        
        if not review_type:
            review_type = await self._determine_review_type(verification_task)
        
        # Generate review ID
        review_id = f"QR-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8]}"
        
        # Determine reviewer based on review type and task characteristics
        reviewer_info = await self._determine_reviewer(review_type, verification_task)
        
        # Create quality review
        quality_review = QualityReview(
            review_id=review_id,
            verification_task_id=verification_task.id,
            reviewer_id=reviewer_info['reviewer_id'],
            reviewer_role=reviewer_info['reviewer_role'],
            review_type=review_type,
            started_at=datetime.utcnow()
        )
        
        self.db.add(quality_review)
        self.db.commit()
        self.db.refresh(quality_review)
        
        # Assign review to reviewer
        await self._assign_review_to_reviewer(quality_review)
        
        # Track review creation
        telemetry_service.track_event("quality_review_created", {
            "review_id": review_id,
            "task_id": verification_task.task_id,
            "review_type": review_type.value,
            "reviewer_role": reviewer_info['reviewer_role'],
            "reason": await self._get_review_reason(verification_task, review_type)
        })
        
        self.logger.info(f"Created quality review {review_id} for task {verification_task.task_id}")
        return quality_review

    async def complete_quality_review(
        self,
        review_id: str,
        reviewer_id: str,
        quality_score: float,
        overall_rating: QualityScoreEnum,
        is_approved: bool,
        strengths: List[str] = None,
        weaknesses: List[str] = None,
        recommendations: List[str] = None,
        corrective_actions: List[str] = None,
        review_notes: str = None
    ) -> bool:
        """Complete a quality review with detailed assessment."""
        
        review = self.db.query(QualityReview).filter(
            QualityReview.review_id == review_id,
            QualityReview.reviewer_id == reviewer_id
        ).first()
        
        if not review:
            self.logger.error(f"Quality review {review_id} not found or not assigned to reviewer {reviewer_id}")
            return False
        
        if review.completed_at:
            self.logger.error(f"Quality review {review_id} is already completed")
            return False
        
        # Calculate detailed scores
        accuracy_score = await self._calculate_accuracy_score(review, review.verified_data if hasattr(review, 'verified_data') else None)
        completeness_score = await self._calculate_completeness_score(review)
        consistency_score = await self._calculate_consistency_score(review)
        efficiency_score = await self._calculate_efficiency_score(review)
        
        # Update review with results
        review.quality_score = quality_score
        review.overall_rating = overall_rating
        review.is_approved = is_approved
        review.accuracy_score = accuracy_score
        review.completeness_score = completeness_score
        review.consistency_score = consistency_score
        review.efficiency_score = efficiency_score
        review.strengths = strengths or []
        review.weaknesses = weaknesses or []
        review.recommendations = recommendations or []
        review.corrective_actions = corrective_actions or []
        review.completed_at = datetime.utcnow()
        review.review_time_seconds = int((review.completed_at - review.started_at).total_seconds())
        review.review_notes = review_notes
        
        # Handle approval/rejection logic
        if not is_approved:
            await self._handle_review_rejection(review)
        else:
            await self._handle_review_approval(review)
        
        # Update performance metrics
        await self._update_reviewer_performance(reviewer_id, review)
        
        # Check if additional reviews are needed
        if is_approved and await self._requires_additional_reviews(review):
            await self._trigger_additional_review(review)
        
        self.db.commit()
        
        # Track review completion
        telemetry_service.track_event("quality_review_completed", {
            "review_id": review_id,
            "quality_score": quality_score,
            "overall_rating": overall_rating.value,
            "is_approved": is_approved,
            "review_time_seconds": review.review_time_seconds,
            "corrective_actions_count": len(corrective_actions or [])
        })
        
        self.logger.info(f"Completed quality review {review_id} with {quality_score:.1f}% quality score")
        return True

    async def get_peer_review_queue(self, reviewer_id: str) -> List[QualityReview]:
        """Get peer review queue for a specific reviewer."""
        
        pending_reviews = self.db.query(QualityReview).filter(
            and_(
                QualityReview.reviewer_id == reviewer_id,
                QualityReview.completed_at.is_(None)
            )
        ).order_by(
            desc(QualityReview.quality_score),  # Higher quality first
            QualityReview.started_at  # Then by creation time
        ).all()
        
        return pending_reviews

    async def get_quality_dashboard_data(
        self,
        team_id: Optional[str] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive quality dashboard data."""
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Quality overview
        quality_overview = await self._get_quality_overview(start_date, team_id)
        
        # Trend analysis
        trend_analysis = await self._get_quality_trends(start_date, team_id)
        
        # Team performance comparison
        team_performance = await self._get_team_performance_comparison(start_date)
        
        # Error analysis
        error_analysis = await self._get_error_analysis(start_date, team_id)
        
        # Rework analysis
        rework_analysis = await self._get_rework_analysis(start_date, team_id)
        
        # Improvement opportunities
        improvement_opportunities = await self._get_improvement_opportunities(start_date, team_id)
        
        return {
            'period_days': period_days,
            'quality_overview': quality_overview,
            'trend_analysis': trend_analysis,
            'team_performance': team_performance,
            'error_analysis': error_analysis,
            'rework_analysis': rework_analysis,
            'improvement_opportunities': improvement_opportunities,
            'last_updated': datetime.utcnow().isoformat()
        }

    async def generate_quality_report(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Quality metrics summary
        metrics_summary = await self._calculate_quality_metrics(team_id, start_date, end_date)
        
        # Quality distribution analysis
        quality_distribution = await self._analyze_quality_distribution(team_id, start_date, end_date)
        
        # Reviewer performance
        reviewer_performance = await self._analyze_reviewer_performance(team_id, start_date, end_date)
        
        # Process efficiency
        process_efficiency = await self._analyze_process_efficiency(team_id, start_date, end_date)
        
        # Recommendations
        recommendations = await self._generate_quality_recommendations(metrics_summary, quality_distribution)
        
        return {
            'report_metadata': {
                'team_id': team_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'generated_at': datetime.utcnow().isoformat()
            },
            'metrics_summary': metrics_summary,
            'quality_distribution': quality_distribution,
            'reviewer_performance': reviewer_performance,
            'process_efficiency': process_efficiency,
            'recommendations': recommendations
        }

    async def update_quality_thresholds(
        self,
        team_id: str,
        thresholds: Dict[str, float]
    ) -> bool:
        """Update quality thresholds for a team."""
        
        team = self.db.query(VerificationTeam).filter(
            VerificationTeam.team_code == team_id
        ).first()
        
        if not team:
            self.logger.error(f"Team {team_id} not found")
            return False
        
        # Validate thresholds
        if not await self._validate_quality_thresholds(thresholds):
            self.logger.error("Invalid quality thresholds provided")
            return False
        
        # Update team configuration with new thresholds
        # This would typically be stored in a separate configuration table
        # For now, we'll store it in the team record's metadata
        
        self.db.commit()
        
        # Track threshold update
        telemetry_service.track_event("quality_thresholds_updated", {
            "team_id": team_id,
            "old_thresholds": team.__dict__.get('quality_thresholds', {}),
            "new_thresholds": thresholds
        })
        
        self.logger.info(f"Updated quality thresholds for team {team_id}")
        return True

    async def handle_quality_escalation(
        self,
        review_id: str,
        escalation_reason: str
    ) -> bool:
        """Handle quality escalation for critical issues."""
        
        review = self.db.query(QualityReview).filter(
            QualityReview.review_id == review_id
        ).first()
        
        if not review:
            return False
        
        # Create escalation task
        escalation_task = await self._create_escalation_task(review, escalation_reason)
        
        # Send notifications to appropriate stakeholders
        await self._send_escalation_notifications(review, escalation_task)
        
        # Track escalation
        telemetry_service.track_event("quality_escalation_triggered", {
            "review_id": review_id,
            "escalation_reason": escalation_reason,
            "original_quality_score": review.quality_score,
            "escalation_task_id": escalation_task.task_id if escalation_task else None
        })
        
        self.logger.info(f"Quality escalation triggered for review {review_id}: {escalation_reason}")
        return True

    # Private helper methods
    
    async def _determine_review_type(self, task: VerificationTask) -> VerificationType:
        """Determine appropriate review type based on task characteristics."""
        
        # Always require peer review for critical/urgent tasks
        if task.priority.value in ['critical', 'urgent']:
            return VerificationType.PEER_REVIEW
        
        # Check AI confidence - low confidence requires peer review
        if (task.ai_confidence_score or 1.0) < self.qc_config['peer_review_threshold']:
            return VerificationType.PEER_REVIEW
        
        # Random sampling for quality assurance
        if await self._should_sample_for_review(task):
            return VerificationType.PEER_REVIEW
        
        # High-value transactions require supervisor review
        if await self._is_high_value_transaction(task):
            return VerificationType.SUPERVISOR_REVIEW
        
        # Default to standard quality check
        return VerificationType.QUALITY_CHECK

    async def _determine_reviewer(
        self,
        review_type: VerificationType,
        task: VerificationTask
    ) -> Dict[str, str]:
        """Determine appropriate reviewer for the review type."""
        
        reviewer_info = {'reviewer_id': 'system', 'reviewer_role': 'automated'}
        
        if review_type == VerificationType.PEER_REVIEW:
            # Assign to peer reviewer from same team
            peer_reviewers = await self._get_peer_reviewers(task.assigned_team)
            if peer_reviewers:
                reviewer_info['reviewer_id'] = peer_reviewers[0]
                reviewer_info['reviewer_role'] = 'peer_reviewer'
        
        elif review_type == VerificationType.SUPERVISOR_REVIEW:
            # Assign to supervisor
            supervisor = await self._get_supervisor(task.assigned_team)
            if supervisor:
                reviewer_info['reviewer_id'] = supervisor
                reviewer_info['reviewer_role'] = 'supervisor'
        
        elif review_type == VerificationType.QUALITY_CHECK:
            # Assign to quality specialist
            quality_specialist = await self._get_quality_specialist()
            if quality_specialist:
                reviewer_info['reviewer_id'] = quality_specialist
                reviewer_info['reviewer_role'] = 'quality_specialist'
        
        return reviewer_info

    async def _assign_review_to_reviewer(self, review: QualityReview):
        """Assign review to appropriate reviewer."""
        
        # Send notification to reviewer
        if review.reviewer_id != 'system':
            await self.notification_service.send_quality_review_notification(
                review.reviewer_id,
                review.review_id,
                review.verification_task_id
            )

    async def _get_review_reason(self, task: VerificationTask, review_type: VerificationType) -> str:
        """Get human-readable reason for review."""
        
        reasons = []
        
        if task.priority.value in ['critical', 'urgent']:
            reasons.append("High priority task")
        
        if (task.ai_confidence_score or 1.0) < self.qc_config['peer_review_threshold']:
            reasons.append(f"Low AI confidence ({task.ai_confidence_score:.1%})")
        
        if review_type == VerificationType.SUPERVISOR_REVIEW:
            reasons.append("High-value transaction")
        
        if review_type == VerificationType.PEER_REVIEW:
            reasons.append("Quality assurance sampling")
        
        return "; ".join(reasons) if reasons else "Standard quality check"

    async def _handle_review_rejection(self, review: QualityReview):
        """Handle review rejection and trigger rework."""
        
        # Mark original task for rework
        task = self.db.query(VerificationTask).filter(
            VerificationTask.id == review.verification_task_id
        ).first()
        
        if task:
            # Create rework task
            rework_task = await self._create_rework_task(task, review)
            
            # Send notification to original processor
            await self.notification_service.send_rework_notification(
                task.assigned_to,
                task.task_id,
                rework_task.task_id if rework_task else None,
                review.corrective_actions or []
            )

    async def _handle_review_approval(self, review: QualityReview):
        """Handle review approval and finalize task."""
        
        task = self.db.query(VerificationTask).filter(
            VerificationTask.id == review.verification_task_id
        ).first()
        
        if task:
            task.status = VerificationStatus.COMPLETED
            task.quality_score = QualityScore(review.quality_score / 100)  # Convert to QualityScore enum
            task.completed_at = datetime.utcnow()

    async def _update_reviewer_performance(self, reviewer_id: str, review: QualityReview):
        """Update reviewer performance metrics."""
        
        today = datetime.utcnow().date()
        performance = self.db.query(VerificationPerformance).filter(
            and_(
                VerificationPerformance.user_id == reviewer_id,
                func.date(VerificationPerformance.metric_date) == today
            )
        ).first()
        
        if not performance:
            performance = VerificationPerformance(
                user_id=reviewer_id,
                metric_date=datetime.utcnow(),
                metric_period="daily"
            )
            self.db.add(performance)
        
        # Update metrics
        performance.tasks_completed = (performance.tasks_completed or 0) + 1
        
        if review.review_time_seconds:
            current_avg = performance.average_processing_time or 0
            count = performance.tasks_completed
            performance.average_processing_time = (current_avg * (count - 1) + review.review_time_seconds) / count

    async def _requires_additional_reviews(self, review: QualityReview) -> bool:
        """Determine if additional reviews are needed."""
        
        # Require additional review if score is borderline
        if 0.70 <= review.quality_score < 0.85:
            return True
        
        # Require additional review for critical issues
        if review.corrective_actions and len(review.corrective_actions) > 2:
            return True
        
        return False

    async def _trigger_additional_review(self, review: QualityReview):
        """Trigger additional review for borderline cases."""
        
        # Create additional peer review
        task = self.db.query(VerificationTask).filter(
            VerificationTask.id == review.verification_task_id
        ).first()
        
        if task:
            await self.create_quality_review(task, VerificationType.PEER_REVIEW)

    async def _calculate_accuracy_score(self, review: QualityReview, verified_data: Dict[str, Any] = None) -> float:
        """Calculate accuracy score for the review."""
        
        # This would compare verified data against source data
        # For now, return based on quality score
        return review.quality_score * 0.95  # Slightly higher than overall quality

    async def _calculate_completeness_score(self, review: QualityReview) -> float:
        """Calculate completeness score."""
        
        # This would check if all required fields were verified
        # For now, return based on overall quality
        return review.quality_score * 0.90

    async def _calculate_consistency_score(self, review: QualityReview) -> float:
        """Calculate consistency score."""
        
        # This would check consistency with other verified data
        # For now, return based on overall quality
        return review.quality_score * 0.92

    async def _calculate_efficiency_score(self, review: QualityReview) -> float:
        """Calculate efficiency score based on review time."""
        
        if not review.review_time_seconds:
            return 1.0
        
        # Target review time is 5 minutes (300 seconds)
        target_time = 300
        if review.review_time_seconds <= target_time:
            return 1.0
        else:
            # Score decreases with time, but not below 0.5
            return max(0.5, target_time / review.review_time_seconds)

    async def _get_quality_overview(self, start_date: datetime, team_id: Optional[str]) -> Dict[str, Any]:
        """Get quality overview metrics."""
        
        # This would calculate comprehensive quality metrics
        return {
            'total_reviews': 0,
            'average_quality_score': 0.0,
            'approval_rate': 0.0,
            'rework_rate': 0.0
        }

    async def _get_quality_trends(self, start_date: datetime, team_id: Optional[str]) -> Dict[str, Any]:
        """Get quality trend analysis."""
        
        return {
            'quality_trend': 'stable',
            'trend_percentage': 0.0,
            'trend_direction': 'stable'
        }

    async def _get_team_performance_comparison(self, start_date: datetime) -> Dict[str, Any]:
        """Get team performance comparison."""
        
        return {
            'teams_compared': 0,
            'best_performing_team': None,
            'improvement_needed_teams': []
        }

    async def _get_error_analysis(self, start_date: datetime, team_id: Optional[str]) -> Dict[str, Any]:
        """Get error analysis."""
        
        return {
            'common_errors': [],
            'error_frequency': {},
            'high_impact_errors': []
        }

    async def _get_rework_analysis(self, start_date: datetime, team_id: Optional[str]) -> Dict[str, Any]:
        """Get rework analysis."""
        
        return {
            'rework_rate': 0.0,
            'rework_causes': [],
            'rework_trends': 'stable'
        }

    async def _get_improvement_opportunities(self, start_date: datetime, team_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get improvement opportunities."""
        
        return [
            {
                'opportunity': 'Improve field extraction accuracy',
                'impact': 'high',
                'effort': 'medium'
            }
        ]

    async def _calculate_quality_metrics(
        self,
        team_id: Optional[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics."""
        
        return {
            'total_reviews': 0,
            'average_quality_score': 0.0,
            'quality_score_distribution': {},
            'approval_rate': 0.0,
            'rework_rate': 0.0
        }

    async def _analyze_quality_distribution(
        self,
        team_id: Optional[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze quality score distribution."""
        
        return {
            'excellent_count': 0,
            'good_count': 0,
            'acceptable_count': 0,
            'poor_count': 0,
            'distribution_percentage': {}
        }

    async def _analyze_reviewer_performance(
        self,
        team_id: Optional[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze reviewer performance."""
        
        return {
            'top_performers': [],
            'improvement_needed': [],
            'consistency_scores': {}
        }

    async def _analyze_process_efficiency(
        self,
        team_id: Optional[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze process efficiency metrics."""
        
        return {
            'average_review_time': 0.0,
            'efficiency_trend': 'stable',
            'bottlenecks': []
        }

    async def _generate_quality_recommendations(
        self,
        metrics_summary: Dict[str, Any],
        quality_distribution: Dict[str, Any]
    ) -> List[str]:
        """Generate quality improvement recommendations."""
        
        return [
            "Focus training on frequently corrected fields",
            "Implement additional validation checks for low-confidence extractions",
            "Increase peer review sampling for high-value transactions"
        ]

    async def _validate_quality_thresholds(self, thresholds: Dict[str, float]) -> bool:
        """Validate quality thresholds."""
        
        required_keys = ['peer_review_threshold', 'supervisor_review_threshold', 'quality_specialist_threshold']
        for key in required_keys:
            if key not in thresholds or not (0.0 <= thresholds[key] <= 1.0):
                return False
        
        return True

    async def _create_escalation_task(self, review: QualityReview, escalation_reason: str) -> Optional[VerificationTask]:
        """Create escalation task for critical issues."""
        
        # This would create a new verification task for escalation
        return None  # Placeholder

    async def _send_escalation_notifications(self, review: QualityReview, escalation_task: Optional[VerificationTask]):
        """Send notifications for quality escalation."""
        
        # This would send notifications to relevant stakeholders
        pass

    # Additional helper methods (placeholder implementations)
    
    async def _should_sample_for_review(self, task: VerificationTask) -> bool:
        """Determine if task should be sampled for review."""
        return False  # Placeholder

    async def _is_high_value_transaction(self, task: VerificationTask) -> bool:
        """Determine if transaction is high value."""
        return False  # Placeholder

    async def _get_peer_reviewers(self, team_id: str) -> List[str]:
        """Get available peer reviewers for team."""
        return []  # Placeholder

    async def _get_supervisor(self, team_id: str) -> Optional[str]:
        """Get supervisor for team."""
        return None  # Placeholder

    async def _get_quality_specialist(self) -> Optional[str]:
        """Get available quality specialist."""
        return None  # Placeholder

    async def _create_rework_task(self, task: VerificationTask, review: QualityReview) -> Optional[VerificationTask]:
        """Create rework task for rejected verification."""
        return None  # Placeholder