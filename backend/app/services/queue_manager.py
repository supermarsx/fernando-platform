import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.models.enterprise import JobQueue, ScheduledTask, TaskRun
from app.models.job import Job
from app.services.enterprise_service import EnterpriseService


class QueueManager:
    """Enhanced queue management for batch processing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.enterprise_service = EnterpriseService(db)
        self.active_workers = {}
        self.job_processors = {
            "document_processing": self._process_document_job,
            "export": self._process_export_job,
            "cleanup": self._process_cleanup_job,
            "report": self._process_report_job
        }
        self._worker_tasks = {}
    
    async def initialize_queues(self):
        """Initialize default job queues"""
        # Default processing queue
        default_queue = self.db.query(JobQueue).filter(
            JobQueue.name == "default"
        ).first()
        
        if not default_queue:
            default_queue = JobQueue(
                tenant_id="system",  # System-wide queue
                name="default",
                description="Default processing queue",
                max_concurrent_jobs=5,
                max_retries=3,
                retry_delay_seconds=60,
                timeout_seconds=3600,
                priority_min=-10,
                priority_max=10
            )
            self.db.add(default_queue)
            self.db.commit()
        
        # High priority queue for urgent jobs
        urgent_queue = self.db.query(JobQueue).filter(
            JobQueue.name == "urgent"
        ).first()
        
        if not urgent_queue:
            urgent_queue = JobQueue(
                tenant_id="system",
                name="urgent",
                description="High priority processing queue",
                max_concurrent_jobs=2,
                max_retries=1,
                retry_delay_seconds=30,
                timeout_seconds=1800,
                priority_min=5,
                priority_max=10
            )
            self.db.add(urgent_queue)
            self.db.commit()
    
    async def start_worker(self, queue_name: str, tenant_id: str = None):
        """Start a worker for a specific queue"""
        if f"{tenant_id}:{queue_name}" in self.active_workers:
            return
        
        worker_id = f"{tenant_id}:{queue_name}" if tenant_id else queue_name
        self.active_workers[worker_id] = True
        
        # Start worker task
        task = asyncio.create_task(self._worker_loop(queue_name, tenant_id))
        self._worker_tasks[worker_id] = task
    
    async def stop_worker(self, queue_name: str, tenant_id: str = None):
        """Stop a worker for a specific queue"""
        worker_id = f"{tenant_id}:{queue_name}" if tenant_id else queue_name
        
        if worker_id in self.active_workers:
            self.active_workers[worker_id] = False
        
        if worker_id in self._worker_tasks:
            self._worker_tasks[worker_id].cancel()
            del self._worker_tasks[worker_id]
    
    async def _worker_loop(self, queue_name: str, tenant_id: str = None):
        """Main worker loop for processing jobs"""
        while self.active_workers.get(f"{tenant_id}:{queue_name}" if tenant_id else queue_name, False):
            try:
                await self._process_next_job(queue_name, tenant_id)
                await asyncio.sleep(1)  # Brief pause between jobs
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(5)  # Longer pause on error
    
    async def _process_next_job(self, queue_name: str, tenant_id: str = None):
        """Get and process the next job from the queue"""
        # Get queue configuration
        queue = self.db.query(JobQueue).filter(
            JobQueue.name == queue_name
        ).first()
        
        if not queue:
            return
        
        # Get next job from queue
        job = self._get_next_job_from_queue(queue_name, tenant_id, queue)
        
        if not job:
            return
        
        # Process the job
        await self._execute_job(job, queue)
    
    def _get_next_job_from_queue(self, queue_name: str, tenant_id: str, queue: JobQueue) -> Optional[Job]:
        """Get the next job from the queue based on priority and availability"""
        query = self.db.query(Job).filter(
            and_(
                Job.queue_name == queue_name,
                Job.status == "queued"
            )
        )
        
        if tenant_id:
            query = query.filter(Job.tenant_id == tenant_id)
        
        # Filter by priority range
        query = query.filter(
            and_(
                Job.priority >= queue.priority_min,
                Job.priority <= queue.priority_max
            )
        )
        
        # Order by priority (highest first) and creation time (oldest first)
        jobs = query.order_by(desc(Job.priority), Job.created_at).limit(1).all()
        
        return jobs[0] if jobs else None
    
    async def _execute_job(self, job: Job, queue: JobQueue):
        """Execute a job with retry logic"""
        job.status = "processing"
        job.started_at = datetime.utcnow()
        self.db.commit()
        
        processor = self._get_job_processor(job)
        if not processor:
            await self._fail_job(job, "No processor available for job type")
            return
        
        retry_count = 0
        max_retries = queue.max_retries
        
        while retry_count <= max_retries:
            try:
                # Create task run record
                task_run = TaskRun(
                    task_id=job.job_id,  # Using job_id as task_id for simplicity
                    status="running"
                )
                self.db.add(task_run)
                self.db.commit()
                
                start_time = datetime.utcnow()
                
                # Execute the job
                result = await processor(job)
                
                end_time = datetime.utcnow()
                execution_time = int((end_time - start_time).total_seconds() * 1000)
                
                # Update task run
                task_run.status = "completed"
                task_run.completed_at = end_time
                task_run.execution_time_ms = execution_time
                task_run.result = result
                self.db.commit()
                
                # Mark job as completed
                job.status = "completed"
                job.finished_at = end_time
                job.actual_duration = execution_time // 1000
                self.db.commit()
                
                self.enterprise_service.increment_quota_usage(job.tenant_id, jobs=1)
                return
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Job execution failed (attempt {retry_count}): {str(e)}"
                print(error_msg)
                
                if retry_count > max_retries:
                    await self._fail_job(job, error_msg)
                    return
                
                # Wait before retry
                await asyncio.sleep(queue.retry_delay_seconds)
    
    async def _fail_job(self, job: Job, error_message: str):
        """Mark job as failed"""
        job.status = "failed"
        job.error_details = error_message
        job.finished_at = datetime.utcnow()
        self.db.commit()
        
        # Create failed task run
        task_run = TaskRun(
            task_id=job.job_id,
            status="failed",
            started_at=job.started_at or datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message=error_message
        )
        self.db.add(task_run)
        self.db.commit()
    
    def _get_job_processor(self, job: Job) -> Optional[Callable]:
        """Get the appropriate processor for a job based on its type"""
        # For now, all jobs use document processing
        # In a real implementation, you'd have job types
        return self._process_document_job
    
    async def _process_document_job(self, job: Job) -> Dict[str, Any]:
        """Process a document job"""
        # Simulate processing time
        await asyncio.sleep(2)
        
        # This would integrate with your existing document processing pipeline
        return {
            "status": "completed",
            "documents_processed": 1,
            "extraction_confidence": 0.95
        }
    
    async def _process_export_job(self, job: Job) -> Dict[str, Any]:
        """Process an export job"""
        await asyncio.sleep(3)
        return {"status": "completed", "records_exported": 100}
    
    async def _process_cleanup_job(self, job: Job) -> Dict[str, Any]:
        """Process a cleanup job"""
        await asyncio.sleep(1)
        return {"status": "completed", "files_cleaned": 5}
    
    async def _process_report_job(self, job: Job) -> Dict[str, Any]:
        """Process a report generation job"""
        await asyncio.sleep(5)
        return {"status": "completed", "report_url": "http://example.com/report.pdf"}
    
    def create_batch_job(self, tenant_id: str, user_id: str, job_ids: List[str],
                        batch_name: str = None) -> Dict[str, Any]:
        """Create a batch processing job"""
        batch_id = str(uuid.uuid4())
        
        # Update jobs to be part of this batch
        for job_id in job_ids:
            job = self.db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.metadata = job.metadata or {}
                job.metadata["batch_id"] = batch_id
                job.metadata["batch_name"] = batch_name or f"Batch {batch_id[:8]}"
        
        self.db.commit()
        
        return {
            "batch_id": batch_id,
            "batch_name": batch_name or f"Batch {batch_id[:8]}",
            "job_count": len(job_ids),
            "status": "created"
        }
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a batch processing job"""
        jobs = self.db.query(Job).filter(
            Job.metadata["batch_id"] == batch_id
        ).all()
        
        if not jobs:
            return {"error": "Batch not found"}
        
        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j.status == "completed"])
        failed_jobs = len([j for j in jobs if j.status == "failed"])
        processing_jobs = len([j for j in jobs if j.status == "processing"])
        
        progress_percentage = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        return {
            "batch_id": batch_id,
            "batch_name": jobs[0].metadata.get("batch_name", f"Batch {batch_id[:8]}"),
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "processing_jobs": processing_jobs,
            "progress_percentage": round(progress_percentage, 2),
            "status": "completed" if completed_jobs == total_jobs else "processing"
        }
    
    async def schedule_recurring_task(self, tenant_id: str, user_id: str, 
                                     task_name: str, task_type: str,
                                     cron_expression: str, config: Dict = None):
        """Schedule a recurring task"""
        task = ScheduledTask(
            tenant_id=tenant_id,
            name=task_name,
            task_type=task_type,
            schedule_cron=cron_expression,
            config=config or {},
            created_by=user_id,
            is_active=True
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def get_queue_statistics(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get queue statistics"""
        query = self.db.query(Job)
        
        if tenant_id:
            query = query.filter(Job.tenant_id == tenant_id)
        
        # Get status breakdown
        status_counts = query.with_entities(Job.status, func.count(Job.job_id)).group_by(Job.status).all()
        status_dict = dict(status_counts)
        
        # Get average processing time
        completed_jobs = self.db.query(Job).filter(
            and_(
                Job.status == "completed",
                Job.actual_duration.isnot(None)
            )
        )
        if tenant_id:
            completed_jobs = completed_jobs.filter(Job.tenant_id == tenant_id)
        
        avg_processing_time = 0
        if completed_jobs.count() > 0:
            avg_time = completed_jobs.with_entities(func.avg(Job.actual_duration)).scalar()
            avg_processing_time = int(avg_time) if avg_time else 0
        
        return {
            "total_jobs": sum(status_dict.values()) if status_dict else 0,
            "queued_jobs": status_dict.get("queued", 0),
            "processing_jobs": status_dict.get("processing", 0),
            "completed_jobs": status_dict.get("completed", 0),
            "failed_jobs": status_dict.get("failed", 0),
            "average_processing_time_seconds": avg_processing_time,
            "active_workers": len([w for w in self.active_workers.values() if w])
        }
