"""
Supplier Server Implementation

This module provides the core functionality for Supplier Server instances,
including licensing capabilities, client server management, and revenue sharing.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import uuid
from decimal import Decimal
import json

from ..core.server_architecture import ServerType, server_architecture
from ..models.server_architecture import (
    SupplierServer, ClientServerRegistration, License,
    ClientServerMetrics, RevenueShare, CommissionTracking,
    SupplierAnalytics, LicenseTier
)
from ..core.database import get_db
from ..core.config import settings
from ..core.telemetry import telemetry_tracker


class LicenseStatus(str, Enum):
    """License status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class LicenseType(str, Enum):
    """License type enumeration"""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class RevenueShareStatus(str, Enum):
    """Revenue share status enumeration"""
    PENDING = "pending"
    CALCULATED = "calculated"
    PAID = "paid"
    DISPUTED = "disputed"


@dataclass
class SupplierMetrics:
    """Supplier metrics and analytics"""
    supplier_id: str
    total_client_servers: int = 0
    total_active_licenses: int = 0
    total_revenue: Decimal = Decimal('0.00')
    monthly_recurring_revenue: Decimal = Decimal('0.00')
    client_servers_onboarded: int = 0
    licenses_issued: int = 0
    commissions_calculated: Decimal = Decimal('0.00')
    last_activity: Optional[datetime] = None
    creation_date: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'supplier_id': self.supplier_id,
            'total_client_servers': self.total_client_servers,
            'total_active_licenses': self.total_active_licenses,
            'total_revenue': float(self.total_revenue),
            'monthly_recurring_revenue': float(self.monthly_recurring_revenue),
            'client_servers_onboarded': self.client_servers_onboarded,
            'licenses_issued': self.licenses_issued,
            'commissions_calculated': float(self.commissions_calculated),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'creation_date': self.creation_date.isoformat(),
            'days_in_operation': (datetime.utcnow() - self.creation_date).days
        }


class LicensingManagement:
    """
    Licensing management system for Supplier Server
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._license_templates = self._initialize_license_templates()
        
    def _initialize_license_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize license tier templates"""
        return {
            LicenseType.BASIC: {
                'name': 'Basic License',
                'price_monthly': Decimal('99.00'),
                'price_yearly': Decimal('990.00'),
                'features': [
                    'document_processing',
                    'basic_customer_management',
                    'email_support',
                    '5gb_storage'
                ],
                'limits': {
                    'documents_per_month': 100,
                    'api_calls_per_month': 1000,
                    'customers': 10,
                    'storage_gb': 5
                },
                'commission_rate': Decimal('0.20')  # 20%
            },
            LicenseType.PROFESSIONAL: {
                'name': 'Professional License',
                'price_monthly': Decimal('299.00'),
                'price_yearly': Decimal('2990.00'),
                'features': [
                    'document_processing',
                    'advanced_customer_management',
                    'billing_integration',
                    'priority_support',
                    '25gb_storage',
                    'custom_branding'
                ],
                'limits': {
                    'documents_per_month': 1000,
                    'api_calls_per_month': 10000,
                    'customers': 100,
                    'storage_gb': 25
                },
                'commission_rate': Decimal('0.25')  # 25%
            },
            LicenseType.ENTERPRISE: {
                'name': 'Enterprise License',
                'price_monthly': Decimal('999.00'),
                'price_yearly': Decimal('9990.00'),
                'features': [
                    'unlimited_document_processing',
                    'full_feature_set',
                    'dedicated_support',
                    'unlimited_storage',
                    'white_label',
                    'custom_integrations',
                    'compliance_tools'
                ],
                'limits': {
                    'documents_per_month': -1,  # Unlimited
                    'api_calls_per_month': -1,
                    'customers': -1,
                    'storage_gb': 1000
                },
                'commission_rate': Decimal('0.30')  # 30%
            }
        }
    
    def create_license(self, client_server_id: str, license_type: LicenseType, 
                      term_months: int = 12) -> str:
        """Create a new license for a client server"""
        try:
            license_id = str(uuid.uuid4())
            template = self._license_templates[license_type]
            
            # Calculate pricing
            if term_months >= 12:
                price = template['price_yearly']
                billing_cycle = 'yearly'
            else:
                price = template['price_monthly']
                billing_cycle = 'monthly'
            
            # Create license
            license_obj = License(
                id=license_id,
                client_server_id=client_server_id,
                license_type=license_type,
                status=LicenseStatus.TRIAL,
                billing_cycle=billing_cycle,
                amount=price,
                commission_rate=template['commission_rate'],
                features=template['features'],
                limits=template['limits'],
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=term_months * 30),
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db = next(get_db())
            db.add(license_obj)
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('license_created', {
                'license_id': license_id,
                'client_server_id': client_server_id,
                'license_type': license_type,
                'amount': float(price),
                'server_type': ServerType.SUPPLIER
            })
            
            self.logger.info(f"Created license {license_id} for client server {client_server_id}")
            return license_id
            
        except Exception as e:
            self.logger.error(f"Error creating license: {str(e)}")
            raise
    
    def activate_license(self, license_id: str, payment_info: Dict[str, Any]) -> bool:
        """Activate a license after payment"""
        try:
            db = next(get_db())
            license_obj = db.query(License).filter(License.id == license_id).first()
            
            if not license_obj:
                raise ValueError(f"License {license_id} not found")
            
            # Verify payment (mock implementation)
            payment_verified = True  # Mock verification
            
            if payment_verified:
                license_obj.status = LicenseStatus.ACTIVE
                license_obj.activation_date = datetime.utcnow()
                license_obj.payment_reference = payment_info.get('transaction_id')
                
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('license_activated', {
                    'license_id': license_id,
                    'client_server_id': license_obj.client_server_id,
                    'amount': float(license_obj.amount),
                    'server_type': ServerType.SUPPLIER
                })
                
                self.logger.info(f"Activated license {license_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error activating license: {str(e)}")
            return False
    
    def suspend_license(self, license_id: str, reason: str) -> bool:
        """Suspend a license"""
        try:
            db = next(get_db())
            license_obj = db.query(License).filter(License.id == license_id).first()
            
            if license_obj:
                license_obj.status = LicenseStatus.SUSPENDED
                license_obj.suspension_reason = reason
                license_obj.suspended_at = datetime.utcnow()
                
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('license_suspended', {
                    'license_id': license_id,
                    'reason': reason,
                    'server_type': ServerType.SUPPLIER
                })
                
                self.logger.info(f"Suspended license {license_id}: {reason}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error suspending license: {str(e)}")
            return False
    
    def get_license_info(self, license_id: str) -> Optional[Dict[str, Any]]:
        """Get license information"""
        try:
            db = next(get_db())
            license_obj = db.query(License).filter(License.id == license_id).first()
            
            if not license_obj:
                return None
            
            return {
                'id': license_obj.id,
                'client_server_id': license_obj.client_server_id,
                'license_type': license_obj.license_type,
                'status': license_obj.status,
                'billing_cycle': license_obj.billing_cycle,
                'amount': float(license_obj.amount),
                'commission_rate': float(license_obj.commission_rate),
                'features': license_obj.features,
                'limits': license_obj.limits,
                'start_date': license_obj.start_date.isoformat(),
                'end_date': license_obj.end_date.isoformat(),
                'activation_date': license_obj.activation_date.isoformat() if license_obj.activation_date else None,
                'created_at': license_obj.created_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting license info: {str(e)}")
            return None
    
    def list_licenses(self, client_server_id: Optional[str] = None, 
                     status: Optional[LicenseStatus] = None) -> List[Dict[str, Any]]:
        """List licenses with optional filtering"""
        try:
            db = next(get_db())
            query = db.query(License)
            
            if client_server_id:
                query = query.filter(License.client_server_id == client_server_id)
            
            if status:
                query = query.filter(License.status == status)
            
            licenses = query.all()
            
            result = []
            for license_obj in licenses:
                result.append({
                    'id': license_obj.id,
                    'client_server_id': license_obj.client_server_id,
                    'license_type': license_obj.license_type,
                    'status': license_obj.status,
                    'amount': float(license_obj.amount),
                    'end_date': license_obj.end_date.isoformat(),
                    'created_at': license_obj.created_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing licenses: {str(e)}")
            return []
    
    def get_license_templates(self) -> Dict[str, Any]:
        """Get available license templates"""
        return self._license_templates


class ClientServerManagement:
    """
    Client server management system for Supplier Server
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._server_metrics: Dict[str, SupplierMetrics] = {}
        
    def register_client_server(self, server_info: Dict[str, Any]) -> str:
        """Register a new client server"""
        try:
            registration_id = str(uuid.uuid4())
            
            # Validate required fields
            required_fields = ['server_id', 'server_name', 'contact_email', 'supplier_server_url']
            for field in required_fields:
                if field not in server_info:
                    raise ValueError(f"Required field '{field}' is missing")
            
            # Create registration
            registration = ClientServerRegistration(
                id=registration_id,
                server_id=server_info['server_id'],
                server_name=server_info['server_name'],
                contact_email=server_info['contact_email'],
                supplier_server_url=server_info['supplier_server_url'],
                registration_token=server_info.get('registration_token', str(uuid.uuid4())),
                status='active',
                registered_at=datetime.utcnow(),
                metadata=server_info.get('metadata', {})
            )
            
            # Save to database
            db = next(get_db())
            db.add(registration)
            db.commit()
            
            # Initialize metrics
            self._server_metrics[server_info['server_id']] = SupplierMetrics(
                supplier_id=server_info['server_id']
            )
            
            # Track telemetry
            telemetry_tracker.track_event('client_server_registered', {
                'registration_id': registration_id,
                'server_id': server_info['server_id'],
                'server_name': server_info['server_name'],
                'server_type': ServerType.SUPPLIER
            })
            
            self.logger.info(f"Registered client server: {server_info['server_id']}")
            return registration_id
            
        except Exception as e:
            self.logger.error(f"Error registering client server: {str(e)}")
            raise
    
    def get_registration_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get client server registration information"""
        try:
            db = next(get_db())
            registration = db.query(ClientServerRegistration).filter(
                ClientServerRegistration.server_id == server_id
            ).first()
            
            if not registration:
                return None
            
            # Get server metrics
            metrics = self._server_metrics.get(server_id, SupplierMetrics(supplier_id=server_id))
            
            return {
                'id': registration.id,
                'server_id': registration.server_id,
                'server_name': registration.server_name,
                'contact_email': registration.contact_email,
                'status': registration.status,
                'registration_token': registration.registration_token,
                'registered_at': registration.registered_at.isoformat(),
                'last_heartbeat': registration.last_heartbeat.isoformat() if registration.last_heartbeat else None,
                'metadata': registration.metadata,
                'metrics': metrics.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting registration info: {str(e)}")
            return None
    
    def update_server_heartbeat(self, server_id: str) -> bool:
        """Update server heartbeat"""
        try:
            db = next(get_db())
            registration = db.query(ClientServerRegistration).filter(
                ClientServerRegistration.server_id == server_id
            ).first()
            
            if registration:
                registration.last_heartbeat = datetime.utcnow()
                registration.status = 'active'
                db.commit()
                
                # Update metrics
                metrics = self._server_metrics.get(server_id)
                if metrics:
                    metrics.last_activity = datetime.utcnow()
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating heartbeat: {str(e)}")
            return False
    
    def list_client_servers(self, status: Optional[str] = None, 
                           limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List registered client servers"""
        try:
            db = next(get_db())
            query = db.query(ClientServerRegistration)
            
            if status:
                query = query.filter(ClientServerRegistration.status == status)
            
            registrations = query.offset(offset).limit(limit).all()
            
            result = []
            for registration in registrations:
                metrics = self._server_metrics.get(registration.server_id, 
                                                 SupplierMetrics(supplier_id=registration.server_id))
                result.append({
                    'id': registration.id,
                    'server_id': registration.server_id,
                    'server_name': registration.server_name,
                    'contact_email': registration.contact_email,
                    'status': registration.status,
                    'registered_at': registration.registered_at.isoformat(),
                    'last_heartbeat': registration.last_heartbeat.isoformat() if registration.last_heartbeat else None,
                    'metrics': metrics.to_dict()
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing client servers: {str(e)}")
            return []
    
    def deactivate_server(self, server_id: str, reason: str) -> bool:
        """Deactivate a client server"""
        try:
            db = next(get_db())
            registration = db.query(ClientServerRegistration).filter(
                ClientServerRegistration.server_id == server_id
            ).first()
            
            if registration:
                registration.status = 'inactive'
                registration.deactivation_reason = reason
                registration.deactivated_at = datetime.utcnow()
                
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('client_server_deactivated', {
                    'server_id': server_id,
                    'reason': reason,
                    'server_type': ServerType.SUPPLIER
                })
                
                self.logger.info(f"Deactivated client server {server_id}: {reason}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deactivating server: {str(e)}")
            return False


class RevenueSharing:
    """
    Revenue sharing and commission tracking system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def calculate_commission(self, license_id: str, revenue_amount: Decimal) -> Decimal:
        """Calculate commission for a license"""
        try:
            db = next(get_db())
            license_obj = db.query(License).filter(License.id == license_id).first()
            
            if not license_obj:
                raise ValueError(f"License {license_id} not found")
            
            commission = revenue_amount * license_obj.commission_rate
            
            # Create commission tracking record
            commission_record = CommissionTracking(
                id=str(uuid.uuid4()),
                license_id=license_id,
                revenue_amount=revenue_amount,
                commission_amount=commission,
                commission_rate=license_obj.commission_rate,
                status=RevenueShareStatus.CALCULATED,
                calculated_at=datetime.utcnow()
            )
            
            db.add(commission_record)
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('commission_calculated', {
                'license_id': license_id,
                'revenue_amount': float(revenue_amount),
                'commission_amount': float(commission),
                'commission_rate': float(license_obj.commission_rate),
                'server_type': ServerType.SUPPLIER
            })
            
            self.logger.info(f"Calculated commission for license {license_id}: {float(commission)}")
            return commission
            
        except Exception as e:
            self.logger.error(f"Error calculating commission: {str(e)}")
            raise
    
    def get_revenue_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get revenue analytics for a period"""
        try:
            db = next(get_db())
            commissions = db.query(CommissionTracking).filter(
                CommissionTracking.calculated_at >= start_date,
                CommissionTracking.calculated_at <= end_date
            ).all()
            
            total_revenue = sum(c.revenue_amount for c in commissions)
            total_commissions = sum(c.commission_amount for c in commissions)
            
            # Group by license type
            revenue_by_license = {}
            commission_by_license = {}
            
            for commission in commissions:
                license_obj = db.query(License).filter(License.id == commission.license_id).first()
                if license_obj:
                    license_type = license_obj.license_type
                    if license_type not in revenue_by_license:
                        revenue_by_license[license_type] = Decimal('0.00')
                        commission_by_license[license_type] = Decimal('0.00')
                    
                    revenue_by_license[license_type] += commission.revenue_amount
                    commission_by_license[license_type] += commission.commission_amount
            
            analytics = {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_revenue': float(total_revenue),
                'total_commissions': float(total_commissions),
                'commission_rate_avg': float(total_commissions / total_revenue) if total_revenue > 0 else 0,
                'revenue_by_license_type': {k: float(v) for k, v in revenue_by_license.items()},
                'commissions_by_license_type': {k: float(v) for k, v in commission_by_license.items()},
                'total_transactions': len(commissions)
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting revenue analytics: {str(e)}")
            return {}
    
    def process_commission_payout(self, commission_id: str) -> bool:
        """Process commission payout"""
        try:
            db = next(get_db())
            commission = db.query(CommissionTracking).filter(
                CommissionTracking.id == commission_id
            ).first()
            
            if commission and commission.status == RevenueShareStatus.CALCULATED:
                commission.status = RevenueShareStatus.PAID
                commission.paid_at = datetime.utcnow()
                
                db.commit()
                
                # Track telemetry
                telemetry_tracker.track_event('commission_paid', {
                    'commission_id': commission_id,
                    'amount': float(commission.commission_amount),
                    'server_type': ServerType.SUPPLIER
                })
                
                self.logger.info(f"Processed payout for commission {commission_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing commission payout: {str(e)}")
            return False


class SupplierDashboard:
    """
    Supplier dashboard and analytics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.licensing = LicensingManagement()
        self.client_mgmt = ClientServerManagement()
        self.revenue_sharing = RevenueSharing()
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary data"""
        try:
            # Get counts
            all_servers = self.client_mgmt.list_client_servers()
            active_servers = [s for s in all_servers if s['status'] == 'active']
            
            all_licenses = self.licensing.list_licenses()
            active_licenses = [l for l in all_licenses if l['status'] == LicenseStatus.ACTIVE]
            
            # Calculate metrics
            total_servers = len(all_servers)
            active_server_count = len(active_servers)
            total_licenses = len(all_licenses)
            active_license_count = len(active_licenses)
            
            # Get recent revenue (last 30 days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            revenue_data = self.revenue_sharing.get_revenue_analytics(start_date, end_date)
            
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'servers': {
                    'total': total_servers,
                    'active': active_server_count,
                    'inactive': total_servers - active_server_count,
                    'activation_rate': (active_server_count / total_servers) if total_servers > 0 else 0
                },
                'licenses': {
                    'total': total_licenses,
                    'active': active_license_count,
                    'trial': len([l for l in all_licenses if l['status'] == LicenseStatus.TRIAL]),
                    'conversion_rate': (active_license_count / len([l for l in all_licenses if l['status'] == LicenseStatus.TRIAL])) if len([l for l in all_licenses if l['status'] == LicenseStatus.TRIAL]) > 0 else 0
                },
                'revenue': {
                    'last_30_days': revenue_data.get('total_revenue', 0),
                    'commissions_calculated': revenue_data.get('total_commissions', 0),
                    'total_transactions': revenue_data.get('total_transactions', 0)
                },
                'system_health': {
                    'average_license_revenue': revenue_data.get('total_revenue', 0) / total_licenses if total_licenses > 0 else 0,
                    'server_utilization': (active_server_count / total_servers) if total_servers > 0 else 0
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard summary: {str(e)}")
            return {}


class SupplierServerAPI:
    """
    Supplier Server API for handling supplier-specific operations
    """
    
    def __init__(self):
        self.licensing = LicensingManagement()
        self.client_mgmt = ClientServerManagement()
        self.revenue_sharing = RevenueSharing()
        self.dashboard = SupplierDashboard()
        self.logger = logging.getLogger(__name__)
    
    def initialize_supplier_server(self, config: Dict[str, Any]) -> bool:
        """Initialize the supplier server"""
        try:
            # Create supplier server record
            supplier = SupplierServer(
                server_id=config.get('server_id'),
                name=config.get('name', 'Supplier Server'),
                contact_email=config.get('contact_email'),
                api_endpoint=config.get('api_endpoint'),
                status='active',
                registered_at=datetime.utcnow()
            )
            
            db = next(get_db())
            db.add(supplier)
            db.commit()
            
            # Track telemetry
            telemetry_tracker.track_event('supplier_server_initialized', {
                'server_id': config.get('server_id'),
                'server_type': ServerType.SUPPLIER
            })
            
            self.logger.info(f"Initialized supplier server: {config.get('server_id')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing supplier server: {str(e)}")
            return False
    
    def get_server_health(self) -> Dict[str, Any]:
        """Get supplier server health status"""
        try:
            # Check various health indicators
            servers = self.client_mgmt.list_client_servers()
            licenses = self.licensing.list_licenses()
            
            healthy_servers = [s for s in servers if s['status'] == 'active']
            unhealthy_servers = [s for s in servers if s['status'] != 'active']
            
            active_licenses = [l for l in licenses if l['status'] == LicenseStatus.ACTIVE]
            expired_licenses = [l for l in licenses if l['status'] == LicenseStatus.EXPIRED]
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'client_servers': {
                        'total': len(servers),
                        'healthy': len(healthy_servers),
                        'unhealthy': len(unhealthy_servers),
                        'health_percentage': (len(healthy_servers) / len(servers)) * 100 if servers else 0
                    },
                    'licenses': {
                        'total': len(licenses),
                        'active': len(active_licenses),
                        'expired': len(expired_licenses),
                        'health_percentage': (len(active_licenses) / len(licenses)) * 100 if licenses else 0
                    },
                    'revenue_system': {
                        'status': 'operational',
                        'last_calculation': datetime.utcnow().isoformat()
                    }
                },
                'warnings': [],
                'errors': []
            }
            
            # Add warnings and errors
            if unhealthy_servers:
                health_status['warnings'].append(f"{len(unhealthy_servers)} client servers are not healthy")
            
            if expired_licenses:
                health_status['warnings'].append(f"{len(expired_licenses)} licenses have expired")
            
            # Determine overall status
            if len(unhealthy_servers) > len(servers) * 0.5:  # More than 50% unhealthy
                health_status['status'] = 'critical'
            elif unhealthy_servers or expired_licenses:
                health_status['status'] = 'warning'
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error getting server health: {str(e)}")
            return {'status': 'error', 'error': str(e)}


# Global instances
supplier_server_api = SupplierServerAPI()
licensing_management = LicensingManagement()
client_server_management = ClientServerManagement()
revenue_sharing = RevenueSharing()
supplier_dashboard = SupplierDashboard()


# API endpoints would go here
"""
Example API endpoint structure:

@router.post("/licenses/")
@require_server_type(ServerType.SUPPLIER)
@require_feature("licensing")
async def create_license(license_data: LicenseCreateRequest):
    license_id = licensing_management.create_license(
        license_data.client_server_id,
        license_data.license_type,
        license_data.term_months
    )
    return {"license_id": license_id, "status": "created"}

@router.post("/client-servers/register/")
@require_server_type(ServerType.SUPPLIER)
@require_feature("client_server_management")
async def register_client_server(server_data: ClientServerRegistrationRequest):
    registration_id = client_server_management.register_client_server(server_data.dict())
    return {"registration_id": registration_id, "status": "registered"}

@router.get("/revenue/analytics/")
@require_server_type(ServerType.SUPPLIER)
@require_feature("revenue_sharing")
async def get_revenue_analytics(start_date: datetime, end_date: datetime):
    analytics = revenue_sharing.get_revenue_analytics(start_date, end_date)
    return analytics

@router.get("/dashboard/summary/")
@require_server_type(ServerType.SUPPLIER)
@require_feature("analytics_dashboard")
async def get_dashboard_summary():
    summary = supplier_dashboard.get_dashboard_summary()
    return summary
"""