"""
Verification Service - Core verification workflow management.

This service handles document verification workflow management, queue management,
task assignment, and integration with AI assistance and quality control systems.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, case
from uuid import uuid4

from app.models.verification import (
    VerificationTask, VerificationStatus, PriorityLevel, VerificationType,
    VerificationTeam, VerificationPerformance, VerificationWorkflow,
    QualityReview, QualityScore
)
from app.services.verification.ai_assistance import AIAssistanceService
from app.services.verification.quality_control import QualityControlService
from app.services.cache.redis_cache import RedisCacheService
from app.core.telemetry import telemetry_service
from app.services.notification_service import NotificationService


class VerificationService:
    """Main verification workflow service."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.ai_service = AIAssistanceService(db)
        self.quality_service = QualityControlService(db)
        self.cache = RedisCacheService()
        self.notification_service = NotificationService()
        
        # Verification configuration
        self.config = {
            'default_sla_hours': 24,
            'urgent_sla_hours': 4,
            'escalation_timeout_hours': 2,
            'max_concurrent_tasks_per_user': 10,
            'batch_processing_threshold': 5,
            'quality_threshold_excellent': 0.95,
            'quality_threshold_good': 0.85,
            'quality_threshold_acceptable': 0.70
        }

    async def create_verification_task(
        self,
        document_id: str,
        extraction_id: str,
        task_type: VerificationType = VerificationType.INITIAL,
        priority: PriorityLevel = PriorityLevel.NORMAL,
        assigned_team: Optional[str] = None,
        created_by: str = "system"
    ) -> VerificationTask:
        """Create a new verification task."""
        
        # Generate unique task ID
        task_id = f"VT-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8]}"
        
        # Calculate due date based on priority
        sla_hours = self.config['urgent_sla_hours'] if priority == PriorityLevel.URGENT else self.config['default_sla_hours']
        due_date = datetime.utcnow() + timedelta(hours=sla_hours)
        
        # Get AI analysis for the extraction
        ai_analysis = await self.ai_service.analyze_extraction(extraction_id)
        
        # Create the task
        task = VerificationTask(
            task_id=task_id,
            document_id=document_id,
            extraction_id=extraction_id,
            task_type=task_type,
            priority=priority,
            due_date=due_date,
            ai_confidence_score=ai_analysis.get('overall_confidence', 0.0),
            ai_suggestions=ai_analysis.get('field_suggestions', {}),
            ai_detected_anomalies=ai_analysis.get('anomaly_alerts', []),
            created_by=created_by
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        # Add to appropriate queue
        await self._add_to_queue(task, assigned_team)
        
        # Track task creation
        telemetry_service.track_event("verification_task_created", {
            "task_id": task_id,
            "task_type": task_type.value,
            "priority": priority.value,
            "ai_confidence": ai_analysis.get('overall_confidence', 0.0),
            "estimated_processing_time": await self._estimate_processing_time(task)
        })
        
        self.logger.info(f"Created verification task {task_id} for document {document_id}")
        return task

    async def assign_task(
        self,
        task_id: str,
        user_id: str,
        auto_assign: bool = False
    ) -> bool:
        """Assign a verification task to a user."""
        
        task = self.db.query(VerificationTask).filter(
            VerificationTask.task_id == task_id
        ).first()
        
        if not task:
            self.logger.error(f"Task {task_id} not found")
            return False
        
        if task.status != VerificationStatus.PENDING:
            self.logger.error(f"Task {task_id} is not pending (status: {task.status})")
            return False
        
        # Check user capacity
        user_task_count = await self._get_user_active_task_count(user_id)
        if user_task_count >= self.config['max_concurrent_tasks_per_user']:
            self.logger.error(f"User {user_id} has reached maximum task capacity")
            return False
        
        # Assign the task
        task.assigned_to = user_id
        task.assigned_at = datetime.utcnow()
        task.status = VerificationStatus.IN_PROGRESS
        
        # Update verification team assignment if needed
        if auto_assign:
            assigned_team = await self._auto_assign_team(task)
            task.assigned_team = assigned_team
        
        self.db.commit()
        
        # Send notification
        await self.notification_service.send_verification_assignment_notification(
            user_id, task_id, task.document_id
        )
        
        # Track assignment
        telemetry_service.track_event("verification_task_assigned", {
            "task_id": task_id,
            "assigned_to": user_id,
            "assigned_team": task.assigned_team,
            "auto_assigned": auto_assign
        })
        
        self.logger.info(f"Assigned task {task_id} to user {user_id}")
        return True

    async def complete_verification(
        self,
        task_id: str,
        user_id: str,
        verified_data: Dict[str, Any],
        verification_comments: Optional[str] = None,
        corrections_made: Optional[List[Dict[str, Any]]] = None,
        quality_score: Optional[QualityScore] = None
    ) -> bool:
        """Complete a verification task."""
        
        task = self.db.query(VerificationTask).filter(
            VerificationTask.task_id == task_id,
            VerificationTask.assigned_to == user_id
        ).first()
        
        if not task:
            self.logger.error(f"Task {task_id} not found or not assigned to user {user_id}")
            return False
        
        if task.status != VerificationStatus.IN_PROGRESS:
            self.logger.error(f"Task {task_id} is not in progress (status: {task.status})")
            return False
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - task.started_at).total_seconds() if task.started_at else None
        if not task.started_at:
            task.started_at = datetime.utcnow()
        
        # Update task with verification results
        task.verified_data = verified_data
        task.verification_comments = verification_comments
        task.corrections_made = corrections_made or []
        task.quality_score = quality_score
        task.completed_at = datetime.utcnow()
        task.processing_time_seconds = int(processing_time) if processing_time else 0
        task.status = VerificationStatus.COMPLETED
        
        # Calculate verification accuracy
        accuracy = await self._calculate_verification_accuracy(task)
        task.verification_accuracy = accuracy
        
        # Update team performance metrics
        await self._update_team_performance(task.assigned_team or "", {
            "tasks_completed": 1,
            "processing_time": task.processing_time_seconds,
            "accuracy": accuracy,
            "quality_score": quality_score.value if quality_score else "unknown"
        })
        
        # Run quality check if required
        if await self._requires_quality_check(task):
            await self._trigger_quality_check(task)
        
        # Log AI learning data
        await self.ai_service.log_human_corrections(
            task.extraction_id, corrections_made or []
        )
        
        self.db.commit()
        
        # Track completion
        telemetry_service.track_event("verification_task_completed", {
            "task_id": task_id,
            "processing_time": task.processing_time_seconds,
            "accuracy": accuracy,
            "quality_score": quality_score.value if quality_score else "unknown",
            "corrections_count": len(corrections_made or [])
        })
        
        # Remove from user's active queue
        await self._remove_from_user_queue(user_id, task_id)
        
        self.logger.info(f"Completed verification task {task_id} with {accuracy:.1%} accuracy")
        return True

    async def reject_verification(
        self,
        task_id: str,
        user_id: str,
        rejection_reason: str
    ) -> bool:
        """Reject a verification task."""
        
        task = self.db.query(VerificationTask).filter(
            VerificationTask.task_id == task_id,
            VerificationTask.assigned_to == user_id
        ).first()
        
        if not task:
            self.logger.error(f"Task {task_id} not found or not assigned to user {user_id}")
            return False
        
        task.status = VerificationStatus.REJECTED
        task.verification_comments = f"REJECTED: {rejection_reason}"
        task.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        # Track rejection
        telemetry_service.track_event("verification_task_rejected", {
            "task_id": task_id,
            "rejection_reason": rejection_reason,
            "assigned_to": user_id
        })
        
        # Remove from queue and potentially requeue
        await self._remove_from_user_queue(user_id, task_id)
        
        self.logger.info(f"Rejected verification task {task_id}: {rejection_reason}")
        return True

    async def get_verification_queue(
        self,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        status: Optional[VerificationStatus] = None,
        priority: Optional[PriorityLevel] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[VerificationTask]:
        """Get verification queue with filtering and pagination."""
        
        query = self.db.query(VerificationTask)
        
        # Apply filters
        if user_id:
            query = query.filter(VerificationTask.assigned_to == user_id)
        
        if team_id:
            query = query.filter(VerificationTask.assigned_team == team_id)
        
        if status:
            query = query.filter(VerificationTask.status == status)
        
        if priority:
            query = query.filter(VerificationTask.priority == priority)
        
        # Sort by priority and due date
        query = query.order_by(
            desc(VerificationTask.priority == PriorityLevel.CRITICAL),
            desc(VerificationTask.priority == PriorityLevel.URGENT),
            desc(VerificationTask.priority == PriorityLevel.HIGH),
            VerificationTask.due_date
        )
        
        # Pagination
        tasks = query.offset(offset).limit(limit).all()
        
        return tasks

    async def get_overdue_tasks(self) -> List[VerificationTask]:
        """Get all overdue verification tasks."""
        
        overdue_tasks = self.db.query(VerificationTask).filter(
            and_(
                VerificationTask.status.in_([VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS]),
                VerificationTask.due_date < datetime.utcnow()
            )
        ).all()
        
        return overdue_tasks

    async def escalate_overdue_tasks(self) -> int:
        """Escalate overdue tasks to higher priority or different teams."""
        
        overdue_tasks = await self.get_overdue_tasks()
        escalated_count = 0
        
        for task in overdue_tasks:
            # Increase escalation level
            task.escalation_level += 1
            
            # Escalate priority
            if task.priority != PriorityLevel.URGENT:
                task.priority = PriorityLevel.URGENT
            
            # If escalated multiple times, reassign to senior team
            if task.escalation_level >= 2:
                senior_team = await self._get_senior_team_for_task(task)
                if senior_team:
                    task.assigned_team = senior_team
            
            # Send escalation notification
            await self.notification_service.send_escalation_notification(
                task.assigned_to or task.assigned_team or "unassigned",
                task.task_id,
                task.escalation_level
            )
            
            escalated_count += 1
            
            # Track escalation
            telemetry_service.track_event("verification_task_escalated", {
                "task_id": task.task_id,
                "escalation_level": task.escalation_level,
                "original_due_date": task.due_date.isoformat()
            })
        
        self.db.commit()
        
        self.logger.info(f"Escalated {escalated_count} overdue verification tasks")
        return escalated_count

    async def batch_process_tasks(
        self,
        task_ids: List[str],
        assigned_to: str,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """Process multiple verification tasks in batch."""
        
        tasks = self.db.query(VerificationTask).filter(
            VerificationTask.task_id.in_(task_ids)
        ).all()
        
        if len(tasks) > batch_size:
            return {"error": f"Batch size exceeds limit of {batch_size}"}
        
        # Check user capacity
        user_active_count = await self._get_user_active_task_count(assigned_to)
        if user_active_count + len(tasks) > self.config['max_concurrent_tasks_per_user']:
            return {"error": "User capacity exceeded for batch processing"}
        
        # Assign all tasks
        assigned_count = 0
        for task in tasks:
            if await self.assign_task(task.task_id, assigned_to, auto_assign=False):
                assigned_count += 1
                task.status = VerificationStatus.BATCH_PROCESSING
        
        self.db.commit()
        
        # Track batch assignment
        telemetry_service.track_event("verification_batch_assigned", {
            "assigned_to": assigned_to,
            "total_tasks": len(tasks),
            "assigned_count": assigned_count,
            "batch_size": len(tasks)
        })
        
        return {
            "total_tasks": len(tasks),
            "assigned_count": assigned_count,
            "batch_id": f"BATCH-{datetime.now().strftime('%Y%m%d')}-{uuid4()[:8]}"
        }

    async def get_team_workload(self, team_id: str) -> Dict[str, Any]:
        """Get detailed workload information for a team."""
        
        team = self.db.query(VerificationTeam).filter(
            VerificationTeam.team_code == team_id
        ).first()
        
        if not team:
            return {"error": f"Team {team_id} not found"}
        
        # Get team statistics
        team_tasks = self.db.query(VerificationTask).filter(
            VerificationTask.assigned_team == team_id
        ).all()
        
        total_tasks = len(team_tasks)
        pending_tasks = len([t for t in team_tasks if t.status == VerificationStatus.PENDING])
        in_progress_tasks = len([t for t in team_tasks if t.status == VerificationStatus.IN_PROGRESS])
        completed_tasks = len([t for t in team_tasks if t.status == VerificationStatus.COMPLETED])
        
        # Calculate average processing time
        completed_with_time = [t for t in team_tasks if t.processing_time_seconds]
        avg_processing_time = (
            sum(t.processing_time_seconds for t in completed_with_time) / len(completed_with_time)
            if completed_with_time else 0
        )
        
        # Calculate accuracy metrics
        completed_with_accuracy = [t for t in team_tasks if t.verification_accuracy]
        avg_accuracy = (
            sum(t.verification_accuracy for t in completed_with_accuracy) / len(completed_with_accuracy)
            if completed_with_accuracy else 0
        )
        
        return {
            "team_info": {
                "team_name": team.team_name,
                "team_code": team.team_code,
                "specialization": team.specialization_area,
                "max_concurrent_tasks": team.max_concurrent_tasks
            },
            "workload": {
                "total_tasks": total_tasks,
                "pending_tasks": pending_tasks,
                "in_progress_tasks": in_progress_tasks,
                "completed_tasks": completed_tasks,
                "utilization_rate": (in_progress_tasks / team.max_concurrent_tasks) * 100 if team.max_concurrent_tasks > 0 else 0
            },
            "performance": {
                "average_processing_time_seconds": avg_processing_time,
                "average_accuracy_percentage": avg_accuracy * 100,
                "completion_rate": (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            }
        }

    async def get_user_performance_metrics(
        self,
        user_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for a user over a specified period."""
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        user_tasks = self.db.query(VerificationTask).filter(
            and_(
                VerificationTask.assigned_to == user_id,
                VerificationTask.created_at >= start_date
            )
        ).all()
        
        if not user_tasks:
            return {"message": "No tasks found for the specified period"}
        
        total_tasks = len(user_tasks)
        completed_tasks = [t for t in user_tasks if t.status == VerificationStatus.COMPLETED]
        rejected_tasks = [t for t in user_tasks if t.status == VerificationStatus.REJECTED]
        
        # Calculate metrics
        completion_rate = len(completed_tasks) / total_tasks * 100
        
        # Processing time
        processing_times = [t.processing_time_seconds for t in completed_tasks if t.processing_time_seconds]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Accuracy
        accuracies = [t.verification_accuracy for t in completed_tasks if t.verification_accuracy]
        avg_accuracy = sum(accuracies) / len(accuracies) * 100 if accuracies else 0
        
        # Quality distribution
        quality_scores = {}
        for task in completed_tasks:
            if task.quality_score:
                score = task.quality_score.value
                quality_scores[score] = quality_scores.get(score, 0) + 1
        
        # Daily productivity
        daily_productivity = {}
        for task in completed_tasks:
            day = task.completed_at.date().isoformat()
            daily_productivity[day] = daily_productivity.get(day, 0) + 1
        
        return {
            "period_days": period_days,
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_tasks),
            "rejected_tasks": len(rejected_tasks),
            "completion_rate_percentage": completion_rate,
            "average_processing_time_seconds": avg_processing_time,
            "average_accuracy_percentage": avg_accuracy,
            "quality_score_distribution": quality_scores,
            "daily_productivity": daily_productivity,
            "trends": {
                "productivity_trend": await self._calculate_productivity_trend(user_id, period_days),
                "accuracy_trend": await self._calculate_accuracy_trend(user_id, period_days)
            }
        }

    # Private helper methods
    
    async def _add_to_queue(self, task: VerificationTask, assigned_team: Optional[str] = None):
        """Add task to appropriate verification queue."""
        
        if assigned_team:
            task.assigned_team = assigned_team
        else:
            # Auto-assign to best available team
            best_team = await self._auto_assign_team(task)
            task.assigned_team = best_team
        
        # Cache the task for quick access
        cache_key = f"verification_queue:{task.assigned_team}"
        await self.cache.add_to_list(cache_key, task.task_id, expire=3600)

    async def _auto_assign_team(self, task: VerificationTask) -> Optional[str]:
        """Auto-assign task to the best available team."""
        
        available_teams = self.db.query(VerificationTeam).filter(
            VerificationTeam.is_active == True
        ).all()
        
        if not available_teams:
            return None
        
        # Score teams based on specialization and workload
        best_team = None
        best_score = -1
        
        for team in available_teams:
            score = await self._calculate_team_assignment_score(team, task)
            if score > best_score:
                best_score = score
                best_team = team.team_code
        
        return best_team

    async def _calculate_team_assignment_score(self, team: VerificationTeam, task: VerificationTask) -> float:
        """Calculate score for team-task assignment."""
        
        score = 0.0
        
        # Specialization match
        if task.task_type.value in team.specialization_area.lower():
            score += 30
        
        # Workload factor (prefer teams with lower workload)
        current_load = len(self.db.query(VerificationTask).filter(
            and_(
                VerificationTask.assigned_team == team.team_code,
                VerificationTask.status.in_([VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS])
            )
        ).all())
        
        max_capacity = team.max_concurrent_tasks
        load_factor = 1 - (current_load / max_capacity) if max_capacity > 0 else 0
        score += load_factor * 40
        
        # Quality score factor
        if team.quality_accuracy_rate:
            score += team.quality_accuracy_rate * 30
        
        return score

    async def _get_user_active_task_count(self, user_id: str) -> int:
        """Get number of active tasks for a user."""
        
        return self.db.query(VerificationTask).filter(
            and_(
                VerificationTask.assigned_to == user_id,
                VerificationTask.status.in_([VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS, VerificationStatus.BATCH_PROCESSING])
            )
        ).count()

    async def _remove_from_user_queue(self, user_id: str, task_id: str):
        """Remove task from user's active queue."""
        
        # Update cache
        cache_key = f"user_queue:{user_id}"
        await self.cache.remove_from_list(cache_key, task_id)

    async def _estimate_processing_time(self, task: VerificationTask) -> int:
        """Estimate processing time for a task based on historical data."""
        
        # Get similar tasks (same document type, priority)
        similar_tasks = self.db.query(VerificationTask).filter(
            and_(
                VerificationTask.task_type == task.task_type,
                VerificationTask.priority == task.priority,
                VerificationTask.status == VerificationStatus.COMPLETED
            )
        ).limit(50).all()
        
        if not similar_tasks:
            return self.config['default_sla_hours'] * 3600  # Default to SLA time in seconds
        
        processing_times = [t.processing_time_seconds for t in similar_tasks if t.processing_time_seconds]
        return int(sum(processing_times) / len(processing_times)) if processing_times else 3600

    async def _update_team_performance(self, team_code: str, metrics: Dict[str, Any]):
        """Update team performance metrics."""
        
        if not team_code:
            return
        
        # Get or create performance record for today
        today = datetime.utcnow().date()
        performance = self.db.query(VerificationPerformance).filter(
            and_(
                VerificationPerformance.team_id == team_code,
                func.date(VerificationPerformance.metric_date) == today
            )
        ).first()
        
        if not performance:
            team = self.db.query(VerificationTeam).filter(
                VerificationTeam.team_code == team_code
            ).first()
            if not team:
                return
            
            performance = VerificationPerformance(
                team_id=team.id,
                metric_date=datetime.utcnow(),
                metric_period="daily"
            )
            self.db.add(performance)
        
        # Update metrics
        performance.tasks_completed = (performance.tasks_completed or 0) + metrics.get('tasks_completed', 0)
        
        if 'processing_time' in metrics:
            current_avg = performance.average_processing_time or 0
            count = performance.tasks_completed or 1
            performance.average_processing_time = (current_avg * (count - 1) + metrics['processing_time']) / count
        
        if 'accuracy' in metrics:
            current_avg = performance.average_accuracy or 0
            count = performance.tasks_completed or 1
            performance.average_accuracy = (current_avg * (count - 1) + metrics['accuracy']) / count

    async def _calculate_verification_accuracy(self, task: VerificationTask) -> float:
        """Calculate verification accuracy based on AI confidence and corrections."""
        
        base_confidence = task.ai_confidence_score or 0.5
        correction_penalty = len(task.corrections_made or []) * 0.1  # 10% penalty per correction
        
        accuracy = max(0.0, base_confidence - correction_penalty)
        return min(1.0, accuracy)

    async def _requires_quality_check(self, task: VerificationTask) -> bool:
        """Determine if task requires quality check."""
        
        # Require quality check for:
        # - Low AI confidence
        # - Multiple corrections
        # - Critical priority tasks
        
        low_confidence = (task.ai_confidence_score or 1.0) < self.config['quality_threshold_acceptable']
        multiple_corrections = len(task.corrections_made or []) > 2
        is_critical = task.priority in [PriorityLevel.CRITICAL, PriorityLevel.URGENT]
        
        return low_confidence or multiple_corrections or is_critical

    async def _trigger_quality_check(self, task: VerificationTask):
        """Trigger quality check for a completed task."""
        
        await self.quality_service.create_quality_review(task)

    async def _get_senior_team_for_task(self, task: VerificationTask) -> Optional[str]:
        """Get senior team for task escalation."""
        
        # Logic to determine appropriate senior team
        senior_teams = self.db.query(VerificationTeam).filter(
            VerificationTeam.expertise_level == "senior"
        ).all()
        
        if not senior_teams:
            return None
        
        # Return first available senior team
        return senior_teams[0].team_code

    async def _calculate_productivity_trend(self, user_id: str, period_days: int) -> str:
        """Calculate productivity trend (improving, stable, declining)."""
        
        # Implementation for productivity trend calculation
        return "stable"  # Placeholder

    async def _calculate_accuracy_trend(self, user_id: str, period_days: int) -> str:
        """Calculate accuracy trend (improving, stable, declining)."""
        
        # Implementation for accuracy trend calculation
        return "stable"  # Placeholder