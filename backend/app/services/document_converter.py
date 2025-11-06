"""
Document Conversion Utility

Handles conversion between document formats when needed for processing.
Supports PDF to image, TIFF to image, and image format conversions.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from PIL import Image

from .format_detector import DocumentFormat
from .pdf_processor import PDFProcessor
from .tiff_processor import TIFFProcessor
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)

class DocumentConverter:
    """Service to convert documents between formats"""
    
    def __init__(self):
        # Conversion configuration
        self.max_output_size = 50 * 1024 * 1024  # 50MB output limit
        self.max_pages = 100  # Maximum pages to convert
        self.default_dpi = 300
        self.quality_settings = {
            'high': {'dpi': 300, 'quality': 95},
            'medium': {'dpi': 200, 'quality': 85},
            'low': {'dpi': 150, 'quality': 75}
        }
        
        # Supported conversions
        self.supported_conversions = {
            # PDF conversions
            ('pdf', 'png'): self._convert_pdf_to_png,
            ('pdf', 'jpeg'): self._convert_pdf_to_jpeg,
            ('pdf', 'jpg'): self._convert_pdf_to_jpeg,
            
            # TIFF conversions
            ('tiff', 'png'): self._convert_tiff_to_png,
            ('tiff', 'jpeg'): self._convert_tiff_to_jpeg,
            ('tiff', 'jpg'): self._convert_tiff_to_jpeg,
            
            # Image format conversions
            ('png', 'jpeg'): self._convert_image_to_jpeg,
            ('png', 'jpg'): self._convert_image_to_jpeg,
            ('jpeg', 'png'): self._convert_jpeg_to_png,
            ('jpg', 'png'): self._convert_jpeg_to_png,
            ('jpeg', 'jpg'): self._convert_jpeg_to_jpg,
            ('jpg', 'jpeg'): self._convert_jpeg_to_jpg,
        }
        
        # Initialize processors
        self.pdf_processor = PDFProcessor() if hasattr(PDFProcessor, '__init__') else None
        self.tiff_processor = TIFFProcessor() if hasattr(TIFFProcessor, '__init__') else None
        self.image_processor = ImageProcessor() if hasattr(ImageProcessor, '__init__') else None
    
    def can_convert(self, source_format: DocumentFormat, target_format: DocumentFormat) -> bool:
        """Check if conversion is supported"""
        return (source_format.value, target_format.value) in self.supported_conversions
    
    def convert_document(self, file_path: str, source_format: DocumentFormat, 
                        target_format: DocumentFormat, **kwargs) -> Dict[str, Any]:
        """
        Convert document from source format to target format
        
        Args:
            file_path: Path to source document
            source_format: Source document format
            target_format: Target document format
            **kwargs: Conversion options (dpi, quality, page_range, etc.)
            
        Returns:
            Conversion results
        """
        try:
            # Validate conversion support
            if not self.can_convert(source_format, target_format):
                return {
                    'success': False,
                    'error': f"Conversion from {source_format.value} to {target_format.value} not supported"
                }
            
            # Get conversion function
            conversion_func = self.supported_conversions[(source_format.value, target_format.value)]
            
            # Set default options
            options = self._get_conversion_options(kwargs)
            
            # Perform conversion
            result = conversion_func(file_path, options)
            
            return result
            
        except Exception as e:
            logger.error(f"Error converting document {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'source_format': source_format.value,
                'target_format': target_format.value
            }
    
    def _get_conversion_options(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Get standardized conversion options"""
        options = {
            'dpi': kwargs.get('dpi', self.default_dpi),
            'quality': kwargs.get('quality', 'medium'),
            'page_range': kwargs.get('page_range', None),
            'max_pages': kwargs.get('max_pages', self.max_pages),
            'preserve_color': kwargs.get('preserve_color', True),
            'optimize_size': kwargs.get('optimize_size', True),
            'background_color': kwargs.get('background_color', (255, 255, 255))
        }
        
        # Validate quality setting
        if options['quality'] not in self.quality_settings:
            options['quality'] = 'medium'
        
        return options
    
    def _convert_pdf_to_png(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert PDF to PNG"""
        try:
            if not self.pdf_processor:
                return {'success': False, 'error': 'PDF processor not available'}
            
            import pdf2image
            dpi = options['dpi']
            quality_settings = self.quality_settings[options['quality']]
            
            # Convert PDF pages to images
            images = pdf2image.convert_from_path(
                file_path,
                dpi=dpi,
                fmt='PNG',
                first_page=options['page_range'][0] if options['page_range'] else 1,
                last_page=options['page_range'][1] if options['page_range'] else options['max_pages']
            )
            
            # Save images and collect paths
            converted_files = []
            for i, image in enumerate(images):
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f'page_{i + 1}.png')
                image.save(output_path, 'PNG')
                converted_files.append(output_path)
            
            return {
                'success': True,
                'converted_files': converted_files,
                'page_count': len(images),
                'conversion_type': 'pdf_to_png',
                'settings': {
                    'dpi': dpi,
                    'format': 'PNG',
                    'quality': options['quality']
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'PDF to PNG conversion failed: {str(e)}'}
    
    def _convert_pdf_to_jpeg(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert PDF to JPEG"""
        try:
            if not self.pdf_processor:
                return {'success': False, 'error': 'PDF processor not available'}
            
            import pdf2image
            dpi = options['dpi']
            quality_settings = self.quality_settings[options['quality']]
            
            # Convert PDF pages to images
            images = pdf2image.convert_from_path(
                file_path,
                dpi=dpi,
                fmt='JPEG',
                quality=quality_settings['quality'],
                first_page=options['page_range'][0] if options['page_range'] else 1,
                last_page=options['page_range'][1] if options['page_range'] else options['max_pages']
            )
            
            # Save images and collect paths
            converted_files = []
            for i, image in enumerate(images):
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f'page_{i + 1}.jpg')
                
                # Convert RGBA to RGB if needed for JPEG
                if image.mode == 'RGBA':
                    background = Image.new('RGB', image.size, options['background_color'])
                    background.paste(image, mask=image.split()[-1])
                    image = background
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                
                image.save(output_path, 'JPEG', quality=quality_settings['quality'], optimize=options['optimize_size'])
                converted_files.append(output_path)
            
            return {
                'success': True,
                'converted_files': converted_files,
                'page_count': len(images),
                'conversion_type': 'pdf_to_jpeg',
                'settings': {
                    'dpi': dpi,
                    'format': 'JPEG',
                    'quality': options['quality']
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'PDF to JPEG conversion failed: {str(e)}'}
    
    def _convert_tiff_to_png(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TIFF to PNG"""
        try:
            converted_files = []
            
            with Image.open(file_path) as img:
                max_pages = options['max_pages']
                
                for page_num in range(max_pages):
                    try:
                        if page_num > 0:
                            img.seek(page_num)
                        
                        # Process current page
                        processed_img = img.copy()
                        
                        # Convert mode if necessary
                        if processed_img.mode not in ('RGB', 'RGBA', 'L'):
                            processed_img = processed_img.convert('RGB')
                        
                        # Save as PNG
                        temp_dir = tempfile.mkdtemp()
                        output_path = os.path.join(temp_dir, f'page_{page_num + 1}.png')
                        processed_img.save(output_path, 'PNG')
                        converted_files.append(output_path)
                        
                    except EOFError:
                        break  # No more pages
                    except Exception as e:
                        logger.warning(f"Error converting TIFF page {page_num + 1}: {e}")
                        continue
            
            return {
                'success': True,
                'converted_files': converted_files,
                'page_count': len(converted_files),
                'conversion_type': 'tiff_to_png',
                'settings': {
                    'format': 'PNG',
                    'page_count': len(converted_files)
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'TIFF to PNG conversion failed: {str(e)}'}
    
    def _convert_tiff_to_jpeg(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TIFF to JPEG"""
        try:
            converted_files = []
            quality_settings = self.quality_settings[options['quality']]
            
            with Image.open(file_path) as img:
                max_pages = options['max_pages']
                
                for page_num in range(max_pages):
                    try:
                        if page_num > 0:
                            img.seek(page_num)
                        
                        # Process current page
                        processed_img = img.copy()
                        
                        # Convert to RGB for JPEG
                        if processed_img.mode == 'RGBA':
                            background = Image.new('RGB', processed_img.size, options['background_color'])
                            background.paste(processed_img, mask=processed_img.split()[-1])
                            processed_img = background
                        elif processed_img.mode not in ('RGB', 'L'):
                            processed_img = processed_img.convert('RGB')
                        
                        # Save as JPEG
                        temp_dir = tempfile.mkdtemp()
                        output_path = os.path.join(temp_dir, f'page_{page_num + 1}.jpg')
                        processed_img.save(output_path, 'JPEG', quality=quality_settings['quality'], optimize=options['optimize_size'])
                        converted_files.append(output_path)
                        
                    except EOFError:
                        break  # No more pages
                    except Exception as e:
                        logger.warning(f"Error converting TIFF page {page_num + 1}: {e}")
                        continue
            
            return {
                'success': True,
                'converted_files': converted_files,
                'page_count': len(converted_files),
                'conversion_type': 'tiff_to_jpeg',
                'settings': {
                    'format': 'JPEG',
                    'quality': options['quality'],
                    'page_count': len(converted_files)
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'TIFF to JPEG conversion failed: {str(e)}'}
    
    def _convert_image_to_jpeg(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert image (PNG) to JPEG"""
        try:
            quality_settings = self.quality_settings[options['quality']]
            
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, options['background_color'])
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Optimize if requested
                if options['optimize_size'] and img.mode == 'RGB':
                    # Apply compression optimizations
                    img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
                    img = img.convert('RGB')
                
                # Save as JPEG
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, 'converted.jpg')
                img.save(output_path, 'JPEG', quality=quality_settings['quality'], optimize=True)
                
                return {
                    'success': True,
                    'converted_files': [output_path],
                    'page_count': 1,
                    'conversion_type': 'png_to_jpeg',
                    'settings': {
                        'format': 'JPEG',
                        'quality': options['quality'],
                        'original_mode': img.mode
                    }
                }
                
        except Exception as e:
            return {'success': False, 'error': f'Image to JPEG conversion failed: {str(e)}'}
    
    def _convert_jpeg_to_png(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JPEG to PNG"""
        try:
            with Image.open(file_path) as img:
                # Ensure RGB mode for PNG
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                # Save as PNG
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, 'converted.png')
                img.save(output_path, 'PNG', optimize=options['optimize_size'])
                
                return {
                    'success': True,
                    'converted_files': [output_path],
                    'page_count': 1,
                    'conversion_type': 'jpeg_to_png',
                    'settings': {
                        'format': 'PNG',
                        'original_mode': img.mode
                    }
                }
                
        except Exception as e:
            return {'success': False, 'error': f'JPEG to PNG conversion failed: {str(e)}'}
    
    def _convert_jpeg_to_jpg(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JPEG to JPG (quality optimization)"""
        try:
            quality_settings = self.quality_settings[options['quality']]
            
            with Image.open(file_path) as img:
                # Ensure RGB mode
                if img.mode not in ('RGB',):
                    img = img.convert('RGB')
                
                # Save with specified quality
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, 'optimized.jpg')
                img.save(output_path, 'JPEG', quality=quality_settings['quality'], optimize=True)
                
                return {
                    'success': True,
                    'converted_files': [output_path],
                    'page_count': 1,
                    'conversion_type': 'jpeg_to_jpg',
                    'settings': {
                        'format': 'JPEG',
                        'quality': options['quality'],
                        'optimized': True
                    }
                }
                
        except Exception as e:
            return {'success': False, 'error': f'JPEG optimization failed: {str(e)}'}
    
    def optimize_for_processing(self, file_path: str, source_format: DocumentFormat, 
                              target_format: DocumentFormat = None) -> Dict[str, Any]:
        """
        Optimize document for processing (OCR/analysis)
        
        Args:
            file_path: Path to document
            source_format: Source format
            target_format: Target format (optional)
            
        Returns:
            Optimization results
        """
        try:
            optimization_result = {
                'success': True,
                'original_file': file_path,
                'optimized_files': [],
                'optimization_type': 'processing_optimization',
                'settings_used': {}
            }
            
            if source_format == DocumentFormat.PDF:
                # Convert PDF to high-quality PNG for OCR
                result = self.convert_document(file_path, source_format, DocumentFormat.PNG, 
                                            quality='high', dpi=300)
                if result['success']:
                    optimization_result['optimized_files'] = result['converted_files']
                    optimization_result['settings_used'] = result['settings']
                    optimization_result['conversion_result'] = result
            
            elif source_format == DocumentFormat.TIFF:
                # Convert TIFF to PNG if needed
                if target_format:
                    result = self.convert_document(file_path, source_format, target_format, 
                                                quality='high', dpi=300)
                    if result['success']:
                        optimization_result['optimized_files'] = result['converted_files']
                        optimization_result['settings_used'] = result['settings']
                        optimization_result['conversion_result'] = result
                else:
                    # Just validate TIFF
                    if self.tiff_processor:
                        tiff_info = self.tiff_processor._load_and_validate_tiff(file_path)
                        optimization_result['tiff_info'] = tiff_info
                        optimization_result['needs_conversion'] = False
            
            elif source_format in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.JPG]:
                # Optimize image for processing
                if self.image_processor:
                    # Use image processor's OCR optimization
                    image_info = self.image_processor._load_and_validate_image(file_path)
                    optimized_path = self.image_processor._optimize_for_ocr(file_path, image_info)
                    
                    if optimized_path != file_path:
                        optimization_result['optimized_files'] = [optimized_path]
                        optimization_result['needs_conversion'] = False
                        optimization_result['optimization_method'] = 'image_enhancement'
                    else:
                        optimization_result['optimized_files'] = [file_path]
                        optimization_result['needs_conversion'] = False
                        optimization_result['optimization_method'] = 'no_optimization_needed'
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Error optimizing document for processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_file': file_path,
                'optimized_files': []
            }
    
    def get_conversion_cost(self, source_format: DocumentFormat, 
                          target_format: DocumentFormat) -> Dict[str, Any]:
        """Estimate conversion cost and complexity"""
        conversion_cost = {
            'estimated_time': 'unknown',
            'complexity': 'medium',
            'quality_loss': 'none',
            'supported': False
        }
        
        if not self.can_convert(source_format, target_format):
            conversion_cost['complexity'] = 'unsupported'
            return conversion_cost
        
        # PDF conversions are typically slower
        if source_format == DocumentFormat.PDF:
            conversion_cost.update({
                'estimated_time': 'slow',
                'complexity': 'high',
                'quality_loss': 'minimal'
            })
        # TIFF multi-page conversions
        elif source_format == DocumentFormat.TIFF:
            conversion_cost.update({
                'estimated_time': 'medium',
                'complexity': 'medium',
                'quality_loss': 'none'
            })
        # Simple image format conversions
        else:
            conversion_cost.update({
                'estimated_time': 'fast',
                'complexity': 'low',
                'quality_loss': 'none'
            })
        
        conversion_cost['supported'] = True
        return conversion_cost
    
    def cleanup_conversion_files(self, conversion_result: Dict[str, Any]) -> int:
        """Clean up temporary conversion files"""
        cleaned_count = 0
        
        try:
            if conversion_result.get('success') and 'converted_files' in conversion_result:
                for file_path in conversion_result['converted_files']:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Error cleaning up conversion file {file_path}: {e}")
                
                # Clean up directories
                dirs_to_clean = set()
                for file_path in conversion_result['converted_files']:
                    dirs_to_clean.add(os.path.dirname(file_path))
                
                for dir_path in dirs_to_clean:
                    try:
                        if os.path.exists(dir_path) and not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except Exception:
                        continue  # Directory not empty or other error
                        
        except Exception as e:
            logger.error(f"Error cleaning up conversion files: {e}")
        
        return cleaned_count


def get_document_converter() -> DocumentConverter:
    """Get a singleton document converter instance"""
    return DocumentConverter()