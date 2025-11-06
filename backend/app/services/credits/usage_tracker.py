"""
Usage Tracker Service

Real-time LLM usage tracking and cost calculation service.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.models.credits import (
    LLMUsageRecord, LLMProvider, CreditBalance, CreditTransaction, 
    CreditTransactionType, CreditStatus, LLMModelPricing
)
from app.models.credits import LlmPricingService
from app.services.credits.credit_manager import CreditManager
from app.db.session import get_db

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Real-time LLM usage tracking and cost calculation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.pricing_service = LlmPricingService(db)
        self.credit_manager = CreditManager(db)
    
    def track_llm_usage(self, user_id: int, provider: str, model_name: str,
                      prompt_tokens: int, completion_tokens: int,
                      operation_type: str = "text_generation",
                      request_id: Optional[str] = None,
                      session_id: Optional[str] = None,
                      document_id: Optional[str] = None,
                      job_id: Optional[str] = None,
                      organization_id: Optional[int] = None,
                      response_time_ms: Optional[int] = None,
                      error_occurred: bool = False,
                      error_code: Optional[str] = None,
                      error_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Track LLM usage and calculate costs
        """
        try:
            # Calculate cost using pricing service
            cost_breakdown = self.pricing_service.calculate_usage_cost(
                provider, model_name, prompt_tokens, completion_tokens
            )
            
            total_cost = cost_breakdown["total_cost_credits"]
            
            # Get or create balance
            balance = self.credit_manager.get_or_create_balance(user_id, organization_id)
            
            # Create usage record
            usage_record = LLMUsageRecord(
                balance_id=balance.id,
                user_id=user_id,
                organization_id=organization_id,
                provider=provider.lower(),
                model_name=model_name,
                operation_type=operation_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_per_1k_prompt_tokens=cost_breakdown["model_pricing"]["prompt_price_per_1k"],
                cost_per_1k_completion_tokens=cost_breakdown["model_pricing"]["completion_price_per_1k"],
                prompt_cost_credits=cost_breakdown["prompt_cost_credits"],
                completion_cost_credits=cost_breakdown["completion_cost_credits"],
                total_cost_credits=total_cost,
                request_id=request_id or f"req_{datetime.utcnow().timestamp()}",
                session_id=session_id,
                document_id=document_id,
                job_id=job_id,
                response_time_ms=response_time_ms,
                error_occurred=error_occurred,
                error_code=error_code,
                error_message=error_message,
                credits_deducted=total_cost if not error_occurred else 0,
                request_start_time=datetime.utcnow(),
                timestamp=datetime.utcnow(),
                request_end_time=datetime.utcnow()
            )
            
            # Deduct credits if no error occurred
            if not error_occurred:
                # Reserve credits first
                if self.credit_manager.check_sufficient_credits(user_id, total_cost, organization_id):
                    if self.credit_manager.reserve_credits(user_id, total_cost, organization_id):
                        # Create credit transaction
                        transaction = self.credit_manager.deduct_credits(
                            user_id=user_id,
                            credit_amount=total_cost,
                            transaction_type=CreditTransactionType.USAGE,
                            description=f"LLM usage: {provider}/{model_name}",
                            reference_type="llm_usage",
                            reference_id=usage_record.request_id,
                            organization_id=organization_id
                        )
                        
                        if transaction:
                            usage_record.transaction_id = self.db.query(CreditTransaction).filter(
                                CreditTransaction.reference_id == usage_record.request_id
                            ).first().id
                        else:
                            logger.error(f"Failed to deduct credits for usage record {usage_record.id}")
                            return {"success": False, "error": "Failed to deduct credits"}
                    else:
                        logger.warning(f"Insufficient credits for user {user_id}: need {total_cost}")
                        return {"success": False, "error": "Insufficient credits"}
                else:
                    logger.warning(f"Insufficient credits for user {user_id}: need {total_cost}")
                    return {"success": False, "error": "Insufficient credits"}
            
            # Save usage record
            self.db.add(usage_record)
            self.db.commit()
            self.db.refresh(usage_record)
            
            logger.info(f"Tracked LLM usage for user {user_id}: {total_cost} credits")
            
            return {
                "success": True,
                "usage_record_id": usage_record.id,
                "request_id": usage_record.request_id,
                "total_cost_credits": total_cost,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "provider": provider,
                "model_name": model_name
            }
            
        except Exception as e:
            logger.error(f"Error tracking LLM usage: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def get_usage_by_date_range(self, user_id: int, start_date: datetime, 
                               end_date: datetime, organization_id: Optional[int] = None) -> List[LLMUsageRecord]:
        """
        Get usage records for user in date range
        """
        query = self.db.query(LLMUsageRecord).filter(
            LLMUsageRecord.user_id == user_id,
            LLMUsageRecord.timestamp >= start_date,
            LLMUsageRecord.timestamp <= end_date
        )
        
        if organization_id:
            query = query.filter(LLMUsageRecord.organization_id == organization_id)
        
        return query.order_by(desc(LLMUsageRecord.timestamp)).all()
    
    def get_usage_summary(self, user_id: int, days: int = 30, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get usage summary for user over specified period
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        usage_records = self.get_usage_by_date_range(user_id, start_date, end_date, organization_id)
        
        if not usage_records:
            return {
                "period_days": days,
                "total_credits_used": 0,
                "total_requests": 0,
                "total_tokens": 0,
                "average_cost_per_request": 0,
                "provider_breakdown": {},
                "model_breakdown": {},
                "daily_usage": []
            }
        
        # Calculate totals
        total_credits = sum(record.total_cost_credits for record in usage_records if not record.error_occurred)
        total_requests = len(usage_records)
        total_tokens = sum(record.total_tokens for record in usage_records if not record.error_occurred)
        total_errors = len([r for r in usage_records if r.error_occurred])
        
        # Provider breakdown
        provider_breakdown = {}
        for record in usage_records:
            provider = record.provider
            if provider not in provider_breakdown:
                provider_breakdown[provider] = {
                    "credits": 0, "requests": 0, "tokens": 0, "errors": 0
                }
            
            if not record.error_occurred:
                provider_breakdown[provider]["credits"] += record.total_cost_credits
                provider_breakdown[provider]["tokens"] += record.total_tokens
            provider_breakdown[provider]["requests"] += 1
            if record.error_occurred:
                provider_breakdown[provider]["errors"] += 1
        
        # Model breakdown
        model_breakdown = {}
        for record in usage_records:
            model = f"{record.provider}/{record.model_name}"
            if model not in model_breakdown:
                model_breakdown[model] = {
                    "credits": 0, "requests": 0, "tokens": 0, "errors": 0
                }
            
            if not record.error_occurred:
                model_breakdown[model]["credits"] += record.total_cost_credits
                model_breakdown[model]["tokens"] += record.total_tokens
            model_breakdown[model]["requests"] += 1
            if record.error_occurred:
                model_breakdown[model]["errors"] += 1
        
        # Daily usage
        daily_usage = {}
        for record in usage_records:
            day = record.timestamp.date().isoformat()
            if day not in daily_usage:
                daily_usage[day] = {"credits": 0, "requests": 0, "tokens": 0}
            
            if not record.error_occurred:
                daily_usage[day]["credits"] += record.total_cost_credits
                daily_usage[day]["tokens"] += record.total_tokens
            daily_usage[day]["requests"] += 1
        
        daily_usage_list = [
            {"date": date, **data} for date, data in sorted(daily_usage.items())
        ]
        
        return {
            "period_days": days,
            "total_credits_used": total_credits,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            "average_cost_per_request": (total_credits / total_requests) if total_requests > 0 else 0,
            "average_tokens_per_request": (total_tokens / total_requests) if total_requests > 0 else 0,
            "provider_breakdown": provider_breakdown,
            "model_breakdown": model_breakdown,
            "daily_usage": daily_usage_list,
            "period_start": start_date,
            "period_end": end_date
        }
    
    def get_top_models(self, user_id: int, limit: int = 10, days: int = 30,
                      organization_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get top used models by user
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query aggregated usage by model
        results = self.db.query(
            LLMUsageRecord.provider,
            LLMUsageRecord.model_name,
            func.sum(LLMUsageRecord.total_cost_credits).label('total_credits'),
            func.sum(LLMUsageRecord.total_tokens).label('total_tokens'),
            func.count(LLMUsageRecord.id).label('request_count'),
            func.avg(LLMUsageRecord.response_time_ms).label('avg_response_time')
        ).filter(
            LLMUsageRecord.user_id == user_id,
            LLMUsageRecord.timestamp >= start_date,
            LLMUsageRecord.timestamp <= end_date,
            LLMUsageRecord.error_occurred == False
        )
        
        if organization_id:
            results = results.filter(LLMUsageRecord.organization_id == organization_id)
        
        results = results.group_by(
            LLMUsageRecord.provider, LLMUsageRecord.model_name
        ).order_by(desc('total_credits')).limit(limit).all()
        
        return [
            {
                "provider": result.provider,
                "model_name": result.model_name,
                "full_model": f"{result.provider}/{result.model_name}",
                "total_credits_used": float(result.total_credits),
                "total_tokens": int(result.total_tokens),
                "request_count": int(result.request_count),
                "average_cost_per_request": float(result.total_credits / result.request_count),
                "average_tokens_per_request": float(result.total_tokens / result.request_count),
                "average_response_time_ms": float(result.avg_response_time) if result.avg_response_time else 0
            }
            for result in results
        ]
    
    def get_usage_trends(self, user_id: int, days: int = 30,
                        organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get usage trends over time
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get daily aggregated usage
        results = self.db.query(
            func.date(LLMUsageRecord.timestamp).label('usage_date'),
            func.sum(LLMUsageRecord.total_cost_credits).label('daily_credits'),
            func.sum(LLMUsageRecord.total_tokens).label('daily_tokens'),
            func.count(LLMUsageRecord.id).label('daily_requests')
        ).filter(
            LLMUsageRecord.user_id == user_id,
            LLMUsageRecord.timestamp >= start_date,
            LLMUsageRecord.timestamp <= end_date,
            LLMUsageRecord.error_occurred == False
        )
        
        if organization_id:
            results = results.filter(LLMUsageRecord.organization_id == organization_id)
        
        results = results.group_by(func.date(LLMUsageRecord.timestamp)).all()
        
        # Convert to list and calculate trends
        daily_data = []
        for result in results:
            daily_data.append({
                "date": result.usage_date.isoformat(),
                "credits_used": float(result.daily_credits),
                "tokens_used": int(result.daily_tokens),
                "requests": int(result.daily_requests)
            })
        
        # Calculate trends
        if len(daily_data) >= 7:
            recent_week = daily_data[-7:]
            previous_week = daily_data[-14:-7] if len(daily_data) >= 14 else []
            
            recent_avg = sum(d["credits_used"] for d in recent_week) / len(recent_week)
            previous_avg = sum(d["credits_used"] for d in previous_week) / len(previous_week) if previous_week else recent_avg
            
            trend = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
        else:
            trend = 0
        
        return {
            "daily_usage": daily_data,
            "trend_percentage": round(trend, 2),
            "trend_direction": "increasing" if trend > 5 else "decreasing" if trend < -5 else "stable",
            "period_days": days,
            "period_start": start_date,
            "period_end": end_date,
            "summary": {
                "total_credits": sum(d["credits_used"] for d in daily_data),
                "total_requests": sum(d["requests"] for d in daily_data),
                "total_tokens": sum(d["tokens_used"] for d in daily_data),
                "average_daily_credits": sum(d["credits_used"] for d in daily_data) / len(daily_data) if daily_data else 0
            }
        }
    
    def get_usage_analytics(self, user_id: int, organization_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive usage analytics
        """
        # Get usage summaries for different time periods
        usage_7d = self.get_usage_summary(user_id, 7, organization_id)
        usage_30d = self.get_usage_summary(user_id, 30, organization_id)
        usage_90d = self.get_usage_summary(user_id, 90, organization_id)
        
        # Get trends
        trends_30d = self.get_usage_trends(user_id, 30, organization_id)
        trends_90d = self.get_usage_trends(user_id, 90, organization_id)
        
        # Get top models
        top_models_30d = self.get_top_models(user_id, 10, 30, organization_id)
        
        return {
            "summary": {
                "last_7_days": usage_7d,
                "last_30_days": usage_30d,
                "last_90_days": usage_90d
            },
            "trends": {
                "last_30_days": trends_30d,
                "last_90_days": trends_90d
            },
            "top_models": top_models_30d,
            "insights": self._generate_usage_insights(usage_30d, trends_30d, top_models_30d)
        }
    
    def _generate_usage_insights(self, usage_30d: Dict[str, Any], 
                               trends: Dict[str, Any], 
                               top_models: List[Dict[str, Any]]) -> List[str]:
        """
        Generate insights from usage data
        """
        insights = []
        
        # High usage insight
        if usage_30d["total_credits_used"] > 10000:
            insights.append(f"High usage detected: {usage_30d['total_credits_used']:.0f} credits in the last 30 days")
        
        # Error rate insight
        if usage_30d["error_rate"] > 10:
            insights.append(f"High error rate: {usage_30d['error_rate']:.1f}% of requests failed")
        elif usage_30d["error_rate"] < 1:
            insights.append("Excellent reliability: Less than 1% error rate")
        
        # Model diversity insight
        if len(top_models) > 5:
            insights.append("Diverse model usage: Using multiple LLM models")
        elif len(top_models) == 1:
            insights.append("Single model usage: Consider exploring other models for different use cases")
        
        # Trend insight
        trend_direction = trends["trend_direction"]
        if trend_direction == "increasing":
            insights.append("Usage is trending upward - consider increasing credit allocation")
        elif trend_direction == "decreasing":
            insights.append("Usage is trending downward - potential cost optimization opportunity")
        
        # Cost efficiency insight
        if usage_30d["average_cost_per_request"] > 50:
            insights.append("High-cost requests detected - consider using more cost-effective models")
        
        return insights


# Utility functions
def get_usage_tracker(db: Session = None) -> UsageTracker:
    """
    Get UsageTracker instance
    """
    if db is None:
        db = next(get_db())
    return UsageTracker(db)


def track_llm_request(user_id: int, provider: str, model_name: str,
                     prompt_tokens: int, completion_tokens: int,
                     db: Session = None, **kwargs) -> Dict[str, Any]:
    """
    Quick function to track LLM request
    """
    tracker = get_usage_tracker(db)
    return tracker.track_llm_usage(
        user_id=user_id,
        provider=provider,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        **kwargs
    )