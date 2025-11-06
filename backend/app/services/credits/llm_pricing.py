"""
LLM Pricing Service

Service for managing per-request credit costing for different LLM models
based on real market rates and token usage.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.credits import LLMModelPricing, LLMProvider
from app.models.credits import LLMUsageRecord
from app.db.session import get_db

logger = logging.getLogger(__name__)


class LlmPricingService:
    """
    Service for calculating LLM usage costs in credits
    """
    
    # Default pricing based on real market rates (credits per 1K tokens)
    DEFAULT_PRICING = {
        "openai": {
            "gpt-4": {
                "prompt": 100.0,  # $0.03 per 1K tokens = 100 credits (at $0.0003 per credit)
                "completion": 100.0,
                "context_window": 8192,
                "max_tokens": 4096
            },
            "gpt-3.5-turbo": {
                "prompt": 10.0,   # $0.0015 per 1K tokens = 10 credits
                "completion": 10.0,
                "context_window": 4096,
                "max_tokens": 4096
            },
            "gpt-4-1106-preview": {
                "prompt": 120.0,  # $0.01 per 1K tokens for prompt
                "completion": 30.0,  # $0.03 per 1K tokens for completion
                "context_window": 128000,
                "max_tokens": 4096
            },
            "gpt-4-vision-preview": {
                "prompt": 150.0,  # Higher cost for vision capabilities
                "completion": 100.0,
                "context_window": 8192,
                "max_tokens": 4096
            }
        },
        "anthropic": {
            "claude-3-opus": {
                "prompt": 80.0,   # $0.015 per 1K tokens = 80 credits
                "completion": 80.0,
                "context_window": 200000,
                "max_tokens": 4096
            },
            "claude-3-sonnet": {
                "prompt": 40.0,   # $0.003 per 1K tokens = 40 credits
                "completion": 40.0,
                "context_window": 200000,
                "max_tokens": 4096
            },
            "claude-3-haiku": {
                "prompt": 5.0,    # $0.00025 per 1K tokens = 5 credits
                "completion": 5.0,
                "context_window": 200000,
                "max_tokens": 4096
            },
            "claude-2.1": {
                "prompt": 60.0,
                "completion": 60.0,
                "context_window": 200000,
                "max_tokens": 4096
            },
            "claude-instant": {
                "prompt": 10.0,
                "completion": 10.0,
                "context_window": 100000,
                "max_tokens": 4096
            }
        },
        "google": {
            "gemini-pro": {
                "prompt": 50.0,   # $0.0005 per 1K characters = ~50 credits
                "completion": 50.0,
                "context_window": 32768,
                "max_tokens": 8192
            },
            "gemini-pro-vision": {
                "prompt": 80.0,   # Higher cost for vision
                "completion": 80.0,
                "context_window": 16384,
                "max_tokens": 8192
            },
            "gemini-ultra": {
                "prompt": 120.0,  # Most expensive Google model
                "completion": 120.0,
                "context_window": 32768,
                "max_tokens": 8192
            }
        },
        "local": {
            "llama-2-70b": {
                "prompt": 20.0,   # Local models - lower cost due to infrastructure savings
                "completion": 20.0,
                "context_window": 4096,
                "max_tokens": 4096
            },
            "codellama": {
                "prompt": 15.0,
                "completion": 15.0,
                "context_window": 16384,
                "max_tokens": 8192
            },
            "mistral": {
                "prompt": 25.0,
                "completion": 25.0,
                "context_window": 32768,
                "max_tokens": 8192
            }
        },
        "custom": {
            "default": {
                "prompt": 30.0,   # Default custom model pricing
                "completion": 30.0,
                "context_window": 8192,
                "max_tokens": 4096
            }
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_model_pricing(self, provider: str, model_name: str, 
                         region: str = "global") -> Optional[LLMModelPricing]:
        """
        Get pricing for specific model from database or defaults
        """
        # Try database first
        pricing = self.db.query(LLMModelPricing).filter(
            LLMModelPricing.provider == provider.lower(),
            LLMModelPricing.model_name == model_name,
            LLMModelPricing.region == region,
            LLMModelPricing.is_active == True
        ).first()
        
        if pricing:
            return pricing
        
        # Fall back to defaults
        provider_lower = provider.lower()
        if provider_lower in self.DEFAULT_PRICING and model_name in self.DEFAULT_PRICING[provider_lower]:
            default_pricing = self.DEFAULT_PRICING[provider_lower][model_name]
            
            # Create temporary pricing object from defaults
            return LLMModelPricing(
                provider=provider_lower,
                model_name=model_name,
                prompt_price_credits=default_pricing["prompt"],
                completion_price_credits=default_pricing["completion"],
                context_window_tokens=default_pricing["context_window"],
                max_tokens_per_request=default_pricing["max_tokens"],
                region=region,
                region_multiplier=1.0
            )
        
        # Use custom default
        custom_default = self.DEFAULT_PRICING["custom"]["default"]
        return LLMModelPricing(
            provider=provider_lower,
            model_name=model_name,
            prompt_price_credits=custom_default["prompt"],
            completion_price_credits=custom_default["completion"],
            context_window_tokens=custom_default["context_window"],
            max_tokens_per_request=custom_default["max_tokens"],
            region=region,
            region_multiplier=1.0
        )
    
    def calculate_usage_cost(self, provider: str, model_name: str,
                           prompt_tokens: int, completion_tokens: int,
                           region: str = "global", apply_discounts: bool = True) -> Dict[str, float]:
        """
        Calculate the credit cost for LLM usage
        """
        pricing = self.get_model_pricing(provider, model_name, region)
        
        if not pricing:
            raise ValueError(f"No pricing found for {provider}/{model_name}")
        
        # Calculate base costs
        prompt_cost = (prompt_tokens / 1000) * pricing.prompt_price_credits
        completion_cost = (completion_tokens / 1000) * pricing.completion_price_credits
        
        # Apply minimum charges if applicable
        if prompt_tokens > 0 and prompt_tokens < pricing.minimum_prompt_tokens:
            prompt_cost = pricing.minimum_prompt_tokens * pricing.prompt_price_credits / 1000
        
        if completion_tokens > 0 and completion_tokens < pricing.minimum_completion_tokens:
            completion_cost = pricing.minimum_completion_tokens * pricing.completion_price_credits / 1000
        
        # Add fixed request cost if applicable
        total_cost = prompt_cost + completion_cost + pricing.request_cost_credits
        
        # Apply regional multiplier
        total_cost *= pricing.region_multiplier
        
        # Apply bulk discounts if applicable
        if apply_discounts and pricing.bulk_discount_threshold and pricing.bulk_discount_percentage > 0:
            total_tokens = prompt_tokens + completion_tokens
            if total_tokens >= pricing.bulk_discount_threshold:
                discount_amount = total_cost * (pricing.bulk_discount_percentage / 100)
                total_cost -= discount_amount
        
        return {
            "prompt_cost_credits": prompt_cost,
            "completion_cost_credits": completion_cost,
            "total_cost_credits": total_cost,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model_pricing": {
                "provider": pricing.provider,
                "model_name": pricing.model_name,
                "prompt_price_per_1k": pricing.prompt_price_credits,
                "completion_price_per_1k": pricing.completion_price_credits,
                "request_cost": pricing.request_cost_credits,
                "region_multiplier": pricing.region_multiplier
            }
        }
    
    def validate_usage_limits(self, provider: str, model_name: str,
                            total_tokens: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Check if usage is within configured limits
        """
        pricing = self.get_model_pricing(provider, model_name)
        
        if not pricing:
            return {"valid": False, "error": f"No pricing found for {provider}/{model_name}"}
        
        # Check maximum tokens per request
        if pricing.max_tokens_per_request and total_tokens > pricing.max_tokens_per_request:
            return {
                "valid": False, 
                "error": f"Request exceeds maximum tokens: {total_tokens} > {pricing.max_tokens_per_request}"
            }
        
        # Check daily/monthly limits for user (if user_id provided)
        if user_id:
            today_usage = self._get_daily_usage(user_id, provider, model_name)
            monthly_usage = self._get_monthly_usage(user_id, provider, model_name)
            
            if pricing.max_requests_per_day and today_usage >= pricing.max_requests_per_day:
                return {
                    "valid": False,
                    "error": f"Daily request limit exceeded: {today_usage} >= {pricing.max_requests_per_day}"
                }
            
            if pricing.max_requests_per_month and monthly_usage >= pricing.max_requests_per_month:
                return {
                    "valid": False,
                    "error": f"Monthly request limit exceeded: {monthly_usage} >= {pricing.max_requests_per_month}"
                }
        
        return {"valid": True, "limits": {
            "max_tokens_per_request": pricing.max_tokens_per_request,
            "max_requests_per_day": pricing.max_requests_per_day,
            "max_requests_per_month": pricing.max_requests_per_month
        }}
    
    def _get_daily_usage(self, user_id: int, provider: str, model_name: str) -> int:
        """Get daily request count for user"""
        from datetime import datetime, timedelta
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        usage = self.db.query(LLMUsageRecord).filter(
            LLMUsageRecord.user_id == user_id,
            LLMUsageRecord.provider == provider.lower(),
            LLMUsageRecord.model_name == model_name,
            LLMUsageRecord.timestamp >= today_start
        ).count()
        
        return usage
    
    def _get_monthly_usage(self, user_id: int, provider: str, model_name: str) -> int:
        """Get monthly request count for user"""
        from datetime import datetime
        
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = self.db.query(LLMUsageRecord).filter(
            LLMUsageRecord.user_id == user_id,
            LLMUsageRecord.provider == provider.lower(),
            LLMUsageRecord.model_name == model_name,
            LLMUsageRecord.timestamp >= month_start
        ).count()
        
        return usage
    
    def get_all_model_pricing(self) -> List[Dict[str, Any]]:
        """
        Get all available model pricing information
        """
        pricing_list = []
        
        # Get from database
        db_pricing = self.db.query(LLMModelPricing).filter(
            LLMModelPricing.is_active == True
        ).all()
        
        for pricing in db_pricing:
            pricing_list.append({
                "provider": pricing.provider,
                "model_name": pricing.model_name,
                "model_version": pricing.model_version,
                "prompt_price_credits": pricing.prompt_price_credits,
                "completion_price_credits": pricing.completion_price_credits,
                "context_window_tokens": pricing.context_window_tokens,
                "quality_tier": pricing.quality_tier,
                "region": pricing.region,
                "is_active": pricing.is_active
            })
        
        # Add defaults that aren't in database
        for provider, models in self.DEFAULT_PRICING.items():
            for model_name, pricing_data in models.items():
                # Check if already in database
                exists = any(
                    p["provider"] == provider and p["model_name"] == model_name 
                    for p in pricing_list
                )
                
                if not exists:
                    pricing_list.append({
                        "provider": provider,
                        "model_name": model_name,
                        "model_version": "latest",
                        "prompt_price_credits": pricing_data["prompt"],
                        "completion_price_credits": pricing_data["completion"],
                        "context_window_tokens": pricing_data["context_window"],
                        "quality_tier": "standard",
                        "region": "global",
                        "is_active": True,
                        "is_default": True
                    })
        
        return pricing_list
    
    def get_provider_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of all providers and their models
        """
        providers = {}
        
        for provider, models in self.DEFAULT_PRICING.items():
            models_info = []
            min_cost = float('inf')
            max_cost = 0
            
            for model_name, pricing_data in models.items():
                avg_cost = (pricing_data["prompt"] + pricing_data["completion"]) / 2
                min_cost = min(min_cost, avg_cost)
                max_cost = max(max_cost, avg_cost)
                
                models_info.append({
                    "model_name": model_name,
                    "avg_cost_per_1k_tokens": avg_cost,
                    "context_window": pricing_data["context_window"],
                    "max_tokens": pricing_data["max_tokens"]
                })
            
            providers[provider] = {
                "model_count": len(models),
                "min_cost_per_1k_tokens": min_cost,
                "max_cost_per_1k_tokens": max_cost,
                "models": models_info
            }
        
        return providers
    
    def estimate_cost_for_prompt(self, provider: str, model_name: str,
                               prompt_text: str, max_response_tokens: int = 1000,
                               region: str = "global") -> Dict[str, Any]:
        """
        Estimate cost for a text prompt (rough token estimation)
        """
        # Rough token estimation (1 token ≈ 4 characters for English text)
        estimated_prompt_tokens = len(prompt_text) // 4
        estimated_completion_tokens = max_response_tokens
        
        cost_breakdown = self.calculate_usage_cost(
            provider, model_name, 
            estimated_prompt_tokens, estimated_completion_tokens, 
            region
        )
        
        # Add estimation metadata
        cost_breakdown["estimation"] = {
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "estimated_completion_tokens": estimated_completion_tokens,
            "characters_in_prompt": len(prompt_text),
            "average_tokens_per_character": estimated_prompt_tokens / max(len(prompt_text), 1),
            "confidence": "low"  # Token estimation is approximate
        }
        
        return cost_breakdown


# Utility functions
def get_llm_pricing_service(db: Session = None) -> LlmPricingService:
    """
    Get LLM pricing service instance
    """
    if db is None:
        db = next(get_db())
    return LlmPricingService(db)


def calculate_llm_cost(provider: str, model_name: str, prompt_tokens: int, 
                      completion_tokens: int, db: Session = None) -> float:
    """
    Quick function to calculate LLM cost
    """
    service = get_llm_pricing_service(db)
    result = service.calculate_usage_cost(provider, model_name, prompt_tokens, completion_tokens)
    return result["total_cost_credits"]


def validate_model_usage(provider: str, model_name: str, total_tokens: int, 
                        user_id: int = None, db: Session = None) -> bool:
    """
    Quick function to validate model usage
    """
    service = get_llm_pricing_service(db)
    validation = service.validate_usage_limits(provider, model_name, total_tokens, user_id)
    return validation["valid"]