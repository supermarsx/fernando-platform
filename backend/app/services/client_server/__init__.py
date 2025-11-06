"""
Client Server Implementation

This module provides the core functionality for Client Server instances,
including customer management, billing integration, and client-specific features.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import uuid
from decimal import Decimal
import json

from .server_architecture import ServerType, server_architecture
from ..models.server_architecture import (
    Client, Subscription, UsageRecord, CustomerOnboarding,
    ClientServerRegistration, BillingIntegration
)
from ..core.database import get_db
from ..core.config import settings
from ..core.telemetry import telemetry_tracker


class CustomerStatus(str, Enum):
    """Customer status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillingStatus(str, Enum):
    """Billing status enumeration"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class UsageType(str, Enum):
    """Usage tracking type enumeration"""
    DOCUMENT_PROCESSING = "document_processing"
    API_CALLS = "api_calls"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    SUPPORT_TICKETS = "support_tickets"


@dataclass
class CustomerMetrics:
    """Customer metrics and analytics"""
    customer_id: str
    total_documents_processed: int = 0
    total_api_calls: int = 0
    storage_used_gb: float = 0.0
    bandwidth_used_gb: float = 0.0
    support_tickets: int = 0
    revenue_generated: Decimal = Decimal('0.00')
    last_activity: Optional[datetime] = None
    account_creation_date: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'customer_id': self.customer_id,
            'total_documents_processed': self.total_documents_processed,
            'total_api_calls': self.total_api_calls,
            'storage_used_gb': self.storage_used_gb,
            'bandwidth_used_gb': self.bandwidth_used_gb,
            'support_tickets': self.support_tickets,
            'revenue_generated': float(self.revenue_generated),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'account_creation_date': self.account_creation_date.isoformat(),
            'account_age_days': (datetime.utcnow() - self.account_creation_date).days
        }


class CustomerManagement:
    """
    Customer management system for Client Server
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._customer_metrics: Dict[str, CustomerMetrics] = {}
        
    def create_customer(self, customer_data: Dict[str, Any]) -> str:
        """Create a new customer"""
        try:
            customer_id = str(uuid.uuid4())
            
            # Validate required fields
            required_fields = ['email', 'company_name', 'plan_type']
            for field in required_fields:
                if field not in customer_data:
                    raise ValueError(f"Required field '{field}' is missing")
            
            # Create customer record
            customer = Client(
                id=customer_id,
                email=customer_data['email'],
                company_name=customer_data['company_name'],
                status=CustomerStatus.PENDING,
                plan_type=customer_data.get('plan_type', 'basic'),
                contact_person=customer_data.get('contact_person'),
                phone=customer_data.get('phone'),
                address=customer_data.get('address'),
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db = next(get_db())
            db.add(customer)
            db.commit()
            db.refresh(customer)
            
            # Initialize metrics
            self._customer_metrics[customer_id] = CustomerMetrics(customer_id=customer_id)
            
            # Track telemetry
            telemetry_tracker.track_event('customer_created', {
                'customer_id': customer_id,
                'plan_type': customer.plan_type,
                'server_type': ServerType.CLIENT
            })
            
            self.logger.info(f"Created customer: {customer_id}")
            return customer_id
            
        except Exception as e:
            self.logger.error(f"Error creating customer: {str(e)}")
            raise
            
    def onboard_customer(self, customer_id: str, onboarding_data: Dict[str, Any]) -> bool:
        """Onboard a new customer"""
        try:
            db = next(get_db())
            customer = db.query(Client).filter(Client.id == customer_id).first()
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            # Create onboarding record
            onboarding = CustomerOnboarding(
                customer_id=customer_id,
                status='initiated',
                steps_completed=[],
                documents_provided=onboarding_data.get('documents_provided', []),
                api_keys_generated=[],
                created_at=datetime.utcnow()
            )
            
            db.add(onboarding)
            
            # Update customer status
            customer.status = CustomerStatus.ACTIVE
            customer.onboarding_completed = True
            
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('customer_onboarded', {
                'customer_id': customer_id,
                'server_type': ServerType.CLIENT
            })
            
            self.logger.info(f"Onboarded customer: {customer_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error onboarding customer {customer_id}: {str(e)}")
            raise
            
    def update_customer_status(self, customer_id: str, status: CustomerStatus) -> bool:
        """Update customer status"""
        try:
            db = next(get_db())
            customer = db.query(Client).filter(Client.id == customer_id).first()
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            old_status = customer.status
            customer.status = status
            customer.updated_at = datetime.utcnow()
            
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('customer_status_updated', {
                'customer_id': customer_id,
                'old_status': old_status,
                'new_status': status,
                'server_type': ServerType.CLIENT
            })
            
            self.logger.info(f"Updated customer {customer_id} status from {old_status} to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating customer status: {str(e)}")
            raise
            
    def get_customer_info(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer information"""
        try:
            db = next(get_db())
            customer = db.query(Client).filter(Client.id == customer_id).first()
            
            if not customer:
                return None
            
            # Get metrics
            metrics = self._customer_metrics.get(customer_id, CustomerMetrics(customer_id))
            
            return {
                'id': customer.id,
                'email': customer.email,
                'company_name': customer.company_name,
                'status': customer.status,
                'plan_type': customer.plan_type,
                'contact_person': customer.contact_person,
                'phone': customer.phone,
                'address': customer.address,
                'created_at': customer.created_at.isoformat(),
                'updated_at': customer.updated_at.isoformat(),
                'metrics': metrics.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting customer info: {str(e)}")
            return None
            
    def get_customer_metrics(self, customer_id: str) -> Optional[CustomerMetrics]:
        """Get customer metrics"""
        return self._customer_metrics.get(customer_id)
        
    def list_customers(self, status: Optional[CustomerStatus] = None, 
                      limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List customers with optional filtering"""
        try:
            db = next(get_db())
            query = db.query(Client)
            
            if status:
                query = query.filter(Client.status == status)
                
            customers = query.offset(offset).limit(limit).all()
            
            result = []
            for customer in customers:
                metrics = self._customer_metrics.get(customer.id, CustomerMetrics(customer.id))
                result.append({
                    'id': customer.id,
                    'email': customer.email,
                    'company_name': customer.company_name,
                    'status': customer.status,
                    'plan_type': customer.plan_type,
                    'created_at': customer.created_at.isoformat(),
                    'metrics': metrics.to_dict()
                })
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing customers: {str(e)}")
            return []


class BillingIntegration:
    """
    Billing integration system for Client Server
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._billing_status: Dict[str, BillingStatus] = {}
        
    def create_subscription(self, customer_id: str, plan_data: Dict[str, Any]) -> str:
        """Create a new subscription"""
        try:
            subscription_id = str(uuid.uuid4())
            
            # Create subscription
            subscription = Subscription(
                id=subscription_id,
                customer_id=customer_id,
                plan_name=plan_data['plan_name'],
                billing_cycle=plan_data.get('billing_cycle', 'monthly'),
                amount=Decimal(str(plan_data.get('amount', 0))),
                currency=plan_data.get('currency', 'USD'),
                status=BillingStatus.TRIAL,
                start_date=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db = next(get_db())
            db.add(subscription)
            db.commit()
            
            # Update billing status
            self._billing_status[customer_id] = BillingStatus.TRIAL
            
            # Track telemetry
            telemetry_tracker.track_event('subscription_created', {
                'customer_id': customer_id,
                'subscription_id': subscription_id,
                'plan_name': plan_data['plan_name'],
                'amount': float(subscription.amount),
                'server_type': ServerType.CLIENT
            })
            
            self.logger.info(f"Created subscription {subscription_id} for customer {customer_id}")
            return subscription_id
            
        except Exception as e:
            self.logger.error(f"Error creating subscription: {str(e)}")
            raise
            
    def process_payment(self, customer_id: str, amount: Decimal, 
                       payment_method: str) -> Dict[str, Any]:
        """Process a payment for a customer"""
        try:
            # Get subscription
            db = next(get_db())
            subscription = db.query(Subscription).filter(
                Subscription.customer_id == customer_id
            ).first()
            
            if not subscription:
                raise ValueError(f"No subscription found for customer {customer_id}")
            
            # Process payment (mock implementation)
            # In real implementation, integrate with Stripe, PayPal, etc.
            payment_success = True  # Mock success
            
            if payment_success:
                subscription.status = BillingStatus.ACTIVE
                subscription.last_payment_date = datetime.utcnow()
                self._billing_status[customer_id] = BillingStatus.ACTIVE
                
                # Update customer metrics
                client_mgmt = CustomerManagement()
                metrics = client_mgmt.get_customer_metrics(customer_id)
                if metrics:
                    metrics.revenue_generated += amount
                    
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('payment_processed', {
                    'customer_id': customer_id,
                    'subscription_id': subscription.id,
                    'amount': float(amount),
                    'payment_method': payment_method,
                    'server_type': ServerType.CLIENT
                })
                
                return {
                    'success': True,
                    'transaction_id': str(uuid.uuid4()),
                    'amount': float(amount),
                    'currency': subscription.currency,
                    'status': 'completed'
                }
            else:
                subscription.status = BillingStatus.PAST_DUE
                self._billing_status[customer_id] = BillingStatus.PAST_DUE
                db.commit()
                
                return {
                    'success': False,
                    'error': 'Payment processing failed',
                    'status': 'failed'
                }
                
        except Exception as e:
            self.logger.error(f"Error processing payment: {str(e)}")
            raise
            
    def check_billing_status(self, customer_id: str) -> BillingStatus:
        """Check customer's billing status"""
        return self._billing_status.get(customer_id, BillingStatus.PAST_DUE)
        
    def suspend_subscription(self, customer_id: str, reason: str) -> bool:
        """Suspend a customer's subscription"""
        try:
            db = next(get_db())
            subscription = db.query(Subscription).filter(
                Subscription.customer_id == customer_id
            ).first()
            
            if subscription:
                subscription.status = BillingStatus.SUSPENDED
                subscription.suspension_reason = reason
                subscription.suspended_at = datetime.utcnow()
                
                self._billing_status[customer_id] = BillingStatus.SUSPENDED
                
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('subscription_suspended', {
                    'customer_id': customer_id,
                    'subscription_id': subscription.id,
                    'reason': reason,
                    'server_type': ServerType.CLIENT
                })
                
                self.logger.info(f"Suspended subscription for customer {customer_id}: {reason}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error suspending subscription: {str(e)}")
            return False


class UsageTracking:
    """
    Usage tracking system for Client Server
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def record_usage(self, customer_id: str, usage_type: UsageType, 
                    amount: float, metadata: Dict[str, Any] = None) -> bool:
        """Record customer usage"""
        try:
            usage_record = UsageRecord(
                id=str(uuid.uuid4()),
                customer_id=customer_id,
                usage_type=usage_type.value,
                amount=amount,
                timestamp=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Save to database
            db = next(get_db())
            db.add(usage_record)
            db.commit()
            
            # Update customer metrics
            client_mgmt = CustomerManagement()
            metrics = client_mgmt.get_customer_metrics(customer_id)
            if metrics:
                metrics.last_activity = datetime.utcnow()
                
                # Update specific metrics based on usage type
                if usage_type == UsageType.DOCUMENT_PROCESSING:
                    metrics.total_documents_processed += int(amount)
                elif usage_type == UsageType.API_CALLS:
                    metrics.total_api_calls += int(amount)
                elif usage_type == UsageType.STORAGE:
                    metrics.storage_used_gb += amount
                elif usage_type == UsageType.BANDWIDTH:
                    metrics.bandwidth_used_gb += amount
                elif usage_type == UsageType.SUPPORT_TICKETS:
                    metrics.support_tickets += int(amount)
            
            # Track telemetry
            telemetry_tracker.track_event('usage_recorded', {
                'customer_id': customer_id,
                'usage_type': usage_type.value,
                'amount': amount,
                'server_type': ServerType.CLIENT
            })
            
            self.logger.debug(f"Recorded usage for customer {customer_id}: {usage_type.value} = {amount}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording usage: {str(e)}")
            return False
            
    def get_usage_summary(self, customer_id: str, 
                         start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get usage summary for a customer"""
        try:
            db = next(get_db())
            usage_records = db.query(UsageRecord).filter(
                UsageRecord.customer_id == customer_id,
                UsageRecord.timestamp >= start_date,
                UsageRecord.timestamp <= end_date
            ).all()
            
            summary = {
                'customer_id': customer_id,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_usage': {},
                'breakdown': []
            }
            
            # Aggregate usage by type
            for record in usage_records:
                usage_type = record.usage_type
                amount = record.amount
                
                if usage_type in summary['total_usage']:
                    summary['total_usage'][usage_type] += amount
                else:
                    summary['total_usage'][usage_type] = amount
                    
                summary['breakdown'].append({
                    'type': usage_type,
                    'amount': amount,
                    'timestamp': record.timestamp.isoformat(),
                    'metadata': record.metadata
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting usage summary: {str(e)}")
            return {}
            
    def check_usage_limits(self, customer_id: str) -> Dict[str, Any]:
        """Check if customer is within usage limits"""
        try:
            # Get customer subscription and limits
            db = next(get_db())
            subscription = db.query(Subscription).filter(
                Subscription.customer_id == customer_id
            ).first()
            
            if not subscription:
                return {'within_limits': False, 'error': 'No subscription found'}
            
            # Get current month usage
            current_month = datetime.utcnow().replace(day=1)
            usage_summary = self.get_usage_summary(customer_id, current_month, datetime.utcnow())
            
            # Check limits based on plan (mock implementation)
            limits = self._get_plan_limits(subscription.plan_name)
            
            status = {'within_limits': True, 'usage': {}, 'limits': limits, 'exceeded': []}
            
            for usage_type, amount in usage_summary.get('total_usage', {}).items():
                status['usage'][usage_type] = amount
                
                if usage_type in limits:
                    if amount > limits[usage_type]:
                        status['within_limits'] = False
                        status['exceeded'].append({
                            'type': usage_type,
                            'current': amount,
                            'limit': limits[usage_type],
                            'overage': amount - limits[usage_type]
                        })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error checking usage limits: {str(e)}")
            return {'within_limits': False, 'error': str(e)}
    
    def _get_plan_limits(self, plan_name: str) -> Dict[str, float]:
        """Get usage limits for a plan"""
        limits = {
            'basic': {
                'document_processing': 100,
                'api_calls': 1000,
                'storage': 1.0,  # GB
                'bandwidth': 5.0  # GB
            },
            'professional': {
                'document_processing': 1000,
                'api_calls': 10000,
                'storage': 10.0,
                'bandwidth': 50.0
            },
            'enterprise': {
                'document_processing': -1,  # Unlimited
                'api_calls': -1,
                'storage': 100.0,
                'bandwidth': 500.0
            }
        }
        
        return limits.get(plan_name, limits['basic'])


class ClientServerAPI:
    """
    Client Server API for handling client-specific operations
    """
    
    def __init__(self):
        self.customer_mgmt = CustomerManagement()
        self.billing = BillingIntegration()
        self.usage_tracking = UsageTracking()
        self.logger = logging.getLogger(__name__)
        
    def register_with_supplier(self, server_info: Dict[str, Any]) -> bool:
        """Register this client server with the supplier"""
        try:
            registration = ClientServerRegistration(
                server_id=server_info.get('server_id'),
                supplier_server_url=server_info.get('supplier_url'),
                registration_token=server_info.get('registration_token'),
                status='active',
                registered_at=datetime.utcnow()
            )
            
            # Save to database
            db = next(get_db())
            db.add(registration)
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('client_server_registered', {
                'server_id': server_info.get('server_id'),
                'supplier_url': server_info.get('supplier_url'),
                'server_type': ServerType.CLIENT
            })
            
            self.logger.info(f"Client server registered with supplier")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering with supplier: {str(e)}")
            return False
            
    def sync_with_supplier(self) -> Dict[str, Any]:
        """Sync data with supplier server"""
        try:
            # Get registration info
            db = next(get_db())
            registration = db.query(ClientServerRegistration).first()
            
            if not registration:
                return {'success': False, 'error': 'Not registered with supplier'}
            
            # Mock sync operation
            # In real implementation, call supplier API
            sync_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'customers_count': len(self.customer_mgmt._customer_metrics),
                'active_subscriptions': len([s for s in self.billing._billing_status.values() 
                                           if s == BillingStatus.ACTIVE]),
                'total_revenue': sum(m.revenue_generated for m in self.customer_mgmt._customer_metrics.values())
            }
            
            # Track telemetry
            telemetry_tracker.track_event('supplier_sync_completed', {
                'customers_count': sync_data['customers_count'],
                'total_revenue': float(sync_data['total_revenue']),
                'server_type': ServerType.CLIENT
            })
            
            self.logger.info("Synced with supplier server")
            return {'success': True, 'data': sync_data}
            
        except Exception as e:
            self.logger.error(f"Error syncing with supplier: {str(e)}")
            return {'success': False, 'error': str(e)}


# Global instances
client_server_api = ClientServerAPI()
customer_management = CustomerManagement()
billing_integration = BillingIntegration()
usage_tracking = UsageTracking()


# API endpoints would go here
# These would be FastAPI endpoints that use the above classes

"""
Example API endpoint structure:

@router.post("/customers/")
@require_feature("customer_management")
async def create_customer(customer_data: CustomerCreateRequest):
    try:
        customer_id = customer_management.create_customer(customer_data.dict())
        return {"customer_id": customer_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/customers/{customer_id}")
@require_feature("customer_management")
async def get_customer(customer_id: str):
    customer_info = customer_management.get_customer_info(customer_id)
    if not customer_info:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer_info

@router.post("/billing/subscription/")
@require_feature("billing_integration")
async def create_subscription(subscription_data: SubscriptionCreateRequest):
    subscription_id = billing_integration.create_subscription(
        subscription_data.customer_id,
        subscription_data.dict()
    )
    return {"subscription_id": subscription_id, "status": "created"}

@router.post("/usage/record/")
@require_feature("usage_tracking")
async def record_usage(usage_data: UsageRecordRequest):
    success = usage_tracking.record_usage(
        usage_data.customer_id,
        usage_data.usage_type,
        usage_data.amount,
        usage_data.metadata
    )
    return {"recorded": success}
"""