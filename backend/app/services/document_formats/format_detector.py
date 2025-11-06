"""
Document Format Detection Service

Automatically detects document formats (PDF, TIFF, PNG, JPEG, JPG)
using magic bytes, file extensions, and MIME type analysis.
"""

import magic
import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class DocumentFormat(Enum):
    """Supported document formats"""
    PDF = "pdf"
    TIFF = "tiff"
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    UNKNOWN = "unknown"

class FormatDetector:
    """Service to detect document formats"""
    
    def __init__(self):
        # Magic bytes signatures for different formats
        self.format_signatures = {
            DocumentFormat.PDF: [b'%PDF'],
            DocumentFormat.TIFF: [b'II*\x00', b'MM\x00*'],  # Little-endian and big-endian TIFF
            DocumentFormat.PNG: [b'\x89PNG\r\n\x1a\n'],
            DocumentFormat.JPEG: [b'\xff\xd8\xff'],  # JPEG/JPG
        }
        
        # MIME type mappings
        self.mime_type_mapping = {
            'application/pdf': DocumentFormat.PDF,
            'image/tiff': DocumentFormat.TIFF,
            'image/png': DocumentFormat.PNG,
            'image/jpeg': DocumentFormat.JPEG,
        }
        
        # File extension mappings
        self.extension_mapping = {
            '.pdf': DocumentFormat.PDF,
            '.tiff': DocumentFormat.TIFF,
            '.tif': DocumentFormat.TIFF,
            '.png': DocumentFormat.PNG,
            '.jpeg': DocumentFormat.JPEG,
            '.jpg': DocumentFormat.JPEG,
        }
    
    def detect_format(self, file_path: str) -> Tuple[DocumentFormat, Dict[str, Any]]:
        """
        Detect document format using multiple methods
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (detected_format, metadata)
        """
        metadata = {
            'detection_method': 'combined',
            'confidence': 0.0,
            'mime_type': None,
            'file_extension': None,
            'magic_bytes_match': False,
            'size_bytes': 0,
            'is_valid_format': False
        }
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file size
        metadata['size_bytes'] = os.path.getsize(file_path)
        
        # Method 1: Magic bytes detection
        detected_by_magic, magic_confidence = self._detect_by_magic_bytes(file_path)
        metadata['magic_bytes_match'] = detected_by_magic != DocumentFormat.UNKNOWN
        metadata['magic_confidence'] = magic_confidence
        
        # Method 2: MIME type detection
        mime_type = self._detect_mime_type(file_path)
        detected_by_mime = self._detect_by_mime_type(mime_type)
        metadata['mime_type'] = mime_type
        
        # Method 3: File extension detection
        extension, detected_by_extension = self._detect_by_extension(file_path)
        metadata['file_extension'] = extension
        
        # Combine results with confidence scoring
        final_format, confidence = self._combine_detections(
            detected_by_magic, detected_by_mime, detected_by_extension,
            metadata['magic_confidence']
        )
        
        metadata['confidence'] = confidence
        metadata['is_valid_format'] = final_format in [
            DocumentFormat.PDF, DocumentFormat.TIFF, DocumentFormat.PNG, 
            DocumentFormat.JPEG, DocumentFormat.JPG
        ]
        
        return final_format, metadata
    
    def _detect_by_magic_bytes(self, file_path: str) -> Tuple[DocumentFormat, float]:
        """Detect format using magic bytes"""
        try:
            with open(file_path, 'rb') as f:
                # Read first 16 bytes for detection
                header = f.read(16)
                
            for format_type, signatures in self.format_signatures.items():
                for signature in signatures:
                    if header.startswith(signature):
                        logger.debug(f"Detected {format_type.value} by magic bytes")
                        return format_type, 0.95
            
            return DocumentFormat.UNKNOWN, 0.0
            
        except Exception as e:
            logger.error(f"Error detecting magic bytes: {e}")
            return DocumentFormat.UNKNOWN, 0.0
    
    def _detect_mime_type(self, file_path: str) -> Optional[str]:
        """Detect MIME type using python-magic or fallback methods"""
        try:
            # Use python-magic for accurate detection
            mime_type = magic.from_file(file_path, mime=True)
            return mime_type
        except Exception:
            try:
                # Fallback to mimetypes module
                mime_type, _ = mimetypes.guess_type(file_path)
                return mime_type
            except Exception as e:
                logger.error(f"Error detecting MIME type: {e}")
                return None
    
    def _detect_by_mime_type(self, mime_type: Optional[str]) -> DocumentFormat:
        """Detect format from MIME type"""
        if not mime_type:
            return DocumentFormat.UNKNOWN
        
        return self.mime_type_mapping.get(mime_type, DocumentFormat.UNKNOWN)
    
    def _detect_by_extension(self, file_path: str) -> Tuple[str, DocumentFormat]:
        """Detect format from file extension"""
        try:
            file_extension = Path(file_path).suffix.lower()
            detected_format = self.extension_mapping.get(file_extension, DocumentFormat.UNKNOWN)
            return file_extension, detected_format
        except Exception as e:
            logger.error(f"Error detecting from extension: {e}")
            return "", DocumentFormat.UNKNOWN
    
    def _combine_detections(self, magic_format: DocumentFormat, 
                          mime_format: DocumentFormat, 
                          ext_format: DocumentFormat,
                          magic_confidence: float) -> Tuple[DocumentFormat, float]:
        """Combine multiple detection methods with confidence scoring"""
        
        # If all methods agree, high confidence
        if magic_format == mime_format == ext_format and magic_format != DocumentFormat.UNKNOWN:
            return magic_format, 0.95
        
        # If magic bytes and MIME type agree, high confidence
        if magic_format == mime_format and magic_format != DocumentFormat.UNKNOWN:
            return magic_format, 0.90
        
        # If magic bytes detected, medium confidence
        if magic_format != DocumentFormat.UNKNOWN:
            return magic_format, 0.80
        
        # If MIME type and extension agree, medium confidence
        if mime_format == ext_format and mime_format != DocumentFormat.UNKNOWN:
            return mime_format, 0.70
        
        # If only extension detected, low confidence
        if ext_format != DocumentFormat.UNKNOWN:
            return ext_format, 0.50
        
        return DocumentFormat.UNKNOWN, 0.0
    
    def validate_format_support(self, detected_format: DocumentFormat, 
                               max_file_size: Optional[int] = None,
                               size_bytes: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate if format is supported and meets requirements
        
        Args:
            detected_format: Detected document format
            max_file_size: Maximum allowed file size in bytes
            size_bytes: Actual file size in bytes
            
        Returns:
            Validation results
        """
        validation = {
            'is_supported': detected_format in [
                DocumentFormat.PDF, DocumentFormat.TIFF, DocumentFormat.PNG,
                DocumentFormat.JPEG, DocumentFormat.JPG
            ],
            'format_name': detected_format.value,
            'size_valid': True,
            'max_size_bytes': max_file_size,
            'actual_size_bytes': size_bytes,
            'issues': []
        }
        
        if not validation['is_supported']:
            validation['issues'].append(f"Format {detected_format.value} is not supported")
        
        if max_file_size and size_bytes and size_bytes > max_file_size:
            validation['size_valid'] = False
            validation['issues'].append(
                f"File size {size_bytes} bytes exceeds maximum {max_file_size} bytes"
            )
        
        if size_bytes == 0:
            validation['issues'].append("File is empty")
        
        return validation


def get_format_detector() -> FormatDetector:
    """Get a singleton format detector instance"""
    return FormatDetector()