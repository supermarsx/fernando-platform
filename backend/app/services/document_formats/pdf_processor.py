"""
PDF Document Processor

Handles PDF text extraction and image processing.
Supports both text-based and image-based PDFs with intelligent processing.
"""

import os
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image
import logging

try:
    import pypdf
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyPDF not available. PDF processing will be limited.")

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logging.warning("pdf2image not available. PDF to image conversion will be limited.")

from .format_detector import DocumentFormat

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Service to process PDF documents"""
    
    def __init__(self):
        self.supported = PDF_AVAILABLE
        if not self.supported:
            logger.warning("PDF processing not available - PyPDF not installed")
        
        # PDF processing configuration
        self.max_pages = 50  # Maximum pages to process
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.image_dpi = 300  # DPI for image conversion
        self.image_format = 'PNG'
        
        # Extract images when possible
        self.extract_embedded_images = True
    
    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Process a PDF document through the complete pipeline
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Processing results including text, images, and metadata
        """
        if not self.supported:
            raise RuntimeError("PDF processing not available")
        
        try:
            # Read PDF
            reader = PdfReader(file_path)
            metadata = self._extract_metadata(reader)
            
            # Check if it's a text-based or image-based PDF
            text_content, has_text = self._extract_text_content(reader)
            
            # Extract images
            images = []
            if self.extract_embedded_images:
                images = self._extract_images(reader, file_path)
            
            # Convert to images if needed
            converted_images = []
            if not has_text or len(text_content.strip()) < 10:  # Likely image-based
                converted_images = self._convert_to_images(file_path)
            
            # Get processing statistics
            stats = self._calculate_stats(reader, text_content, images, converted_images)
            
            return {
                'format': DocumentFormat.PDF.value,
                'text_content': text_content,
                'has_text_layer': has_text,
                'metadata': metadata,
                'images': images,
                'converted_images': converted_images,
                'statistics': stats,
                'processing_method': self._determine_processing_method(has_text, images),
                'confidence': stats.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            raise
    
    def _extract_metadata(self, reader: PdfReader) -> Dict[str, Any]:
        """Extract PDF metadata"""
        try:
            metadata = {}
            
            if reader.metadata:
                pdf_metadata = reader.metadata
                
                # Common metadata fields
                metadata.update({
                    'title': pdf_metadata.get('/Title', ''),
                    'author': pdf_metadata.get('/Author', ''),
                    'subject': pdf_metadata.get('/Subject', ''),
                    'creator': pdf_metadata.get('/Creator', ''),
                    'producer': pdf_metadata.get('/Producer', ''),
                    'creation_date': pdf_metadata.get('/CreationDate', ''),
                    'modification_date': pdf_metadata.get('/ModDate', '')
                })
            
            # Add technical metadata
            metadata.update({
                'pdf_version': reader.pdf_header,
                'is_encrypted': reader.is_encrypted,
                'num_pages': len(reader.pages)
            })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return {}
    
    def _extract_text_content(self, reader: PdfReader) -> Tuple[str, bool]:
        """Extract text content from PDF"""
        try:
            text_content = ""
            has_text = False
            
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        has_text = True
                        text_content += f"\n--- Page {page_num + 1} ---\n"
                        text_content += page_text.strip()
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                    continue
            
            return text_content, has_text
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return "", False
    
    def _extract_images(self, reader: PdfReader, file_path: str) -> List[Dict[str, Any]]:
        """Extract embedded images from PDF"""
        images = []
        
        try:
            if not self.extract_embedded_images:
                return images
            
            # Note: PyPDF2/PyPDF doesn't have built-in image extraction
            # This is a placeholder for more advanced PDF parsing
            # In production, you might want to use libraries like:
            # - pdfplumber for better text and image extraction
            # - fitz (PyMuPDF) for comprehensive PDF manipulation
            
            logger.info("PDF image extraction not fully implemented - using conversion instead")
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
        
        return images
    
    def _convert_to_images(self, file_path: str) -> List[Dict[str, Any]]:
        """Convert PDF pages to images"""
        converted_images = []
        
        try:
            if not PDF2IMAGE_AVAILABLE:
                logger.warning("PDF2IMAGE not available for conversion")
                return converted_images
            
            # Convert PDF to images
            images = pdf2image.convert_from_path(
                file_path, 
                dpi=self.image_dpi,
                fmt=self.image_format.lower(),
                first_page=1,
                last_page=self.max_pages
            )
            
            # Save converted images to temporary files
            for page_num, image in enumerate(images):
                try:
                    # Create temporary file for this page
                    temp_dir = tempfile.mkdtemp()
                    image_path = os.path.join(temp_dir, f"page_{page_num + 1}.{self.image_format.lower()}")
                    
                    image.save(image_path, self.image_format)
                    
                    # Get image metadata
                    with Image.open(image_path) as img:
                        image_info = {
                            'page_number': page_num + 1,
                            'file_path': image_path,
                            'width': img.width,
                            'height': img.height,
                            'mode': img.mode,
                            'format': img.format,
                            'size_bytes': os.path.getsize(image_path),
                            'source': 'pdf_conversion'
                        }
                        converted_images.append(image_info)
                    
                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {e}")
                    continue
            
            logger.info(f"Converted {len(converted_images)} PDF pages to images")
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
        
        return converted_images
    
    def _calculate_stats(self, reader: PdfReader, text_content: str,
                        images: List[Dict], converted_images: List[Dict]) -> Dict[str, Any]:
        """Calculate processing statistics"""
        try:
            total_pages = len(reader.pages)
            text_length = len(text_content.strip())
            
            # Determine confidence based on content quality
            confidence = 0.0
            if text_length > 100:  # Substantial text content
                confidence = 0.9
            elif text_length > 10:  # Some text content
                confidence = 0.7
            elif converted_images:  # Image-based PDF
                confidence = 0.6
            else:  # Minimal content
                confidence = 0.3
            
            return {
                'total_pages': total_pages,
                'text_length': text_length,
                'has_text_content': text_length > 0,
                'embedded_images_count': len(images),
                'converted_images_count': len(converted_images),
                'total_images_count': len(images) + len(converted_images),
                'confidence': confidence,
                'processing_time': 'estimated',  # Could be measured in production
                'content_quality': self._assess_content_quality(text_length, converted_images)
            }
            
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            return {}
    
    def _determine_processing_method(self, has_text: bool, images: List[Dict]) -> str:
        """Determine the best processing method for this PDF"""
        if has_text and len(images) == 0:
            return "text_extraction"
        elif has_text and len(images) > 0:
            return "hybrid"  # Text + images
        elif not has_text and len(images) > 0:
            return "image_based"
        else:
            return "conversion_required"
    
    def _assess_content_quality(self, text_length: int, converted_images: List[Dict]) -> str:
        """Assess the quality of extracted content"""
        if text_length > 1000 and not converted_images:
            return "excellent"
        elif text_length > 100 and not converted_images:
            return "good"
        elif text_length > 0 and converted_images:
            return "mixed"
        elif converted_images:
            return "image_only"
        else:
            return "poor"
    
    def validate_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Validate if PDF can be processed
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Validation results
        """
        validation = {
            'is_valid_pdf': False,
            'is_processable': False,
            'issues': [],
            'warnings': [],
            'file_size_bytes': 0,
            'page_count': 0,
            'is_encrypted': False
        }
        
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            validation['file_size_bytes'] = file_size
            
            if file_size == 0:
                validation['issues'].append("File is empty")
                return validation
            
            if file_size > self.max_file_size:
                validation['issues'].append(f"File size {file_size} exceeds maximum {self.max_file_size}")
                return validation
            
            # Check if it's a valid PDF
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if not header.startswith(b'%PDF'):
                    validation['issues'].append("File is not a valid PDF (missing PDF header)")
                    return validation
            
            # Try to read PDF
            if self.supported:
                reader = PdfReader(file_path)
                validation['is_valid_pdf'] = True
                validation['page_count'] = len(reader.pages)
                validation['is_encrypted'] = reader.is_encrypted
                
                if reader.is_encrypted:
                    validation['issues'].append("PDF is encrypted and cannot be processed")
                    return validation
                
                if validation['page_count'] > self.max_pages:
                    validation['warnings'].append(
                        f"PDF has {validation['page_count']} pages, only first {self.max_pages} will be processed"
                    )
                
                validation['is_processable'] = True
            
        except Exception as e:
            validation['issues'].append(f"Error validating PDF: {str(e)}")
        
        return validation


def get_pdf_processor() -> PDFProcessor:
    """Get a singleton PDF processor instance"""
    return PDFProcessor()