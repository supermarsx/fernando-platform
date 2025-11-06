"""
Cost Calculator

Real-time cost calculation for LLM and API usage:
- Dynamic pricing models
- Cost optimization recommendations
- Bulk pricing calculations
- Cost forecasting and budgeting
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math

from app.models.credit import LLMModelType


class PricingTier(Enum):
    """Pricing tiers for different usage levels"""
    STANDARD = "standard"
    HIGH_VOLUME = "high_volume"
    ENTERPRISE = "enterprise"


@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    base_cost: float
    token_cost: float
    processing_cost: float
    infrastructure_cost: float
    total_cost: float
    currency: str = "USD"
    cost_per_1k_tokens: float = 0.0
    efficiency_score: float = 0.0


@dataclass
class PricingModel:
    """Pricing model configuration"""
    model_type: LLMModelType
    prompt_cost_per_1k: float
    completion_cost_per_1k: float
    infrastructure_fee: float
    processing_overhead: float
    min_cost_per_request: float
    currency: str = "USD"


class CostCalculator:
    """
    Advanced cost calculation and optimization service
    """
    
    def __init__(self):
        # Base pricing models (updated regularly)
        self.pricing_models = {
            LLMModelType.GPT4: PricingModel(
                model_type=LLMModelType.GPT4,
                prompt_cost_per_1k=0.03,
                completion_cost_per_1k=0.06,
                infrastructure_fee=0.001,
                processing_overhead=0.002,
                min_cost_per_request=0.001,
                currency="USD"
            ),
            LLMModelType.GPT35_TURBO: PricingModel(
                model_type=LLMModelType.GPT35_TURBO,
                prompt_cost_per_1k=0.002,
                completion_cost_per_1k=0.006,
                infrastructure_fee=0.0001,
                processing_overhead=0.0005,
                min_cost_per_request=0.0001,
                currency="USD"
            ),
            LLMModelType.CLAUDE_3_SONNET: PricingModel(
                model_type=LLMModelType.CLAUDE_3_SONNET,
                prompt_cost_per_1k=0.015,
                completion_cost_per_1k=0.075,
                infrastructure_fee=0.001,
                processing_overhead=0.003,
                min_cost_per_request=0.001,
                currency="USD"
            ),
            LLMModelType.CLAUDE_3_HAIKU: PricingModel(
                model_type=LLMModelType.CLAUDE_3_HAIKU,
                prompt_cost_per_1k=0.00025,
                completion_cost_per_1k=0.00125,
                infrastructure_fee=0.00001,
                processing_overhead=0.0001,
                min_cost_per_request=0.00001,
                currency="USD"
            ),
            LLMModelType.LOCAL_MODEL: PricingModel(
                model_type=LLMModelType.LOCAL_MODEL,
                prompt_cost_per_1k=0.001,
                completion_cost_per_1k=0.001,
                infrastructure_fee=0.00005,
                processing_overhead=0.0002,
                min_cost_per_request=0.00005,
                currency="USD"
            )
        }
        
        # Bulk discount tiers
        self.bulk_discounts = {
            1000: 0.05,      # 5% discount for 1000+ requests
            10000: 0.10,     # 10% discount for 10,000+ requests
            100000: 0.15,    # 15% discount for 100,000+ requests
            1000000: 0.20    # 20% discount for 1M+ requests
        }
        
        # Token efficiency factors (how efficiently models use tokens)
        self.token_efficiency = {
            LLMModelType.GPT4: 1.0,
            LLMModelType.GPT35_TURBO: 0.95,
            LLMModelType.CLAUDE_3_SONNET: 1.1,
            LLMModelType.CLAUDE_3_HAIKU: 0.9,
            LLMModelType.LOCAL_MODEL: 0.85
        }
    
    def calculate_request_cost(
        self,
        model_type: LLMModelType,
        prompt_tokens: int,
        completion_tokens: int,
        request_overhead: float = 0.0,
        context_length: Optional[int] = None,
        priority: str = "normal"
    ) -> CostBreakdown:
        """
        Calculate cost for a single LLM request
        
        Args:
            model_type: LLM model being used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            request_overhead: Additional overhead per request
            context_length: Context window length (affects cost)
            priority: Request priority (normal, high, premium)
        
        Returns:
            Detailed cost breakdown
        """
        if model_type not in self.pricing_models:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        pricing = self.pricing_models[model_type]
        
        # Calculate token costs
        prompt_cost = (prompt_tokens / 1000) * pricing.prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * pricing.completion_cost_per_1k
        
        # Apply priority multipliers
        priority_multiplier = self._get_priority_multiplier(priority)
        prompt_cost *= priority_multiplier
        completion_cost *= priority_multiplier
        
        # Calculate infrastructure and processing costs
        infrastructure_cost = pricing.infrastructure_fee
        processing_cost = pricing.processing_overhead + request_overhead
        
        # Apply context length factor (longer contexts cost more)
        if context_length:
            context_factor = self._calculate_context_factor(context_length, model_type)
            token_cost = (prompt_cost + completion_cost) * context_factor
        else:
            token_cost = prompt_cost + completion_cost
        
        # Apply minimum cost
        total_cost = max(
            token_cost + infrastructure_cost + processing_cost,
            pricing.min_cost_per_request
        )
        
        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(
            model_type, prompt_tokens, completion_tokens, total_cost
        )
        
        # Calculate cost per 1K tokens
        total_tokens = prompt_tokens + completion_tokens
        cost_per_1k_tokens = (total_cost / max(1, total_tokens)) * 1000
        
        return CostBreakdown(
            base_cost=prompt_cost + completion_cost,
            token_cost=token_cost,
            processing_cost=processing_cost,
            infrastructure_cost=infrastructure_cost,
            total_cost=total_cost,
            currency=pricing.currency,
            cost_per_1k_tokens=cost_per_1k_tokens,
            efficiency_score=efficiency_score
        )
    
    def calculate_batch_cost(
        self,
        requests: List[Dict[str, Any]],
        model_type: LLMModelType,
        discount_tier: Optional[PricingTier] = None
    ) -> Tuple[CostBreakdown, List[Dict[str, Any]]]:
        """
        Calculate cost for a batch of requests
        
        Args:
            requests: List of request dictionaries with token counts
            model_type: Model type for all requests
            discount_tier: Volume discount tier
        
        Returns:
            Tuple of (total_cost_breakdown, individual_request_costs)
        """
        if not requests:
            return CostBreakdown(0, 0, 0, 0, 0), []
        
        total_base_cost = 0
        total_token_cost = 0
        total_processing_cost = 0
        total_infrastructure_cost = 0
        individual_costs = []
        
        for i, request in enumerate(requests):
            prompt_tokens = request.get("prompt_tokens", 0)
            completion_tokens = request.get("completion_tokens", 0)
            request_overhead = request.get("request_overhead", 0.0)
            
            request_cost = self.calculate_request_cost(
                model_type=model_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                request_overhead=request_overhead,
                context_length=request.get("context_length"),
                priority=request.get("priority", "normal")
            )
            
            individual_costs.append({
                "request_id": request.get("request_id", f"batch_req_{i}"),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_breakdown": request_cost
            })
            
            total_base_cost += request_cost.base_cost
            total_token_cost += request_cost.token_cost
            total_processing_cost += request_cost.processing_cost
            total_infrastructure_cost += request_cost.infrastructure_cost
        
        # Apply bulk discount
        discount_rate = self._get_bulk_discount_rate(len(requests), discount_tier)
        discount_amount = total_token_cost * discount_rate
        
        discounted_token_cost = total_token_cost - discount_amount
        total_cost = (discounted_token_cost + total_processing_cost + 
                     total_infrastructure_cost + total_base_cost)
        
        # Calculate average efficiency
        avg_efficiency = sum(c["cost_breakdown"].efficiency_score for c in individual_costs) / len(individual_costs)
        
        # Calculate cost per 1K tokens for batch
        total_tokens = sum(r.get("prompt_tokens", 0) + r.get("completion_tokens", 0) for r in requests)
        batch_cost_per_1k = (total_cost / max(1, total_tokens)) * 1000
        
        total_breakdown = CostBreakdown(
            base_cost=total_base_cost,
            token_cost=discounted_token_cost,
            processing_cost=total_processing_cost,
            infrastructure_cost=total_infrastructure_cost,
            total_cost=total_cost,
            cost_per_1k_tokens=batch_cost_per_1k,
            efficiency_score=avg_efficiency
        )
        
        # Add discount information
        total_breakdown.discount_applied = discount_rate
        total_breakdown.discount_amount = discount_amount
        total_breakdown.request_count = len(requests)
        
        return total_breakdown, individual_costs
    
    def estimate_tokens_from_text(
        self,
        text: str,
        model_type: LLMModelType,
        include_overhead: bool = True
    ) -> int:
        """
        Estimate token count from text
        
        Args:
            text: Text to estimate
            model_type: Target model type
            include_overhead: Include system/formatting overhead
        
        Returns:
            Estimated token count
        """
        # Base character-to-token ratios for different models
        char_ratios = {
            LLMModelType.GPT4: 3.8,
            LLMModelType.GPT35_TURBO: 3.8,
            LLMModelType.CLAUDE_3_SONNET: 3.5,
            LLMModelType.CLAUDE_3_HAIKU: 3.5,
            LLMModelType.LOCAL_MODEL: 4.0
        }
        
        base_ratio = char_ratios.get(model_type, 4.0)
        base_tokens = max(1, len(text) // base_ratio)
        
        if include_overhead:
            # Add overhead for system prompts, formatting, JSON structure, etc.
            overhead_tokens = self._calculate_overhead_tokens(model_type)
            total_tokens = base_tokens + overhead_tokens
        else:
            total_tokens = base_tokens
        
        return total_tokens
    
    def get_cost_optimization_recommendations(
        self,
        recent_usage: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate cost optimization recommendations based on usage patterns
        
        Args:
            recent_usage: Recent usage records
            user_id: User ID for personalized recommendations
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        if not recent_usage:
            return recommendations
        
        # Analyze usage patterns
        total_requests = len(recent_usage)
        model_distribution = {}
        avg_tokens_per_request = 0
        cost_per_request = []
        
        for usage in recent_usage:
            model = usage.get("model_type", "unknown")
            if model not in model_distribution:
                model_distribution[model] = 0
            model_distribution[model] += 1
            
            total_tokens = (usage.get("prompt_tokens", 0) + 
                          usage.get("completion_tokens", 0))
            avg_tokens_per_request += total_tokens
            cost_per_request.append(usage.get("total_cost", 0))
        
        avg_tokens_per_request /= total_requests if total_requests > 0 else 1
        
        # Recommendation 1: Model optimization
        if "gpt-4" in model_distribution and avg_tokens_per_request < 500:
            recommendations.append({
                "type": "model_switch",
                "priority": "high",
                "title": "Consider using GPT-3.5-Turbo for small requests",
                "description": "Your average request size is small enough that GPT-3.5-Turbo could provide similar quality at lower cost.",
                "potential_savings": "60-80%",
                "affected_requests": model_distribution.get("gpt-4", 0)
            })
        
        # Recommendation 2: Token optimization
        if avg_tokens_per_request > 2000:
            recommendations.append({
                "type": "token_optimization",
                "priority": "medium",
                "title": "Optimize prompt length",
                "description": "Your average prompt length is quite large. Consider using more concise prompts or implementing prompt compression.",
                "potential_savings": "20-40%",
                "avg_tokens": round(avg_tokens_per_request)
            })
        
        # Recommendation 3: Batch processing
        if total_requests > 100:
            recommendations.append({
                "type": "batch_processing",
                "priority": "medium",
                "title": "Use batch processing for multiple requests",
                "description": "You have a high volume of requests. Consider batching to benefit from volume discounts.",
                "potential_savings": "5-15%",
                "volume": total_requests
            })
        
        # Recommendation 4: Cache optimization
        if total_requests > 50:
            unique_prompts = len(set(usage.get("prompt_text", "") for usage in recent_usage))
            cache_hit_potential = (total_requests - unique_prompts) / total_requests if total_requests > 0 else 0
            
            if cache_hit_potential > 0.1:  # 10% cache potential
                recommendations.append({
                    "type": "caching",
                    "priority": "low",
                    "title": "Implement response caching",
                    "description": "Many similar requests detected. Response caching could reduce costs.",
                    "potential_savings": f"{int(cache_hit_potential * 100)}%",
                    "cache_potential": cache_hit_potential
                })
        
        return recommendations
    
    def calculate_budget_projection(
        self,
        current_usage: List[Dict[str, Any]],
        projected_growth_rate: float = 0.1,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate budget projection based on current usage and growth
        
        Args:
            current_usage: Current usage records
            projected_growth_rate: Expected growth rate (0.1 = 10%)
            time_period_days: Projection period in days
        
        Returns:
            Budget projection data
        """
        if not current_usage:
            return {"projection": "insufficient_data"}
        
        # Calculate current metrics
        total_cost = sum(usage.get("total_cost", 0) for usage in current_usage)
        total_requests = len(current_usage)
        avg_daily_cost = total_cost / 30  # Assuming data is from last 30 days
        avg_requests_per_day = total_requests / 30
        
        # Project growth
        projected_daily_cost = avg_daily_cost * (1 + projected_growth_rate)
        projected_daily_requests = avg_requests_per_day * (1 + projected_growth_rate)
        
        # Calculate total projection
        total_projected_cost = projected_daily_cost * time_period_days
        total_projected_requests = projected_daily_requests * time_period_days
        
        # Cost per request analysis
        cost_per_request_trend = []
        for i in range(min(10, len(current_usage))):
            recent_usage = current_usage[-i-1:] if i > 0 else current_usage[-1:]
            if recent_usage:
                avg_cost = sum(u.get("total_cost", 0) for u in recent_usage) / len(recent_usage)
                cost_per_request_trend.append(avg_cost)
        
        # Confidence level based on data quality
        confidence_level = min(0.9, len(current_usage) / 100)  # Higher confidence with more data
        
        return {
            "projection_period_days": time_period_days,
            "current_avg_daily_cost": round(avg_daily_cost, 6),
            "projected_daily_cost": round(projected_daily_cost, 6),
            "total_projected_cost": round(total_projected_cost, 6),
            "total_projected_requests": int(total_projected_requests),
            "cost_per_request_trend": cost_per_request_trend,
            "projected_growth_rate": projected_growth_rate,
            "confidence_level": confidence_level,
            "recommendations": self.get_cost_optimization_recommendations(current_usage)
        }
    
    def compare_models(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model_types: List[LLMModelType]
    ) -> List[Dict[str, Any]]:
        """
        Compare costs across different models
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model_types: List of models to compare
        
        Returns:
            List of cost comparisons for each model
        """
        comparisons = []
        
        for model_type in model_types:
            if model_type not in self.pricing_models:
                continue
            
            cost_breakdown = self.calculate_request_cost(
                model_type=model_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            
            # Calculate quality-price ratio (simplified)
            quality_score = self._get_model_quality_score(model_type)
            price_per_quality = cost_breakdown.total_cost / quality_score
            
            comparisons.append({
                "model_type": model_type.value,
                "cost_breakdown": cost_breakdown,
                "total_cost": cost_breakdown.total_cost,
                "quality_score": quality_score,
                "price_per_quality": price_per_quality,
                "efficiency_score": cost_breakdown.efficiency_score,
                "recommendation_score": quality_score / max(0.01, cost_breakdown.total_cost)
            })
        
        # Sort by recommendation score (higher is better)
        comparisons.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        return comparisons
    
    # Helper methods
    def _get_priority_multiplier(self, priority: str) -> float:
        """Get cost multiplier based on priority"""
        multipliers = {
            "normal": 1.0,
            "high": 1.2,
            "premium": 1.5,
            "urgent": 2.0
        }
        return multipliers.get(priority, 1.0)
    
    def _calculate_context_factor(self, context_length: int, model_type: LLMModelType) -> float:
        """Calculate cost factor based on context length"""
        base_contexts = {
            LLMModelType.GPT4: 8192,
            LLMModelType.GPT35_TURBO: 4096,
            LLMModelType.CLAUDE_3_SONNET: 200000,
            LLMModelType.CLAUDE_3_HAIKU: 200000,
            LLMModelType.LOCAL_MODEL: 4096
        }
        
        base_context = base_contexts.get(model_type, 8192)
        if context_length <= base_context:
            return 1.0
        
        # Cost increases with context length (logarithmic)
        return 1.0 + math.log(context_length / base_context) * 0.1
    
    def _calculate_overhead_tokens(self, model_type: LLMModelType) -> int:
        """Calculate overhead tokens for different model types"""
        overhead_map = {
            LLMModelType.GPT4: 50,
            LLMModelType.GPT35_TURBO: 40,
            LLMModelType.CLAUDE_3_SONNET: 60,
            LLMModelType.CLAUDE_3_HAIKU: 30,
            LLMModelType.LOCAL_MODEL: 20
        }
        return overhead_map.get(model_type, 50)
    
    def _calculate_efficiency_score(
        self,
        model_type: LLMModelType,
        prompt_tokens: int,
        completion_tokens: int,
        total_cost: float
    ) -> float:
        """Calculate efficiency score for the request"""
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens == 0 or total_cost == 0:
            return 0.0
        
        # Base efficiency from model characteristics
        base_efficiency = self.token_efficiency.get(model_type, 1.0)
        
        # Adjust based on token balance (completion tokens are typically more valuable)
        token_balance_factor = min(1.2, completion_tokens / max(1, prompt_tokens))
        
        # Cost efficiency (lower cost per token is better)
        cost_efficiency = 1.0 / max(0.001, (total_cost / total_tokens) * 1000)
        
        # Combine factors
        efficiency_score = base_efficiency * token_balance_factor * cost_efficiency / 100
        
        return min(1.0, max(0.0, efficiency_score))
    
    def _get_bulk_discount_rate(self, request_count: int, discount_tier: Optional[PricingTier]) -> float:
        """Get bulk discount rate"""
        if discount_tier:
            tier_discounts = {
                PricingTier.STANDARD: 0.05,
                PricingTier.HIGH_VOLUME: 0.15,
                PricingTier.ENTERPRISE: 0.25
            }
            return tier_discounts.get(discount_tier, 0.0)
        
        # Find applicable discount from bulk discounts
        applicable_rate = 0.0
        for threshold, rate in sorted(self.bulk_discounts.items()):
            if request_count >= threshold:
                applicable_rate = rate
        
        return applicable_rate
    
    def _get_model_quality_score(self, model_type: LLMModelType) -> float:
        """Get relative quality score for models"""
        quality_scores = {
            LLMModelType.GPT4: 1.0,
            LLMModelType.GPT35_TURBO: 0.85,
            LLMModelType.CLAUDE_3_SONNET: 0.95,
            LLMModelType.CLAUDE_3_HAIKU: 0.80,
            LLMModelType.LOCAL_MODEL: 0.70
        }
        return quality_scores.get(model_type, 0.75)