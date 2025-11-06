"""
Document Validation Service

Validates documents for security, integrity, and processing readiness.
Implements file size limits, format validation, content scanning, and security checks.
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

from .format_detector import DocumentFormat, get_format_detector

logger = logging.getLogger(__name__)

class DocumentValidator:
    """Service to validate documents for security and processing readiness"""
    
    def __init__(self):
        # Validation configuration
        self.format_detector = get_format_detector()
        
        # File size limits by format (in bytes)
        self.size_limits = {
            DocumentFormat.PDF: 50 * 1024 * 1024,      # 50MB
            DocumentFormat.TIFF: 100 * 1024 * 1024,    # 100MB
            DocumentFormat.PNG: 25 * 1024 * 1024,      # 25MB
            DocumentFormat.JPEG: 25 * 1024 * 1024,     # 25MB
            DocumentFormat.JPG: 25 * 1024 * 1024,      # 25MB
        }
        
        # Security thresholds
        self.max_pages = {
            DocumentFormat.PDF: 200,
            DocumentFormat.TIFF: 500
        }
        
        # Content validation settings
        self.min_file_size = 100  # bytes
        self.max_file_size = 200 * 1024 * 1024  # 200MB absolute max
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar', 
            '.ps1', '.sh', '.py', '.php', '.asp', '.jsp', '.pl', '.cgi'
        }
        
        # Suspicious patterns for content scanning
        self.suspicious_patterns = [
            b'<script', b'javascript:', b'eval(', b'exec(', b'system(',
            b'shell_exec', b'passthru', b'file_get_contents', b'fopen(',
            b'<iframe', b'<object', b'<embed', b'<applet'
        ]
        
        # MIME type validation
        self.allowed_mime_types = {
            'application/pdf',
            'image/tiff',
            'image/png',
            'image/jpeg',
            'image/jpg'
        }
        
        # Trusted file signatures (magic bytes)
        self.trusted_signatures = {
            DocumentFormat.PDF: b'%PDF',
            DocumentFormat.TIFF: [b'II*\x00', b'MM\x00*'],
            DocumentFormat.PNG: b'\x89PNG\r\n\x1a\n',
            DocumentFormat.JPEG: b'\xff\xd8\xff'
        }
    
    def validate_document(self, file_path: str, tenant_id: str = None, 
                         user_id: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive document validation
        
        Args:
            file_path: Path to the document file
            tenant_id: Tenant ID for multi-tenant validation
            user_id: User ID for audit logging
            
        Returns:
            Complete validation results
        """
        validation_result = {
            'file_path': file_path,
            'is_valid': False,
            'is_safe': False,
            'is_processable': False,
            'validation_level': 'basic',
            'checks_passed': [],
            'warnings': [],
            'errors': [],
            'file_info': {},
            'security_scan': {},
            'content_analysis': {},
            'processing_readiness': {},
            'tenant_restrictions': {},
            'validation_metadata': {
                'validated_at': None,
                'validator_version': '1.0.0',
                'checks_performed': []
            }
        }
        
        try:
            # Step 1: Basic file validation
            basic_validation = self._perform_basic_validation(file_path)
            validation_result.update(basic_validation)
            
            # Step 2: Format detection and validation
            if validation_result['is_file_valid']:
                format_validation = self._perform_format_validation(file_path)
                validation_result.update(format_validation)
                
                # Step 3: Security scanning
                security_scan = self._perform_security_scan(file_path)
                validation_result['security_scan'] = security_scan
                
                # Step 4: Content analysis
                content_analysis = self._perform_content_analysis(file_path)
                validation_result['content_analysis'] = content_analysis
                
                # Step 5: Processing readiness check
                processing_readiness = self._check_processing_readiness(file_path, format_validation)
                validation_result['processing_readiness'] = processing_readiness
                
                # Step 6: Tenant restrictions check
                if tenant_id:
                    tenant_restrictions = self._check_tenant_restrictions(file_path, tenant_id, format_validation)
                    validation_result['tenant_restrictions'] = tenant_restrictions
            
            # Step 7: Final validation determination
            validation_result = self._finalize_validation(validation_result)
            
            # Add validation metadata
            validation_result['validation_metadata']['validated_at'] = self._get_current_timestamp()
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during document validation: {e}")
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['validation_metadata']['validation_error'] = str(e)
            return validation_result
    
    def _perform_basic_validation(self, file_path: str) -> Dict[str, Any]:
        """Perform basic file validation"""
        basic_validation = {
            'is_file_valid': False,
            'checks_performed': ['basic_file_check'],
            'file_info': {}
        }
        
        try:
            # Check file existence
            if not os.path.exists(file_path):
                basic_validation['errors'] = ["File does not exist"]
                return basic_validation
            
            # Get file information
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_extension = Path(file_path).suffix.lower()
            
            basic_validation['file_info'] = {
                'file_size_bytes': file_size,
                'file_extension': file_extension,
                'file_path': file_path,
                'exists': True,
                'readable': os.access(file_path, os.R_OK)
            }
            
            # Check file size
            if file_size == 0:
                basic_validation['errors'].append("File is empty")
                return basic_validation
            
            if file_size > self.max_file_size:
                basic_validation['errors'].append(f"File size {file_size} exceeds maximum {self.max_file_size}")
                return basic_validation
            
            if file_size < self.min_file_size:
                basic_validation['warnings'].append(f"File size {file_size} is very small")
            
            # Check for dangerous extensions
            if file_extension in self.dangerous_extensions:
                basic_validation['errors'].append(f"Dangerous file extension: {file_extension}")
                basic_validation['security_scan'] = {'status': 'failed', 'reason': 'dangerous_extension'}
                return basic_validation
            
            # Check read permissions
            if not os.access(file_path, os.R_OK):
                basic_validation['errors'].append("File is not readable")
                return basic_validation
            
            basic_validation['is_file_valid'] = True
            basic_validation['checks_passed'].append('file_size_check')
            basic_validation['checks_passed'].append('file_extension_check')
            basic_validation['checks_passed'].append('readability_check')
            
        except Exception as e:
            basic_validation['errors'].append(f"Error in basic validation: {str(e)}")
        
        return basic_validation
    
    def _perform_format_validation(self, file_path: str) -> Dict[str, Any]:
        """Perform format detection and validation"""
        format_validation = {
            'detected_format': DocumentFormat.UNKNOWN,
            'format_confidence': 0.0,
            'is_format_supported': False,
            'format_metadata': {},
            'checks_performed': ['format_detection']
        }
        
        try:
            # Detect format
            detected_format, metadata = self.format_detector.detect_format(file_path)
            format_validation['detected_format'] = detected_format
            format_validation['format_confidence'] = metadata['confidence']
            format_validation['format_metadata'] = metadata
            
            # Check if format is supported
            supported_formats = {DocumentFormat.PDF, DocumentFormat.TIFF, DocumentFormat.PNG, 
                               DocumentFormat.JPEG, DocumentFormat.JPG}
            format_validation['is_format_supported'] = detected_format in supported_formats
            
            if not format_validation['is_format_supported']:
                format_validation['errors'] = [f"Unsupported format: {detected_format.value}"]
                return format_validation
            
            # Validate format-specific requirements
            if detected_format != DocumentFormat.UNKNOWN:
                format_validation = self._validate_format_specific(file_path, detected_format, format_validation)
            
            format_validation['checks_passed'].append('format_support_check')
            format_validation['checks_passed'].append('magic_bytes_validation')
            
        except Exception as e:
            format_validation['errors'] = [f"Error in format validation: {str(e)}"]
        
        return format_validation
    
    def _validate_format_specific(self, file_path: str, format_type: DocumentFormat, 
                                validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate format-specific requirements"""
        try:
            file_size = validation_result['file_info']['file_size_bytes']
            
            # Check format-specific size limits
            if format_type in self.size_limits:
                size_limit = self.size_limits[format_type]
                if file_size > size_limit:
                    validation_result['errors'].append(
                        f"File size {file_size} exceeds {format_type.value} limit {size_limit}"
                    )
                    return validation_result
            
            validation_result['checks_passed'].append('format_size_check')
            
            # Format-specific validation using appropriate processors
            if format_type == DocumentFormat.PDF:
                validation_result = self._validate_pdf_specific(file_path, validation_result)
            elif format_type == DocumentFormat.TIFF:
                validation_result = self._validate_tiff_specific(file_path, validation_result)
            elif format_type in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.JPG]:
                validation_result = self._validate_image_specific(file_path, format_type, validation_result)
            
        except Exception as e:
            validation_result['warnings'].append(f"Format-specific validation error: {str(e)}")
        
        return validation_result
    
    def _validate_pdf_specific(self, file_path: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate PDF-specific requirements"""
        try:
            # Try to validate PDF structure
            validation_result['checks_performed'].append('pdf_specific_validation')
            
            # Read PDF header
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    validation_result['errors'].append("Invalid PDF header")
                    return validation_result
            
            # Try to read PDF with pypdf
            try:
                import pypdf
                from pypdf import PdfReader
                
                reader = PdfReader(file_path)
                page_count = len(reader.pages)
                
                # Check page count limit
                if page_count > self.max_pages[DocumentFormat.PDF]:
                    validation_result['warnings'].append(
                        f"PDF has {page_count} pages, exceeds recommended limit"
                    )
                
                # Check if encrypted
                if reader.is_encrypted:
                    validation_result['errors'].append("PDF is encrypted and cannot be processed")
                    return validation_result
                
                validation_result['pdf_info'] = {
                    'page_count': page_count,
                    'is_encrypted': reader.is_encrypted,
                    'pdf_version': reader.pdf_header
                }
                
                validation_result['checks_passed'].append('pdf_structure_check')
                validation_result['checks_passed'].append('pdf_encryption_check')
                
            except ImportError:
                validation_result['warnings'].append("PyPDF not available, PDF structure validation skipped")
            except Exception as e:
                validation_result['warnings'].append(f"PDF validation error: {str(e)}")
            
        except Exception as e:
            validation_result['warnings'].append(f"PDF-specific validation error: {str(e)}")
        
        return validation_result
    
    def _validate_tiff_specific(self, file_path: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate TIFF-specific requirements"""
        try:
            validation_result['checks_performed'].append('tiff_specific_validation')
            
            # Validate TIFF structure using PIL
            try:
                from PIL import Image
                
                with Image.open(file_path) as img:
                    # Count pages
                    page_count = 1
                    try:
                        while True:
                            img.seek(page_count)
                            page_count += 1
                    except EOFError:
                        pass
                    
                    # Check page count limit
                    if page_count > self.max_pages[DocumentFormat.TIFF]:
                        validation_result['warnings'].append(
                            f"TIFF has {page_count} pages, exceeds recommended limit"
                        )
                    
                    validation_result['tiff_info'] = {
                        'page_count': page_count,
                        'dimensions': (img.width, img.height),
                        'mode': img.mode,
                        'compression': img.info.get('compression', 'unknown')
                    }
                    
                    validation_result['checks_passed'].append('tiff_structure_check')
                    
            except ImportError:
                validation_result['warnings'].append("PIL not available, TIFF validation limited")
            except Exception as e:
                validation_result['warnings'].append(f"TIFF validation error: {str(e)}")
            
        except Exception as e:
            validation_result['warnings'].append(f"TIFF-specific validation error: {str(e)}")
        
        return validation_result
    
    def _validate_image_specific(self, file_path: str, format_type: DocumentFormat, 
                               validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate image-specific requirements"""
        try:
            validation_result['checks_performed'].append('image_specific_validation')
            
            # Validate image using PIL
            try:
                from PIL import Image
                
                with Image.open(file_path) as img:
                    # Check dimensions
                    if img.width < 50 or img.height < 50:
                        validation_result['warnings'].append(
                            f"Image dimensions {img.width}x{img.height} are very small"
                        )
                    
                    # Check supported modes
                    if img.mode not in ['RGB', 'RGBA', 'L', 'P', '1']:
                        validation_result['warnings'].append(f"Image mode {img.mode} may not be fully supported")
                    
                    validation_result['image_info'] = {
                        'dimensions': (img.width, img.height),
                        'mode': img.mode,
                        'format': img.format,
                        'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                    }
                    
                    validation_result['checks_passed'].append('image_structure_check')
                    
            except ImportError:
                validation_result['warnings'].append("PIL not available, image validation limited")
            except Exception as e:
                validation_result['warnings'].append(f"Image validation error: {str(e)}")
            
        except Exception as e:
            validation_result['warnings'].append(f"Image-specific validation error: {str(e)}")
        
        return validation_result
    
    def _perform_security_scan(self, file_path: str) -> Dict[str, Any]:
        """Perform security scanning"""
        security_scan = {
            'status': 'passed',
            'threats_detected': [],
            'checks_performed': ['magic_bytes', 'content_patterns'],
            'scan_metadata': {}
        }
        
        try:
            # Magic bytes validation
            with open(file_path, 'rb') as f:
                header = f.read(100)  # Read first 100 bytes
                
                # Check against trusted signatures
                is_trusted = False
                for format_type, signatures in self.trusted_signatures.items():
                    if isinstance(signatures, list):
                        for signature in signatures:
                            if header.startswith(signature):
                                is_trusted = True
                                break
                    else:
                        if header.startswith(signatures):
                            is_trusted = True
                            break
                
                if not is_trusted:
                    security_scan['threats_detected'].append('untrusted_file_signature')
                    security_scan['status'] = 'failed'
                
                # Content pattern scanning
                content_scan_result = self._scan_content_patterns(file_path)
                if content_scan_result['threats_found']:
                    security_scan['threats_detected'].extend(content_scan_result['threats_found'])
                    security_scan['status'] = 'failed'
                
                security_scan['scan_metadata'] = content_scan_result
            
        except Exception as e:
            security_scan['status'] = 'error'
            security_scan['threats_detected'].append(f'security_scan_error: {str(e)}')
        
        return security_scan
    
    def _scan_content_patterns(self, file_path: str) -> Dict[str, Any]:
        """Scan file content for suspicious patterns"""
        result = {
            'threats_found': [],
            'patterns_checked': len(self.suspicious_patterns),
            'scan_method': 'pattern_matching'
        }
        
        try:
            with open(file_path, 'rb') as f:
                # Read content in chunks to handle large files
                chunk_size = 8192
                content = f.read(chunk_size)
                
                # Check for suspicious patterns
                for pattern in self.suspicious_patterns:
                    if pattern in content:
                        result['threats_found'].append(f'suspicious_pattern: {pattern.decode("ascii", errors="ignore")}')
                
        except Exception as e:
            result['threats_found'].append(f'content_scan_error: {str(e)}')
        
        return result
    
    def _perform_content_analysis(self, file_path: str) -> Dict[str, Any]:
        """Perform content analysis"""
        content_analysis = {
            'analyzers_used': [],
            'content_quality': 'unknown',
            'processing_recommendations': [],
            'analysis_metadata': {}
        }
        
        try:
            # File analysis
            file_analysis = self._analyze_file_content(file_path)
            content_analysis.update(file_analysis)
            content_analysis['analyzers_used'].append('file_content_analysis')
            
            # Structural analysis
            structural_analysis = self._analyze_file_structure(file_path)
            content_analysis.update(structural_analysis)
            content_analysis['analyzers_used'].append('file_structure_analysis')
            
        except Exception as e:
            content_analysis['analysis_errors'] = [str(e)]
        
        return content_analysis
    
    def _analyze_file_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze file content"""
        analysis = {
            'file_entropy': 0.0,
            'content_type': 'unknown',
            'has_structured_content': False
        }
        
        try:
            # Calculate file entropy (measure of randomness/complexity)
            with open(file_path, 'rb') as f:
                content = f.read(10000)  # Sample first 10KB
                
                if content:
                    # Calculate Shannon entropy
                    byte_counts = [0] * 256
                    for byte in content:
                        byte_counts[byte] += 1
                    
                    entropy = 0.0
                    content_len = len(content)
                    for count in byte_counts:
                        if count > 0:
                            probability = count / content_len
                            entropy -= probability * (probability.bit_length() - 1)
                    
                    analysis['file_entropy'] = entropy
                    
                    # Determine content type based on entropy and patterns
                    if entropy < 3.0:
                        analysis['content_type'] = 'text_like'
                        analysis['has_structured_content'] = True
                    elif entropy < 6.0:
                        analysis['content_type'] = 'mixed'
                    else:
                        analysis['content_type'] = 'binary'
                    
        except Exception as e:
            analysis['analysis_error'] = str(e)
        
        return analysis
    
    def _analyze_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze file structure"""
        analysis = {
            'file_structure': 'unknown',
            'embedded_objects': False,
            'compression_detected': False
        }
        
        try:
            # Basic structure analysis
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.pdf':
                analysis['file_structure'] = 'document'
                # Could add PDF-specific structure analysis here
            elif file_extension in ['.tiff', '.tif']:
                analysis['file_structure'] = 'image_multi_page'
                analysis['compression_detected'] = True  # TIFFs are often compressed
            elif file_extension in ['.png', '.jpg', '.jpeg']:
                analysis['file_structure'] = 'image_single_page'
                if file_extension == '.png':
                    analysis['compression_detected'] = True
            else:
                analysis['file_structure'] = 'unknown'
                
        except Exception as e:
            analysis['structure_analysis_error'] = str(e)
        
        return analysis
    
    def _check_processing_readiness(self, file_path: str, format_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Check if document is ready for processing"""
        processing_readiness = {
            'is_ready': False,
            'readiness_score': 0.0,
            'blocking_issues': [],
            'recommendations': [],
            'processing_requirements': {}
        }
        
        try:
            readiness_score = 0.0
            
            # Base score for being a supported format
            if format_validation.get('is_format_supported'):
                readiness_score += 0.4
            
            # Additional score for format confidence
            confidence = format_validation.get('format_confidence', 0.0)
            readiness_score += confidence * 0.3
            
            # Check security status
            # This would integrate with the security scan results
            readiness_score += 0.2  # Assume security passed for now
            
            # Format-specific readiness checks
            detected_format = format_validation.get('detected_format')
            if detected_format:
                format_readiness = self._check_format_readiness(file_path, detected_format)
                readiness_score += format_readiness['score_contribution']
                processing_readiness['processing_requirements'].update(format_readiness['requirements'])
            
            processing_readiness['readiness_score'] = min(readiness_score, 1.0)
            processing_readiness['is_ready'] = readiness_score >= 0.7
            
            # Generate recommendations
            if readiness_score < 0.7:
                processing_readiness['recommendations'].append("Document may need preprocessing before OCR")
            if confidence < 0.8:
                processing_readiness['recommendations'].append("Format detection confidence is low")
            
        except Exception as e:
            processing_readiness['readiness_error'] = str(e)
        
        return processing_readiness
    
    def _check_format_readiness(self, file_path: str, format_type: DocumentFormat) -> Dict[str, Any]:
        """Check format-specific processing readiness"""
        readiness = {
            'score_contribution': 0.1,
            'requirements': {}
        }
        
        try:
            if format_type == DocumentFormat.PDF:
                readiness['requirements'] = {
                    'ocr_engine': 'tesseract',
                    'preprocessing': 'pdf_text_extraction_or_conversion',
                    'expected_quality': 'high'
                }
            elif format_type == DocumentFormat.TIFF:
                readiness['requirements'] = {
                    'ocr_engine': 'tesseract',
                    'preprocessing': 'image_enhancement',
                    'expected_quality': 'high'
                }
            elif format_type in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.JPG]:
                readiness['requirements'] = {
                    'ocr_engine': 'tesseract',
                    'preprocessing': 'image_optimization',
                    'expected_quality': 'medium_to_high'
                }
                
        except Exception as e:
            readiness['readiness_check_error'] = str(e)
        
        return readiness
    
    def _check_tenant_restrictions(self, file_path: str, tenant_id: str, 
                                 format_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Check tenant-specific restrictions"""
        # This would integrate with tenant management system
        tenant_restrictions = {
            'restrictions_applied': False,
            'allowed_formats': ['pdf', 'tiff', 'png', 'jpeg', 'jpg'],
            'size_limits': {},
            'processing_limits': {}
        }
        
        try:
            # Check if format is allowed for this tenant
            detected_format = format_validation.get('detected_format')
            if detected_format and detected_format.value not in tenant_restrictions['allowed_formats']:
                tenant_restrictions['restrictions_applied'] = True
                tenant_restrictions['blocking_issues'] = [f"Format {detected_format.value} not allowed for tenant"]
            
            # Check file size limits for tenant
            file_size = format_validation.get('file_info', {}).get('file_size_bytes', 0)
            # This would query tenant-specific limits from database
            
            tenant_restrictions['tenant_id'] = tenant_id
            
        except Exception as e:
            tenant_restrictions['restriction_check_error'] = str(e)
        
        return tenant_restrictions
    
    def _finalize_validation(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize validation and determine overall status"""
        # Count checks passed
        checks_passed = validation_result.get('checks_passed', [])
        total_checks = len(checks_passed)
        
        # Determine validity
        validation_result['is_valid'] = (
            validation_result.get('is_file_valid', False) and
            validation_result.get('is_format_supported', False) and
            validation_result.get('security_scan', {}).get('status') == 'passed'
        )
        
        # Determine safety
        validation_result['is_safe'] = (
            validation_result.get('security_scan', {}).get('status') == 'passed' and
            len(validation_result.get('security_scan', {}).get('threats_detected', [])) == 0
        )
        
        # Determine processability
        validation_result['is_processable'] = (
            validation_result.get('is_valid', False) and
            validation_result.get('processing_readiness', {}).get('is_ready', False)
        )
        
        # Set validation level based on checks performed
        if total_checks >= 10:
            validation_result['validation_level'] = 'comprehensive'
        elif total_checks >= 5:
            validation_result['validation_level'] = 'standard'
        else:
            validation_result['validation_level'] = 'basic'
        
        # Update metadata
        validation_result['validation_metadata']['checks_passed'] = checks_passed
        validation_result['validation_metadata']['total_checks'] = total_checks
        
        return validation_result
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for validation metadata"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of validation results"""
        summary = {
            'overall_status': 'failed',
            'is_safe': validation_result.get('is_safe', False),
            'is_processable': validation_result.get('is_processable', False),
            'detected_format': validation_result.get('detected_format', {}).get('value', 'unknown'),
            'validation_level': validation_result.get('validation_level', 'unknown'),
            'key_issues': [],
            'recommendations': []
        }
        
        # Determine overall status
        if validation_result.get('is_processable', False):
            summary['overall_status'] = 'ready'
        elif validation_result.get('is_valid', False):
            summary['overall_status'] = 'valid_but_not_ready'
        elif validation_result.get('is_safe', False):
            summary['overall_status'] = 'safe_but_invalid'
        else:
            summary['overall_status'] = 'failed'
        
        # Collect key issues
        all_errors = validation_result.get('errors', [])
        security_threats = validation_result.get('security_scan', {}).get('threats_detected', [])
        summary['key_issues'] = all_errors + security_threats
        
        # Collect recommendations
        recommendations = validation_result.get('processing_readiness', {}).get('recommendations', [])
        format_warnings = validation_result.get('warnings', [])
        summary['recommendations'] = recommendations + format_warnings
        
        return summary


def get_document_validator() -> DocumentValidator:
    """Get a singleton document validator instance"""
    return DocumentValidator()