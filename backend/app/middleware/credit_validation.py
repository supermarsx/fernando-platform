"""
Credit Validation Middleware

Comprehensive credit validation and reservation system for LLM requests:
- Credit balance validation before requests
- Credit reservation system for long-running operations
- Automatic credit replenishment alerts
- Credit overage protection
- Credit usage rate limiting
"""

import asyncio
import time
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from functools import wraps
import logging

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.credit import (
    CreditAccount, CreditTransaction, CreditPolicy, CreditAlert,
    CreditTransactionType, CreditStatus, CreditPolicyType, LLMModelType
)
from app.services.credit_service import CreditService
from app.core.telemetry import telemetry_event, TelemetryEvent, TelemetryLevel

logger = logging.getLogger(__name__)


class CreditValidationError(HTTPException):
    """Credit validation exception"""
    def __init__(self, detail: str, available_balance: float = 0, required_amount: float = 0):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Insufficient credits",
                "message": detail,
                "available_balance": available_balance,
                "required_amount": required_amount,
                "error_code": "CREDIT_INSUFFICIENT"
            }
        )


class CreditReservationError(HTTPException):
    """Credit reservation exception"""
    def __init__(self, detail: str, reserved_amount: float = 0):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "error": "Credit reservation failed",
                "message": detail,
                "reserved_amount": reserved_amount,
                "error_code": "CREDIT_RESERVATION_FAILED"
            }
        )


class CreditRateLimitError(HTTPException):
    """Credit rate limit exception"""
    def __init__(self, detail: str, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Credit rate limit exceeded",
                "message": detail,
                "retry_after": retry_after,
                "error_code": "CREDIT_RATE_LIMIT"
            }
        )


class CreditReservation:
    """Credit reservation for long-running operations"""
    
    def __init__(self, reservation_id: str, account_id: int, amount: float, expires_at: datetime):
        self.reservation_id = reservation_id
        self.account_id = account_id
        self.amount = amount
        self.expires_at = expires_at
        self.created_at = datetime.utcnow()
        self.status = "active"
    
    def is_expired(self) -> bool:
        """Check if reservation has expired"""
        return datetime.utcnow() > self.expires_at
    
    def extend(self, additional_seconds: int):
        """Extend reservation expiration"""
        self.expires_at += timedelta(seconds=additional_seconds)


class CreditValidator:
    """Credit validation and reservation manager"""
    
    def __init__(self, db: Session):
        self.db = db
        self.credit_service = CreditService(db)
        self.active_reservations: Dict[str, CreditReservation] = {}
        self.rate_limit_cache: Dict[str, List[datetime]] = {}
        
        # Rate limiting settings
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_requests = 100  # requests per window
        
        # Reservation settings
        self.default_reservation_timeout = 300  # 5 minutes
        self.max_reservation_timeout = 3600  # 1 hour
    
    async def validate_credit_balance(
        self,
        user_id: int,
        estimated_cost: float,
        operation_type: str,
        service_type: str = "llm",
        model_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Validate credit balance before operation
        
        Args:
            user_id: User performing the operation
            estimated_cost: Estimated cost of the operation
            operation_type: Type of operation (extract_fields, generate_text, etc.)
            service_type: Type of service (llm, api, document_processing)
            model_type: LLM model type if applicable
            **kwargs: Additional validation parameters
        
        Returns:
            Validation result with balance information
        
        Raises:
            CreditValidationError: If insufficient credits
        """
        try:
            # Get user's credit account
            credit_account = self.db.query(CreditAccount).filter(
                and_(
                    CreditAccount.user_id == user_id,
                    CreditAccount.status == CreditStatus.ACTIVE
                )
            ).first()
            
            if not credit_account:
                raise CreditValidationError(
                    "No active credit account found",
                    available_balance=0,
                    required_amount=estimated_cost
                )
            
            # Check minimum balance requirements
            policies = self.db.query(CreditPolicy).filter(
                and_(
                    CreditPolicy.account_id == credit_account.id,
                    CreditPolicy.is_active == True,
                    CreditPolicy.valid_from <= datetime.utcnow(),
                    or_(CreditPolicy.valid_to.is_(None), CreditPolicy.valid_to >= datetime.utcnow())
                )
            ).all()
            
            min_balance_required = 0
            for policy in policies:
                if policy.minimum_balance and policy.minimum_balance > min_balance_required:
                    min_balance_required = policy.minimum_balance
            
            # Available balance (current - reserved - minimum required)
            available_balance = credit_account.current_balance - credit_account.reserved_balance - min_balance_required
            
            # Check if user has enough credits
            if available_balance < estimated_cost:
                # Log failed validation
                await self._log_credit_event(
                    user_id, "validation_failed", {
                        "available_balance": available_balance,
                        "required_amount": estimated_cost,
                        "operation_type": operation_type,
                        "service_type": service_type
                    }
                )
                
                # Check if overage is allowed
                if await self._check_overage_allowed(user_id, credit_account):
                    # Allow overage but flag it
                    logger.warning(f"Allowing credit overage for user {user_id}: {estimated_cost} > {available_balance}")
                    return {
                        "sufficient_credits": True,
                        "overage_allowed": True,
                        "available_balance": available_balance,
                        "required_amount": estimated_cost,
                        "balance_after_operation": available_balance - estimated_cost,
                        "warning": "Operation will exceed available balance but overage is allowed"
                    }
                else:
                    raise CreditValidationError(
                        f"Insufficient credits. Required: {estimated_cost}, Available: {available_balance}",
                        available_balance=available_balance,
                        required_amount=estimated_cost
                    )
            
            # Apply rate limiting
            await self._check_rate_limit(user_id, operation_type, service_type)
            
            # Success validation
            result = {
                "sufficient_credits": True,
                "overage_allowed": False,
                "available_balance": available_balance,
                "required_amount": estimated_cost,
                "balance_after_operation": available_balance - estimated_cost,
                "credit_account_id": credit_account.id
            }
            
            # Log successful validation
            await self._log_credit_event(
                user_id, "validation_success", {
                    "available_balance": available_balance,
                    "required_amount": estimated_cost,
                    "operation_type": operation_type,
                    "service_type": service_type
                }
            )
            
            return result
            
        except CreditValidationError:
            raise
        except Exception as e:
            logger.error(f"Credit validation error: {e}")
            raise CreditValidationError(
                f"Credit validation failed: {str(e)}",
                available_balance=0,
                required_amount=estimated_cost
            )
    
    async def reserve_credits(
        self,
        user_id: int,
        amount: float,
        operation_id: str,
        timeout_seconds: Optional[int] = None,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Reserve credits for a long-running operation
        
        Args:
            user_id: User performing the operation
            amount: Amount of credits to reserve
            operation_id: Unique ID for the operation
            timeout_seconds: Reservation timeout (default: 5 minutes)
            **kwargs: Additional reservation parameters
        
        Returns:
            Tuple of (success, reservation_id)
        
        Raises:
            CreditReservationError: If reservation fails
        """
        if operation_id in self.active_reservations:
            return True, self.active_reservations[operation_id].reservation_id
        
        timeout_seconds = timeout_seconds or self.default_reservation_timeout
        timeout_seconds = min(timeout_seconds, self.max_reservation_timeout)
        
        try:
            # Get credit account
            credit_account = self.db.query(CreditAccount).filter(
                and_(
                    CreditAccount.user_id == user_id,
                    CreditAccount.status == CreditStatus.ACTIVE
                )
            ).with_for_update().first()
            
            if not credit_account:
                raise CreditReservationError("No active credit account found")
            
            # Check available balance
            available_balance = credit_account.current_balance - credit_account.reserved_balance
            if available_balance < amount:
                raise CreditReservationError(
                    f"Insufficient credits for reservation. Required: {amount}, Available: {available_balance}",
                    amount
                )
            
            # Create reservation
            reservation = CreditReservation(
                reservation_id=f"res_{int(time.time())}_{operation_id}",
                account_id=credit_account.id,
                amount=amount,
                expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds)
            )
            
            # Update account reserved balance
            credit_account.reserved_balance += amount
            credit_account.last_activity = datetime.utcnow()
            
            # Store reservation
            self.active_reservations[operation_id] = reservation
            
            self.db.commit()
            
            # Log reservation
            await self._log_credit_event(
                user_id, "reservation_created", {
                    "reservation_id": reservation.reservation_id,
                    "amount": amount,
                    "operation_id": operation_id,
                    "timeout_seconds": timeout_seconds
                }
            )
            
            logger.info(f"Reserved {amount} credits for operation {operation_id}")
            return True, reservation.reservation_id
            
        except CreditReservationError:
            raise
        except Exception as e:
            logger.error(f"Credit reservation error: {e}")
            raise CreditReservationError(f"Credit reservation failed: {str(e)}")
    
    async def release_reservation(self, operation_id: str, user_id: int) -> bool:
        """
        Release credit reservation
        
        Args:
            operation_id: ID of the operation
            user_id: User who made the reservation
        
        Returns:
            True if reservation was released
        """
        if operation_id not in self.active_reservations:
            return False
        
        reservation = self.active_reservations[operation_id]
        
        try:
            # Get credit account
            credit_account = self.db.query(CreditAccount).filter(
                and_(
                    CreditAccount.id == reservation.account_id,
                    CreditAccount.user_id == user_id
                )
            ).with_for_update().first()
            
            if credit_account:
                # Release reservation
                credit_account.reserved_balance = max(0, credit_account.reserved_balance - reservation.amount)
                credit_account.last_activity = datetime.utcnow()
                
                self.db.commit()
            
            # Remove from active reservations
            del self.active_reservations[operation_id]
            
            # Log release
            await self._log_credit_event(
                user_id, "reservation_released", {
                    "operation_id": operation_id,
                    "amount": reservation.amount,
                    "reservation_id": reservation.reservation_id
                }
            )
            
            logger.info(f"Released {reservation.amount} credits for operation {operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing reservation: {e}")
            return False
    
    async def execute_with_reserved_credits(
        self,
        user_id: int,
        operation_id: str,
        cost: float,
        operation_func,
        *args,
        **kwargs
    ):
        """
        Execute operation with credit reservation and automatic cleanup
        
        Args:
            user_id: User performing the operation
            operation_id: Unique operation ID
            cost: Cost of the operation
            operation_func: Function to execute
            *args: Arguments for operation function
            **kwargs: Keyword arguments for operation function
        
        Returns:
            Result of operation function
        """
        reservation_id = None
        try:
            # Reserve credits
            success, reservation_id = await self.reserve_credits(
                user_id=user_id,
                amount=cost,
                operation_id=operation_id
            )
            
            if not success:
                raise CreditReservationError("Failed to reserve credits")
            
            # Execute operation
            result = await operation_func(*args, **kwargs)
            
            # Release reservation and deduct cost
            await self._finalize_reserved_operation(
                user_id, operation_id, cost, reservation_id
            )
            
            return result
            
        except Exception as e:
            # Release reservation on error
            await self.release_reservation(operation_id, user_id)
            logger.error(f"Operation {operation_id} failed, reservation released: {e}")
            raise
    
    async def _finalize_reserved_operation(
        self,
        user_id: int,
        operation_id: str,
        cost: float,
        reservation_id: str
    ):
        """Finalize operation by releasing reservation and deducting cost"""
        try:
            # Release reservation
            await self.release_reservation(operation_id, user_id)
            
            # Deduct cost
            await self.credit_service.deduct_credits(
                user_id=user_id,
                amount=cost,
                transaction_type=CreditTransactionType.USAGE_DEDUCTION,
                description=f"Reserved operation: {operation_id}",
                metadata={
                    "reservation_id": reservation_id,
                    "operation_id": operation_id,
                    "operation_type": "llm_extraction"
                }
            )
            
        except Exception as e:
            logger.error(f"Error finalizing reserved operation: {e}")
            raise
    
    async def cleanup_expired_reservations(self):
        """Clean up expired reservations"""
        expired_operations = []
        now = datetime.utcnow()
        
        for operation_id, reservation in self.active_reservations.items():
            if reservation.is_expired():
                expired_operations.append(operation_id)
        
        for operation_id in expired_operations:
            await self.release_reservation(operation_id, reservation.account_id)
            logger.info(f"Cleaned up expired reservation for operation {operation_id}")
    
    async def _check_rate_limit(self, user_id: int, operation_type: str, service_type: str):
        """Check rate limiting for credit operations"""
        key = f"{user_id}:{operation_type}:{service_type}"
        now = datetime.utcnow()
        
        if key not in self.rate_limit_cache:
            self.rate_limit_cache[key] = []
        
        # Remove old timestamps outside the window
        cutoff_time = now - timedelta(seconds=self.rate_limit_window)
        self.rate_limit_cache[key] = [
            timestamp for timestamp in self.rate_limit_cache[key]
            if timestamp > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.rate_limit_cache[key]) >= self.rate_limit_max_requests:
            raise CreditRateLimitError(
                f"Rate limit exceeded for {operation_type} operations",
                retry_after=self.rate_limit_window
            )
        
        # Add current timestamp
        self.rate_limit_cache[key].append(now)
    
    async def _check_overage_allowed(self, user_id: int, credit_account: CreditAccount) -> bool:
        """Check if overage is allowed for user"""
        # Check user subscription/plan
        # This would integrate with billing/subscription system
        # For now, allow overage for all users
        return True
    
    async def _log_credit_event(self, user_id: int, event_type: str, metadata: Dict[str, Any]):
        """Log credit-related events for telemetry"""
        try:
            telemetry_event(
                event_name=f"credit.{event_type}",
                event_type=TelemetryEvent.SYSTEM_EVENT,
                level=TelemetryLevel.INFO,
                user_id=user_id,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Error logging credit event: {e}")


# Decorator for automatic credit validation
def validate_credits(
    estimated_cost_func=None,
    operation_type: str = "llm_operation",
    service_type: str = "llm",
    auto_reserve: bool = False
):
    """
    Decorator to automatically validate and reserve credits
    
    Args:
        estimated_cost_func: Function to calculate estimated cost
        operation_type: Type of operation
        service_type: Type of service
        auto_reserve: Whether to auto-reserve credits
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Extract user_id from request context
            user_id = getattr(request.state, 'user_id', None)
            if not user_id:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            # Get cost estimator
            cost = 0.1  # default cost
            if estimated_cost_func:
                try:
                    cost = await estimated_cost_func(*args, **kwargs)
                except:
                    pass
            
            # Validate credits
            validator = request.app.state.credit_validator
            validation_result = await validator.validate_credit_balance(
                user_id=user_id,
                estimated_cost=cost,
                operation_type=operation_type,
                service_type=service_type
            )
            
            # Add validation result to request state
            request.state.credit_validation = validation_result
            
            # Auto-reserve if requested
            if auto_reserve:
                operation_id = f"{func.__name__}_{int(time.time())}"
                success, reservation_id = await validator.reserve_credits(
                    user_id=user_id,
                    amount=cost,
                    operation_id=operation_id
                )
                request.state.credit_reservation_id = reservation_id
            
            # Execute function
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Background task for periodic cleanup
async def start_credit_cleanup_task():
    """Start background task for cleaning up expired reservations"""
    while True:
        try:
            # This would be initialized with proper DB dependency
            # await credit_validator.cleanup_expired_reservations()
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            logger.error(f"Error in credit cleanup task: {e}")
            await asyncio.sleep(60)