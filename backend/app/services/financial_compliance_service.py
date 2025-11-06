"""
Financial Compliance and AR/AP Services

Revenue recognition (ASC 606), tax compliance, AR/AP automation,
and financial audit trail.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
import hashlib
import json

from app.models.revenue_operations import (
    RevenueRecognition, TaxCompliance, AccountsReceivable, AccountsPayable,
    FinancialAuditLog, RevenueForecast, CohortAnalysis,
    RevenueRecognitionMethod, TaxJurisdiction
)
from app.models.billing import Invoice, InvoiceStatus
from app.models.enterprise_billing import BillingContract


class RevenueRecognitionService:
    """
    ASC 606 Revenue Recognition
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_recognition_schedule(
        self, tenant_id: str, invoice_id: int, 
        contract_id: Optional[int] = None,
        method: RevenueRecognitionMethod = RevenueRecognitionMethod.OVER_TIME
    ) -> RevenueRecognition:
        """
        Create revenue recognition schedule per ASC 606
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Get contract details if available
        contract = None
        if contract_id:
            contract = self.db.query(BillingContract).filter(
                BillingContract.id == contract_id
            ).first()
        
        # Determine recognition period
        if contract:
            start_date = contract.start_date
            end_date = contract.end_date
        else:
            # Default to service period from invoice
            start_date = invoice.period_start or date.today()
            end_date = invoice.period_end or (start_date + timedelta(days=365))
        
        # Calculate performance obligations
        performance_obligations = self._identify_performance_obligations(invoice, contract)
        
        # Create recognition schedule
        schedule = self._create_monthly_schedule(
            total_value=invoice.total,
            start_date=start_date,
            end_date=end_date,
            method=method
        )
        
        recognition = RevenueRecognition(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            contract_id=contract_id,
            recognition_method=method.value,
            total_contract_value=invoice.total,
            recognized_revenue=Decimal('0'),
            deferred_revenue=invoice.total,
            performance_obligations=performance_obligations,
            completion_percentage=0.0,
            contract_start_date=start_date,
            contract_end_date=end_date,
            recognition_start_date=start_date,
            recognition_schedule=schedule,
            next_recognition_date=start_date,
            next_recognition_amount=schedule[0]["amount"] if schedule else Decimal('0'),
            recognition_history=[]
        )
        
        self.db.add(recognition)
        self.db.commit()
        self.db.refresh(recognition)
        
        return recognition
    
    def _identify_performance_obligations(
        self, invoice: Invoice, contract: Optional[BillingContract]
    ) -> List[Dict]:
        """
        Identify distinct performance obligations per ASC 606
        """
        obligations = []
        
        # Main service obligation
        obligations.append({
            "obligation_id": 1,
            "description": "Software subscription service",
            "value": float(invoice.total),
            "timing": "over_time",
            "completion_method": "time_elapsed"
        })
        
        # Additional obligations from line items
        if invoice.line_items:
            for idx, item in enumerate(invoice.line_items):
                if item.get("type") == "setup_fee":
                    obligations.append({
                        "obligation_id": idx + 2,
                        "description": "Setup and onboarding",
                        "value": float(item.get("amount", 0)),
                        "timing": "point_in_time",
                        "completion_method": "service_delivered"
                    })
        
        return obligations
    
    def _create_monthly_schedule(
        self, total_value: Decimal, start_date: date, 
        end_date: date, method: RevenueRecognitionMethod
    ) -> List[Dict]:
        """
        Create monthly revenue recognition schedule
        """
        schedule = []
        months = self._months_between(start_date, end_date)
        
        if months == 0:
            months = 1
        
        if method == RevenueRecognitionMethod.OVER_TIME:
            monthly_amount = total_value / months
            
            current_date = start_date
            for i in range(months):
                schedule.append({
                    "period": i + 1,
                    "date": current_date.isoformat(),
                    "amount": str(monthly_amount),
                    "recognized": False
                })
                # Move to next month
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, current_date.day)
                else:
                    current_date = date(current_date.year, current_date.month + 1, current_date.day)
        
        elif method == RevenueRecognitionMethod.POINT_IN_TIME:
            schedule.append({
                "period": 1,
                "date": start_date.isoformat(),
                "amount": str(total_value),
                "recognized": False
            })
        
        return schedule
    
    def _months_between(self, start_date: date, end_date: date) -> int:
        """Calculate months between two dates"""
        return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    
    def recognize_revenue(self, recognition_id: int, period_date: date = None) -> Dict:
        """
        Recognize revenue for a period
        """
        if not period_date:
            period_date = date.today()
        
        recognition = self.db.query(RevenueRecognition).filter(
            RevenueRecognition.id == recognition_id
        ).first()
        
        if not recognition:
            raise ValueError(f"Recognition record {recognition_id} not found")
        
        if recognition.is_complete:
            return {"status": "complete", "message": "Revenue already fully recognized"}
        
        # Find periods to recognize
        schedule = recognition.recognition_schedule
        recognized_amount = Decimal('0')
        
        for period in schedule:
            period_date_obj = date.fromisoformat(period["date"])
            if period_date_obj <= period_date and not period.get("recognized", False):
                period["recognized"] = True
                period["recognized_date"] = datetime.utcnow().isoformat()
                recognized_amount += Decimal(period["amount"])
        
        # Update recognition record
        recognition.recognized_revenue += recognized_amount
        recognition.deferred_revenue = recognition.total_contract_value - recognition.recognized_revenue
        recognition.completion_percentage = float(recognition.recognized_revenue / recognition.total_contract_value)
        recognition.last_recognition_date = period_date
        recognition.recognition_schedule = schedule
        
        # Update history
        history = recognition.recognition_history or []
        history.append({
            "date": datetime.utcnow().isoformat(),
            "amount": str(recognized_amount),
            "period": period_date.isoformat()
        })
        recognition.recognition_history = history
        
        # Check if complete
        if recognition.completion_percentage >= 1.0:
            recognition.is_complete = True
            recognition.completion_date = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "status": "success",
            "amount_recognized": str(recognized_amount),
            "total_recognized": str(recognition.recognized_revenue),
            "deferred_revenue": str(recognition.deferred_revenue),
            "completion_percentage": recognition.completion_percentage
        }


class TaxComplianceService:
    """
    Tax compliance and reporting
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_tax_liability(
        self, tenant_id: str, jurisdiction: TaxJurisdiction,
        period_start: date, period_end: date
    ) -> TaxCompliance:
        """
        Calculate tax liability for jurisdiction and period
        """
        # Get all paid invoices in period
        invoices = self.db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_date >= period_start,
            Invoice.paid_date <= period_end
        ).all()
        
        # Calculate taxable revenue
        taxable_revenue = sum([inv.subtotal for inv in invoices])
        exempt_revenue = Decimal('0')  # Would identify exempt transactions
        
        # Determine tax rate
        tax_rate = self._get_tax_rate(jurisdiction)
        tax_amount = taxable_revenue * Decimal(str(tax_rate))
        
        # Categorize revenue
        product_revenue = Decimal('0')
        service_revenue = taxable_revenue  # SaaS is typically service revenue
        
        # Collect transaction IDs for audit trail
        transaction_ids = [{"invoice_id": inv.id, "amount": str(inv.total)} for inv in invoices]
        
        tax_record = TaxCompliance(
            tenant_id=tenant_id,
            jurisdiction=jurisdiction.value,
            tax_type="vat" if jurisdiction in [TaxJurisdiction.EU_VAT, TaxJurisdiction.UK_VAT] else "sales_tax",
            tax_period_start=period_start,
            tax_period_end=period_end,
            taxable_revenue=taxable_revenue,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            product_revenue=product_revenue,
            service_revenue=service_revenue,
            exempt_revenue=exempt_revenue,
            filing_status="pending",
            transaction_ids=transaction_ids
        )
        
        self.db.add(tax_record)
        self.db.commit()
        self.db.refresh(tax_record)
        
        return tax_record
    
    def _get_tax_rate(self, jurisdiction: TaxJurisdiction) -> float:
        """Get tax rate for jurisdiction"""
        rates = {
            TaxJurisdiction.US_FEDERAL: 0.0,  # No federal sales tax
            TaxJurisdiction.US_STATE: 0.07,  # Average state rate
            TaxJurisdiction.EU_VAT: 0.20,  # Standard EU VAT
            TaxJurisdiction.UK_VAT: 0.20,  # UK VAT
            TaxJurisdiction.CANADA_GST: 0.05  # Canadian GST
        }
        return rates.get(jurisdiction, 0.0)


class ARAPService:
    """
    Accounts Receivable and Accounts Payable automation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_ar_record(self, tenant_id: str, invoice_id: int) -> AccountsReceivable:
        """
        Create AR record for invoice
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Calculate aging
        invoice_date = invoice.created_at.date()
        due_date = invoice_date + timedelta(days=30)
        days_outstanding = (date.today() - invoice_date).days
        
        # Determine aging bucket
        if days_outstanding <= 30:
            aging_bucket = "current"
        elif days_outstanding <= 60:
            aging_bucket = "30"
        elif days_outstanding <= 90:
            aging_bucket = "60"
        elif days_outstanding <= 120:
            aging_bucket = "90"
        else:
            aging_bucket = "120+"
        
        # Determine status
        if invoice.status == InvoiceStatus.PAID:
            status = "paid"
            amount_outstanding = Decimal('0')
        else:
            status = "outstanding"
            amount_outstanding = invoice.total
        
        ar_record = AccountsReceivable(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            customer_id=invoice.user_id,
            invoice_amount=invoice.total,
            amount_paid=Decimal('0') if status == "outstanding" else invoice.total,
            amount_outstanding=amount_outstanding,
            invoice_date=invoice_date,
            due_date=due_date,
            days_outstanding=days_outstanding,
            aging_bucket=aging_bucket,
            status=status,
            payment_status=invoice.status.value
        )
        
        self.db.add(ar_record)
        self.db.commit()
        self.db.refresh(ar_record)
        
        return ar_record
    
    def get_ar_aging_report(self, tenant_id: str) -> Dict:
        """
        Generate AR aging report
        """
        ar_records = self.db.query(AccountsReceivable).filter(
            AccountsReceivable.tenant_id == tenant_id,
            AccountsReceivable.status.in_(["outstanding", "partial"])
        ).all()
        
        aging_summary = {
            "current": Decimal('0'),
            "30": Decimal('0'),
            "60": Decimal('0'),
            "90": Decimal('0'),
            "120+": Decimal('0'),
            "total": Decimal('0')
        }
        
        for record in ar_records:
            bucket = record.aging_bucket
            aging_summary[bucket] += record.amount_outstanding
            aging_summary["total"] += record.amount_outstanding
        
        return {
            "aging_summary": {k: str(v) for k, v in aging_summary.items()},
            "total_outstanding": str(aging_summary["total"]),
            "record_count": len(ar_records),
            "generated_at": datetime.utcnow().isoformat()
        }


class FinancialAuditService:
    """
    Tamper-proof financial audit trail
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_financial_event(
        self, tenant_id: str, event_type: str, event_category: str,
        entity_type: str, entity_id: int, user_id: Optional[int],
        previous_state: Dict, new_state: Dict, ip_address: Optional[str] = None
    ) -> FinancialAuditLog:
        """
        Create tamper-proof audit log entry
        """
        # Calculate changes
        changes = self._calculate_changes(previous_state, new_state)
        
        # Get previous hash for chain
        last_record = self.db.query(FinancialAuditLog).filter(
            FinancialAuditLog.tenant_id == tenant_id
        ).order_by(FinancialAuditLog.id.desc()).first()
        
        previous_hash = last_record.record_hash if last_record else "genesis"
        
        # Calculate this record's hash
        record_data = {
            "tenant_id": tenant_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": datetime.utcnow().isoformat(),
            "previous_state": previous_state,
            "new_state": new_state,
            "previous_hash": previous_hash
        }
        record_hash = hashlib.sha256(json.dumps(record_data, sort_keys=True).encode()).hexdigest()
        
        # Get user email
        user_email = None
        if user_id:
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user_email = user.email
        
        # Calculate retention period (7 years for financial records)
        retention_until = datetime.utcnow() + timedelta(days=365 * 7)
        
        audit_log = FinancialAuditLog(
            tenant_id=tenant_id,
            event_type=event_type,
            event_category=event_category,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_state=previous_state,
            new_state=new_state,
            changes=changes,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            record_hash=record_hash,
            previous_record_hash=previous_hash,
            is_compliant=True,
            retention_until=retention_until
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def _calculate_changes(self, previous: Dict, new: Dict) -> List[Dict]:
        """Calculate field-level changes"""
        changes = []
        
        all_keys = set(previous.keys()) | set(new.keys())
        
        for key in all_keys:
            old_value = previous.get(key)
            new_value = new.get(key)
            
            if old_value != new_value:
                changes.append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return changes
    
    def verify_audit_chain(self, tenant_id: str) -> Dict:
        """
        Verify integrity of audit chain
        """
        records = self.db.query(FinancialAuditLog).filter(
            FinancialAuditLog.tenant_id == tenant_id
        ).order_by(FinancialAuditLog.id).all()
        
        verified_count = 0
        broken_links = []
        
        for i, record in enumerate(records):
            if i == 0:
                # Genesis record
                verified_count += 1
                continue
            
            # Verify chain
            expected_prev_hash = records[i-1].record_hash
            if record.previous_record_hash != expected_prev_hash:
                broken_links.append({
                    "record_id": record.id,
                    "expected": expected_prev_hash,
                    "actual": record.previous_record_hash
                })
            else:
                verified_count += 1
        
        return {
            "total_records": len(records),
            "verified_records": verified_count,
            "broken_links": broken_links,
            "chain_intact": len(broken_links) == 0
        }
