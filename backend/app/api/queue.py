from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.services.queue_manager import QueueManager
from app.models.job import Job
from app.models.enterprise import JobQueue, ScheduledTask, TaskRun

router = APIRouter(prefix="/queue", tags=["queue"])

# Global queue manager instance
queue_manager = None

def get_queue_manager(db: Session = Depends(get_db)) -> QueueManager:
    global queue_manager
    if queue_manager is None:
        queue_manager = QueueManager(db)
    return queue_manager


@router.post("/start-worker/{queue_name}")
async def start_queue_worker(
    queue_name: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Start a worker for a specific queue"""
    # Check if user has admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to start workers"
        )
    
    await queue_manager.start_worker(queue_name, current_user.tenant_id)
    
    return {"message": f"Worker started for queue: {queue_name}"}


@router.post("/stop-worker/{queue_name}")
async def stop_queue_worker(
    queue_name: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Stop a worker for a specific queue"""
    # Check if user has admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to stop workers"
        )
    
    await queue_manager.stop_worker(queue_name, current_user.tenant_id)
    
    return {"message": f"Worker stopped for queue: {queue_name}"}


@router.post("/batches")
async def create_batch_job(
    batch_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Create a batch processing job"""
    job_ids = batch_data.get("job_ids", [])
    batch_name = batch_data.get("batch_name")
    
    if not job_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_ids is required"
        )
    
    # Verify all jobs belong to the current tenant
    jobs = db.query(Job).filter(
        Job.tenant_id == current_user.tenant_id,
        Job.job_id.in_(job_ids)
    ).all()
    
    if len(jobs) != len(job_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some job IDs are invalid or belong to different tenant"
        )
    
    batch_result = queue_manager.create_batch_job(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        job_ids=job_ids,
        batch_name=batch_name
    )
    
    return batch_result


@router.get("/batches/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get status of a batch processing job"""
    # This would need to be enhanced to check batch ownership
    status_result = queue_manager.get_batch_status(batch_id)
    
    if "error" in status_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=status_result["error"]
        )
    
    return status_result


@router.get("/statistics")
async def get_queue_statistics(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get queue statistics"""
    stats = queue_manager.get_queue_statistics(current_user.tenant_id)
    
    return stats


@router.get("/queues")
async def list_queues(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all job queues"""
    queues = db.query(JobQueue).filter(
        (JobQueue.tenant_id == current_user.tenant_id) | 
        (JobQueue.tenant_id == "system")
    ).all()
    
    return [
        {
            "queue_id": q.queue_id,
            "name": q.name,
            "description": q.description,
            "max_concurrent_jobs": q.max_concurrent_jobs,
            "max_retries": q.max_retries,
            "retry_delay_seconds": q.retry_delay_seconds,
            "timeout_seconds": q.timeout_seconds,
            "priority_min": q.priority_min,
            "priority_max": q.priority_max,
            "is_active": q.is_active
        }
        for q in queues
    ]


@router.post("/queues")
async def create_queue(
    queue_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new job queue"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to create queues"
        )
    
    queue = JobQueue(
        tenant_id=current_user.tenant_id,
        name=queue_data["name"],
        description=queue_data.get("description"),
        max_concurrent_jobs=queue_data.get("max_concurrent_jobs", 5),
        max_retries=queue_data.get("max_retries", 3),
        retry_delay_seconds=queue_data.get("retry_delay_seconds", 60),
        timeout_seconds=queue_data.get("timeout_seconds", 3600),
        priority_min=queue_data.get("priority_min", -10),
        priority_max=queue_data.get("priority_max", 10)
    )
    
    db.add(queue)
    db.commit()
    db.refresh(queue)
    
    return {
        "queue_id": queue.queue_id,
        "name": queue.name,
        "message": "Queue created successfully"
    }


@router.put("/queues/{queue_id}")
async def update_queue(
    queue_id: str,
    updates: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update queue configuration"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to update queues"
        )
    
    queue = db.query(JobQueue).filter(
        JobQueue.queue_id == queue_id,
        JobQueue.tenant_id == current_user.tenant_id
    ).first()
    
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue not found"
        )
    
    # Update fields
    for field, value in updates.items():
        if hasattr(queue, field):
            setattr(queue, field, value)
    
    queue.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Queue updated successfully"}


@router.delete("/queues/{queue_id}")
async def delete_queue(
    queue_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a job queue"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to delete queues"
        )
    
    queue = db.query(JobQueue).filter(
        JobQueue.queue_id == queue_id,
        JobQueue.tenant_id == current_user.tenant_id
    ).first()
    
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue not found"
        )
    
    # Check if queue has active jobs
    active_jobs = db.query(Job).filter(
        Job.queue_name == queue.name,
        Job.status.in_(["queued", "processing"])
    ).count()
    
    if active_jobs > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete queue with {active_jobs} active jobs"
        )
    
    db.delete(queue)
    db.commit()
    
    return {"message": "Queue deleted successfully"}


@router.get("/jobs/{queue_name}")
async def get_queue_jobs(
    queue_name: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get jobs from a specific queue"""
    query = db.query(Job).filter(
        Job.tenant_id == current_user.tenant_id,
        Job.queue_name == queue_name
    )
    
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "job_id": j.job_id,
            "status": j.status,
            "priority": j.priority,
            "uploaded_by": j.uploaded_by,
            "assigned_to": j.assigned_to,
            "created_at": j.created_at.isoformat(),
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            "progress_percentage": j.progress_percentage,
            "retry_count": j.retry_count,
            "error_code": j.error_code
        }
        for j in jobs
    ]


# Scheduled Tasks Endpoints

@router.post("/scheduled-tasks")
async def create_scheduled_task(
    task_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Create a scheduled task"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to create scheduled tasks"
        )
    
    task = await queue_manager.schedule_recurring_task(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        task_name=task_data["name"],
        task_type=task_data["task_type"],
        cron_expression=task_data.get("schedule_cron"),
        config=task_data.get("config", {})
    )
    
    return {
        "task_id": task.task_id,
        "name": task.name,
        "task_type": task.task_type,
        "message": "Scheduled task created successfully"
    }


@router.get("/scheduled-tasks")
async def list_scheduled_tasks(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all scheduled tasks"""
    tasks = db.query(ScheduledTask).filter(
        ScheduledTask.tenant_id == current_user.tenant_id
    ).all()
    
    return [
        {
            "task_id": t.task_id,
            "name": t.name,
            "description": t.description,
            "task_type": t.task_type,
            "schedule_cron": t.schedule_cron,
            "schedule_interval": t.schedule_interval,
            "is_active": t.is_active,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "next_run": t.next_run.isoformat() if t.next_run else None,
            "created_at": t.created_at.isoformat()
        }
        for t in tasks
    ]


@router.get("/scheduled-tasks/{task_id}")
async def get_scheduled_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a scheduled task"""
    task = db.query(ScheduledTask).filter(
        ScheduledTask.task_id == task_id,
        ScheduledTask.tenant_id == current_user.tenant_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Get recent runs
    runs = db.query(TaskRun).filter(
        TaskRun.task_id == task_id
    ).order_by(TaskRun.started_at.desc()).limit(10).all()
    
    return {
        "task": {
            "task_id": task.task_id,
            "name": task.name,
            "description": task.description,
            "task_type": task.task_type,
            "schedule_cron": task.schedule_cron,
            "schedule_interval": task.schedule_interval,
            "is_active": task.is_active,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "config": task.config,
            "created_at": task.created_at.isoformat()
        },
        "recent_runs": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "execution_time_ms": r.execution_time_ms,
                "error_message": r.error_message
            }
            for r in runs
        ]
    }


@router.put("/scheduled-tasks/{task_id}")
async def update_scheduled_task(
    task_id: str,
    updates: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a scheduled task"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to update scheduled tasks"
        )
    
    task = db.query(ScheduledTask).filter(
        ScheduledTask.task_id == task_id,
        ScheduledTask.tenant_id == current_user.tenant_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Update fields
    for field, value in updates.items():
        if hasattr(task, field):
            setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Scheduled task updated successfully"}


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scheduled task"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to delete scheduled tasks"
        )
    
    task = db.query(ScheduledTask).filter(
        ScheduledTask.task_id == task_id,
        ScheduledTask.tenant_id == current_user.tenant_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    db.delete(task)
    db.commit()
    
    return {"message": "Scheduled task deleted successfully"}


@router.post("/scheduled-tasks/{task_id}/run")
async def run_scheduled_task_now(
    task_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger a scheduled task"""
    # Check admin permissions
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to run scheduled tasks"
        )
    
    task = db.query(ScheduledTask).filter(
        ScheduledTask.task_id == task_id,
        ScheduledTask.tenant_id == current_user.tenant_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled task not found"
        )
    
    # Create a task run record
    task_run = TaskRun(
        task_id=task_id,
        status="running"
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)
    
    # Update task's last_run
    task.last_run = datetime.utcnow()
    db.commit()
    
    return {
        "run_id": task_run.run_id,
        "message": "Task execution started"
    }
