"""
Usage Reporting Service

Generates usage reports in various formats (CSV, PDF, JSON, Excel)
for analysis and export.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import csv
import json
import io
import os

from app.models.usage import (
    UsageMetric, UsageAggregation, UsageQuota, UsageAlert,
    UsageReport, UsageForecast, UsageAnomaly
)
from app.models.billing import Subscription

logger = logging.getLogger(__name__)


class UsageReportingService:
    """
    Service for generating and exporting usage reports
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.reports_dir = "./reports/usage"
        os.makedirs(self.reports_dir, exist_ok=True)
    
    async def generate_usage_report(
        self,
        user_id: int,
        subscription_id: Optional[int],
        generated_by: int,
        report_type: str = "summary",
        report_format: str = "pdf",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        metric_types: Optional[List[str]] = None,
        filters: Optional[Dict] = None
    ) -> UsageReport:
        """
        Generate a comprehensive usage report
        
        Args:
            user_id: User ID for the report
            subscription_id: Subscription ID
            generated_by: User ID of report generator
            report_type: Type of report (summary, detailed, forecast, anomaly)
            report_format: Output format (pdf, csv, json, excel)
            period_start: Start of reporting period
            period_end: End of reporting period
            metric_types: List of metrics to include
            filters: Additional filters
        
        Returns:
            UsageReport instance with file path
        """
        try:
            # Set default period if not provided (last 30 days)
            if not period_end:
                period_end = datetime.utcnow()
            if not period_start:
                period_start = period_end - timedelta(days=30)
            
            # Generate report based on type
            if report_type == "summary":
                report_data = await self._generate_summary_report(
                    user_id, subscription_id, period_start, period_end, metric_types
                )
            elif report_type == "detailed":
                report_data = await self._generate_detailed_report(
                    user_id, subscription_id, period_start, period_end, metric_types
                )
            elif report_type == "forecast":
                report_data = await self._generate_forecast_report(
                    user_id, subscription_id, metric_types
                )
            elif report_type == "anomaly":
                report_data = await self._generate_anomaly_report(
                    user_id, subscription_id, period_start, period_end
                )
            else:
                raise ValueError(f"Invalid report type: {report_type}")
            
            # Export to requested format
            if report_format == "csv":
                file_path = await self._export_to_csv(report_data, user_id, report_type)
            elif report_format == "json":
                file_path = await self._export_to_json(report_data, user_id, report_type)
            elif report_format == "pdf":
                file_path = await self._export_to_pdf(report_data, user_id, report_type)
            elif report_format == "excel":
                file_path = await self._export_to_excel(report_data, user_id, report_type)
            else:
                raise ValueError(f"Invalid report format: {report_format}")
            
            # Calculate file size
            file_size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # Create report record
            report = UsageReport(
                user_id=user_id,
                subscription_id=subscription_id,
                generated_by=generated_by,
                report_type=report_type,
                report_format=report_format,
                period_start=period_start,
                period_end=period_end,
                metric_types=metric_types,
                filters=filters or {},
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                file_url=f"/api/v1/usage/reports/download/{os.path.basename(file_path)}",
                status="completed",
                generated_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),  # Reports expire after 7 days
                total_documents_processed=report_data.get("summary", {}).get("total_documents", 0),
                total_api_calls=report_data.get("summary", {}).get("total_api_calls", 0),
                total_storage_gb=report_data.get("summary", {}).get("total_storage_gb", 0),
                total_overage_charges=report_data.get("summary", {}).get("total_overage_charges", 0)
            )
            
            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)
            
            logger.info(
                f"Generated {report_type} report for user {user_id} in {report_format} format"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating usage report: {str(e)}")
            self.db.rollback()
            raise
    
    async def _generate_summary_report(
        self,
        user_id: int,
        subscription_id: Optional[int],
        period_start: datetime,
        period_end: datetime,
        metric_types: Optional[List[str]]
    ) -> Dict:
        """Generate summary usage report"""
        report = {
            "report_type": "summary",
            "user_id": user_id,
            "subscription_id": subscription_id,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days": (period_end - period_start).days
            },
            "summary": {},
            "quotas": [],
            "alerts": []
        }
        
        # Get aggregated metrics
        query = self.db.query(
            UsageAggregation.metric_type,
            func.sum(UsageAggregation.total_value).label("total"),
            func.avg(UsageAggregation.average_value).label("average"),
            func.max(UsageAggregation.max_value).label("peak")
        ).filter(
            and_(
                UsageAggregation.user_id == user_id,
                UsageAggregation.aggregation_date >= period_start,
                UsageAggregation.aggregation_date <= period_end
            )
        )
        
        if metric_types:
            query = query.filter(UsageAggregation.metric_type.in_(metric_types))
        
        aggregations = query.group_by(UsageAggregation.metric_type).all()
        
        summary = {}
        for agg in aggregations:
            summary[agg.metric_type] = {
                "total": float(agg.total),
                "average": float(agg.average),
                "peak": float(agg.peak)
            }
        
        report["summary"] = summary
        
        # Get current quotas
        quotas = self.db.query(UsageQuota).filter(
            and_(
                UsageQuota.user_id == user_id,
                UsageQuota.is_active == True
            )
        )
        
        if subscription_id:
            quotas = quotas.filter(UsageQuota.subscription_id == subscription_id)
        
        report["quotas"] = [
            {
                "metric_type": q.metric_type,
                "quota_limit": q.quota_limit,
                "current_usage": q.current_usage,
                "usage_percentage": q.usage_percentage,
                "is_exceeded": q.is_exceeded,
                "overage": q.current_overage,
                "overage_cost": q.current_overage * q.overage_rate if q.overage_rate else 0
            }
            for q in quotas.all()
        ]
        
        # Get recent alerts
        alerts = self.db.query(UsageAlert).filter(
            and_(
                UsageAlert.user_id == user_id,
                UsageAlert.triggered_at >= period_start,
                UsageAlert.triggered_at <= period_end
            )
        ).order_by(UsageAlert.triggered_at.desc()).limit(10).all()
        
        report["alerts"] = [
            {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "triggered_at": a.triggered_at.isoformat(),
                "status": a.status
            }
            for a in alerts
        ]
        
        return report
    
    async def _generate_detailed_report(
        self,
        user_id: int,
        subscription_id: Optional[int],
        period_start: datetime,
        period_end: datetime,
        metric_types: Optional[List[str]]
    ) -> Dict:
        """Generate detailed usage report with daily breakdown"""
        summary = await self._generate_summary_report(
            user_id, subscription_id, period_start, period_end, metric_types
        )
        
        # Add daily breakdown
        daily_query = self.db.query(UsageAggregation).filter(
            and_(
                UsageAggregation.user_id == user_id,
                UsageAggregation.aggregation_type == "daily",
                UsageAggregation.aggregation_date >= period_start,
                UsageAggregation.aggregation_date <= period_end
            )
        )
        
        if metric_types:
            daily_query = daily_query.filter(UsageAggregation.metric_type.in_(metric_types))
        
        daily_data = daily_query.order_by(UsageAggregation.aggregation_date).all()
        
        # Group by date
        daily_breakdown = {}
        for agg in daily_data:
            date_key = agg.aggregation_date.date().isoformat()
            if date_key not in daily_breakdown:
                daily_breakdown[date_key] = {}
            
            daily_breakdown[date_key][agg.metric_type] = {
                "total": agg.total_value,
                "average": agg.average_value,
                "min": agg.min_value,
                "max": agg.max_value,
                "trend": agg.trend
            }
        
        summary["daily_breakdown"] = daily_breakdown
        summary["report_type"] = "detailed"
        
        return summary
    
    async def _generate_forecast_report(
        self,
        user_id: int,
        subscription_id: Optional[int],
        metric_types: Optional[List[str]]
    ) -> Dict:
        """Generate forecast report"""
        report = {
            "report_type": "forecast",
            "user_id": user_id,
            "subscription_id": subscription_id,
            "forecasts": []
        }
        
        # Get latest forecasts
        forecasts_query = self.db.query(UsageForecast).filter(
            UsageForecast.user_id == user_id
        )
        
        if subscription_id:
            forecasts_query = forecasts_query.filter(UsageForecast.subscription_id == subscription_id)
        
        if metric_types:
            forecasts_query = forecasts_query.filter(UsageForecast.metric_type.in_(metric_types))
        
        forecasts = forecasts_query.order_by(UsageForecast.created_at.desc()).all()
        
        for forecast in forecasts:
            report["forecasts"].append({
                "metric_type": forecast.metric_type,
                "forecast_date": forecast.forecast_date.isoformat(),
                "predicted_value": forecast.predicted_value,
                "confidence_lower": forecast.confidence_lower,
                "confidence_upper": forecast.confidence_upper,
                "confidence_level": forecast.confidence_level,
                "model_type": forecast.model_type,
                "model_accuracy": forecast.model_accuracy,
                "will_exceed_quota": forecast.will_exceed_quota,
                "expected_overage": forecast.expected_overage,
                "estimated_overage_cost": forecast.estimated_overage_cost
            })
        
        return report
    
    async def _generate_anomaly_report(
        self,
        user_id: int,
        subscription_id: Optional[int],
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Generate anomaly detection report"""
        report = {
            "report_type": "anomaly",
            "user_id": user_id,
            "subscription_id": subscription_id,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "anomalies": []
        }
        
        # Get detected anomalies
        anomalies_query = self.db.query(UsageAnomaly).filter(
            and_(
                UsageAnomaly.user_id == user_id,
                UsageAnomaly.detected_at >= period_start,
                UsageAnomaly.detected_at <= period_end
            )
        )
        
        if subscription_id:
            anomalies_query = anomalies_query.filter(UsageAnomaly.subscription_id == subscription_id)
        
        anomalies = anomalies_query.order_by(UsageAnomaly.detected_at.desc()).all()
        
        for anomaly in anomalies:
            report["anomalies"].append({
                "anomaly_type": anomaly.anomaly_type,
                "severity": anomaly.severity,
                "confidence_score": anomaly.confidence_score,
                "detected_at": anomaly.detected_at.isoformat(),
                "metric_type": anomaly.metric_type,
                "observed_value": anomaly.observed_value,
                "expected_value": anomaly.expected_value,
                "deviation_percentage": anomaly.deviation_percentage,
                "pattern_description": anomaly.pattern_description,
                "risk_score": anomaly.risk_score,
                "is_fraud_suspect": anomaly.is_fraud_suspect,
                "status": anomaly.status
            })
        
        return report
    
    async def _export_to_csv(self, report_data: Dict, user_id: int, report_type: str) -> str:
        """Export report to CSV format"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"usage_report_{report_type}_{user_id}_{timestamp}.csv"
        file_path = os.path.join(self.reports_dir, filename)
        
        with open(file_path, 'w', newline='') as csvfile:
            if report_type == "summary" or report_type == "detailed":
                # Write summary section
                writer = csv.writer(csvfile)
                writer.writerow(["Usage Report Summary"])
                writer.writerow(["Period Start", report_data["period"]["start"]])
                writer.writerow(["Period End", report_data["period"]["end"]])
                writer.writerow([])
                
                # Write metrics
                writer.writerow(["Metric Type", "Total", "Average", "Peak"])
                for metric_type, values in report_data.get("summary", {}).items():
                    writer.writerow([
                        metric_type,
                        values.get("total", 0),
                        values.get("average", 0),
                        values.get("peak", 0)
                    ])
                
                # Write quotas
                writer.writerow([])
                writer.writerow(["Quotas"])
                writer.writerow(["Metric Type", "Limit", "Current Usage", "Usage %", "Exceeded", "Overage Cost"])
                for quota in report_data.get("quotas", []):
                    writer.writerow([
                        quota["metric_type"],
                        quota["quota_limit"],
                        quota["current_usage"],
                        f"{quota['usage_percentage']:.1f}%",
                        "Yes" if quota["is_exceeded"] else "No",
                        f"€{quota['overage_cost']:.2f}"
                    ])
            
            elif report_type == "forecast":
                writer = csv.writer(csvfile)
                writer.writerow(["Usage Forecast Report"])
                writer.writerow([])
                writer.writerow([
                    "Metric Type", "Forecast Date", "Predicted Value",
                    "Lower Bound", "Upper Bound", "Model", "Accuracy",
                    "Will Exceed Quota", "Expected Overage", "Estimated Cost"
                ])
                for forecast in report_data.get("forecasts", []):
                    writer.writerow([
                        forecast["metric_type"],
                        forecast["forecast_date"],
                        f"{forecast['predicted_value']:.2f}",
                        f"{forecast['confidence_lower']:.2f}",
                        f"{forecast['confidence_upper']:.2f}",
                        forecast["model_type"],
                        f"{forecast['model_accuracy']:.2f}",
                        "Yes" if forecast["will_exceed_quota"] else "No",
                        f"{forecast['expected_overage']:.2f}",
                        f"€{forecast['estimated_overage_cost']:.2f}"
                    ])
            
            elif report_type == "anomaly":
                writer = csv.writer(csvfile)
                writer.writerow(["Anomaly Detection Report"])
                writer.writerow([])
                writer.writerow([
                    "Detected At", "Anomaly Type", "Severity", "Metric Type",
                    "Observed Value", "Expected Value", "Deviation %",
                    "Risk Score", "Fraud Suspect", "Status"
                ])
                for anomaly in report_data.get("anomalies", []):
                    writer.writerow([
                        anomaly["detected_at"],
                        anomaly["anomaly_type"],
                        anomaly["severity"],
                        anomaly["metric_type"],
                        f"{anomaly['observed_value']:.2f}",
                        f"{anomaly['expected_value']:.2f}",
                        f"{anomaly['deviation_percentage']:.1f}%",
                        anomaly["risk_score"],
                        "Yes" if anomaly["is_fraud_suspect"] else "No",
                        anomaly["status"]
                    ])
        
        return file_path
    
    async def _export_to_json(self, report_data: Dict, user_id: int, report_type: str) -> str:
        """Export report to JSON format"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"usage_report_{report_type}_{user_id}_{timestamp}.json"
        file_path = os.path.join(self.reports_dir, filename)
        
        with open(file_path, 'w') as jsonfile:
            json.dump(report_data, jsonfile, indent=2)
        
        return file_path
    
    async def _export_to_pdf(self, report_data: Dict, user_id: int, report_type: str) -> str:
        """Export report to PDF format (simplified - would use reportlab in production)"""
        # For now, create a text file with .pdf extension
        # In production, use reportlab or similar library
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"usage_report_{report_type}_{user_id}_{timestamp}.pdf"
        file_path = os.path.join(self.reports_dir, filename)
        
        # Write as plain text for now (would be PDF in production)
        with open(file_path, 'w') as f:
            f.write(json.dumps(report_data, indent=2))
        
        return file_path
    
    async def _export_to_excel(self, report_data: Dict, user_id: int, report_type: str) -> str:
        """Export report to Excel format (would use openpyxl in production)"""
        # For now, use CSV format
        # In production, use openpyxl to create proper Excel files
        return await self._export_to_csv(report_data, user_id, report_type)
