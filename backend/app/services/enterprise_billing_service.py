"""
Enterprise Billing Service

Comprehensive service for enterprise billing operations including:
- Multi-entity billing and consolidated invoicing
- Department allocation and cost center management
- Contract management and SLA tracking
- Budget tracking and enforcement
- Approval workflows
- Dispute management
- Financial integration
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import uuid
import json

from app.models.enterprise_billing import (
    BillingEntity, Department, CostAllocation,
    BillingContract, ContractAmendment, ContractStatus,
    Budget, BudgetAlert, BudgetPeriod,
    ApprovalRequest, ApprovalAction, ApprovalRule, ApprovalStatus,
    BillingDispute, DisputeComment, DisputeStatus,
    FinancialIntegration, IntegrationSyncLog, GLCodeMapping,
    EnterpriseReport, EntityType, DisputeCategory
)
from app.models.billing import Invoice, Subscription, InvoiceStatus
from app.models.user import User


class EnterpriseBillingService:
    """Core service for enterprise billing operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================
    # Multi-Entity Management
    # ============================
    
    def create_billing_entity(
        self,
        name: str,
        tenant_id: str,
        entity_type: EntityType,
        parent_entity_id: Optional[int] = None,
        legal_name: Optional[str] = None,
        tax_id: Optional[str] = None,
        billing_address: Optional[Dict] = None,
        consolidated_billing: bool = False,
        **kwargs
    ) -> BillingEntity:
        """Create a new billing entity"""
        entity = BillingEntity(
            entity_id=f"ENT-{uuid.uuid4().hex[:12].upper()}",
            name=name,
            legal_name=legal_name or name,
            entity_type=entity_type,
            parent_entity_id=parent_entity_id,
            tenant_id=tenant_id,
            tax_id=tax_id,
            billing_address=billing_address or {},
            consolidated_billing=consolidated_billing,
            **kwargs
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def get_entity_hierarchy(self, entity_id: int) -> Dict[str, Any]:
        """Get complete hierarchy for an entity (parent and children)"""
        entity = self.db.query(BillingEntity).filter(BillingEntity.id == entity_id).first()
        if not entity:
            return None
        
        def build_hierarchy(ent):
            return {
                "entity": ent,
                "children": [build_hierarchy(child) for child in ent.child_entities if child.is_active],
                "parent": build_hierarchy(ent.parent_entity) if ent.parent_entity else None
            }
        
        return build_hierarchy(entity)
    
    def generate_consolidated_invoice(
        self,
        parent_entity_id: int,
        period_start: datetime,
        period_end: datetime,
        user_id: int
    ) -> Invoice:
        """Generate consolidated invoice for parent entity and all children"""
        parent_entity = self.db.query(BillingEntity).filter(
            BillingEntity.id == parent_entity_id
        ).first()
        
        if not parent_entity:
            raise ValueError("Parent entity not found")
        
        # Get all child entities
        child_entities = self._get_all_child_entities(parent_entity_id)
        all_entities = [parent_entity] + child_entities
        
        # Collect all subscriptions for these entities
        line_items = []
        total_amount = 0
        
        for entity in all_entities:
            if entity.subscription_id:
                subscription = self.db.query(Subscription).filter(
                    Subscription.id == entity.subscription_id
                ).first()
                
                if subscription:
                    line_items.append({
                        "description": f"{entity.name} - {subscription.plan.name}",
                        "quantity": 1,
                        "unit_price": subscription.base_amount,
                        "amount": subscription.base_amount,
                        "entity_id": entity.id,
                        "subscription_id": subscription.id
                    })
                    total_amount += subscription.base_amount
        
        # Create consolidated invoice
        invoice_number = f"INV-CONS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        invoice = Invoice(
            invoice_number=invoice_number,
            user_id=user_id,
            subscription_id=parent_entity.subscription_id,
            status=InvoiceStatus.PENDING,
            subtotal=total_amount,
            total_amount=total_amount,
            amount_due=total_amount,
            line_items=line_items,
            issue_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=parent_entity.payment_terms_days or 30),
            period_start=period_start,
            period_end=period_end,
            currency=parent_entity.currency,
            metadata={"consolidated": True, "parent_entity_id": parent_entity_id}
        )
        
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice
    
    def _get_all_child_entities(self, parent_entity_id: int) -> List[BillingEntity]:
        """Recursively get all child entities"""
        children = []
        direct_children = self.db.query(BillingEntity).filter(
            BillingEntity.parent_entity_id == parent_entity_id,
            BillingEntity.is_active == True
        ).all()
        
        for child in direct_children:
            children.append(child)
            children.extend(self._get_all_child_entities(child.id))
        
        return children
    
    # ============================
    # Department & Cost Center Management
    # ============================
    
    def create_department(
        self,
        name: str,
        entity_id: int,
        department_code: str,
        cost_center_code: str,
        manager_user_id: Optional[int] = None,
        **kwargs
    ) -> Department:
        """Create a new department with cost center"""
        department = Department(
            department_id=f"DEPT-{uuid.uuid4().hex[:12].upper()}",
            name=name,
            entity_id=entity_id,
            department_code=department_code,
            cost_center_code=cost_center_code,
            manager_user_id=manager_user_id,
            **kwargs
        )
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        return department
    
    def allocate_cost(
        self,
        department_id: int,
        allocation_type: str,
        amount: float,
        period_start: datetime,
        period_end: datetime,
        subscription_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        **kwargs
    ) -> CostAllocation:
        """Allocate cost to a department"""
        allocation = CostAllocation(
            department_id=department_id,
            allocation_type=allocation_type,
            amount=amount,
            period_start=period_start,
            period_end=period_end,
            subscription_id=subscription_id,
            invoice_id=invoice_id,
            **kwargs
        )
        self.db.add(allocation)
        self.db.commit()
        self.db.refresh(allocation)
        return allocation
    
    def get_department_costs(
        self,
        department_id: int,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get total costs for a department in a period"""
        allocations = self.db.query(CostAllocation).filter(
            CostAllocation.department_id == department_id,
            CostAllocation.period_start >= period_start,
            CostAllocation.period_end <= period_end
        ).all()
        
        total = sum(a.amount for a in allocations)
        by_type = {}
        for allocation in allocations:
            by_type[allocation.allocation_type] = by_type.get(allocation.allocation_type, 0) + allocation.amount
        
        return {
            "department_id": department_id,
            "period_start": period_start,
            "period_end": period_end,
            "total_cost": total,
            "cost_by_type": by_type,
            "allocation_count": len(allocations)
        }
    
    # ============================
    # Contract Management
    # ============================
    
    def create_contract(
        self,
        name: str,
        entity_id: int,
        contract_type: str,
        start_date: datetime,
        term_length_months: int,
        contract_value: float,
        created_by_user_id: int,
        **kwargs
    ) -> BillingContract:
        """Create a new billing contract"""
        end_date = start_date + timedelta(days=30 * term_length_months)
        contract_number = f"CON-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"
        
        contract = BillingContract(
            contract_id=f"CONT-{uuid.uuid4().hex[:12].upper()}",
            contract_number=contract_number,
            name=name,
            contract_type=contract_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            term_length_months=term_length_months,
            contract_value=contract_value,
            status=ContractStatus.DRAFT,
            created_by_user_id=created_by_user_id,
            **kwargs
        )
        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        return contract
    
    def activate_contract(self, contract_id: int, signed_by_customer: str, signed_by_vendor: str) -> BillingContract:
        """Activate a contract after signatures"""
        contract = self.db.query(BillingContract).filter(BillingContract.id == contract_id).first()
        if not contract:
            raise ValueError("Contract not found")
        
        contract.status = ContractStatus.ACTIVE
        contract.signed_by_customer = signed_by_customer
        contract.signed_by_customer_date = datetime.utcnow()
        contract.signed_by_vendor = signed_by_vendor
        contract.signed_by_vendor_date = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(contract)
        return contract
    
    def add_contract_amendment(
        self,
        contract_id: int,
        description: str,
        amendment_type: str,
        old_values: Dict,
        new_values: Dict,
        effective_date: datetime,
        created_by_user_id: int
    ) -> ContractAmendment:
        """Add an amendment to an existing contract"""
        amendment = ContractAmendment(
            contract_id=contract_id,
            amendment_number=f"AMD-{len(self.db.query(ContractAmendment).filter(ContractAmendment.contract_id == contract_id).all()) + 1}",
            description=description,
            amendment_type=amendment_type,
            old_values=old_values,
            new_values=new_values,
            effective_date=effective_date,
            created_by_user_id=created_by_user_id
        )
        self.db.add(amendment)
        self.db.commit()
        self.db.refresh(amendment)
        return amendment
    
    def check_contract_renewal(self, contract_id: int) -> Dict[str, Any]:
        """Check if contract needs renewal and return details"""
        contract = self.db.query(BillingContract).filter(BillingContract.id == contract_id).first()
        if not contract:
            return None
        
        days_until_end = (contract.end_date - datetime.utcnow()).days
        needs_renewal = (
            contract.auto_renew and
            contract.status == ContractStatus.ACTIVE and
            days_until_end <= contract.renewal_notice_days
        )
        
        return {
            "contract_id": contract_id,
            "needs_renewal": needs_renewal,
            "days_until_end": days_until_end,
            "renewal_notice_days": contract.renewal_notice_days,
            "auto_renew": contract.auto_renew,
            "end_date": contract.end_date
        }
    
    # ============================
    # Budget Management
    # ============================
    
    def create_budget(
        self,
        name: str,
        allocated_amount: float,
        period_start: datetime,
        period_end: datetime,
        entity_id: Optional[int] = None,
        department_id: Optional[int] = None,
        owner_user_id: Optional[int] = None,
        **kwargs
    ) -> Budget:
        """Create a budget for an entity or department"""
        budget = Budget(
            budget_id=f"BDG-{uuid.uuid4().hex[:12].upper()}",
            name=name,
            allocated_amount=allocated_amount,
            remaining_amount=allocated_amount,
            period_start=period_start,
            period_end=period_end,
            entity_id=entity_id,
            department_id=department_id,
            owner_user_id=owner_user_id,
            **kwargs
        )
        self.db.add(budget)
        self.db.commit()
        self.db.refresh(budget)
        return budget
    
    def check_budget_availability(
        self,
        budget_id: int,
        amount: float
    ) -> Dict[str, Any]:
        """Check if budget has sufficient funds for a charge"""
        budget = self.db.query(Budget).filter(Budget.id == budget_id).first()
        if not budget:
            return {"available": False, "reason": "Budget not found"}
        
        if not budget.is_active:
            return {"available": False, "reason": "Budget is not active"}
        
        if budget.is_frozen:
            return {"available": False, "reason": "Budget is frozen"}
        
        available = budget.remaining_amount - budget.committed_amount
        
        if amount > available:
            if budget.allow_overspend:
                max_overspend = budget.allocated_amount * (budget.overspend_limit_percent or 0) / 100
                total_spent_with_new = budget.spent_amount + budget.committed_amount + amount
                if total_spent_with_new <= budget.allocated_amount + max_overspend:
                    return {
                        "available": True,
                        "overspend": True,
                        "overspend_amount": total_spent_with_new - budget.allocated_amount,
                        "requires_approval": amount > (budget.require_approval_above or float('inf'))
                    }
            return {
                "available": False,
                "reason": "Insufficient budget",
                "available_amount": available,
                "requested_amount": amount
            }
        
        return {
            "available": True,
            "overspend": False,
            "available_amount": available,
            "requires_approval": amount > (budget.require_approval_above or float('inf'))
        }
    
    def commit_budget_amount(self, budget_id: int, amount: float) -> Budget:
        """Commit an amount (e.g., for pending approval)"""
        budget = self.db.query(Budget).filter(Budget.id == budget_id).first()
        if budget:
            budget.committed_amount += amount
            budget.remaining_amount = budget.allocated_amount - budget.spent_amount - budget.committed_amount
            self.db.commit()
            self.db.refresh(budget)
            self._check_budget_alerts(budget)
        return budget
    
    def charge_budget(self, budget_id: int, amount: float, release_commitment: bool = True) -> Budget:
        """Charge an amount to the budget"""
        budget = self.db.query(Budget).filter(Budget.id == budget_id).first()
        if budget:
            budget.spent_amount += amount
            if release_commitment:
                budget.committed_amount = max(0, budget.committed_amount - amount)
            budget.remaining_amount = budget.allocated_amount - budget.spent_amount - budget.committed_amount
            self.db.commit()
            self.db.refresh(budget)
            self._check_budget_alerts(budget)
        return budget
    
    def _check_budget_alerts(self, budget: Budget):
        """Check if budget alerts should be generated"""
        percent_spent = (budget.spent_amount / budget.allocated_amount * 100) if budget.allocated_amount > 0 else 0
        
        # Check alert threshold
        if percent_spent >= budget.alert_threshold_percent:
            self._create_budget_alert(
                budget.id,
                "threshold",
                "warning",
                f"Budget {budget.name} has reached {percent_spent:.1f}% utilization",
                percent_spent,
                budget.spent_amount,
                budget.allocated_amount
            )
        
        # Check warning threshold
        if percent_spent >= budget.warning_threshold_percent:
            self._create_budget_alert(
                budget.id,
                "threshold",
                "critical",
                f"Budget {budget.name} has reached {percent_spent:.1f}% utilization (Warning threshold)",
                percent_spent,
                budget.spent_amount,
                budget.allocated_amount
            )
        
        # Check overspend
        if budget.spent_amount > budget.allocated_amount:
            self._create_budget_alert(
                budget.id,
                "overspend",
                "critical",
                f"Budget {budget.name} has been exceeded by {budget.spent_amount - budget.allocated_amount:.2f}",
                percent_spent,
                budget.spent_amount,
                budget.allocated_amount
            )
    
    def _create_budget_alert(
        self,
        budget_id: int,
        alert_type: str,
        severity: str,
        message: str,
        threshold_percent: float,
        spent_amount: float,
        allocated_amount: float
    ):
        """Create a budget alert"""
        # Check if similar alert already exists
        existing = self.db.query(BudgetAlert).filter(
            BudgetAlert.budget_id == budget_id,
            BudgetAlert.alert_type == alert_type,
            BudgetAlert.is_resolved == False
        ).first()
        
        if not existing:
            alert = BudgetAlert(
                budget_id=budget_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                threshold_percent=threshold_percent,
                spent_amount=spent_amount,
                allocated_amount=allocated_amount
            )
            self.db.add(alert)
            self.db.commit()
    
    # ============================
    # Approval Workflow Management
    # ============================
    
    def create_approval_request(
        self,
        request_type: str,
        title: str,
        amount: float,
        requested_by_user_id: int,
        description: Optional[str] = None,
        contract_id: Optional[int] = None,
        budget_id: Optional[int] = None,
        department_id: Optional[int] = None,
        **kwargs
    ) -> ApprovalRequest:
        """Create an approval request"""
        # Find applicable approval rules
        rules = self._find_applicable_approval_rules(
            request_type, amount, department_id
        )
        
        required_approvals = max([r.required_approval_count for r in rules], default=1)
        
        request = ApprovalRequest(
            request_id=f"APR-{uuid.uuid4().hex[:12].upper()}",
            request_type=request_type,
            title=title,
            description=description,
            amount=amount,
            requested_by_user_id=requested_by_user_id,
            contract_id=contract_id,
            budget_id=budget_id,
            department_id=department_id,
            required_approvals=required_approvals,
            status=ApprovalStatus.PENDING,
            **kwargs
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        # Commit budget if applicable
        if budget_id:
            self.commit_budget_amount(budget_id, amount)
        
        return request
    
    def _find_applicable_approval_rules(
        self,
        request_type: str,
        amount: float,
        department_id: Optional[int]
    ) -> List[ApprovalRule]:
        """Find approval rules that apply to a request"""
        rules = self.db.query(ApprovalRule).filter(
            ApprovalRule.is_active == True,
            or_(
                ApprovalRule.request_type == request_type,
                ApprovalRule.request_type.is_(None)
            ),
            or_(
                ApprovalRule.min_amount.is_(None),
                ApprovalRule.min_amount <= amount
            ),
            or_(
                ApprovalRule.max_amount.is_(None),
                ApprovalRule.max_amount >= amount
            )
        ).order_by(desc(ApprovalRule.priority)).all()
        
        return rules
    
    def approve_request(
        self,
        request_id: int,
        approver_user_id: int,
        comments: Optional[str] = None
    ) -> ApprovalRequest:
        """Approve an approval request"""
        request = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError("Approval request not found")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError("Request is not pending approval")
        
        # Record approval action
        action = ApprovalAction(
            request_id=request_id,
            approver_user_id=approver_user_id,
            approval_level=request.approval_level,
            action="approved",
            comments=comments
        )
        self.db.add(action)
        
        request.approvals_received += 1
        
        # Check if all approvals received
        if request.approvals_received >= request.required_approvals:
            request.status = ApprovalStatus.APPROVED
            request.approved_at = datetime.utcnow()
            
            # Charge budget if applicable
            if request.budget_id:
                self.charge_budget(request.budget_id, request.amount, release_commitment=True)
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def reject_request(
        self,
        request_id: int,
        approver_user_id: int,
        reason: str,
        comments: Optional[str] = None
    ) -> ApprovalRequest:
        """Reject an approval request"""
        request = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError("Approval request not found")
        
        # Record rejection action
        action = ApprovalAction(
            request_id=request_id,
            approver_user_id=approver_user_id,
            approval_level=request.approval_level,
            action="rejected",
            comments=comments
        )
        self.db.add(action)
        
        request.status = ApprovalStatus.REJECTED
        request.rejected_at = datetime.utcnow()
        request.rejection_reason = reason
        
        # Release committed budget
        if request.budget_id:
            budget = self.db.query(Budget).filter(Budget.id == request.budget_id).first()
            if budget:
                budget.committed_amount = max(0, budget.committed_amount - request.amount)
                budget.remaining_amount = budget.allocated_amount - budget.spent_amount - budget.committed_amount
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    # ============================
    # Dispute Management
    # ============================
    
    def create_dispute(
        self,
        title: str,
        description: str,
        category: DisputeCategory,
        disputed_amount: float,
        raised_by_user_id: int,
        invoice_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
        **kwargs
    ) -> BillingDispute:
        """Create a billing dispute"""
        dispute = BillingDispute(
            dispute_id=f"DIS-{uuid.uuid4().hex[:12].upper()}",
            title=title,
            description=description,
            category=category,
            disputed_amount=disputed_amount,
            raised_by_user_id=raised_by_user_id,
            invoice_id=invoice_id,
            payment_id=payment_id,
            subscription_id=subscription_id,
            status=DisputeStatus.OPEN,
            **kwargs
        )
        self.db.add(dispute)
        self.db.commit()
        self.db.refresh(dispute)
        return dispute
    
    def add_dispute_comment(
        self,
        dispute_id: int,
        author_user_id: int,
        comment: str,
        comment_type: str = "comment",
        is_internal: bool = False,
        attachments: Optional[List[str]] = None
    ) -> DisputeComment:
        """Add a comment to a dispute"""
        dispute_comment = DisputeComment(
            dispute_id=dispute_id,
            author_user_id=author_user_id,
            comment=comment,
            comment_type=comment_type,
            is_internal=is_internal,
            attachments=attachments or []
        )
        self.db.add(dispute_comment)
        self.db.commit()
        self.db.refresh(dispute_comment)
        return dispute_comment
    
    def resolve_dispute(
        self,
        dispute_id: int,
        resolution: str,
        resolution_type: str,
        credit_amount: float = 0,
        refund_amount: float = 0,
        resolved_amount: Optional[float] = None
    ) -> BillingDispute:
        """Resolve a billing dispute"""
        dispute = self.db.query(BillingDispute).filter(
            BillingDispute.id == dispute_id
        ).first()
        
        if not dispute:
            raise ValueError("Dispute not found")
        
        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution = resolution
        dispute.resolution_type = resolution_type
        dispute.credit_amount = credit_amount
        dispute.refund_amount = refund_amount
        dispute.resolved_amount = resolved_amount if resolved_amount is not None else dispute.disputed_amount
        dispute.resolved_at = datetime.utcnow()
        
        # Process refund if refund_amount > 0
        if refund_amount > 0 and dispute.payment_id:
            try:
                from app.services.payment_service import PaymentService
                payment_service = PaymentService(self.db)
                
                # Get the payment record
                from app.models.billing import Payment
                payment = self.db.query(Payment).filter(
                    Payment.id == dispute.payment_id
                ).first()
                
                if payment:
                    # Process refund through payment service
                    refund_result = payment_service.process_refund(
                        payment_id=payment.payment_id,
                        amount=refund_amount,
                        reason=f"Dispute resolution: {resolution}"
                    )
                    
                    if not refund_result.get('success'):
                        # Log refund failure but don't fail the dispute resolution
                        dispute.meta_data = dispute.meta_data or {}
                        dispute.meta_data['refund_error'] = refund_result.get('error')
                        print(f"Warning: Refund failed for dispute {dispute_id}: {refund_result.get('error')}")
                    else:
                        dispute.meta_data = dispute.meta_data or {}
                        dispute.meta_data['refund_processed'] = True
                        dispute.meta_data['refund_transaction_id'] = refund_result.get('transaction_id')
            
            except Exception as e:
                # Log error but don't fail the dispute resolution
                dispute.meta_data = dispute.meta_data or {}
                dispute.meta_data['refund_error'] = str(e)
                print(f"Error processing refund for dispute {dispute_id}: {str(e)}")
        
        self.db.commit()
        self.db.refresh(dispute)
        return dispute
    
    # ============================
    # Financial Integration
    # ============================
    
    def create_financial_integration(
        self,
        name: str,
        provider: str,
        entity_id: int,
        api_endpoint: str,
        credentials: str,
        **kwargs
    ) -> FinancialIntegration:
        """Create a financial system integration"""
        integration = FinancialIntegration(
            integration_id=f"INT-{uuid.uuid4().hex[:12].upper()}",
            name=name,
            provider=provider,
            entity_id=entity_id,
            api_endpoint=api_endpoint,
            credentials=credentials,  # Should be encrypted
            **kwargs
        )
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration
    
    def sync_to_financial_system(
        self,
        integration_id: int,
        sync_type: str = "invoice"
    ) -> IntegrationSyncLog:
        """Sync data to external financial system"""
        integration = self.db.query(FinancialIntegration).filter(
            FinancialIntegration.id == integration_id
        ).first()
        
        if not integration or not integration.is_active:
            raise ValueError("Integration not found or inactive")
        
        # Create sync log
        sync_log = IntegrationSyncLog(
            integration_id=integration_id,
            sync_type=sync_type,
            sync_direction="export",
            status="started"
        )
        self.db.add(sync_log)
        self.db.commit()
        
        try:
            # Import the connector factory
            from app.services.financial_connectors import get_connector
            import json
            
            # Parse credentials (should be encrypted in production)
            credentials = json.loads(integration.credentials) if isinstance(integration.credentials, str) else integration.credentials
            
            # Build config for connector
            config = {
                'api_endpoint': integration.api_endpoint,
                'credentials': credentials,
                **(integration.meta_data if integration.meta_data else {})
            }
            
            # Get the appropriate connector
            connector = get_connector(integration.provider, config)
            
            # Authenticate
            connector.authenticate()
            
            # Perform sync based on type
            records_processed = 0
            records_succeeded = 0
            records_failed = 0
            errors = []
            
            if sync_type == "invoice":
                # Get recent invoices to sync
                from app.models.billing import Invoice, InvoiceStatus
                invoices = self.db.query(Invoice).filter(
                    Invoice.status == InvoiceStatus.PAID
                ).limit(100).all()  # Limit to recent 100
                
                records_processed = len(invoices)
                
                for invoice in invoices:
                    try:
                        # Transform invoice data
                        invoice_data = {
                            'customer_ref': str(invoice.user_id),  # Would map to external customer ID
                            'invoice_number': invoice.invoice_number,
                            'txn_date': invoice.issue_date.strftime('%Y-%m-%d'),
                            'due_date': invoice.due_date.strftime('%Y-%m-%d'),
                            'line_items': invoice.line_items if invoice.line_items else [],
                            'total_amount': invoice.total_amount
                        }
                        
                        # Sync to financial system
                        result = connector.sync_invoice(invoice_data)
                        
                        if result.get('success'):
                            records_succeeded += 1
                        else:
                            records_failed += 1
                            errors.append(f"Invoice {invoice.invoice_number}: {result.get('error')}")
                    
                    except Exception as e:
                        records_failed += 1
                        errors.append(f"Invoice {invoice.invoice_number}: {str(e)}")
            
            elif sync_type == "payment":
                # Similar implementation for payments
                records_processed = 0  # Would process payments
                records_succeeded = 0
                records_failed = 0
            
            elif sync_type == "customer":
                # Similar implementation for customers
                records_processed = 0  # Would process customers
                records_succeeded = 0
                records_failed = 0
            
            # Update sync log with results
            sync_log.status = "completed" if records_failed == 0 else "partial"
            sync_log.records_processed = records_processed
            sync_log.records_succeeded = records_succeeded
            sync_log.records_failed = records_failed
            sync_log.completed_at = datetime.utcnow()
            sync_log.duration_seconds = int((datetime.utcnow() - sync_log.started_at).total_seconds())
            
            if errors:
                sync_log.error_details = {"errors": errors}
            
            integration.last_sync_at = datetime.utcnow()
            integration.error_count = 0
            
        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.utcnow()
            integration.last_error = str(e)
            integration.error_count += 1
        
        self.db.commit()
        self.db.refresh(sync_log)
        return sync_log
    
    # ============================
    # Enterprise Reporting
    # ============================
    
    def generate_enterprise_report(
        self,
        report_name: str,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        generated_by_user_id: int,
        entity_id: Optional[int] = None
    ) -> EnterpriseReport:
        """Generate an enterprise financial report"""
        report = EnterpriseReport(
            report_id=f"REP-{uuid.uuid4().hex[:12].upper()}",
            report_name=report_name,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            entity_id=entity_id,
            generated_by_user_id=generated_by_user_id,
            status="generating"
        )
        self.db.add(report)
        self.db.commit()
        
        try:
            # Generate report data based on type
            if report_type == "financial":
                report_data = self._generate_financial_report_data(
                    entity_id, period_start, period_end
                )
            elif report_type == "budget":
                report_data = self._generate_budget_report_data(
                    entity_id, period_start, period_end
                )
            else:
                report_data = {}
            
            report.report_data = report_data
            report.status = "completed"
            report.last_generated_at = datetime.utcnow()
            
        except Exception as e:
            report.status = "failed"
            report.report_data = {"error": str(e)}
        
        self.db.commit()
        self.db.refresh(report)
        return report
    
    def _generate_financial_report_data(
        self,
        entity_id: Optional[int],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Generate financial report data"""
        # Query invoices for period
        query = self.db.query(Invoice).filter(
            Invoice.issue_date >= period_start,
            Invoice.issue_date <= period_end
        )
        
        if entity_id:
            # Filter by entity's subscriptions
            query = query.join(Subscription).join(BillingEntity).filter(
                BillingEntity.id == entity_id
            )
        
        invoices = query.all()
        
        total_invoiced = sum(inv.total_amount for inv in invoices)
        total_paid = sum(inv.amount_paid for inv in invoices)
        total_outstanding = sum(inv.amount_due for inv in invoices if inv.status != InvoiceStatus.PAID)
        
        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "invoice_count": len(invoices),
            "paid_invoice_count": len([inv for inv in invoices if inv.status == InvoiceStatus.PAID])
        }
    
    def _generate_budget_report_data(
        self,
        entity_id: Optional[int],
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Generate budget report data"""
        query = self.db.query(Budget).filter(
            Budget.period_start >= period_start,
            Budget.period_end <= period_end,
            Budget.is_active == True
        )
        
        if entity_id:
            query = query.filter(Budget.entity_id == entity_id)
        
        budgets = query.all()
        
        total_allocated = sum(b.allocated_amount for b in budgets)
        total_spent = sum(b.spent_amount for b in budgets)
        total_remaining = sum(b.remaining_amount for b in budgets)
        
        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_allocated": total_allocated,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
            "budget_count": len(budgets),
            "utilization_percent": (total_spent / total_allocated * 100) if total_allocated > 0 else 0
        }
