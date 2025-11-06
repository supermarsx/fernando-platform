"""
API endpoints for human verification and quality control workflow.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.db.session import get_db
from app.services.verification.verification_service import VerificationService
from app.services.verification.ai_assistance import AIAssistanceService
from app.services.verification.quality_control import QualityControlService
from app.models.verification import (
    VerificationTask, VerificationStatus, PriorityLevel, VerificationType,
    QualityReview, VerificationTeam, VerificationPerformance
)

router = APIRouter(prefix="/api/verification", tags=["verification"])

# Dependency to get database session
def get_db_session():
    db = get_db()
    try:
        yield db
    finally:
        db.close()

# Dependency to get services
def get_verification_service(db: Session = Depends(get_db_session)):
    return VerificationService(db)

def get_ai_service(db: Session = Depends(get_db_session)):
    return AIAssistanceService(db)

def get_quality_service(db: Session = Depends(get_db_session)):
    return QualityControlService(db)


@router.post("/tasks/create")
async def create_verification_task(
    task_data: Dict[str, Any],
    verification_service: VerificationService = Depends(get_verification_service),
    db: Session = Depends(get_db_session)
):
    """Create a new verification task."""
    try:
        task = await verification_service.create_verification_task(
            document_id=task_data["document_id"],
            extraction_id=task_data["extraction_id"],
            task_type=task_data.get("task_type", VerificationType.INITIAL),
            priority=task_data.get("priority", PriorityLevel.NORMAL),
            assigned_team=task_data.get("assigned_team"),
            created_by=task_data.get("created_by", "system")
        )
        return {"task": task, "message": "Task created successfully"}
    except Exception as e:
        logging.error(f"Error creating verification task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_verification_task(
    task_id: str,
    db: Session = Depends(get_db_session)
):
    """Get verification task details."""
    try:
        task = db.query(VerificationTask).filter(
            VerificationTask.task_id == task_id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get AI analysis data
        ai_service = AIAssistanceService(db)
        analysis = await ai_service.analyze_extraction(task.extraction_id)
        
        return {
            "taskId": task.task_id,
            "documentId": task.document_id,
            "extractionId": task.extraction_id,
            "taskType": task.task_type.value,
            "status": task.status.value,
            "priority": task.priority.value,
            "assignedTo": task.assigned_to,
            "assignedTeam": task.assigned_team,
            "createdAt": task.created_at.isoformat(),
            "dueDate": task.due_date.isoformat() if task.due_date else None,
            "extractedData": task.verified_data or {},  # This would come from extraction service
            "aiConfidence": task.ai_confidence_score,
            "aiSuggestions": task.ai_suggestions,
            "anomalies": task.ai_detected_anomalies
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting verification task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/assign")
async def assign_verification_task(
    task_id: str,
    assignment_data: Dict[str, Any],
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Assign a verification task to a user."""
    try:
        success = await verification_service.assign_task(
            task_id=task_id,
            user_id=assignment_data["user_id"],
            auto_assign=assignment_data.get("auto_assign", False)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to assign task")
        
        return {"message": "Task assigned successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error assigning verification task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/complete")
async def complete_verification_task(
    task_id: str,
    completion_data: Dict[str, Any],
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Complete a verification task."""
    try:
        success = await verification_service.complete_verification(
            task_id=task_id,
            user_id=completion_data["user_id"],
            verified_data=completion_data["verified_data"],
            verification_comments=completion_data.get("comments"),
            corrections_made=completion_data.get("corrections", []),
            quality_score=completion_data.get("quality_score")
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete task")
        
        return {"message": "Task completed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error completing verification task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/reject")
async def reject_verification_task(
    task_id: str,
    rejection_data: Dict[str, Any],
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Reject a verification task."""
    try:
        success = await verification_service.reject_verification(
            task_id=task_id,
            user_id=rejection_data["user_id"],
            rejection_reason=rejection_data["reason"]
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reject task")
        
        return {"message": "Task rejected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error rejecting verification task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_verification_queue(
    user_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    status: Optional[VerificationStatus] = Query(None),
    priority: Optional[PriorityLevel] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Get verification queue with filtering."""
    try:
        tasks = await verification_service.get_verification_queue(
            user_id=user_id,
            team_id=team_id,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        return {
            "tasks": [
                {
                    "taskId": task.task_id,
                    "documentId": task.document_id,
                    "documentType": "invoice",  # This would come from document service
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "assignedAt": task.assigned_at.isoformat() if task.assigned_at else None,
                    "dueDate": task.due_date.isoformat() if task.due_date else None,
                    "aiConfidence": task.ai_confidence_score,
                    "estimatedProcessingTime": 300,  # This would be calculated
                    "hasAnomalies": len(task.ai_detected_anomalies or []) > 0,
                    "assignedTo": task.assigned_to
                }
                for task in tasks
            ],
            "total": len(tasks),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logging.error(f"Error getting verification queue: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/stats")
async def get_verification_queue_stats(
    verification_service: VerificationService = Depends(get_verification_service),
    db: Session = Depends(get_db_session)
):
    """Get verification queue statistics."""
    try:
        # Get basic stats
        total_tasks = db.query(VerificationTask).count()
        pending_tasks = db.query(VerificationTask).filter(
            VerificationTask.status == VerificationStatus.PENDING
        ).count()
        in_progress_tasks = db.query(VerificationTask).filter(
            VerificationTask.status == VerificationStatus.IN_PROGRESS
        ).count()
        overdue_tasks = db.query(VerificationTask).filter(
            and_(
                VerificationTask.status.in_([VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS]),
                VerificationTask.due_date < datetime.utcnow()
            )
        ).count()
        
        # Calculate average processing time
        completed_tasks = db.query(VerificationTask).filter(
            and_(
                VerificationTask.status == VerificationStatus.COMPLETED,
                VerificationTask.processing_time_seconds.isnot(None)
            )
        ).all()
        
        avg_processing_time = 0
        if completed_tasks:
            avg_processing_time = sum(
                task.processing_time_seconds for task in completed_tasks
            ) / len(completed_tasks)
        
        # For "my tasks", we'd need user authentication
        my_tasks_count = 0  # This would be based on authenticated user
        
        return {
            "totalTasks": total_tasks,
            "pendingTasks": pending_tasks,
            "inProgressTasks": in_progress_tasks,
            "overdueTasks": overdue_tasks,
            "averageProcessingTime": int(avg_processing_time),
            "myTasksCount": my_tasks_count
        }
    except Exception as e:
        logging.error(f"Error getting queue stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/process")
async def start_batch_verification(
    batch_data: Dict[str, Any],
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Start batch verification processing."""
    try:
        result = await verification_service.batch_process_tasks(
            task_ids=batch_data["task_ids"],
            assigned_to=batch_data["user_id"],
            batch_size=batch_data.get("batch_size", 10)
        )
        
        return result
    except Exception as e:
        logging.error(f"Error starting batch verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_verification_dashboard(
    db: Session = Depends(get_db_session)
):
    """Get verification dashboard data."""
    try:
        today = datetime.utcnow().date()
        
        # User stats (simplified - would need user auth)
        user_stats = {
            "tasksCompleted": 0,
            "averageAccuracy": 85.0,
            "averageProcessingTime": 300,
            "qualityScore": "good",
            "streakDays": 5,
            "todayTasks": 2
        }
        
        # Team stats
        total_team_members = db.query(VerificationTeam).filter(
            VerificationTeam.is_active == True
        ).count()
        
        active_members = total_team_members  # Simplified
        team_accuracy = 87.5  # Calculated from performance data
        queue_size = db.query(VerificationTask).filter(
            VerificationTask.status == VerificationStatus.PENDING
        ).count()
        overdue_tasks = db.query(VerificationTask).filter(
            and_(
                VerificationTask.status.in_([VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS]),
                VerificationTask.due_date < datetime.utcnow()
            )
        ).count()
        
        team_stats = {
            "totalTeamMembers": total_team_members,
            "activeMembers": active_members,
            "teamAccuracy": team_accuracy,
            "queueSize": queue_size,
            "overdueTasks": overdue_tasks
        }
        
        # Recent tasks
        recent_tasks = db.query(VerificationTask).filter(
            VerificationTask.status == VerificationStatus.COMPLETED
        ).order_by(desc(VerificationTask.completed_at)).limit(5).all()
        
        recent_tasks_data = [
            {
                "taskId": task.task_id,
                "documentId": task.document_id,
                "completedAt": task.completed_at.isoformat(),
                "qualityScore": task.verification_accuracy or 0,
                "processingTime": task.processing_time_seconds or 0
            }
            for task in recent_tasks
        ]
        
        # Quality metrics
        quality_metrics = {
            "overallAccuracy": 85.0,
            "qualityTrend": "improving",
            "peerReviewScore": 88.0,
            "errorRate": 5.0
        }
        
        # Alerts (simplified)
        alerts = []
        if overdue_tasks > 0:
            alerts.append({
                "id": "overdue_tasks",
                "type": "warning",
                "title": "Overdue Tasks",
                "message": f"{overdue_tasks} tasks are overdue",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return {
            "userStats": user_stats,
            "teamStats": team_stats,
            "recentTasks": recent_tasks_data,
            "qualityMetrics": quality_metrics,
            "alerts": alerts
        }
    except Exception as e:
        logging.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/members")
async def get_team_members(
    db: Session = Depends(get_db_session)
):
    """Get verification team members."""
    try:
        # This is simplified - in reality, team members would come from user management
        team_members = [
            {
                "id": "user_1",
                "name": "John Doe",
                "email": "john@example.com",
                "role": "senior_reviewer",
                "status": "active",
                "currentTasks": 3,
                "completedToday": 5,
                "accuracyRate": 92.5,
                "averageProcessingTime": 240,
                "joinDate": "2024-01-15"
            },
            {
                "id": "user_2",
                "name": "Jane Smith",
                "email": "jane@example.com",
                "role": "reviewer",
                "status": "active",
                "currentTasks": 2,
                "completedToday": 3,
                "accuracyRate": 88.0,
                "averageProcessingTime": 320,
                "joinDate": "2024-02-01"
            }
        ]
        
        return {"members": team_members}
    except Exception as e:
        logging.error(f"Error getting team members: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/stats")
async def get_team_statistics(
    db: Session = Depends(get_db_session)
):
    """Get team statistics."""
    try:
        total_members = 10  # This would come from user management
        active_members = 8
        total_completed = 45  # Today's completions across team
        
        return {
            "totalMembers": total_members,
            "activeMembers": active_members,
            "totalCompleted": total_completed,
            "averageAccuracy": 87.5,
            "queueSize": 12
        }
    except Exception as e:
        logging.error(f"Error getting team stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/workload")
async def get_team_workload(
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Get team workload data."""
    try:
        workload_data = [
            {
                "teamId": "team_1",
                "teamName": "Invoice Review Team",
                "currentLoad": 5,
                "maxCapacity": 10,
                "utilizationRate": 50.0,
                "averageAccuracy": 89.0,
                "pendingTasks": 8,
                "overdueTasks": 1
            },
            {
                "teamId": "team_2",
                "teamName": "Receipt Processing Team",
                "currentLoad": 7,
                "maxCapacity": 8,
                "utilizationRate": 87.5,
                "averageAccuracy": 85.5,
                "pendingTasks": 4,
                "overdueTasks": 0
            }
        ]
        
        return workload_data
    except Exception as e:
        logging.error(f"Error getting team workload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/review/{review_id}")
async def get_quality_review(
    review_id: str,
    quality_service: QualityControlService = Depends(get_quality_service),
    db: Session = Depends(get_db_session)
):
    """Get quality review details."""
    try:
        review = db.query(QualityReview).filter(
            QualityReview.review_id == review_id
        ).first()
        
        if not review:
            raise HTTPException(status_code=404, detail="Quality review not found")
        
        return {
            "reviewId": review.review_id,
            "verificationTaskId": review.verification_task_id,
            "reviewerId": review.reviewer_id,
            "reviewerRole": review.reviewer_role,
            "reviewType": review.review_type.value,
            "qualityScore": review.quality_score,
            "overallRating": review.overall_rating.value if review.overall_rating else None,
            "isApproved": review.is_approved,
            "accuracyScore": review.accuracy_score,
            "completenessScore": review.completeness_score,
            "consistencyScore": review.consistency_score,
            "efficiencyScore": review.efficiency_score,
            "strengths": review.strengths or [],
            "weaknesses": review.weaknesses or [],
            "recommendations": review.recommendations or [],
            "correctiveActions": review.corrective_actions or [],
            "reviewNotes": review.review_notes,
            "startedAt": review.started_at.isoformat(),
            "completedAt": review.completed_at.isoformat() if review.completed_at else None,
            "reviewTimeSeconds": review.review_time_seconds
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting quality review: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/review/{review_id}/complete")
async def complete_quality_review(
    review_id: str,
    review_data: Dict[str, Any],
    quality_service: QualityControlService = Depends(get_quality_service)
):
    """Complete a quality review."""
    try:
        success = await quality_service.complete_quality_review(
            review_id=review_id,
            reviewer_id=review_data["reviewer_id"],
            quality_score=review_data["quality_score"],
            overall_rating=review_data["overall_rating"],
            is_approved=review_data["is_approved"],
            strengths=review_data.get("strengths"),
            weaknesses=review_data.get("weaknesses"),
            recommendations=review_data.get("recommendations"),
            corrective_actions=review_data.get("corrective_actions"),
            review_notes=review_data.get("review_notes")
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to complete quality review")
        
        return {"message": "Quality review completed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error completing quality review: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/performance")
async def get_performance_analytics(
    user_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    verification_service: VerificationService = Depends(get_verification_service)
):
    """Get performance analytics."""
    try:
        if user_id:
            metrics = await verification_service.get_user_performance_metrics(user_id, days)
            return {"userMetrics": metrics}
        else:
            # Return team or overall analytics
            return {
                "periodDays": days,
                "message": "Team analytics would be returned here"
            }
    except Exception as e:
        logging.error(f"Error getting performance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/quality")
async def get_quality_analytics(
    team_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    quality_service: QualityControlService = Depends(get_quality_service)
):
    """Get quality analytics and trends."""
    try:
        quality_dashboard = await quality_service.get_quality_dashboard_data(team_id, days)
        return quality_dashboard
    except Exception as e:
        logging.error(f"Error getting quality analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))