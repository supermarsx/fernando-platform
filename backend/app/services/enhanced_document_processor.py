"""
Enhanced Document Processing Service

Orchestrates multi-format document processing with intelligent pipelines.
Supports PDF, TIFF, PNG, JPEG, JPG with format detection, validation, 
preview generation, and integration with existing OCR/LLM services.
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from app.models.document import Document
from app.models.job import Job
from app.models.extraction import ExtractionRun
from app.services.ocr_service import get_ocr_service
from app.services.llm_service import get_llm_service
from app.middleware.telemetry_decorators import (
    document_telemetry, extraction_telemetry, business_telemetry
)

# Import format-specific processors
from .document_formats.format_detector import get_format_detector, DocumentFormat
from .document_formats.pdf_processor import get_pdf_processor
from .document_formats.tiff_processor import get_tiff_processor
from .document_formats.image_processor import get_image_processor
from .document_formats.preview_generator import get_preview_generator
from .document_converter import get_document_converter
from .document_validator import get_document_validator

logger = logging.getLogger(__name__)

class EnhancedDocumentProcessor:
    """Enhanced document processing service with multi-format support"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Initialize all processors and services
        self.format_detector = get_format_detector()
        self.pdf_processor = get_pdf_processor()
        self.tiff_processor = get_tiff_processor()
        self.image_processor = get_image_processor()
        self.preview_generator = get_preview_generator()
        self.document_converter = get_document_converter()
        self.document_validator = get_document_validator()
        
        # Initialize OCR and LLM services
        self.ocr_service = get_ocr_service()
        self.llm_service = get_llm_service()
        
        # Processing configuration
        self.cache_enabled = True
        self.preview_enabled = True
        self.validation_enabled = True
        self.max_processing_time = 300  # 5 minutes max processing time
        
        # Processing statistics
        self.processing_stats = {
            'total_processed': 0,
            'successful_processing': 0,
            'failed_processing': 0,
            'format_distribution': {}
        }
    
    @document_telemetry("process_document_enhanced")
    def process_document(self, document: Document, user_id: str, 
                        processing_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process document through enhanced multi-format pipeline
        
        Args:
            document: Document model instance
            user_id: ID of user who initiated processing
            processing_options: Optional processing configuration
            
        Returns:
            Complete processing results
        """
        start_time = time.time()
        processing_options = processing_options or {}
        
        processing_result = {
            'document_id': document.document_id,
            'success': False,
            'processing_pipeline': [],
            'format_detected': None,
            'preview_generated': False,
            'validation_passed': False,
            'extraction_results': {},
            'processing_metadata': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Update job status
            job = self.db.query(Job).filter(Job.job_id == document.job_id).first()
            if job:
                job.status = "processing"
                job.started_at = datetime.utcnow()
                self.db.commit()
            
            # Step 1: Format Detection
            format_result = self._detect_document_format(document.storage_url)
            processing_result['format_detected'] = format_result['format']
            processing_result['processing_pipeline'].append('format_detection')
            
            if not format_result['success']:
                processing_result['errors'].append(format_result['error'])
                return self._finalize_processing(processing_result, document, job, start_time)
            
            # Step 2: Document Validation (optional)
            if self.validation_enabled:
                validation_result = self._validate_document(document.storage_url, 
                                                          document.tenant_id, user_id)
                processing_result['validation_passed'] = validation_result['is_valid']
                processing_result['processing_pipeline'].append('validation')
                
                if not validation_result['is_valid']:
                    processing_result['errors'].extend(validation_result.get('errors', []))
                    if not processing_options.get('continue_on_validation_failure', False):
                        return self._finalize_processing(processing_result, document, job, start_time)
                
                processing_result['validation_results'] = validation_result
            
            # Step 3: Document Conversion (if needed)
            conversion_result = None
            if processing_options.get('force_conversion'):
                conversion_result = self._convert_document_for_processing(
                    document.storage_url, format_result['format'], processing_options
                )
                processing_result['processing_pipeline'].append('conversion')
                
                if conversion_result['success']:
                    document.storage_url = conversion_result['optimized_files'][0]
                else:
                    processing_result['warnings'].append('Conversion failed, proceeding with original')
            
            # Step 4: Preview Generation (optional)
            if self.preview_enabled:
                preview_result = self._generate_document_preview(
                    document.storage_url, format_result['format']
                )
                processing_result['preview_generated'] = preview_result.get('success', False)
                processing_result['processing_pipeline'].append('preview_generation')
                processing_result['preview_results'] = preview_result
            
            # Step 5: Format-Specific Processing
            format_processing_result = self._process_by_format(
                document.storage_url, format_result['format'], processing_options
            )
            processing_result['processing_pipeline'].append('format_specific_processing')
            processing_result['format_processing_results'] = format_processing_result
            
            # Step 6: OCR Processing
            ocr_result = self._process_with_ocr(
                document.storage_url, format_result['format'], processing_options
            )
            processing_result['processing_pipeline'].append('ocr_processing')
            processing_result['ocr_results'] = ocr_result
            
            if not ocr_result['success']:
                processing_result['errors'].append(ocr_result.get('error', 'OCR processing failed'))
            
            # Step 7: LLM Extraction
            llm_result = self._process_with_llm(
                ocr_result.get('extracted_text', ''), 
                format_result['format'], 
                processing_options
            )
            processing_result['processing_pipeline'].append('llm_extraction')
            processing_result['extraction_results'] = llm_result
            
            # Step 8: Integration with existing pipeline
            if processing_options.get('integrate_with_existing', True):
                integration_result = self._integrate_with_existing_pipeline(
                    document, ocr_result, llm_result, user_id
                )
                processing_result['existing_pipeline_integration'] = integration_result
            
            # Finalize processing
            processing_result['success'] = True
            processing_result['processing_metadata'] = {
                'processing_time': time.time() - start_time,
                'format_detected': format_result['format'].value,
                'pipeline_steps': len(processing_result['processing_pipeline']),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Update statistics
            self._update_processing_stats(format_result['format'].value, True)
            
            return self._finalize_processing(processing_result, document, job, start_time)
            
        except Exception as e:
            logger.error(f"Error in enhanced document processing: {e}")
            processing_result['errors'].append(f"Processing error: {str(e)}")
            processing_result['processing_metadata']['error'] = str(e)
            
            # Update statistics
            if processing_result.get('format_detected'):
                self._update_processing_stats(processing_result['format_detected'].value, False)
            
            return self._finalize_processing(processing_result, document, job, start_time)
    
    def _detect_document_format(self, file_path: str) -> Dict[str, Any]:
        """Detect document format"""
        try:
            detected_format, metadata = self.format_detector.detect_format(file_path)
            
            return {
                'success': True,
                'format': detected_format,
                'confidence': metadata['confidence'],
                'metadata': metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Format detection failed: {str(e)}"
            }
    
    def _validate_document(self, file_path: str, tenant_id: str = None, 
                          user_id: str = None) -> Dict[str, Any]:
        """Validate document for processing"""
        try:
            validation_result = self.document_validator.validate_document(
                file_path, tenant_id, user_id
            )
            
            return validation_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Validation failed: {str(e)}",
                'is_valid': False
            }
    
    def _convert_document_for_processing(self, file_path: str, format_type: DocumentFormat,
                                       processing_options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert document for optimal processing"""
        try:
            # Determine if conversion is needed
            if format_type == DocumentFormat.PDF:
                # Convert PDF to images for better OCR
                target_format = DocumentFormat.PNG
            elif format_type == DocumentFormat.TIFF:
                # Convert TIFF to PNG for consistency
                target_format = DocumentFormat.PNG
            else:
                # Images may not need conversion
                return {
                    'success': True,
                    'optimized_files': [file_path],
                    'conversion_needed': False
                }
            
            # Check if conversion is supported
            if not self.document_converter.can_convert(format_type, target_format):
                return {
                    'success': False,
                    'error': f"Conversion from {format_type.value} to {target_format.value} not supported"
                }
            
            # Perform conversion
            conversion_options = {
                'quality': processing_options.get('conversion_quality', 'high'),
                'dpi': processing_options.get('conversion_dpi', 300)
            }
            
            conversion_result = self.document_converter.convert_document(
                file_path, format_type, target_format, **conversion_options
            )
            
            return conversion_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Document conversion failed: {str(e)}"
            }
    
    def _generate_document_preview(self, file_path: str, format_type: DocumentFormat) -> Dict[str, Any]:
        """Generate document preview and thumbnails"""
        try:
            preview_result = self.preview_generator.generate_previews(file_path, format_type)
            return preview_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Preview generation failed: {str(e)}"
            }
    
    def _process_by_format(self, file_path: str, format_type: DocumentFormat,
                          processing_options: Dict[str, Any]) -> Dict[str, Any]:
        """Process document using format-specific processor"""
        try:
            if format_type == DocumentFormat.PDF:
                if hasattr(self.pdf_processor, 'process_pdf'):
                    result = self.pdf_processor.process_pdf(file_path)
                    return {
                        'success': True,
                        'result': result,
                        'processor': 'pdf_processor'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'PDF processor not available'
                    }
            
            elif format_type == DocumentFormat.TIFF:
                if hasattr(self.tiff_processor, 'process_tiff'):
                    result = self.tiff_processor.process_tiff(file_path)
                    return {
                        'success': True,
                        'result': result,
                        'processor': 'tiff_processor'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'TIFF processor not available'
                    }
            
            elif format_type in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.JPG]:
                if hasattr(self.image_processor, 'process_image'):
                    result = self.image_processor.process_image(file_path)
                    return {
                        'success': True,
                        'result': result,
                        'processor': 'image_processor'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Image processor not available'
                    }
            
            else:
                return {
                    'success': False,
                    'error': f"Unsupported format: {format_type.value}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Format-specific processing failed: {str(e)}"
            }
    
    def _process_with_ocr(self, file_path: str, format_type: DocumentFormat,
                         processing_options: Dict[str, Any]) -> Dict[str, Any]:
        """Process document with OCR"""
        try:
            # Prepare document for OCR based on format
            ocr_input_path = file_path
            
            # For PDFs, we might need to convert to images first
            if format_type == DocumentFormat.PDF:
                # This would ideally convert PDF pages to images
                # For now, pass the PDF directly to OCR service
                pass
            
            # Call OCR service
            ocr_result = self.ocr_service.process_document(ocr_input_path)
            
            return {
                'success': True,
                'extracted_text': ocr_result.get('text', ''),
                'confidence': ocr_result.get('confidence', 0.0),
                'engine': ocr_result.get('engine', 'unknown'),
                'metadata': ocr_result.get('metadata', {})
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"OCR processing failed: {str(e)}"
            }
    
    def _process_with_llm(self, ocr_text: str, format_type: DocumentFormat,
                         processing_options: Dict[str, Any]) -> Dict[str, Any]:
        """Process OCR text with LLM for field extraction"""
        try:
            # Prepare context based on document format
            context = {
                'document_format': format_type.value,
                'processing_timestamp': datetime.utcnow().isoformat(),
                'extraction_purpose': 'accounting_document_processing'
            }
            
            # Call LLM service for extraction
            llm_result = self.llm_service.extract_fields(ocr_text, context=context)
            
            return {
                'success': True,
                'extracted_fields': llm_result.get('fields', {}),
                'confidence_scores': llm_result.get('confidence_scores', {}),
                'model_info': llm_result.get('model_info', {}),
                'processing_metadata': llm_result.get('metadata', {})
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"LLM extraction failed: {str(e)}"
            }
    
    def _integrate_with_existing_pipeline(self, document: Document, 
                                        ocr_result: Dict[str, Any],
                                        llm_result: Dict[str, Any],
                                        user_id: str) -> Dict[str, Any]:
        """Integrate results with existing extraction pipeline"""
        try:
            # This would integrate with the existing document_processor.py
            # For now, create extraction runs similar to the existing pipeline
            
            # Create OCR extraction run
            ocr_run = ExtractionRun(
                document_id=document.document_id,
                stage="ocr",
                status="success" if ocr_result['success'] else "failed",
                engine_name=ocr_result.get('engine', 'enhanced_processor'),
                model_version="enhanced_v1.0",
                confidence_avg=ocr_result.get('confidence', 0.0),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow()
            )
            self.db.add(ocr_run)
            self.db.commit()
            self.db.refresh(ocr_run)
            
            # Store OCR text if available
            if ocr_result.get('extracted_text'):
                from app.models.extraction import ExtractionField
                ocr_text_field = ExtractionField(
                    run_id=ocr_run.run_id,
                    field_name="ocr_text",
                    value=ocr_result['extracted_text'],
                    confidence=ocr_result.get('confidence', 0.0),
                    validation_status="valid"
                )
                self.db.add(ocr_text_field)
                self.db.commit()
            
            # Create LLM extraction run
            if llm_result.get('success'):
                llm_run = ExtractionRun(
                    document_id=document.document_id,
                    stage="llm",
                    status="success",
                    engine_name=llm_result.get('model_info', {}).get('name', 'enhanced_llm'),
                    model_version=llm_result.get('model_info', {}).get('version', 'enhanced_v1.0'),
                    confidence_avg=sum(llm_result.get('confidence_scores', {}).values()) / 
                                   max(len(llm_result.get('confidence_scores', {})), 1),
                    started_at=datetime.utcnow(),
                    finished_at=datetime.utcnow()
                )
                self.db.add(llm_run)
                self.db.commit()
                self.db.refresh(llm_run)
                
                # Store extracted fields
                if llm_result.get('extracted_fields'):
                    from app.models.extraction import ExtractionField
                    for field_name, field_value in llm_result['extracted_fields'].items():
                        confidence = llm_result.get('confidence_scores', {}).get(field_name, 0.0)
                        extraction_field = ExtractionField(
                            run_id=llm_run.run_id,
                            field_name=field_name,
                            value=field_value,
                            confidence=confidence,
                            validation_status="pending"
                        )
                        self.db.add(extraction_field)
                    
                    self.db.commit()
            
            return {
                'success': True,
                'extraction_runs_created': True,
                'ocr_run_id': ocr_run.run_id,
                'llm_run_id': llm_run.run_id if llm_result.get('success') else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Integration with existing pipeline failed: {str(e)}"
            }
    
    def _finalize_processing(self, processing_result: Dict[str, Any], document: Document,
                           job: Job, start_time: float) -> Dict[str, Any]:
        """Finalize processing and update database"""
        try:
            # Update document processed timestamp
            if processing_result['success']:
                document.processed_at = datetime.utcnow()
            
            # Update job status
            if job:
                if processing_result['success']:
                    job.status = "needs_review"
                else:
                    job.status = "failed"
                    job.error_code = "PROCESSING_ERROR"
                    job.error_message = "; ".join(processing_result.get('errors', []))
                
                job.updated_at = datetime.utcnow()
                job.finished_at = datetime.utcnow()
                self.db.commit()
            
            # Add final processing metadata
            processing_result['processing_metadata']['total_time'] = time.time() - start_time
            processing_result['processing_metadata']['finalized_at'] = datetime.utcnow().isoformat()
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Error finalizing processing: {e}")
            processing_result['finalization_error'] = str(e)
            return processing_result
    
    def _update_processing_stats(self, format_type: str, success: bool):
        """Update processing statistics"""
        self.processing_stats['total_processed'] += 1
        
        if success:
            self.processing_stats['successful_processing'] += 1
        else:
            self.processing_stats['failed_processing'] += 1
        
        # Update format distribution
        if format_type not in self.processing_stats['format_distribution']:
            self.processing_stats['format_distribution'][format_type] = {'total': 0, 'success': 0, 'failed': 0}
        
        self.processing_stats['format_distribution'][format_type]['total'] += 1
        if success:
            self.processing_stats['format_distribution'][format_type]['success'] += 1
        else:
            self.processing_stats['format_distribution'][format_type]['failed'] += 1
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'current_stats': self.processing_stats,
            'processor_info': {
                'version': '1.0.0',
                'formats_supported': [fmt.value for fmt in DocumentFormat],
                'features_enabled': {
                    'format_detection': True,
                    'validation': self.validation_enabled,
                    'preview_generation': self.preview_enabled,
                    'format_conversion': True
                }
            }
        }
    
    def cleanup_temp_files(self, processing_result: Dict[str, Any]) -> int:
        """Clean up temporary files generated during processing"""
        cleaned_count = 0
        
        try:
            # Clean up preview files
            if 'preview_results' in processing_result:
                preview_result = processing_result['preview_results']
                if preview_result.get('success'):
                    cleaned_count += self.preview_generator.cleanup_previews(preview_result)
            
            # Clean up conversion files
            if 'conversion_result' in processing_result:
                conversion_result = processing_result['conversion_result']
                if conversion_result.get('success'):
                    cleaned_count += self.document_converter.cleanup_conversion_files(conversion_result)
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
        
        return cleaned_count


def get_enhanced_document_processor(db: Session) -> EnhancedDocumentProcessor:
    """Get enhanced document processor instance"""
    return EnhancedDocumentProcessor(db)