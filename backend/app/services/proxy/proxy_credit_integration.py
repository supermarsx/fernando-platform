"""
Proxy Credit Integration

Integration module for credit tracking in the proxy server:
- Add credit tracking to proxy LLM requests
- Implement credit-based request throttling
- Add credit usage logging to request logger
- Integrate credit monitoring with performance monitor
- Add credit-based circuit breaker logic
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import logging

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp

from app.services.credit_service import CreditService
from app.services.usage_tracking.llm_usage_tracker import LLMUsageTracker
from app.services.usage_tracking.cost_calculator import CostCalculator
from app.middleware.credit_validation import CreditValidator, CreditValidationError
from app.models.credit import LLMModelType, CreditTransactionType

logger = logging.getLogger(__name__)


class ProxyCreditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for credit tracking and validation in proxy requests
    
    Features:
    - Credit validation before LLM proxy requests
    - Credit-based request throttling
    - Usage tracking and cost calculation
    - Credit-based circuit breaker logic
    - Real-time credit monitoring
    """
    
    def __init__(
        self,
        app: ASGIApp,
        credit_service: CreditService,
        usage_tracker: LLMUsageTracker,
        cost_calculator: CostCalculator,
        credit_validator: CreditValidator,
        db: Any = None
    ):
        super().__init__(app)
        self.credit_service = credit_service
        self.usage_tracker = usage_tracker
        self.cost_calculator = cost_calculator
        self.credit_validator = credit_validator
        self.db = db
        
        # Credit-based throttling
        self.throttle_thresholds = {
            "low_balance": 0.1,      # 10% of typical usage
            "medium_balance": 0.5,   # 50% of typical usage  
            "high_usage_rate": 10.0  # requests per minute
        }
        
        # Credit-based circuit breaker thresholds
        self.circuit_breaker_thresholds = {
            "insufficient_credits": 5,    # Failures due to insufficient credits
            "high_cost_requests": 20.0,   # Cost threshold for circuit breaker
            "rapid_exhaustion": 3         # Rapid balance exhaustion
        }
        
        # User credit tracking
        self.user_request_counts: Dict[str, Dict[str, Any]] = {}
        self.circuit_breaker_states: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with credit tracking"""
        start_time = time.time()
        
        # Extract user information
        user_id = self._extract_user_id(request)
        client_ip = self._get_client_ip(request)
        
        # Skip credit validation for non-LLM endpoints
        if not self._is_llm_endpoint(request):
            return await call_next(request)
        
        # Check credit-based circuit breaker
        if user_id and await self._is_circuit_breaker_active(user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Circuit breaker active due to credit issues",
                    "message": "Please try again later or contact support",
                    "retry_after": 300  # 5 minutes
                }
            )
        
        # Track request for throttling
        if user_id:
            await self._track_user_request(user_id, client_ip)
            
            # Check credit-based throttling
            throttle_response = await self._check_credit_throttling(user_id)
            if throttle_response:
                return throttle_response
        
        # Initialize session tracking
        session_id = self._generate_session_id(request)
        request.state.credit_session_id = session_id
        request.state.credit_user_id = user_id
        
        try:
            # Validate credits before processing
            if user_id:
                validation_result = await self._validate_request_credits(
                    request, user_id, session_id
                )
                request.state.credit_validation = validation_result
            
            # Process the request
            response = await call_next(request)
            
            # Track successful usage and deduct credits
            if user_id and response.status_code < 400:
                await self._track_successful_usage(
                    request, response, user_id, session_id, start_time
                )
            
            # Update circuit breaker state on success
            if user_id:
                await self._update_circuit_breaker_success(user_id)
            
            return response
        
        except CreditValidationError as e:
            # Track credit validation failure
            if user_id:
                await self._track_credit_failure(user_id, "validation_failed", str(e))
                await self._update_circuit_breaker_failure(user_id, "insufficient_credits")
            
            # Return detailed credit error
            return await self._create_credit_error_response(e)
        
        except HTTPException as e:
            # Track other HTTP errors
            if user_id and user_id in self.circuit_breaker_states:
                self.circuit_breaker_states[user_id]["error_count"] += 1
            
            raise
        
        except Exception as e:
            # Track unexpected errors
            if user_id:
                await self._track_credit_failure(user_id, "unexpected_error", str(e))
            
            # Re-raise the exception
            raise
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        # Try multiple sources for user ID
        sources = [
            lambda: request.headers.get("X-User-ID"),
            lambda: request.headers.get("X-UserId"),
            lambda: getattr(request.state, "user_id", None),
            lambda: getattr(request.state, "current_user", {}).get("id") if hasattr(request.state, "current_user") else None
        ]
        
        for source in sources:
            try:
                user_id = source()
                if user_id:
                    return str(user_id)
            except:
                continue
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        return (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "")
            or request.client.host if request.client else "unknown"
        )
    
    def _is_llm_endpoint(self, request: Request) -> bool:
        """Check if request is for LLM services"""
        llm_patterns = [
            "/api/llm/",
            "/api/openai/",
            "/api/anthropic/",
            "/proxy/llm/",
            "/proxy/openai/",
            "/proxy/anthropic/"
        ]
        
        path = request.url.path.lower()
        return any(pattern in path for pattern in llm_patterns)
    
    def _generate_session_id(self, request: Request) -> str:
        """Generate session ID for request"""
        from uuid import uuid4
        return f"proxy_{uuid4().hex[:16]}"
    
    async def _validate_request_credits(
        self,
        request: Request,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Validate credits before processing request"""
        # Estimate request cost
        estimated_cost = await self._estimate_request_cost(request)
        
        # Get operation type
        operation_type = self._get_operation_type(request)
        
        # Validate credits
        validation_result = await self.credit_validator.validate_credit_balance(
            user_id=int(user_id),
            estimated_cost=estimated_cost,
            operation_type=operation_type,
            service_type="llm",
            model_type=self._get_model_type(request),
            **self._get_additional_validation_params(request)
        )
        
        # Store validation result for later use
        if hasattr(request.state, 'credit_validation'):
            request.state.credit_validation = validation_result
        
        return validation_result
    
    async def _estimate_request_cost(self, request: Request) -> float:
        """Estimate cost of the request"""
        try:
            # Get request details
            model_type = self._get_model_type(request)
            
            # Estimate tokens based on request body
            prompt_tokens = 0
            completion_tokens = 0
            
            if request.method in ["POST", "PUT"] and request.headers.get("content-type", "").startswith("application/json"):
                try:
                    body = await request.json()
                    
                    # Extract prompt/completion token estimates
                    if isinstance(body, dict):
                        # OpenAI format
                        messages = body.get("messages", [])
                        prompt_tokens = self._estimate_tokens_from_messages(messages)
                        
                        # Completion parameters
                        max_tokens = body.get("max_tokens", 100)
                        completion_tokens = max_tokens
                        
                        # Handle streaming
                        if body.get("stream", False):
                            completion_tokens *= 1.2  # Streaming overhead
                    
                except Exception:
                    # Fallback estimates
                    prompt_tokens = 100
                    completion_tokens = 50
            
            else:
                # GET requests - minimal tokens
                prompt_tokens = 50
                completion_tokens = 20
            
            # Calculate cost
            cost, _ = self.cost_calculator.calculate_request_cost(
                model_type=model_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                request_overhead=0.01  # Base overhead
            )
            
            return cost
        
        except Exception as e:
            logger.warning(f"Error estimating request cost: {e}")
            return 0.05  # Conservative default
    
    def _get_model_type(self, request: Request) -> LLMModelType:
        """Extract model type from request"""
        # Try multiple sources for model information
        sources = [
            lambda: getattr(request.state, "model_type", None),
            lambda: request.query_params.get("model"),
            lambda: request.headers.get("X-Model"),
        ]
        
        for source in sources:
            try:
                model_name = source()
                if model_name:
                    # Convert model name to enum
                    model_mapping = {
                        "gpt-4": LLMModelType.GPT4,
                        "gpt-3.5-turbo": LLMModelType.GPT35_TURBO,
                        "claude-3-sonnet": LLMModelType.CLAUDE_3_SONNET,
                        "claude-3-haiku": LLMModelType.CLAUDE_3_HAIKU,
                    }
                    return model_mapping.get(model_name, LLMModelType.GPT35_TURBO)
            except:
                continue
        
        return LLMModelType.GPT35_TURBO  # Default model
    
    def _get_operation_type(self, request: Request) -> str:
        """Determine operation type from request"""
        path = request.url.path.lower()
        
        if "extract" in path:
            return "extract_fields"
        elif "generate" in path:
            return "generate_text"
        elif "chat" in path:
            return "chat_completion"
        elif "embed" in path:
            return "create_embeddings"
        else:
            return "llm_request"
    
    def _get_additional_validation_params(self, request: Request) -> Dict[str, Any]:
        """Get additional parameters for credit validation"""
        params = {}
        
        # Get max_tokens if available
        try:
            if request.method in ["POST", "PUT"]:
                body = await request.json()
                max_tokens = body.get("max_tokens")
                if max_tokens:
                    params["estimated_tokens"] = max_tokens
        except:
            pass
        
        return params
    
    def _estimate_tokens_from_messages(self, messages: List[Dict[str, str]]) -> int:
        """Estimate tokens from message structure"""
        total_chars = 0
        
        for message in messages:
            if isinstance(message, dict):
                content = message.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    # Handle multi-modal content
                    for item in content:
                        if isinstance(item, dict):
                            total_chars += len(item.get("text", ""))
        
        # Rough estimate: ~4 characters per token
        return max(1, total_chars // 4)
    
    async def _track_user_request(self, user_id: str, client_ip: str):
        """Track user request for throttling"""
        current_time = time.time()
        
        if user_id not in self.user_request_counts:
            self.user_request_counts[user_id] = {
                "request_times": [],
                "client_ips": set(),
                "total_requests": 0
            }
        
        user_data = self.user_request_counts[user_id]
        user_data["request_times"].append(current_time)
        user_data["client_ips"].add(client_ip)
        user_data["total_requests"] += 1
        
        # Clean old requests (keep only last minute)
        cutoff_time = current_time - 60
        user_data["request_times"] = [
            t for t in user_data["request_times"] if t > cutoff_time
        ]
        
        # Clean old IPs (keep only recent ones)
        if len(user_data["client_ips"]) > 10:
            user_data["client_ips"] = set(list(user_data["client_ips"])[-10:])
    
    async def _check_credit_throttling(self, user_id: str) -> Optional[Response]:
        """Check credit-based throttling for user"""
        if user_id not in self.user_request_counts:
            return None
        
        user_data = self.user_request_counts[user_id]
        current_time = time.time()
        
        # Check request rate
        recent_requests = len(user_data["request_times"])
        if recent_requests > self.throttle_thresholds["high_usage_rate"]:
            return StarletteResponse(
                content=json.dumps({
                    "error": "rate_limited",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": 60
                }),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"}
            )
        
        # Check balance-based throttling
        try:
            credit_account = self.credit_service.get_credit_account(int(user_id))
            if credit_account:
                # Get user's typical usage rate
                typical_daily_usage = self._calculate_typical_usage(user_id)
                
                if typical_daily_usage > 0:
                    current_balance_percentage = credit_account.current_balance / typical_daily_usage
                    
                    if current_balance_percentage < self.throttle_thresholds["low_balance"]:
                        return StarletteResponse(
                            content=json.dumps({
                                "error": "low_balance",
                                "message": "Low credit balance detected. Please add credits.",
                                "balance": credit_account.current_balance,
                                "retry_after": 300
                            }),
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers={"Retry-After": "300"}
                        )
        
        except Exception as e:
            logger.warning(f"Error checking balance throttling: {e}")
        
        return None
    
    def _calculate_typical_usage(self, user_id: str) -> float:
        """Calculate user's typical daily usage"""
        if user_id not in self.user_request_counts:
            return 10.0  # Default daily usage
        
        # This would typically query historical data
        # For now, use request count as proxy
        user_data = self.user_request_counts[user_id]
        return min(100.0, user_data["total_requests"] * 0.5)  # Conservative estimate
    
    async def _is_circuit_breaker_active(self, user_id: str) -> bool:
        """Check if circuit breaker is active for user"""
        if user_id not in self.circuit_breaker_states:
            return False
        
        state = self.circuit_breaker_states[user_id]
        current_time = time.time()
        
        # Check if in cooldown period
        if state.get("cooldown_until", 0) > current_time:
            return True
        
        # Check failure thresholds
        if state.get("consecutive_failures", 0) >= self.circuit_breaker_thresholds["insufficient_credits"]:
            # Activate circuit breaker
            state["cooldown_until"] = current_time + 300  # 5 minutes
            state["activation_reason"] = "insufficient_credits"
            return True
        
        # Check high cost threshold
        if state.get("total_cost_today", 0) > self.circuit_breaker_thresholds["high_cost_requests"]:
            state["cooldown_until"] = current_time + 600  # 10 minutes
            state["activation_reason"] = "high_cost_requests"
            return True
        
        return False
    
    async def _track_successful_usage(
        self,
        request: Request,
        response: Response,
        user_id: str,
        session_id: str,
        start_time: float
    ):
        """Track successful usage and update credits"""
        try:
            # Calculate final cost based on actual response
            processing_time = time.time() - start_time
            
            # Get model type and estimate actual tokens used
            model_type = self._get_model_type(request)
            
            # For now, estimate based on response size and processing time
            estimated_tokens = max(100, int(processing_time * 10))  # Simple heuristic
            estimated_cost = estimated_tokens * 0.0001  # Rough cost estimate
            
            # Start usage session
            self.usage_tracker.start_usage_session(
                session_id=session_id,
                user_id=int(user_id),
                model_type=model_type.value,
                operation_type=self._get_operation_type(request),
                context={
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "response_status": response.status_code
                }
            )
            
            # Track request completion
            request_info = self.usage_tracker.track_request_start(
                session_id=session_id,
                prompt="Proxy request",
                request_params={
                    "model": model_type.value,
                    "method": request.method
                }
            )
            
            self.usage_tracker.track_request_complete(
                session_id=session_id,
                request_id=request_info["request_id"],
                response="Proxy response",
                completion_tokens=estimated_tokens,
                total_tokens=estimated_tokens,
                success=True,
                response_time_ms=int(processing_time * 1000)
            )
            
            # Finalize usage session
            self.usage_tracker.finalize_usage_session(
                session_id=session_id,
                user_id=int(user_id),
                resource_id=f"proxy_{session_id}",
                endpoint=str(request.url.path)
            )
            
            # Update circuit breaker state
            await self._update_circuit_breaker_success(user_id)
            
        except Exception as e:
            logger.warning(f"Error tracking usage: {e}")
    
    async def _track_credit_failure(self, user_id: str, failure_type: str, error_message: str):
        """Track credit-related failures"""
        if user_id not in self.circuit_breaker_states:
            self.circuit_breaker_states[user_id] = {
                "consecutive_failures": 0,
                "total_failures": 0,
                "last_failure_time": None,
                "error_types": []
            }
        
        state = self.circuit_breaker_states[user_id]
        state["consecutive_failures"] += 1
        state["total_failures"] += 1
        state["last_failure_time"] = time.time()
        state["error_types"].append(failure_type)
        
        # Keep only recent errors
        if len(state["error_types"]) > 20:
            state["error_types"] = state["error_types"][-20:]
    
    async def _update_circuit_breaker_failure(self, user_id: str, failure_type: str):
        """Update circuit breaker state on failure"""
        if user_id not in self.circuit_breaker_states:
            return
        
        state = self.circuit_breaker_states[user_id]
        
        if failure_type == "insufficient_credits":
            state["insufficient_credit_failures"] = state.get("insufficient_credit_failures", 0) + 1
        elif failure_type == "high_cost":
            state["high_cost_failures"] = state.get("high_cost_failures", 0) + 1
        
        # Check if threshold exceeded
        if (state.get("insufficient_credit_failures", 0) >= 
            self.circuit_breaker_thresholds["insufficient_credits"]):
            
            state["cooldown_until"] = time.time() + 300  # 5 minutes
            state["activation_reason"] = "insufficient_credits"
    
    async def _update_circuit_breaker_success(self, user_id: str):
        """Update circuit breaker state on success"""
        if user_id not in self.circuit_breaker_states:
            return
        
        state = self.circuit_breaker_states[user_id]
        
        # Reset consecutive failures on success
        state["consecutive_failures"] = 0
        
        # Update success metrics
        state["last_success_time"] = time.time()
        state["total_successes"] = state.get("total_successes", 0) + 1
    
    async def _create_credit_error_response(self, error: CreditValidationError) -> Response:
        """Create detailed credit error response"""
        detail = error.detail if hasattr(error, 'detail') else str(error)
        
        error_response = {
            "error": "insufficient_credits",
            "message": detail,
            "code": "CREDIT_VALIDATION_FAILED"
        }
        
        if hasattr(error, 'args') and len(error.args) >= 2:
            error_response.update({
                "available_balance": error.args[1] if len(error.args) > 1 else 0,
                "required_amount": error.args[2] if len(error.args) > 2 else 0
            })
        
        return StarletteResponse(
            content=json.dumps(error_response),
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            headers={"Content-Type": "application/json"}
        )


class ProxyCreditIntegration:
    """
    Integration manager for credit functionality in proxy server
    
    Handles setup and coordination of credit tracking components
    """
    
    def __init__(self, db: Any):
        self.db = db
        self.credit_service = None
        self.usage_tracker = None
        self.cost_calculator = None
        self.credit_validator = None
        self.middleware = None
    
    async def initialize(self) -> ProxyCreditMiddleware:
        """Initialize credit integration components"""
        # Initialize services
        self.credit_service = CreditService(self.db)
        self.usage_tracker = LLMUsageTracker(self.db, self.credit_service)
        self.cost_calculator = CostCalculator()
        self.credit_validator = CreditValidator(self.db)
        
        # Create middleware
        self.middleware = ProxyCreditMiddleware(
            app=None,  # Will be set by FastAPI
            credit_service=self.credit_service,
            usage_tracker=self.usage_tracker,
            cost_calculator=self.cost_calculator,
            credit_validator=self.credit_validator,
            db=self.db
        )
        
        # Start background tasks
        asyncio.create_task(self._cleanup_expired_states())
        
        return self.middleware
    
    async def _cleanup_expired_states(self):
        """Background task to cleanup expired states"""
        while True:
            try:
                current_time = time.time()
                
                # Cleanup user request counts
                expired_users = []
                for user_id, data in self.middleware.user_request_counts.items():
                    if not data["request_times"]:  # No recent activity
                        expired_users.append(user_id)
                
                for user_id in expired_users:
                    del self.middleware.user_request_counts[user_id]
                
                # Cleanup circuit breaker states
                expired_circuit_breakers = []
                for user_id, state in self.middleware.circuit_breaker_states.items():
                    if state.get("cooldown_until", 0) < current_time:
                        # Reset circuit breaker state
                        state["consecutive_failures"] = 0
                        state["cooldown_until"] = 0
                
                logger.debug(f"Cleaned up {len(expired_users)} expired user states")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
            
            # Run cleanup every 5 minutes
            await asyncio.sleep(300)
    
    async def get_user_credit_status(self, user_id: str) -> Dict[str, Any]:
        """Get current credit status for user"""
        try:
            credit_account = self.credit_service.get_credit_account(int(user_id))
            if not credit_account:
                return {"error": "No credit account found"}
            
            # Get recent usage
            recent_usage = self.usage_tracker.get_real_time_usage(int(user_id), 60)
            
            # Check circuit breaker status
            circuit_breaker_active = await self.middleware._is_circuit_breaker_active(user_id)
            
            return {
                "balance": credit_account.current_balance,
                "reserved_balance": credit_account.reserved_balance,
                "status": credit_account.status.value,
                "recent_usage": recent_usage,
                "circuit_breaker_active": circuit_breaker_active,
                "last_activity": credit_account.last_activity.isoformat() if credit_account.last_activity else None
            }
        
        except Exception as e:
            logger.error(f"Error getting credit status for user {user_id}: {e}")
            return {"error": str(e)}
    
    async def force_circuit_breaker(self, user_id: str, reason: str, duration: int = 300):
        """Force circuit breaker activation for user (admin function)"""
        if user_id not in self.middleware.circuit_breaker_states:
            self.middleware.circuit_breaker_states[user_id] = {
                "consecutive_failures": 0,
                "total_failures": 0,
                "last_failure_time": None
            }
        
        state = self.middleware.circuit_breaker_states[user_id]
        state["cooldown_until"] = time.time() + duration
        state["activation_reason"] = reason
        state["forced"] = True
        
        logger.warning(f"Circuit breaker activated for user {user_id}: {reason}")
    
    async def reset_user_circuit_breaker(self, user_id: str):
        """Reset circuit breaker for user (admin function)"""
        if user_id in self.middleware.circuit_breaker_states:
            del self.middleware.circuit_breaker_states[user_id]
        
        if user_id in self.middleware.user_request_counts:
            del self.middleware.user_request_counts[user_id]
        
        logger.info(f"Circuit breaker reset for user {user_id}")


# Integration function
async def integrate_credit_tracking(proxy_app: Any, db: Any) -> ProxyCreditIntegration:
    """Integrate credit tracking with proxy server"""
    integration = ProxyCreditIntegration(db)
    middleware = await integration.initialize()
    
    # Add middleware to proxy app
    proxy_app.add_middleware(ProxyCreditMiddleware, 
                           credit_service=integration.credit_service,
                           usage_tracker=integration.usage_tracker,
                           cost_calculator=integration.cost_calculator,
                           credit_validator=integration.credit_validator,
                           db=db)
    
    return integration