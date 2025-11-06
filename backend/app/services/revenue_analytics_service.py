"""
Revenue Analytics Service

Comprehensive revenue operations with ML-based predictive analytics,
financial compliance, and automated accounting integration.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, date
from decimal import Decimal
import hashlib
import json
import numpy as np
from collections import defaultdict

from app.models.revenue_operations import (
    RevenueMetric, CustomerLifetimeValue, ChurnPrediction, RevenueForecast,
    RevenueRecognition, TaxCompliance, AccountsReceivable, AccountsPayable,
    FinancialAuditLog, CohortAnalysis, RevenueMetricType, ChurnRiskLevel,
    RevenueRecognitionMethod, TaxJurisdiction
)
from app.models.billing import Subscription, Invoice, SubscriptionStatus
from app.models.user import User
from app.models.usage import UsageMetric
from app.ml.revenue_ml_models import ltv_model, churn_model
from app.middleware.telemetry_decorators import (
    extraction_telemetry, business_telemetry, business_operation_telemetry,
    record_business_metric, increment_metric, timer_metric
)


class RevenueAnalyticsService:
    """
    Core revenue analytics and KPI calculations
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_mrr(self, tenant_id: str, as_of_date: date = None) -> Decimal:
        """
        Calculate Monthly Recurring Revenue
        """
        if not as_of_date:
            as_of_date = date.today()
        
        # Get all active subscriptions
        active_subscriptions = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_start <= as_of_date,
            Subscription.current_period_end >= as_of_date
        ).all()
        
        total_mrr = Decimal('0')
        for sub in active_subscriptions:
            # Normalize to monthly
            if sub.billing_cycle == "monthly":
                total_mrr += sub.amount
            elif sub.billing_cycle == "annually":
                total_mrr += sub.amount / 12
            elif sub.billing_cycle == "quarterly":
                total_mrr += sub.amount / 3
        
        return total_mrr
    
    def calculate_arr(self, tenant_id: str, as_of_date: date = None) -> Decimal:
        """
        Calculate Annual Recurring Revenue
        """
        mrr = self.calculate_mrr(tenant_id, as_of_date)
        return mrr * 12
    
    def calculate_revenue_breakdown(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> Dict[str, Decimal]:
        """
        Calculate new, expansion, contraction, and churn revenue
        """
        # Get previous period subscriptions for comparison
        prev_start = start_date - timedelta(days=30)
        
        current_subs = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.current_period_start <= end_date,
            Subscription.current_period_end >= start_date
        ).all()
        
        prev_subs = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.current_period_start <= start_date,
            Subscription.current_period_end >= prev_start
        ).all()
        
        # Create dictionaries for comparison
        current_dict = {sub.user_id: sub.amount for sub in current_subs}
        prev_dict = {sub.user_id: sub.amount for sub in prev_subs}
        
        new_revenue = Decimal('0')
        expansion_revenue = Decimal('0')
        contraction_revenue = Decimal('0')
        churn_revenue = Decimal('0')
        
        # Analyze changes
        for user_id, amount in current_dict.items():
            if user_id not in prev_dict:
                new_revenue += amount
            elif amount > prev_dict[user_id]:
                expansion_revenue += (amount - prev_dict[user_id])
            elif amount < prev_dict[user_id]:
                contraction_revenue += (prev_dict[user_id] - amount)
        
        # Churned customers
        for user_id, amount in prev_dict.items():
            if user_id not in current_dict:
                churn_revenue += amount
        
        return {
            "new_revenue": new_revenue,
            "expansion_revenue": expansion_revenue,
            "contraction_revenue": contraction_revenue,
            "churn_revenue": churn_revenue,
            "net_new_mrr": new_revenue + expansion_revenue - contraction_revenue - churn_revenue
        }
    
    def calculate_nrr(self, tenant_id: str, period_months: int = 12) -> float:
        """
        Calculate Net Revenue Retention
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_months * 30)
        
        breakdown = self.calculate_revenue_breakdown(tenant_id, start_date, end_date)
        starting_mrr = self.calculate_mrr(tenant_id, start_date)
        
        if starting_mrr == 0:
            return 0.0
        
        # NRR = (Starting MRR + Expansion - Contraction - Churn) / Starting MRR
        ending_arr_from_cohort = (
            starting_mrr + 
            breakdown["expansion_revenue"] - 
            breakdown["contraction_revenue"] - 
            breakdown["churn_revenue"]
        )
        
        return float(ending_arr_from_cohort / starting_mrr)
    
    def save_revenue_metrics(
        self, tenant_id: str, period_start: date, period_end: date
    ) -> RevenueMetric:
        """
        Calculate and save comprehensive revenue metrics
        """
        mrr = self.calculate_mrr(tenant_id, period_end)
        arr = self.calculate_arr(tenant_id, period_end)
        breakdown = self.calculate_revenue_breakdown(tenant_id, period_start, period_end)
        
        # Calculate growth rates
        prev_period_start = period_start - timedelta(days=30)
        prev_period_end = period_start - timedelta(days=1)
        prev_mrr = self.calculate_mrr(tenant_id, prev_period_end)
        
        growth_rate = 0.0
        if prev_mrr > 0:
            growth_rate = float((mrr - prev_mrr) / prev_mrr)
        
        metric = RevenueMetric(
            tenant_id=tenant_id,
            metric_type=RevenueMetricType.MRR.value,
            value=mrr,
            period_start=period_start,
            period_end=period_end,
            new_business=breakdown["new_revenue"],
            expansion=breakdown["expansion_revenue"],
            contraction=breakdown["contraction_revenue"],
            churn=breakdown["churn_revenue"],
            growth_rate=growth_rate,
            month_over_month_change=growth_rate,
            calculation_meta_data={
                "arr": str(arr),
                "nrr": self.calculate_nrr(tenant_id),
                "calculated_at": datetime.utcnow().isoformat()
            }
        )
        
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        
        return metric


class PredictiveAnalyticsService:
    """
    ML-based predictive analytics for LTV and churn
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    @extraction_telemetry("calculate_customer_ltv")
    def calculate_customer_ltv(self, tenant_id: str, user_id: int) -> CustomerLifetimeValue:
        """
        Calculate Customer Lifetime Value with ML prediction
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Get customer history
        subscriptions = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.user_id == user_id
        ).all()
        
        invoices = self.db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.user_id == user_id
        ).all()
        
        # Calculate historical LTV
        historical_ltv = sum([inv.total for inv in invoices if inv.paid])
        
        # Calculate behavioral features
        total_spend = historical_ltv
        purchase_count = len([inv for inv in invoices if inv.paid])
        avg_order_value = total_spend / purchase_count if purchase_count > 0 else Decimal('0')
        
        customer_age_days = (datetime.utcnow() - user.created_at).days
        
        last_invoice = max(invoices, key=lambda x: x.created_at) if invoices else None
        last_purchase_days = (datetime.utcnow() - last_invoice.created_at).days if last_invoice else customer_age_days
        
        purchase_frequency = purchase_count / (customer_age_days / 30) if customer_age_days > 0 else 0
        
        # Use trained ML model for LTV prediction
        customer_features = {
            'historical_ltv': float(historical_ltv),
            'avg_order_value': float(avg_order_value),
            'purchase_frequency': purchase_frequency,
            'customer_age_days': customer_age_days,
            'last_purchase_days': last_purchase_days,
            'feature_adoption_score': 0.75,  # Would calculate from usage data
            'support_ticket_count': 0,
            'payment_issues': 0
        }
        
        predicted_ltv, confidence_score = ltv_model.predict(customer_features)
        
        # Calculate CAC (simplified - would come from marketing data)
        cac = Decimal('100')  # Placeholder
        ltv_cac_ratio = float(predicted_ltv / cac) if cac > 0 else 0
        
        # Calculate payback period
        monthly_value = float(avg_order_value) * purchase_frequency
        payback_months = float(cac / Decimal(str(monthly_value))) if monthly_value > 0 else 0
        
        ltv_record = CustomerLifetimeValue(
            tenant_id=tenant_id,
            user_id=user_id,
            historical_ltv=historical_ltv,
            predicted_ltv=Decimal(str(predicted_ltv)),
            ltv_confidence_score=confidence_score,
            customer_acquisition_cost=cac,
            ltv_cac_ratio=ltv_cac_ratio,
            payback_period_months=payback_months,
            total_spend=total_spend,
            average_order_value=avg_order_value,
            purchase_frequency=purchase_frequency,
            customer_age_days=customer_age_days,
            last_purchase_days_ago=last_purchase_days,
            feature_adoption_score=0.75,  # Would calculate from usage data
            support_ticket_count=0,
            nps_score=8,
            model_version="GradientBoosting_v1.0" if ltv_model.is_trained else "Heuristic_v1.0",
            features_used={
                "historical_ltv": float(historical_ltv),
                "purchase_frequency": purchase_frequency,
                "customer_age": customer_age_days
            }
        )
        
        self.db.add(ltv_record)
        self.db.commit()
        self.db.refresh(ltv_record)
        
        return ltv_record
    
    @extraction_telemetry("predict_ltv_simple")
    def _predict_ltv_simple(
        self, historical_ltv: float, avg_order_value: float, 
        purchase_frequency: float, customer_age_days: int, 
        last_purchase_days: int
    ) -> float:
        """
        Simple LTV prediction model
        In production, replace with trained ML model (GradientBoosting/RandomForest)
        """
        # Recency score (recent purchases indicate higher future value)
        recency_score = max(0, 1 - (last_purchase_days / 365))
        
        # Frequency score
        frequency_score = min(1, purchase_frequency / 2)  # Normalize to 0-1
        
        # Monetary score
        monetary_score = min(1, avg_order_value / 1000)  # Normalize
        
        # Customer maturity
        maturity_score = min(1, customer_age_days / 730)  # 2 years max
        
        # Weighted prediction
        base_value = historical_ltv
        growth_multiplier = (
            1.0 + 
            (0.3 * recency_score) + 
            (0.3 * frequency_score) + 
            (0.2 * monetary_score) + 
            (0.2 * maturity_score)
        )
        
        predicted_ltv = base_value * growth_multiplier
        
        return predicted_ltv
    
    @extraction_telemetry("predict_churn")
    def predict_churn(self, tenant_id: str, user_id: int) -> ChurnPrediction:
        """
        Predict customer churn probability using ML model
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Get customer behavior data
        subscriptions = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.user_id == user_id
        ).order_by(Subscription.created_at.desc()).all()
        
        usage_records = self.db.query(UsageMetric).filter(
            UsageMetric.tenant_id == tenant_id,
            UsageMetric.user_id == user_id
        ).order_by(UsageMetric.recorded_at.desc()).limit(90).all()
        
        # Calculate churn indicators
        usage_decline = self._calculate_usage_decline(usage_records)
        payment_issues = len([s for s in subscriptions if s.status == SubscriptionStatus.PAST_DUE])
        
        # Calculate feature engagement
        recent_usage = usage_records[:30]
        feature_engagement = len(set([r.metric_type for r in recent_usage])) / 10  # Normalized
        
        # Get customer metrics for ML model
        invoices = self.db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.user_id == user_id
        ).all()
        
        purchase_count = len([inv for inv in invoices if inv.paid])
        total_spend = sum([inv.total for inv in invoices if inv.paid])
        avg_order_value = float(total_spend / purchase_count) if purchase_count > 0 else 0
        customer_age_days = (datetime.utcnow() - user.created_at).days
        purchase_frequency = purchase_count / (customer_age_days / 30) if customer_age_days > 0 else 0
        last_invoice = max(invoices, key=lambda x: x.created_at) if invoices else None
        last_purchase_days = (datetime.utcnow() - last_invoice.created_at).days if last_invoice else customer_age_days
        
        # Use trained ML model for churn prediction
        customer_features = {
            'usage_decline_rate': usage_decline,
            'payment_issues_count': payment_issues,
            'feature_engagement_score': feature_engagement,
            'customer_age_days': customer_age_days,
            'last_purchase_days': last_purchase_days,
            'support_escalations': 0,
            'login_frequency_decline': 0.0,
            'avg_order_value': avg_order_value,
            'purchase_frequency': purchase_frequency,
            'contract_length_days': 365
        }
        
        churn_prob, risk_level_str, feature_importance = churn_model.predict(customer_features)
        
        # Convert string risk level to enum
        risk_level = ChurnRiskLevel(risk_level_str)
        
        # Risk factors
        risk_factors = []
        if usage_decline > 0.3:
            risk_factors.append({"factor": "usage_decline", "severity": "high", "value": usage_decline})
        if payment_issues > 0:
            risk_factors.append({"factor": "payment_issues", "severity": "critical", "count": payment_issues})
        if feature_engagement < 0.3:
            risk_factors.append({"factor": "low_engagement", "severity": "medium", "score": feature_engagement})
        
        # Recommended interventions
        interventions = self._recommend_interventions(risk_level, risk_factors)
        
        prediction = ChurnPrediction(
            tenant_id=tenant_id,
            user_id=user_id,
            churn_probability=churn_prob,
            risk_level=risk_level.value,
            predicted_churn_date=date.today() + timedelta(days=30) if churn_prob > 0.5 else None,
            risk_factors=risk_factors,
            risk_score_breakdown={
                "usage_decline": usage_decline,
                "payment_issues": payment_issues,
                "feature_engagement": feature_engagement
            },
            usage_decline_rate=usage_decline,
            payment_issues_count=payment_issues,
            support_escalations=0,
            feature_engagement_score=feature_engagement,
            login_frequency_decline=0.0,
            recommended_interventions=interventions,
            intervention_priority=1 if risk_level == ChurnRiskLevel.CRITICAL else 2,
            estimated_save_probability=0.6,
            model_version="RandomForest_v1.0" if churn_model.is_trained else "Heuristic_v1.0",
            model_accuracy=churn_model.get_model_accuracy()
        )
        
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        
        return prediction
    
    def _calculate_usage_decline(self, usage_records: List) -> float:
        """Calculate usage decline rate"""
        if len(usage_records) < 30:
            return 0.0
        
        recent = usage_records[:30]
        previous = usage_records[30:60] if len(usage_records) >= 60 else usage_records
        
        recent_count = len(recent)
        previous_count = len(previous)
        
        if previous_count == 0:
            return 0.0
        
        decline = (previous_count - recent_count) / previous_count
        return max(0, decline)
    
    @extraction_telemetry("predict_churn_probability")
    def _predict_churn_probability(
        self, usage_decline: float, payment_issues: int, 
        feature_engagement: float, customer_age: int
    ) -> float:
        """
        Simple churn probability model
        In production, replace with trained RandomForest model
        """
        # Weights based on feature importance
        prob = 0.0
        
        # Usage decline (most important feature)
        prob += usage_decline * 0.4
        
        # Payment issues (critical indicator)
        prob += min(1.0, payment_issues * 0.3) * 0.3
        
        # Low engagement
        prob += (1 - feature_engagement) * 0.2
        
        # New customers have higher churn
        if customer_age < 90:
            prob += 0.1
        
        return min(1.0, prob)
    
    def _recommend_interventions(
        self, risk_level: ChurnRiskLevel, risk_factors: List[Dict]
    ) -> List[Dict]:
        """Recommend intervention strategies"""
        interventions = []
        
        if risk_level in [ChurnRiskLevel.HIGH, ChurnRiskLevel.CRITICAL]:
            interventions.append({
                "action": "personal_outreach",
                "description": "Schedule call with customer success manager",
                "priority": 1
            })
        
        for factor in risk_factors:
            if factor["factor"] == "usage_decline":
                interventions.append({
                    "action": "engagement_campaign",
                    "description": "Send feature adoption email series",
                    "priority": 2
                })
            elif factor["factor"] == "payment_issues":
                interventions.append({
                    "action": "payment_assistance",
                    "description": "Offer payment plan or temporary discount",
                    "priority": 1
                })
        
        return interventions


# Continue in next file due to length...
