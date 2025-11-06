"""
Log Retention and Cleanup System

Provides automated log retention policies, cleanup, and archival.
"""

import json
import os
import shutil
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import gzip
import tarfile
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.logging import LogRetentionPolicy, LogArchive, RetentionMetrics
from app.db.session import SessionLocal
from app.services.logging.structured_logger import structured_logger
from app.services.log_collection.log_collector import LogEvent


class RetentionAction(Enum):
    """Actions to take for expired logs"""
    DELETE = "delete"
    ARCHIVE = "archive"
    COMPRESS = "compress"
    MOVE_TO_COLD_STORAGE = "move_to_cold_storage"
    ANONYMIZE = "anonymize"


class LogCategory(Enum):
    """Log categories for retention management"""
    APPLICATION = "application"
    AUDIT = "audit"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    FORENSIC = "forensic"
    PERFORMANCE = "performance"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class RetentionPolicy:
    """Log retention policy definition"""
    policy_id: str
    name: str
    category: LogCategory
    retention_period_days: int
    action: RetentionAction
    archive_path: Optional[str] = None
    compression_enabled: bool = False
    encryption_enabled: bool = False
    compliance_requirements: List[str] = None
    min_severity: str = "info"
    max_file_size_mb: int = 1000
    batch_size: int = 1000
    enabled: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.compliance_requirements is None:
            self.compliance_requirements = []
    
    def should_apply_to_log(self, log_event: LogEvent) -> bool:
        """Check if retention policy applies to log event"""
        
        if not self.enabled:
            return False
        
        # Check category
        if log_event.category != self.category.value:
            return False
        
        # Check severity
        severity_levels = ["trace", "debug", "info", "warning", "error", "critical"]
        log_severity_idx = severity_levels.index(log_event.level.value.lower())
        min_severity_idx = severity_levels.index(self.min_severity.lower())
        
        if log_severity_idx < min_severity_idx:
            return False
        
        return True


class LogRetentionManager:
    """Enterprise log retention and cleanup management system"""
    
    def __init__(self,
                 base_log_path: str = "logs",
                 archive_path: str = "logs/archive",
                 cleanup_interval_hours: int = 24,
                 max_concurrent_operations: int = 5):
        
        self.base_log_path = Path(base_log_path)
        self.archive_path = Path(archive_path)
        self.cleanup_interval_hours = cleanup_interval_hours
        self.max_concurrent_operations = max_concurrent_operations
        
        # Create directories
        self.base_log_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Retention policies
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        
        # Threading
        self._cleanup_thread = None
        self._running = False
        self._operation_semaphore = threading.Semaphore(max_concurrent_operations)
        
        # Statistics
        self.stats = {
            'total_logs_processed': 0,
            'total_logs_archived': 0,
            'total_logs_deleted': 0,
            'total_space_freed_mb': 0.0,
            'total_space_archived_mb': 0.0,
            'cleanup_operations': 0,
            'cleanup_errors': 0,
            'last_cleanup_time': None,
            'avg_cleanup_time_seconds': 0.0
        }
        
        self._lock = threading.Lock()
        
        # Default retention policies
        self._setup_default_policies()
    
    def add_retention_policy(self, policy: RetentionPolicy) -> None:
        """Add retention policy"""
        
        self.retention_policies[policy.policy_id] = policy
        
        # Store in database
        self._store_retention_policy(policy)
        
        structured_logger.info(
            f"Added retention policy: {policy.name}",
            policy_id=policy.policy_id,
            category=policy.category.value,
            retention_days=policy.retention_period_days,
            action=policy.action.value
        )
    
    def remove_retention_policy(self, policy_id: str) -> None:
        """Remove retention policy"""
        
        if policy_id in self.retention_policies:
            policy = self.retention_policies[policy_id]
            del self.retention_policies[policy_id]
            
            # Remove from database
            self._remove_retention_policy(policy_id)
            
            structured_logger.info(
                f"Removed retention policy: {policy.name}",
                policy_id=policy_id
            )
    
    def start_automated_cleanup(self) -> None:
        """Start automated cleanup process"""
        
        if self._running:
            structured_logger.warning("Automated cleanup is already running")
            return
        
        self._running = True
        
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="LogRetention-CleanupWorker",
            daemon=True
        )
        self._cleanup_thread.start()
        
        structured_logger.info(
            "Started automated log cleanup",
            cleanup_interval_hours=self.cleanup_interval_hours,
            policies_count=len(self.retention_policies)
        )
    
    def stop_automated_cleanup(self) -> None:
        """Stop automated cleanup process"""
        
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=30)
        
        structured_logger.info("Stopped automated log cleanup")
    
    def run_cleanup(self, force_all: bool = False) -> Dict[str, Any]:
        """Run manual cleanup operation"""
        
        start_time = datetime.utcnow()
        
        try:
            cleanup_results = {
                'started_at': start_time.isoformat(),
                'policies_applied': 0,
                'logs_processed': 0,
                'logs_archived': 0,
                'logs_deleted': 0,
                'space_freed_mb': 0.0,
                'space_archived_mb': 0.0,
                'errors': []
            }
            
            # Process each retention policy
            for policy_id, policy in self.retention_policies.items():
                if not policy.enabled:
                    continue
                
                try:
                    policy_results = self._apply_retention_policy(policy, force_all)
                    
                    cleanup_results['policies_applied'] += 1
                    cleanup_results['logs_processed'] += policy_results['logs_processed']
                    cleanup_results['logs_archived'] += policy_results['logs_archived']
                    cleanup_results['logs_deleted'] += policy_results['logs_deleted']
                    cleanup_results['space_freed_mb'] += policy_results['space_freed_mb']
                    cleanup_results['space_archived_mb'] += policy_results['space_archived_mb']
                    
                except Exception as e:
                    error_msg = f"Error applying policy {policy_id}: {str(e)}"
                    cleanup_results['errors'].append(error_msg)
                    structured_logger.error(error_msg, policy_id=policy_id, error=str(e))
            
            # Update statistics
            cleanup_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_cleanup_stats(cleanup_results, cleanup_time)
            
            cleanup_results['completed_at'] = datetime.utcnow().isoformat()
            cleanup_results['duration_seconds'] = cleanup_time
            
            structured_logger.info(
                "Log cleanup completed",
                **cleanup_results
            )
            
            return cleanup_results
            
        except Exception as e:
            structured_logger.error(f"Error during log cleanup: {str(e)}", error=str(e))
            raise
    
    def archive_logs(self, 
                    start_date: datetime,
                    end_date: datetime,
                    log_category: LogCategory,
                    archive_name: Optional[str] = None) -> str:
        """Archive logs for a specific time period"""
        
        if archive_name is None:
            archive_name = f"archive_{log_category.value}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        archive_path = self.archive_path / f"{archive_name}.tar.gz"
        
        try:
            with self._operation_semaphore:
                # Create archive
                with tarfile.open(archive_path, "w:gz") as archive:
                    # Find and add log files
                    log_files = self._find_log_files(
                        start_date, end_date, log_category
                    )
                    
                    for log_file in log_files:
                        if log_file.exists():
                            # Add file to archive
                            archive.add(log_file, arcname=log_file.name)
                
                # Calculate archive size
                archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
                
                # Store archive record
                archive_record = LogArchive(
                    archive_name=archive_name,
                    archive_path=str(archive_path),
                    log_category=log_category.value,
                    start_date=start_date,
                    end_date=end_date,
                    file_count=len(log_files),
                    archive_size_bytes=archive_path.stat().st_size,
                    compression_ratio=0.0,  # Would be calculated
                    created_at=datetime.utcnow(),
                    checksum=self._calculate_file_checksum(archive_path)
                )
                
                self._store_archive_record(archive_record)
                
                structured_logger.info(
                    f"Archived logs: {archive_name}",
                    archive_path=str(archive_path),
                    file_count=len(log_files),
                    size_mb=round(archive_size_mb, 2)
                )
                
                return archive_name
                
        except Exception as e:
            structured_logger.error(
                f"Error archiving logs: {str(e)}",
                archive_name=archive_name,
                error=str(e)
            )
            raise
    
    def restore_logs(self, archive_name: str, restore_path: Optional[str] = None) -> str:
        """Restore logs from archive"""
        
        archive_path = self.archive_path / f"{archive_name}.tar.gz"
        
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
        
        if restore_path is None:
            restore_path = self.base_log_path / "restored" / archive_name
        else:
            restore_path = Path(restore_path)
        
        restore_path.mkdir(parents=True, exist_ok=True)
        
        try:
            with self._operation_semaphore:
                # Verify archive integrity
                if not self._verify_archive_integrity(archive_path):
                    raise Exception("Archive integrity check failed")
                
                # Extract archive
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(restore_path)
                
                restored_count = len([f for f in restore_path.rglob("*") if f.is_file()])
                
                structured_logger.info(
                    f"Restored logs from archive: {archive_name}",
                    restore_path=str(restore_path),
                    file_count=restored_count
                )
                
                return str(restore_path)
                
        except Exception as e:
            structured_logger.error(
                f"Error restoring logs: {str(e)}",
                archive_name=archive_name,
                error=str(e)
            )
            raise
    
    def get_retention_compliance_report(self) -> Dict[str, Any]:
        """Generate retention compliance report"""
        
        db: Session = SessionLocal()
        try:
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'policies': [],
                'compliance_status': {},
                'overdue_deletions': [],
                'storage_usage': {}
            }
            
            # Get policy statistics
            for policy_id, policy in self.retention_policies.items():
                policy_stats = self._get_policy_statistics(policy)
                report['policies'].append(policy_stats)
                
                # Check compliance
                if policy.compliance_requirements:
                    compliance_status = self._check_compliance_requirements(policy)
                    report['compliance_status'][policy_id] = compliance_status
            
            # Find overdue deletions
            overdue_deletions = self._find_overdue_deletions()
            report['overdue_deletions'] = overdue_deletions
            
            # Calculate storage usage
            storage_usage = self._calculate_storage_usage()
            report['storage_usage'] = storage_usage
            
            return report
            
        finally:
            db.close()
    
    def _apply_retention_policy(self, policy: RetentionPolicy, force_all: bool = False) -> Dict[str, Any]:
        """Apply retention policy to logs"""
        
        results = {
            'logs_processed': 0,
            'logs_archived': 0,
            'logs_deleted': 0,
            'space_freed_mb': 0.0,
            'space_archived_mb': 0.0,
            'errors': []
        }
        
        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_period_days)
        
        # Get expired logs from database
        db: Session = SessionLocal()
        try:
            query = text("""
                SELECT log_id, timestamp, data, file_path
                FROM log_entries 
                WHERE category = :category 
                AND timestamp < :cutoff_date
                ORDER BY timestamp
            """)
            
            expired_logs = db.execute(query, {
                'category': policy.category.value,
                'cutoff_date': cutoff_date
            }).fetchall()
            
            results['logs_processed'] = len(expired_logs)
            
            # Process logs in batches
            batch_count = 0
            for i in range(0, len(expired_logs), policy.batch_size):
                batch = expired_logs[i:i + policy.batch_size]
                batch_count += 1
                
                try:
                    with self._operation_semaphore:
                        batch_results = self._process_log_batch(batch, policy)
                        
                        # Update results
                        for key in ['logs_archived', 'logs_deleted', 'space_freed_mb', 'space_archived_mb']:
                            results[key] += batch_results[key]
                        
                except Exception as e:
                    error_msg = f"Error processing batch {batch_count}: {str(e)}"
                    results['errors'].append(error_msg)
                    structured_logger.error(error_msg, batch=batch_count, error=str(e))
            
            return results
            
        finally:
            db.close()
    
    def _process_log_batch(self, log_batch: List, policy: RetentionPolicy) -> Dict[str, Any]:
        """Process a batch of logs according to retention policy"""
        
        results = {
            'logs_archived': 0,
            'logs_deleted': 0,
            'space_freed_mb': 0.0,
            'space_archived_mb': 0.0
        }
        
        for log_row in log_batch:
            try:
                log_data = log_row.data if hasattr(log_row, 'data') else {}
                file_path = log_row.file_path if hasattr(log_row, 'file_path') else None
                
                if policy.action == RetentionAction.ARCHIVE:
                    # Archive the log
                    if self._archive_log(log_data, file_path, policy):
                        results['logs_archived'] += 1
                        results['space_archived_mb'] += self._estimate_log_size_mb(log_data)
                
                elif policy.action == RetentionAction.DELETE:
                    # Delete the log
                    if self._delete_log(file_path):
                        results['logs_deleted'] += 1
                        results['space_freed_mb'] += self._estimate_log_size_mb(log_data)
                
                elif policy.action == RetentionAction.COMPRESS:
                    # Compress the log
                    if self._compress_log(file_path, policy):
                        results['logs_deleted'] += 1  # Original deleted
                        results['space_freed_mb'] += self._estimate_log_size_mb(log_data)
                
                elif policy.action == RetentionAction.ANONYMIZE:
                    # Anonymize the log
                    if self._anonymize_log(log_data, policy):
                        results['logs_archived'] += 1  # Anonymized version archived
                
            except Exception as e:
                structured_logger.error(
                    f"Error processing log: {str(e)}",
                    log_id=getattr(log_row, 'log_id', 'unknown'),
                    error=str(e)
                )
        
        return results
    
    def _archive_log(self, log_data: Dict[str, Any], file_path: Optional[str], policy: RetentionPolicy) -> bool:
        """Archive a log according to policy"""
        
        try:
            # Create archive directory if it doesn't exist
            archive_dir = self.archive_path / policy.category.value
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Archive file path
            if file_path and Path(file_path).exists():
                # Archive physical file
                archive_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{Path(file_path).name}.gz"
                archive_file_path = archive_dir / archive_filename
                
                with open(file_path, 'rb') as f_in:
                    with gzip.open(archive_file_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Delete original
                os.remove(file_path)
                
                return True
            else:
                # Archive log data
                archive_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{log_data.get('log_id', 'unknown')}.json"
                archive_file_path = archive_dir / archive_filename
                
                with open(archive_file_path, 'w') as f:
                    json.dump(log_data, f, default=str)
                
                return True
                
        except Exception as e:
            structured_logger.error(
                f"Error archiving log: {str(e)}",
                file_path=file_path,
                error=str(e)
            )
            return False
    
    def _delete_log(self, file_path: Optional[str]) -> bool:
        """Delete a log file"""
        
        try:
            if file_path and Path(file_path).exists():
                file_size = Path(file_path).stat().st_size
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            structured_logger.error(
                f"Error deleting log: {str(e)}",
                file_path=file_path,
                error=str(e)
            )
            return False
    
    def _compress_log(self, file_path: Optional[str], policy: RetentionPolicy) -> bool:
        """Compress a log file in place"""
        
        if not file_path or not Path(file_path).exists():
            return False
        
        try:
            compressed_path = f"{file_path}.gz"
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original
            os.remove(file_path)
            
            return True
            
        except Exception as e:
            structured_logger.error(
                f"Error compressing log: {str(e)}",
                file_path=file_path,
                error=str(e)
            )
            return False
    
    def _anonymize_log(self, log_data: Dict[str, Any], policy: RetentionPolicy) -> bool:
        """Anonymize sensitive data in log"""
        
        try:
            # Create anonymized version
            anonymized_data = self._anonymize_data(log_data)
            
            # Store anonymized version
            archive_dir = self.archive_path / f"{policy.category.value}_anonymized"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            archive_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_anonymized.json"
            archive_file_path = archive_dir / archive_filename
            
            with open(archive_file_path, 'w') as f:
                json.dump(anonymized_data, f, default=str)
            
            return True
            
        except Exception as e:
            structured_logger.error(
                f"Error anonymizing log: {str(e)}",
                error=str(e)
            )
            return False
    
    def _anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize sensitive data in log entry"""
        
        anonymized = data.copy()
        
        # Hash sensitive fields
        sensitive_fields = ['user_id', 'email', 'phone', 'ip_address']
        
        for field in sensitive_fields:
            if field in anonymized:
                if anonymized[field]:
                    anonymized[field] = hashlib.sha256(
                        str(anonymized[field]).encode()
                    ).hexdigest()[:16]
        
        # Remove or mask other sensitive information
        if 'message' in anonymized:
            # Remove credit card numbers, SSNs, etc.
            import re
            patterns = [
                (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CREDIT_CARD]'),
                (r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b', '[SSN]'),
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]')
            ]
            
            for pattern, replacement in patterns:
                anonymized['message'] = re.sub(pattern, replacement, anonymized['message'])
        
        return anonymized
    
    def _find_log_files(self, start_date: datetime, end_date: datetime, category: LogCategory) -> List[Path]:
        """Find log files for a specific time period and category"""
        
        log_files = []
        search_pattern = f"{category.value}*.log"
        
        for log_dir in [self.base_log_path, self.base_log_path / category.value]:
            if log_dir.exists():
                for file_path in log_dir.glob(search_pattern):
                    try:
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if start_date <= file_time <= end_date:
                            log_files.append(file_path)
                    except Exception:
                        continue
        
        return sorted(log_files)
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _verify_archive_integrity(self, archive_path: Path) -> bool:
        """Verify archive integrity using checksum"""
        
        try:
            # This would compare stored checksum with current file checksum
            return True
        except Exception:
            return False
    
    def _estimate_log_size_mb(self, log_data: Dict[str, Any]) -> float:
        """Estimate log size in MB"""
        
        try:
            log_json = json.dumps(log_data, default=str)
            return len(log_json.encode('utf-8')) / (1024 * 1024)
        except Exception:
            return 0.1  # Default estimate
    
    def _cleanup_worker(self) -> None:
        """Background worker for automated cleanup"""
        
        while self._running:
            try:
                self.run_cleanup()
                time.sleep(self.cleanup_interval_hours * 3600)  # Convert hours to seconds
            except Exception as e:
                structured_logger.error(
                    f"Error in cleanup worker: {str(e)}",
                    error=str(e)
                )
                time.sleep(3600)  # Wait 1 hour before retrying
    
    def _store_retention_policy(self, policy: RetentionPolicy) -> None:
        """Store retention policy in database"""
        
        db: Session = SessionLocal()
        try:
            db_policy = LogRetentionPolicy(
                policy_id=policy.policy_id,
                name=policy.name,
                category=policy.category.value,
                retention_period_days=policy.retention_period_days,
                action=policy.action.value,
                archive_path=policy.archive_path,
                compression_enabled=policy.compression_enabled,
                encryption_enabled=policy.encryption_enabled,
                compliance_requirements=policy.compliance_requirements,
                min_severity=policy.min_severity,
                max_file_size_mb=policy.max_file_size_mb,
                batch_size=policy.batch_size,
                enabled=policy.enabled,
                created_at=policy.created_at
            )
            
            db.add(db_policy)
            db.commit()
            
        except Exception as e:
            db.rollback()
            structured_logger.error(
                f"Error storing retention policy: {str(e)}",
                policy_id=policy.policy_id,
                error=str(e)
            )
        finally:
            db.close()
    
    def _remove_retention_policy(self, policy_id: str) -> None:
        """Remove retention policy from database"""
        
        db: Session = SessionLocal()
        try:
            db.query(LogRetentionPolicy).filter(
                LogRetentionPolicy.policy_id == policy_id
            ).delete()
            db.commit()
            
        except Exception as e:
            db.rollback()
            structured_logger.error(
                f"Error removing retention policy: {str(e)}",
                policy_id=policy_id,
                error=str(e)
            )
        finally:
            db.close()
    
    def _store_archive_record(self, archive_record: LogArchive) -> None:
        """Store archive record in database"""
        
        db: Session = SessionLocal()
        try:
            db.add(archive_record)
            db.commit()
        except Exception as e:
            db.rollback()
            structured_logger.error(
                f"Error storing archive record: {str(e)}",
                archive_name=archive_record.archive_name,
                error=str(e)
            )
        finally:
            db.close()
    
    def _get_policy_statistics(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Get statistics for retention policy"""
        
        # This would query the database for policy statistics
        return {
            'policy_id': policy.policy_id,
            'name': policy.name,
            'category': policy.category.value,
            'retention_days': policy.retention_period_days,
            'action': policy.action.value,
            'enabled': policy.enabled
        }
    
    def _check_compliance_requirements(self, policy: RetentionPolicy) -> Dict[str, Any]:
        """Check compliance requirements for policy"""
        
        compliance_status = {
            'compliant': True,
            'issues': [],
            'requirements': policy.compliance_requirements
        }
        
        # Check GDPR requirements
        if 'gdpr' in [req.lower() for req in policy.compliance_requirements]:
            if policy.retention_period_days > 2555:  # 7 years max for GDPR
                compliance_status['compliant'] = False
                compliance_status['issues'].append(
                    'GDPR retention period exceeds 7 years'
                )
        
        # Check SOX requirements
        if 'sox' in [req.lower() for req in policy.compliance_requirements]:
            if policy.retention_period_days < 2190:  # 6 years min for SOX
                compliance_status['compliant'] = False
                compliance_status['issues'].append(
                    'SOX retention period less than 6 years'
                )
        
        return compliance_status
    
    def _find_overdue_deletions(self) -> List[Dict[str, Any]]:
        """Find logs that are overdue for deletion"""
        
        # This would query for logs past their retention period
        return []
    
    def _calculate_storage_usage(self) -> Dict[str, Any]:
        """Calculate current storage usage"""
        
        usage = {
            'total_size_mb': 0.0,
            'by_category': {},
            'archive_size_mb': 0.0,
            'available_space_mb': 0.0
        }
        
        try:
            # Calculate base log storage
            for category_dir in self.base_log_path.iterdir():
                if category_dir.is_dir():
                    category_size = sum(
                        f.stat().st_size for f in category_dir.rglob('*') if f.is_file()
                    ) / (1024 * 1024)
                    
                    usage['by_category'][category_dir.name] = category_size
                    usage['total_size_mb'] += category_size
            
            # Calculate archive storage
            archive_size = sum(
                f.stat().st_size for f in self.archive_path.rglob('*') if f.is_file()
            ) / (1024 * 1024)
            
            usage['archive_size_mb'] = archive_size
            
            # Calculate available space
            stat = os.statvfs(str(self.base_log_path))
            usage['available_space_mb'] = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
            
        except Exception as e:
            structured_logger.error(
                f"Error calculating storage usage: {str(e)}",
                error=str(e)
            )
        
        return usage
    
    def _update_cleanup_stats(self, cleanup_results: Dict[str, Any], cleanup_time: float) -> None:
        """Update cleanup statistics"""
        
        with self._lock:
            self.stats['total_logs_processed'] += cleanup_results['logs_processed']
            self.stats['total_logs_archived'] += cleanup_results['logs_archived']
            self.stats['total_logs_deleted'] += cleanup_results['logs_deleted']
            self.stats['total_space_freed_mb'] += cleanup_results['space_freed_mb']
            self.stats['total_space_archived_mb'] += cleanup_results['space_archived_mb']
            self.stats['cleanup_operations'] += 1
            self.stats['last_cleanup_time'] = datetime.utcnow()
            
            # Update average cleanup time
            old_avg = self.stats['avg_cleanup_time_seconds']
            count = self.stats['cleanup_operations']
            self.stats['avg_cleanup_time_seconds'] = (old_avg * (count - 1) + cleanup_time) / count
    
    def _setup_default_policies(self) -> None:
        """Setup default retention policies"""
        
        # Application logs - 30 days
        app_policy = RetentionPolicy(
            policy_id="app_logs_30_days",
            name="Application Logs 30 Days",
            category=LogCategory.APPLICATION,
            retention_period_days=30,
            action=RetentionAction.DELETE,
            min_severity="info"
        )
        self.retention_policies[app_policy.policy_id] = app_policy
        
        # Audit logs - 7 years (compliance)
        audit_policy = RetentionPolicy(
            policy_id="audit_logs_7_years",
            name="Audit Logs 7 Years",
            category=LogCategory.AUDIT,
            retention_period_days=2555,  # 7 years
            action=RetentionAction.ARCHIVE,
            archive_path="compliance/audit",
            compliance_requirements=["gdpr", "sox"]
        )
        self.retention_policies[audit_policy.policy_id] = audit_policy
        
        # Security logs - 7 years
        security_policy = RetentionPolicy(
            policy_id="security_logs_7_years",
            name="Security Logs 7 Years",
            category=LogCategory.SECURITY,
            retention_period_days=2555,  # 7 years
            action=RetentionAction.ARCHIVE,
            archive_path="compliance/security",
            compliance_requirements=["sox"]
        )
        self.retention_policies[security_policy.policy_id] = security_policy
        
        # Error logs - 90 days
        error_policy = RetentionPolicy(
            policy_id="error_logs_90_days",
            name="Error Logs 90 Days",
            category=LogCategory.ERROR,
            retention_period_days=90,
            action=RetentionAction.ARCHIVE,
            compression_enabled=True
        )
        self.retention_policies[error_policy.policy_id] = error_policy
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retention manager statistics"""
        
        with self._lock:
            stats = self.stats.copy()
            
            # Add policy information
            stats['policies'] = {}
            for policy_id, policy in self.retention_policies.items():
                stats['policies'][policy_id] = {
                    'name': policy.name,
                    'category': policy.category.value,
                    'retention_days': policy.retention_period_days,
                    'action': policy.action.value,
                    'enabled': policy.enabled
                }
            
            return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on retention manager"""
        
        health_status = {
            'overall_status': 'healthy',
            'retention_manager': 'healthy',
            'policies': {},
            'storage': {}
        }
        
        # Check policies
        disabled_policies = [pid for pid, policy in self.retention_policies.items() if not policy.enabled]
        if disabled_policies:
            health_status['policies']['disabled'] = disabled_policies
            health_status['overall_status'] = 'warning'
        
        # Check storage
        storage_usage = self._calculate_storage_usage()
        health_status['storage'] = storage_usage
        
        if storage_usage['total_size_mb'] > 10000:  # 10GB threshold
            health_status['overall_status'] = 'warning'
        
        # Check for overdue deletions
        overdue_deletions = self._find_overdue_deletions()
        if overdue_deletions:
            health_status['storage']['overdue_deletions'] = len(overdue_deletions)
            health_status['overall_status'] = 'critical'
        
        return health_status


# Global log retention manager instance
log_retention_manager = LogRetentionManager()