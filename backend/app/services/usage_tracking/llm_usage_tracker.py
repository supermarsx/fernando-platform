"""
LLM Usage Tracker

Advanced LLM usage tracking with:
- Detailed token counting and cost calculation
- Model-specific usage patterns
- Performance metrics collection
- Real-time usage monitoring
"""

import time
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.credit import (
    CreditUsageRecord, LLMUsageMetrics, LLMModelType
)
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel
from app.services.credit_service import CreditService


class LLMUsageTracker:
    """
    Advanced LLM usage tracking and monitoring
    """
    
    def __init__(self, db: Session, credit_service: CreditService):
        self.db = db
        self.credit_service = credit_service
        
        # Token estimation for different models
        self.token_estimates = {
            "gpt-3.5-turbo": {
                "chars_per_token": 4.0,
                "words_per_token": 0.75
            },
            "gpt-4": {
                "chars_per_token": 4.0,
                "words_per_token": 0.75
            },
            "claude-3-sonnet": {
                "chars_per_token": 3.5,
                "words_per_token": 0.8
            },
            "claude-3-haiku": {
                "chars_per_token": 3.5,
                "words_per_token": 0.8
            },
            "local_model": {
                "chars_per_token": 4.0,
                "words_per_token": 0.75
            }
        }
        
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def start_usage_session(
        self,
        session_id: str,
        user_id: int,
        model_type: str,
        operation_type: str = "llm_request",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new usage tracking session
        
        Args:
            session_id: Unique session identifier
            user_id: User performing the operation
            model_type: LLM model being used
            operation_type: Type of operation
            context: Additional context information
        
        Returns:
            Session tracking token
        """
        tracking_data = {
            "session_id": session_id,
            "user_id": user_id,
            "model_type": model_type,
            "operation_type": operation_type,
            "context": context or {},
            "start_time": datetime.utcnow(),
            "tokens_estimate": 0,
            "cost_estimate": 0.0,
            "request_count": 0,
            "success_count": 0,
            "error_count": 0,
            "total_response_time": 0,
            "metadata": {}
        }
        
        self.active_sessions[session_id] = tracking_data
        
        return session_id
    
    def estimate_tokens(
        self,
        text: str,
        model_type: str,
        include_overhead: bool = True
    ) -> int:
        """
        Estimate tokens for text using model-specific calculations
        
        Args:
            text: Text to estimate tokens for
            model_type: LLM model type
            include_overhead: Include overhead for request structure
        
        Returns:
            Estimated token count
        """
        if model_type not in self.token_estimates:
            # Fallback to general estimate
            return max(1, len(text) // 4)
        
        estimator = self.token_estimates[model_type]
        
        # Basic token count
        base_tokens = max(1, len(text) // int(estimator["chars_per_token"]))
        
        if include_overhead:
            # Add overhead for system prompts, formatting, etc.
            overhead_tokens = 50  # Base overhead
            total_tokens = base_tokens + overhead_tokens
        else:
            total_tokens = base_tokens
        
        return total_tokens
    
    def track_request_start(
        self,
        session_id: str,
        prompt: str,
        request_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track the start of an LLM request
        
        Args:
            session_id: Session identifier
            prompt: User prompt
            request_params: Request parameters
        
        Returns:
            Request tracking information
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = self.active_sessions[session_id]
        
        # Estimate tokens
        prompt_tokens = self.estimate_tokens(prompt, session_data["model_type"])
        
        # Track request start
        request_info = {
            "request_id": f"req_{int(time.time() * 1000)}_{session_data['request_count']}",
            "session_id": session_id,
            "start_time": datetime.utcnow(),
            "prompt_tokens": prompt_tokens,
            "prompt_length": len(prompt),
            "request_params": request_params or {},
            "model_type": session_data["model_type"]
        }
        
        session_data["request_count"] += 1
        session_data["tokens_estimate"] += prompt_tokens
        
        # Store in session metadata
        if "requests" not in session_data["metadata"]:
            session_data["metadata"]["requests"] = []
        session_data["metadata"]["requests"].append(request_info)
        
        return request_info
    
    def track_request_complete(
        self,
        session_id: str,
        request_id: str,
        response: str,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Track completion of an LLM request
        
        Args:
            session_id: Session identifier
            request_id: Request identifier from track_request_start
            response: LLM response
            completion_tokens: Actual completion tokens (if available)
            total_tokens: Total tokens used (if available)
            success: Whether request was successful
            error_message: Error message if failed
            response_time_ms: Response time in milliseconds
        
        Returns:
            Completion tracking information
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_data = self.active_sessions[session_id]
        end_time = datetime.utcnow()
        
        # Calculate actual token counts
        if completion_tokens is None:
            completion_tokens = self.estimate_tokens(response, session_data["model_type"])
        
        if total_tokens is None:
            # Find request info to get prompt tokens
            request_info = None
            for req in session_data["metadata"]["requests"]:
                if req["request_id"] == request_id:
                    request_info = req
                    break
            
            if request_info:
                total_tokens = request_info["prompt_tokens"] + completion_tokens
            else:
                total_tokens = completion_tokens
        
        # Calculate cost
        try:
            model_type_enum = LLMModelType(session_data["model_type"].replace("-", "_").lower())
            cost, cost_breakdown = self.credit_service.calculate_llm_cost(
                model_type=model_type_enum,
                prompt_tokens=request_info["prompt_tokens"] if 'request_info' in locals() else 0,
                completion_tokens=completion_tokens
            )
        except Exception:
            # Fallback cost calculation
            cost = (total_tokens / 1000) * 0.01  # Default $0.01 per 1K tokens
            cost_breakdown = {"method": "fallback", "total_tokens": total_tokens}
        
        # Update session statistics
        if success:
            session_data["success_count"] += 1
        else:
            session_data["error_count"] += 1
        
        if response_time_ms:
            session_data["total_response_time"] += response_time_ms
        
        # Update total cost estimate
        session_data["cost_estimate"] += cost
        
        # Complete request tracking
        for i, req in enumerate(session_data["metadata"]["requests"]):
            if req["request_id"] == request_id:
                session_data["metadata"]["requests"][i].update({
                    "end_time": end_time,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "response_length": len(response),
                    "success": success,
                    "error_message": error_message,
                    "response_time_ms": response_time_ms,
                    "cost": cost,
                    "cost_breakdown": cost_breakdown
                })
                break
        
        completion_info = {
            "request_id": request_id,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "success": success,
            "response_time_ms": response_time_ms,
            "cost_breakdown": cost_breakdown
        }
        
        return completion_info
    
    def finalize_usage_session(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> Optional[CreditUsageRecord]:
        """
        Finalize usage session and create usage record
        
        Args:
            session_id: Session identifier
            user_id: User ID (if not in session)
            resource_id: Associated resource ID
            endpoint: API endpoint
        
        Returns:
            Created usage record
        """
        if session_id not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[session_id]
        
        # Use user_id from session if not provided
        effective_user_id = user_id or session_data["user_id"]
        
        # Calculate aggregate metrics
        avg_response_time = None
        if session_data["total_response_time"] > 0 and session_data["success_count"] > 0:
            avg_response_time = session_data["total_response_time"] / session_data["success_count"]
        
        # Create usage record
        usage_data = {
            "account_id": self._get_account_id(effective_user_id),
            "service_type": "llm",
            "operation_type": session_data["operation_type"],
            "resource_id": resource_id,
            "quantity_used": session_data["tokens_estimate"],
            "unit_type": "tokens",
            "cost_per_unit": session_data["cost_estimate"] / max(1, session_data["tokens_estimate"]),
            "total_cost": session_data["cost_estimate"],
            "prompt_tokens": sum(req.get("prompt_tokens", 0) for req in session_data["metadata"]["requests"]),
            "completion_tokens": sum(req.get("completion_tokens", 0) for req in session_data["metadata"]["requests"]),
            "model_used": session_data["model_type"],
            "response_time_ms": int(avg_response_time) if avg_response_time else None,
            "success": session_data["error_count"] == 0,
            "endpoint": endpoint,
            "metadata": {
                "session_id": session_id,
                "request_count": session_data["request_count"],
                "success_count": session_data["success_count"],
                "error_count": session_data["error_count"],
                "total_response_time_ms": session_data["total_response_time"],
                "requests": session_data["metadata"]["requests"],
                "context": session_data["context"],
                "duration_seconds": (datetime.utcnow() - session_data["start_time"]).total_seconds()
            }
        }
        
        from app.schemas.credit_schemas import CreditUsageRecordCreate
        usage_record = self.credit_service.record_usage(
            user_id=effective_user_id,
            usage_data=CreditUsageRecordCreate(**usage_data)
        )
        
        # Log telemetry
        try:
            telemetry_event(
                event_name="llm.session_completed",
                event_type=TelemetryEvent.SYSTEM_EVENT,
                level=TelemetryLevel.INFO,
                user_id=effective_user_id,
                metadata={
                    "session_id": session_id,
                    "request_count": session_data["request_count"],
                    "total_tokens": session_data["tokens_estimate"],
                    "total_cost": session_data["cost_estimate"],
                    "success_rate": session_data["success_count"] / max(1, session_data["request_count"]),
                    "avg_response_time_ms": avg_response_time,
                    "model_type": session_data["model_type"],
                    "operation_type": session_data["operation_type"]
                }
            )
        except Exception:
            pass
        
        # Clean up session
        del self.active_sessions[session_id]
        
        return usage_record
    
    def get_real_time_usage(
        self,
        user_id: int,
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Get real-time usage statistics for user
        
        Args:
            user_id: User ID
            time_window_minutes: Time window in minutes
        
        Returns:
            Real-time usage statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        # Get recent usage records
        usage_records = self.db.query(CreditUsageRecord).join(
            CreditAccount, CreditUsageRecord.account_id == CreditAccount.id
        ).filter(
            and_(
                CreditAccount.user_id == user_id,
                CreditUsageRecord.created_at >= cutoff_time
            )
        ).all()
        
        # Calculate real-time metrics
        total_requests = len(usage_records)
        total_tokens = sum(record.total_cost / record.cost_per_unit for record in usage_records if record.cost_per_unit > 0)
        total_cost = sum(record.total_cost for record in usage_records)
        
        # Success rate
        successful_requests = sum(1 for record in usage_records if record.success)
        success_rate = successful_requests / max(1, total_requests)
        
        # Response time metrics
        response_times = [record.response_time_ms for record in usage_records if record.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        # Model distribution
        model_usage = {}
        for record in usage_records:
            model = record.model_used or "unknown"
            if model not in model_usage:
                model_usage[model] = {"requests": 0, "tokens": 0, "cost": 0}
            model_usage[model]["requests"] += 1
            model_usage[model]["tokens"] += record.total_cost / record.cost_per_unit if record.cost_per_unit > 0 else 0
            model_usage[model]["cost"] += record.total_cost
        
        # Active sessions
        active_sessions_count = len([s for s in self.active_sessions.values() if s["user_id"] == user_id])
        
        return {
            "user_id": user_id,
            "time_window_minutes": time_window_minutes,
            "total_requests": total_requests,
            "total_tokens": int(total_tokens),
            "total_cost": round(total_cost, 6),
            "success_rate": success_rate,
            "avg_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
            "model_distribution": model_usage,
            "active_sessions": active_sessions_count,
            "last_request_time": max(record.created_at for record in usage_records) if usage_records else None
        }
    
    def aggregate_usage_metrics(
        self,
        aggregation_period: str = "hourly",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        model_filter: Optional[str] = None
    ) -> List[LLMUsageMetrics]:
        """
        Aggregate usage metrics for analytics
        
        Args:
            aggregation_period: Period for aggregation (hourly, daily, monthly)
            start_time: Start time for aggregation
            end_time: End time for aggregation
            model_filter: Filter by model type
        
        Returns:
            List of aggregated metrics
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=30)
        if not end_time:
            end_time = datetime.utcnow()
        
        # Group usage records by period and model
        # This is a simplified aggregation - in production, you'd want more sophisticated logic
        
        # Get usage records in time range
        query = self.db.query(CreditUsageRecord).filter(
            and_(
                CreditUsageRecord.created_at >= start_time,
                CreditUsageRecord.created_at <= end_time,
                CreditUsageRecord.service_type == "llm"
            )
        )
        
        if model_filter:
            query = query.filter(CreditUsageRecord.model_used == model_filter)
        
        usage_records = query.all()
        
        # Group by model and aggregate
        aggregated_data = {}
        
        for record in usage_records:
            model = record.model_used or "unknown"
            if model not in aggregated_data:
                aggregated_data[model] = {
                    "total_requests": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_cost": 0.0,
                    "response_times": [],
                    "success_count": 0,
                    "users": set()
                }
            
            data = aggregated_data[model]
            data["total_requests"] += 1
            data["total_prompt_tokens"] += record.prompt_tokens or 0
            data["total_completion_tokens"] += record.completion_tokens or 0
            data["total_cost"] += record.total_cost
            
            if record.response_time_ms:
                data["response_times"].append(record.response_time_ms)
            
            if record.success:
                data["success_count"] += 1
        
        # Create aggregated metrics records
        metrics_records = []
        for model, data in aggregated_data.items():
            # Calculate period boundaries
            if aggregation_period == "hourly":
                period_start = start_time.replace(minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(hours=1)
            elif aggregation_period == "daily":
                period_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1)
            else:  # monthly
                period_start = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=31)  # Approximate
        
            avg_response_time = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else None
            success_rate = data["success_count"] / max(1, data["total_requests"])
            
            # Get unique users count
            unique_users = len(data["users"])  # This would need proper user linking in production
            
            metrics_record = LLMUsageMetrics(
                aggregation_period=aggregation_period,
                period_start=period_start,
                period_end=period_end,
                model_type=LLMModelType(model.replace("_", "-").lower()) if model != "unknown" else LLMModelType.GPT35_TURBO,
                total_requests=data["total_requests"],
                total_prompt_tokens=data["total_prompt_tokens"],
                total_completion_tokens=data["total_completion_tokens"],
                total_cost=data["total_cost"],
                avg_response_time_ms=avg_response_time,
                success_rate=success_rate,
                unique_users=unique_users
            )
            
            metrics_records.append(metrics_record)
        
        # Save to database
        for record in metrics_records:
            self.db.add(record)
        self.db.commit()
        
        return metrics_records
    
    def _get_account_id(self, user_id: int) -> int:
        """Get credit account ID for user"""
        from app.models.credit import CreditAccount, CreditStatus
        
        account = self.db.query(CreditAccount).filter(
            and_(
                CreditAccount.user_id == user_id,
                CreditAccount.status == CreditStatus.ACTIVE
            )
        ).first()
        
        if not account:
            # Create account if doesn't exist
            from app.schemas.credit_schemas import CreditAccountCreate
            account = self.credit_service.create_credit_account(
                CreditAccountCreate(user_id=user_id)
            )
        
        return account.id