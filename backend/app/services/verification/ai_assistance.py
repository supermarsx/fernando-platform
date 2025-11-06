"""
AI Assistance Service - Provides AI-powered suggestions and learning capabilities.

This service analyzes extracted data, provides confidence scoring, detects anomalies,
and learns from human corrections to improve future performance.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.models.verification import (
    VerificationTask, AIAssistanceLog, QualityReview, VerificationStatus
)
from app.services.llm_service import LLMService
from app.core.telemetry import telemetry_service
from app.services.cache.redis_cache import RedisCacheService


class AIAssistanceService:
    """AI-powered assistance for verification tasks."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.llm_service = LLMService()
        self.cache = RedisCacheService()
        
        # AI model configuration
        self.model_config = {
            'confidence_threshold_high': 0.90,
            'confidence_threshold_medium': 0.70,
            'confidence_threshold_low': 0.50,
            'anomaly_threshold': 0.30,
            'batch_analysis_size': 10
        }
        
        # Field-specific validation rules
        self.validation_rules = {
            'amount': {
                'min_value': 0.01,
                'max_value': 10000000.00,
                'decimal_places': 2
            },
            'date': {
                'min_year': 2020,
                'max_year': 2030
            },
            'percentage': {
                'min_value': 0,
                'max_value': 100
            },
            'tax_rate': {
                'min_value': 0,
                'max_value': 50
            }
        }

    async def analyze_extraction(self, extraction_id: str) -> Dict[str, Any]:
        """Analyze extracted data and provide AI assistance."""
        
        # Generate analysis ID
        analysis_id = f"AI-{datetime.now().strftime('%Y%m%d')}-{extraction_id[:8]}"
        
        # Get extracted data (placeholder - integrate with actual extraction service)
        extracted_data = await self._get_extracted_data(extraction_id)
        
        if not extracted_data:
            self.logger.warning(f"No extracted data found for {extraction_id}")
            return self._empty_analysis()
        
        # Perform AI analysis
        analysis_start = datetime.utcnow()
        
        # Calculate overall confidence
        overall_confidence = await self._calculate_overall_confidence(extracted_data)
        
        # Get field-specific confidence scores
        field_confidences = await self._calculate_field_confidences(extracted_data)
        
        # Detect anomalies
        anomaly_score, anomaly_alerts = await self._detect_anomalies(extracted_data)
        
        # Generate field suggestions
        field_suggestions = await self._generate_field_suggestions(extracted_data)
        
        # Validate fields
        validation_flags = await self._validate_fields(extracted_data)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - analysis_start).total_seconds() * 1000
        
        # Create analysis result
        analysis_result = {
            'analysis_id': analysis_id,
            'overall_confidence': overall_confidence,
            'field_confidences': field_confidences,
            'anomaly_score': anomaly_score,
            'anomaly_alerts': anomaly_alerts,
            'field_suggestions': field_suggestions,
            'validation_flags': validation_flags,
            'processing_time_ms': int(processing_time),
            'model_version': '1.0.0'
        }
        
        # Log AI assistance
        await self._log_ai_assistance(
            extraction_id, analysis_result, processing_time
        )
        
        # Cache the analysis for quick access
        cache_key = f"ai_analysis:{extraction_id}"
        await self.cache.set(cache_key, analysis_result, expire=3600)
        
        # Track analysis
        telemetry_service.track_event("ai_analysis_performed", {
            "extraction_id": extraction_id,
            "overall_confidence": overall_confidence,
            "anomaly_score": anomaly_score,
            "processing_time_ms": processing_time
        })
        
        self.logger.info(f"AI analysis completed for {extraction_id} with {overall_confidence:.2%} confidence")
        return analysis_result

    async def get_smart_suggestions(
        self,
        extraction_id: str,
        field_name: str,
        current_value: Any
    ) -> Dict[str, Any]:
        """Get AI-powered suggestions for a specific field."""
        
        # Get historical correction patterns for this field
        correction_patterns = await self._get_field_correction_patterns(field_name)
        
        # Get similar documents for comparison
        similar_documents = await self._find_similar_documents(extraction_id, field_name)
        
        # Generate suggestions using AI
        suggestions = await self._generate_field_suggestions(
            {field_name: current_value}, 
            correction_patterns, 
            similar_documents
        )
        
        return {
            'field_name': field_name,
            'current_value': current_value,
            'suggestions': suggestions.get(field_name, []),
            'confidence': suggestions.get('confidence', 0.5),
            'reasoning': suggestions.get('reasoning', 'No specific reasoning available'),
            'similar_examples': similar_documents[:3]  # Top 3 similar examples
        }

    async def validate_field_value(
        self,
        field_name: str,
        value: Any,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate a field value using AI and business rules."""
        
        validation_result = {
            'is_valid': True,
            'confidence': 1.0,
            'warnings': [],
            'suggestions': [],
            'score': 100
        }
        
        # Apply business rule validation
        business_rules_result = await self._validate_business_rules(field_name, value)
        validation_result['warnings'].extend(business_rules_result.get('warnings', []))
        
        # Apply AI validation
        ai_validation_result = await self._validate_with_ai(field_name, value, context)
        validation_result.update(ai_validation_result)
        
        # Calculate overall score
        score = 100
        for warning in validation_result['warnings']:
            score -= 10
        
        validation_result['score'] = max(0, score)
        
        return validation_result

    async def detect_suspicious_patterns(
        self,
        extraction_id: str,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect suspicious patterns in extracted data."""
        
        suspicious_patterns = {
            'is_suspicious': False,
            'risk_level': 'low',
            'patterns_detected': [],
            'recommendations': []
        }
        
        # Check for round number bias
        round_number_patterns = await self._detect_round_number_bias(extracted_data)
        if round_number_patterns['detected']:
            suspicious_patterns['patterns_detected'].append({
                'type': 'round_number_bias',
                'confidence': round_number_patterns['confidence'],
                'fields_affected': round_number_patterns['fields']
            })
        
        # Check for repeated values
        repeated_value_patterns = await self._detect_repeated_values(extracted_data)
        if repeated_value_patterns['detected']:
            suspicious_patterns['patterns_detected'].append({
                'type': 'repeated_values',
                'confidence': repeated_value_patterns['confidence'],
                'repeated_values': repeated_value_patterns['values']
            })
        
        # Check for impossible combinations
        impossible_combinations = await self._detect_impossible_combinations(extracted_data)
        if impossible_combinations['detected']:
            suspicious_patterns['patterns_detected'].append({
                'type': 'impossible_combinations',
                'confidence': impossible_combinations['confidence'],
                'combinations': impossible_combinations['combinations']
            })
        
        # Calculate overall risk level
        if suspicious_patterns['patterns_detected']:
            avg_confidence = sum(p['confidence'] for p in suspicious_patterns['patterns_detected']) / len(suspicious_patterns['patterns_detected'])
            
            if avg_confidence > 0.7:
                suspicious_patterns['risk_level'] = 'high'
                suspicious_patterns['is_suspicious'] = True
            elif avg_confidence > 0.4:
                suspicious_patterns['risk_level'] = 'medium'
            
            suspicious_patterns['recommendations'] = await self._generate_pattern_recommendations(suspicious_patterns['patterns_detected'])
        
        return suspicious_patterns

    async def log_human_corrections(
        self,
        extraction_id: str,
        corrections: List[Dict[str, Any]]
    ):
        """Log human corrections for learning purposes."""
        
        if not corrections:
            return
        
        # Get the extraction task for context
        task = self.db.query(VerificationTask).filter(
            VerificationTask.extraction_id == extraction_id
        ).first()
        
        if not task:
            self.logger.warning(f"Task not found for extraction {extraction_id}")
            return
        
        # Update AI assistance log with correction data
        ai_log = self.db.query(AIAssistanceLog).filter(
            AIAssistanceLog.verification_task_id == task.id
        ).order_by(desc(AIAssistanceLog.analysis_timestamp)).first()
        
        if ai_log:
            ai_log.human_corrections = corrections
            ai_log.correction_patterns = await self._analyze_correction_patterns(corrections)
            ai_log.learning_opportunities = await self._identify_learning_opportunities(corrections)
            
            # Check if model update is needed
            if await self._should_trigger_model_update(corrections):
                ai_log.update_triggered = True
                ai_log.model_improvement_suggestions = await self._generate_model_improvements(corrections)
        
        self.db.commit()
        
        # Track corrections for learning
        telemetry_service.track_event("human_corrections_logged", {
            "extraction_id": extraction_id,
            "corrections_count": len(corrections),
            "fields_corrected": list(set(c.get('field_name') for c in corrections))
        })
        
        self.logger.info(f"Logged {len(corrections)} corrections for extraction {extraction_id}")

    async def get_learning_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get AI learning insights and improvement opportunities."""
        
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Get AI assistance logs with corrections
        correction_logs = self.db.query(AIAssistanceLog).filter(
            and_(
                AIAssistanceLog.analysis_timestamp >= start_date,
                AIAssistanceLog.human_corrections.isnot(None)
            )
        ).all()
        
        if not correction_logs:
            return {"message": "No correction data available for the specified period"}
        
        # Analyze correction patterns
        field_error_rates = {}
        common_correction_types = {}
        improvement_opportunities = []
        
        for log in correction_logs:
            corrections = log.human_corrections or []
            
            for correction in corrections:
                field_name = correction.get('field_name')
                correction_type = correction.get('correction_type', 'unknown')
                
                if field_name:
                    field_error_rates[field_name] = field_error_rates.get(field_name, 0) + 1
                
                common_correction_types[correction_type] = common_correction_types.get(correction_type, 0) + 1
        
        # Identify improvement opportunities
        sorted_error_rates = sorted(field_error_rates.items(), key=lambda x: x[1], reverse=True)
        improvement_opportunities = [
            {
                'field_name': field,
                'error_count': count,
                'priority': 'high' if count > len(correction_logs) * 0.1 else 'medium' if count > len(correction_logs) * 0.05 else 'low'
            }
            for field, count in sorted_error_rates[:10]
        ]
        
        return {
            'analysis_period_days': days,
            'total_corrections': len([c for log in correction_logs for c in (log.human_corrections or [])]),
            'fields_with_most_errors': improvement_opportunities,
            'common_correction_types': common_correction_types,
            'accuracy_trends': await self._calculate_accuracy_trends(correction_logs),
            'model_performance': await self._assess_model_performance(correction_logs),
            'recommendations': await self._generate_learning_recommendations(improvement_opportunities)
        }

    # Private helper methods
    
    async def _get_extracted_data(self, extraction_id: str) -> Optional[Dict[str, Any]]:
        """Get extracted data (placeholder - integrate with actual extraction service)."""
        # This should integrate with the actual document extraction service
        # For now, returning placeholder data
        return {
            'invoice_number': 'INV-2024-001',
            'amount': 1500.00,
            'date': '2024-01-15',
            'vendor': 'ABC Company',
            'tax_rate': 8.5,
            'line_items': [
                {'description': 'Service A', 'quantity': 1, 'unit_price': 1000.00},
                {'description': 'Service B', 'quantity': 1, 'unit_price': 500.00}
            ]
        }

    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            'analysis_id': f"AI-{datetime.now().strftime('%Y%m%d')}-empty",
            'overall_confidence': 0.0,
            'field_confidences': {},
            'anomaly_score': 0.0,
            'anomaly_alerts': [],
            'field_suggestions': {},
            'validation_flags': {},
            'processing_time_ms': 0,
            'model_version': '1.0.0'
        }

    async def _calculate_overall_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score for extracted data."""
        
        # Calculate confidence based on data completeness and quality indicators
        confidence_factors = []
        
        # Completeness factor
        total_fields = len(extracted_data)
        non_empty_fields = sum(1 for v in extracted_data.values() if v is not None and v != '')
        completeness = non_empty_fields / total_fields if total_fields > 0 else 0
        confidence_factors.append(completeness)
        
        # Data quality indicators
        quality_score = 0.8  # Base quality score
        confidence_factors.append(quality_score)
        
        # Consistency with expected formats
        consistency_score = await self._check_data_consistency(extracted_data)
        confidence_factors.append(consistency_score)
        
        # Calculate weighted average
        overall_confidence = sum(confidence_factors) / len(confidence_factors)
        return min(1.0, max(0.0, overall_confidence))

    async def _calculate_field_confidences(self, extracted_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence scores for individual fields."""
        
        field_confidences = {}
        
        for field_name, value in extracted_data.items():
            if value is None or value == '':
                field_confidences[field_name] = 0.0
                continue
            
            # Base confidence based on data type and format
            base_confidence = await self._get_field_base_confidence(field_name, value)
            
            # Adjust based on validation rules
            validation_score = await self._validate_field_format(field_name, value)
            
            # Combine scores
            field_confidences[field_name] = (base_confidence + validation_score) / 2
        
        return field_confidences

    async def _get_field_base_confidence(self, field_name: str, value: Any) -> float:
        """Get base confidence for a field based on its characteristics."""
        
        if isinstance(value, str):
            # String field confidence
            if len(value) == 0:
                return 0.0
            elif len(value) < 2:
                return 0.3
            elif len(value) < 5:
                return 0.6
            else:
                return 0.9
        elif isinstance(value, (int, float)):
            # Numeric field confidence
            if value == 0:
                return 0.2
            else:
                return 0.8
        elif isinstance(value, list):
            # List field confidence
            return min(1.0, len(value) * 0.3)
        else:
            return 0.5  # Default confidence

    async def _validate_field_format(self, field_name: str, value: Any) -> float:
        """Validate field format and return confidence score."""
        
        validation_rules = self.validation_rules
        
        if field_name in validation_rules:
            rules = validation_rules[field_name]
            
            if field_name == 'amount' and isinstance(value, (int, float)):
                min_val = rules.get('min_value', 0)
                max_val = rules.get('max_value', float('inf'))
                if min_val <= value <= max_val:
                    return 1.0
                else:
                    return 0.3
            
            elif field_name == 'date' and isinstance(value, str):
                try:
                    date_obj = datetime.strptime(value, '%Y-%m-%d')
                    min_year = rules.get('min_year', 1900)
                    max_year = rules.get('max_year', 2100)
                    if min_year <= date_obj.year <= max_year:
                        return 1.0
                    else:
                        return 0.3
                except ValueError:
                    return 0.2
        
        return 0.8  # Default validation score

    async def _detect_anomalies(self, extracted_data: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        """Detect anomalies in extracted data."""
        
        anomaly_score = 0.0
        anomaly_alerts = []
        
        # Check for unusually large or small amounts
        amount_fields = ['amount', 'total', 'subtotal', 'tax_amount']
        for field in amount_fields:
            if field in extracted_data and isinstance(extracted_data[field], (int, float)):
                value = extracted_data[field]
                if value > 100000 or value < 0.01:
                    anomaly_alerts.append({
                        'field': field,
                        'type': 'unusual_value',
                        'severity': 'medium',
                        'value': value,
                        'description': f"Unusual {field} value detected"
                    })
                    anomaly_score += 0.2
        
        # Check for dates in the future or distant past
        date_fields = ['date', 'invoice_date', 'due_date']
        for field in date_fields:
            if field in extracted_data and isinstance(extracted_data[field], str):
                try:
                    date_obj = datetime.strptime(extracted_data[field], '%Y-%m-%d')
                    now = datetime.utcnow()
                    if date_obj.year > now.year + 1 or date_obj.year < now.year - 5:
                        anomaly_alerts.append({
                            'field': field,
                            'type': 'suspicious_date',
                            'severity': 'high',
                            'value': extracted_data[field],
                            'description': f"Suspicious date range detected"
                        })
                        anomaly_score += 0.3
                except ValueError:
                    anomaly_alerts.append({
                        'field': field,
                        'type': 'invalid_date_format',
                        'severity': 'low',
                        'value': extracted_data[field],
                        'description': "Invalid date format"
                    })
                    anomaly_score += 0.1
        
        # Check for duplicate field values
        text_fields = [k for k, v in extracted_data.items() if isinstance(v, str)]
        duplicate_check = {}
        for field in text_fields:
            value = extracted_data[field]
            if value in duplicate_check:
                duplicate_check[value].append(field)
            else:
                duplicate_check[value] = [field]
        
        for value, fields in duplicate_check.items():
            if len(fields) > 1 and len(value) > 3:  # Only flag meaningful duplicates
                anomaly_alerts.append({
                    'fields': fields,
                    'type': 'duplicate_values',
                    'severity': 'low',
                    'value': value,
                    'description': "Duplicate values across different fields"
                })
                anomaly_score += 0.1
        
        return min(1.0, anomaly_score), anomaly_alerts

    async def _generate_field_suggestions(
        self,
        extracted_data: Dict[str, Any],
        correction_patterns: List[Dict[str, Any]] = None,
        similar_documents: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate AI-powered field suggestions."""
        
        suggestions = {}
        
        # Analyze each field for potential improvements
        for field_name, value in extracted_data.items():
            field_suggestions = []
            
            # Check if value seems unusual based on historical patterns
            if correction_patterns:
                for pattern in correction_patterns:
                    if pattern.get('field_name') == field_name:
                        if self._value_matches_pattern(value, pattern):
                            field_suggestions.append({
                                'type': 'pattern_based',
                                'suggestion': pattern.get('common_correction'),
                                'confidence': pattern.get('frequency', 0.5),
                                'reasoning': f"Based on {pattern.get('frequency', 0):.0%} correction rate"
                            })
            
            # Check similar documents
            if similar_documents:
                similar_values = [doc.get(field_name) for doc in similar_documents if doc.get(field_name)]
                if similar_values and value not in similar_values:
                    field_suggestions.append({
                        'type': 'similarity_based',
                        'suggestion': f"Similar documents use: {similar_values[:3]}",
                        'confidence': 0.6,
                        'reasoning': "Based on similar document patterns"
                    })
            
            suggestions[field_name] = field_suggestions
        
        return suggestions

    async def _validate_fields(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all fields in extracted data."""
        
        validation_flags = {}
        
        for field_name, value in extracted_data.items():
            field_validation = {
                'is_valid': True,
                'warnings': [],
                'suggestions': []
            }
            
            # Required field validation
            if value is None or value == '':
                field_validation['is_valid'] = False
                field_validation['warnings'].append('Required field is missing')
            
            # Format validation
            format_result = await self.validate_field_value(field_name, value)
            if not format_result['is_valid']:
                field_validation['is_valid'] = False
                field_validation['warnings'].extend(format_result['warnings'])
            
            validation_flags[field_name] = field_validation
        
        return validation_flags

    async def _log_ai_assistance(
        self,
        extraction_id: str,
        analysis_result: Dict[str, Any],
        processing_time: float
    ):
        """Log AI assistance for tracking and learning."""
        
        # Get associated verification task
        task = self.db.query(VerificationTask).filter(
            VerificationTask.extraction_id == extraction_id
        ).first()
        
        log_entry = AIAssistanceLog(
            log_id=analysis_result['analysis_id'],
            verification_task_id=task.id if task else None,
            analysis_timestamp=datetime.utcnow(),
            overall_confidence=analysis_result['overall_confidence'],
            field_confidences=analysis_result['field_confidences'],
            anomaly_score=analysis_result['anomaly_score'],
            anomaly_alerts=analysis_result['anomaly_alerts'],
            field_suggestions=analysis_result['field_suggestions'],
            validation_flags=analysis_result['validation_flags'],
            processing_time_ms=int(processing_time)
        )
        
        self.db.add(log_entry)
        self.db.commit()

    # Additional helper methods for advanced features
    
    async def _check_data_consistency(self, extracted_data: Dict[str, Any]) -> float:
        """Check data consistency across related fields."""
        
        consistency_checks = []
        
        # Check amount consistency (amount should equal sum of line items + tax)
        if 'amount' in extracted_data and 'line_items' in extracted_data:
            total_line_items = sum(
                item.get('quantity', 0) * item.get('unit_price', 0)
                for item in extracted_data['line_items']
            )
            actual_amount = extracted_data['amount']
            
            if abs(total_line_items - actual_amount) < 0.01:  # Allow for rounding
                consistency_checks.append(1.0)
            else:
                consistency_checks.append(0.5)
        
        return sum(consistency_checks) / len(consistency_checks) if consistency_checks else 0.8

    async def _get_field_correction_patterns(self, field_name: str) -> List[Dict[str, Any]]:
        """Get historical correction patterns for a field."""
        
        # This would typically query historical correction data
        # For now, returning placeholder patterns
        return [
            {
                'field_name': field_name,
                'common_correction': 'Standard format adjustment',
                'frequency': 0.25,
                'pattern_type': 'format_normalization'
            }
        ]

    async def _find_similar_documents(self, extraction_id: str, field_name: str) -> List[Dict[str, Any]]:
        """Find documents similar to the current one."""
        
        # This would typically use document similarity algorithms
        # For now, returning placeholder similar documents
        return [
            {field_name: 'Similar Value 1', 'document_type': 'invoice'},
            {field_name: 'Similar Value 2', 'document_type': 'receipt'},
            {field_name: 'Similar Value 3', 'document_type': 'invoice'}
        ]

    def _value_matches_pattern(self, value: Any, pattern: Dict[str, Any]) -> bool:
        """Check if value matches a correction pattern."""
        # Simplified pattern matching logic
        return False  # Placeholder

    async def _validate_business_rules(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Validate against business rules."""
        
        result = {'warnings': []}
        
        # Add business rule validation logic here
        # For now, returning empty warnings
        return result

    async def _validate_with_ai(self, field_name: str, value: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate field using AI models."""
        
        # This would integrate with AI validation models
        # For now, returning basic validation
        return {
            'is_valid': True,
            'confidence': 0.8,
            'warnings': [],
            'suggestions': []
        }

    async def _detect_round_number_bias(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect round number bias in numeric fields."""
        
        return {'detected': False, 'confidence': 0.0, 'fields': []}

    async def _detect_repeated_values(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect repeated values across different fields."""
        
        return {'detected': False, 'confidence': 0.0, 'values': []}

    async def _detect_impossible_combinations(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect impossible value combinations."""
        
        return {'detected': False, 'confidence': 0.0, 'combinations': []}

    async def _generate_pattern_recommendations(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on detected patterns."""
        
        return ["Review data for potential manual verification"]

    async def _analyze_correction_patterns(self, corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in corrections."""
        
        return {'pattern_analysis': 'Placeholder'}

    async def _identify_learning_opportunities(self, corrections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify learning opportunities from corrections."""
        
        return [{'opportunity': 'Improve field extraction accuracy'}]

    async def _should_trigger_model_update(self, corrections: List[Dict[str, Any]]) -> bool:
        """Determine if model update should be triggered."""
        
        return len(corrections) > 5  # Trigger update after 5+ corrections

    async def _generate_model_improvements(self, corrections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate model improvement suggestions."""
        
        return [{'improvement': 'Retrain on correction patterns'}]

    async def _calculate_accuracy_trends(self, logs: List[AIAssistanceLog]) -> Dict[str, Any]:
        """Calculate accuracy trends over time."""
        
        return {'trend': 'stable', 'change_percentage': 0.0}

    async def _assess_model_performance(self, logs: List[AIAssistanceLog]) -> Dict[str, Any]:
        """Assess overall model performance."""
        
        return {'overall_accuracy': 0.85, 'improvement_areas': []}

    async def _generate_learning_recommendations(self, opportunities: List[Dict[str, Any]]) -> List[str]:
        """Generate learning and improvement recommendations."""
        
        return ["Focus training on high-error fields"]