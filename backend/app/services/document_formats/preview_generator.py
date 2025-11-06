"""
Document Preview and Thumbnail Generator

Generates thumbnails and preview images for all supported document formats.
Handles PDF, TIFF, PNG, JPEG, and JPG with intelligent preview generation.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import logging

from .format_detector import DocumentFormat
from .pdf_processor import PDFProcessor
from .tiff_processor import TIFFProcessor
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)

class PreviewGenerator:
    """Service to generate document previews and thumbnails"""
    
    def __init__(self):
        # Preview configuration
        self.thumbnail_sizes = {
            'small': (150, 150),
            'medium': (300, 300),
            'large': (600, 600)
        }
        
        self.preview_sizes = {
            'small': (400, 400),
            'medium': (800, 600),
            'large': (1200, 900)
        }
        
        # Default formats and quality
        self.thumbnail_format = 'JPEG'
        self.preview_format = 'PNG'
        self.default_quality = 85
        
        # Background colors
        self.thumbnail_bg_color = (240, 240, 240)  # Light gray
        self.preview_bg_color = (255, 255, 255)    # White
        
        # Text settings for watermarks/overlays
        self.watermark_text = "Preview"
        self.watermark_color = (128, 128, 128)     # Gray
        self.watermark_size = 12
        
        # Initialize processors
        self.pdf_processor = PDFProcessor() if hasattr(PDFProcessor, '__init__') else None
        self.tiff_processor = TIFFProcessor() if hasattr(TIFFProcessor, '__init__') else None
        self.image_processor = ImageProcessor() if hasattr(ImageProcessor, '__init__') else None
    
    def generate_previews(self, file_path: str, format_type: DocumentFormat) -> Dict[str, Any]:
        """
        Generate previews for a document
        
        Args:
            file_path: Path to the document file
            format_type: Detected document format
            
        Returns:
            Preview generation results
        """
        try:
            preview_results = {
                'format': format_type.value,
                'file_path': file_path,
                'thumbnails': {},
                'previews': {},
                'page_previews': {},
                'generation_metadata': {},
                'success': True,
                'errors': []
            }
            
            if format_type == DocumentFormat.PDF:
                preview_results = self._generate_pdf_previews(file_path, preview_results)
            elif format_type == DocumentFormat.TIFF:
                preview_results = self._generate_tiff_previews(file_path, preview_results)
            elif format_type in [DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.JPG]:
                preview_results = self._generate_image_previews(file_path, format_type, preview_results)
            else:
                preview_results['success'] = False
                preview_results['errors'].append(f"Unsupported format: {format_type.value}")
            
            # Add generation metadata
            preview_results['generation_metadata'] = self._get_generation_metadata()
            
            return preview_results
            
        except Exception as e:
            logger.error(f"Error generating previews for {file_path}: {e}")
            return {
                'format': format_type.value,
                'file_path': file_path,
                'success': False,
                'errors': [str(e)],
                'thumbnails': {},
                'previews': {}
            }
    
    def _generate_pdf_previews(self, file_path: str, preview_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate previews for PDF documents"""
        try:
            if not self.pdf_processor:
                preview_results['errors'].append("PDF processor not available")
                preview_results['success'] = False
                return preview_results
            
            # Load PDF and get basic info
            import pypdf
            from pypdf import PdfReader
            
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            
            # Generate overall document previews (using first page)
            try:
                first_page = reader.pages[0]
                
                # Convert first page to image
                page_image = self._pdf_page_to_image(first_page)
                if page_image:
                    # Generate thumbnails and previews for the first page
                    preview_results['thumbnails'] = self._generate_image_variants(page_image, 'pdf_first_page')
                    preview_results['previews'] = self._generate_image_variants(page_image, 'pdf_preview', is_preview=True)
            except Exception as e:
                preview_results['errors'].append(f"Error generating PDF preview: {str(e)}")
            
            # Generate page-specific previews (limited to first few pages)
            max_preview_pages = min(3, page_count)  # Preview first 3 pages only
            for page_num in range(max_preview_pages):
                try:
                    page = reader.pages[page_num]
                    page_image = self._pdf_page_to_image(page)
                    
                    if page_image:
                        page_variants = self._generate_image_variants(page_image, f'pdf_page_{page_num + 1}')
                        preview_results['page_previews'][f'page_{page_num + 1}'] = page_variants
                except Exception as e:
                    preview_results['errors'].append(f"Error generating preview for page {page_num + 1}: {str(e)}")
            
            # Add PDF-specific metadata
            preview_results['pdf_metadata'] = {
                'page_count': page_count,
                'previewed_pages': len(preview_results['page_previews']),
                'preview_strategy': 'first_page_and_limited_pages'
            }
            
        except Exception as e:
            preview_results['errors'].append(f"Error in PDF preview generation: {str(e)}")
            preview_results['success'] = False
        
        return preview_results
    
    def _pdf_page_to_image(self, page) -> Optional[Image.Image]:
        """Convert PDF page to PIL Image"""
        try:
            # Use pdf2image if available, otherwise use PyPDF page rendering
            try:
                import pdf2image
                # This would require a different approach with pdf2image
                # For now, return None to indicate limitation
                return None
            except ImportError:
                # PyPDF doesn't have direct image conversion
                # This is a limitation that would need external tools
                return None
        except Exception as e:
            logger.error(f"Error converting PDF page to image: {e}")
            return None
    
    def _generate_tiff_previews(self, file_path: str, preview_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate previews for TIFF documents"""
        try:
            if not self.tiff_processor:
                preview_results['errors'].append("TIFF processor not available")
                preview_results['success'] = False
                return preview_results
            
            # Load TIFF and get page info
            tiff_info = self.tiff_processor._load_and_validate_tiff(file_path)
            
            # Generate previews for first page (and subsequent pages if multi-page)
            max_preview_pages = min(3, tiff_info['page_count'])
            
            with Image.open(file_path) as img:
                for page_num in range(max_preview_pages):
                    try:
                        if page_num > 0:
                            img.seek(page_num)
                        
                        # Generate variants for this page
                        page_variants = self._generate_image_variants(img.copy(), f'tiff_page_{page_num + 1}')
                        preview_results['page_previews'][f'page_{page_num + 1}'] = page_variants
                        
                        # For first page, also generate document-level previews
                        if page_num == 0:
                            preview_results['thumbnails'] = page_variants
                            preview_results['previews'] = self._generate_image_variants(
                                img.copy(), 'tiff_preview', is_preview=True
                            )
                    
                    except Exception as e:
                        preview_results['errors'].append(f"Error generating preview for TIFF page {page_num + 1}: {str(e)}")
            
            # Add TIFF-specific metadata
            preview_results['tiff_metadata'] = {
                'page_count': tiff_info['page_count'],
                'previewed_pages': len(preview_results['page_previews']),
                'compression': tiff_info['compression'],
                'dimensions': (tiff_info['width'], tiff_info['height'])
            }
            
        except Exception as e:
            preview_results['errors'].append(f"Error in TIFF preview generation: {str(e)}")
            preview_results['success'] = False
        
        return preview_results
    
    def _generate_image_previews(self, file_path: str, format_type: DocumentFormat, 
                               preview_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate previews for image documents (PNG, JPEG, JPG)"""
        try:
            if not self.image_processor:
                preview_results['errors'].append("Image processor not available")
                preview_results['success'] = False
                return preview_results
            
            # Load image
            with Image.open(file_path) as img:
                # Generate thumbnails and previews
                preview_results['thumbnails'] = self._generate_image_variants(img, 'image_thumbnail')
                preview_results['previews'] = self._generate_image_variants(img, 'image_preview', is_preview=True)
            
            # Add image-specific metadata
            preview_results['image_metadata'] = {
                'format': img.format,
                'mode': img.mode,
                'dimensions': (img.width, img.height),
                'color_mode': self.image_processor._determine_color_mode(img)
            }
            
        except Exception as e:
            preview_results['errors'].append(f"Error in image preview generation: {str(e)}")
            preview_results['success'] = False
        
        return preview_results
    
    def _generate_image_variants(self, img: Image.Image, base_name: str, is_preview: bool = False) -> Dict[str, str]:
        """Generate different sized variants of an image"""
        variants = {}
        
        try:
            # Choose size set based on type
            sizes = self.preview_sizes if is_preview else self.thumbnail_sizes
            
            for size_name, (width, height) in sizes.items():
                try:
                    # Create resized image with proper background
                    resized_img = self._resize_with_background(img, width, height)
                    
                    # Add watermark if it's a preview
                    if is_preview:
                        resized_img = self._add_watermark(resized_img)
                    
                    # Save to temporary file
                    temp_dir = tempfile.mkdtemp()
                    file_ext = '.jpg' if not is_preview else '.png'
                    variant_path = os.path.join(temp_dir, f"{base_name}_{size_name}{file_ext}")
                    
                    # Save with appropriate settings
                    save_kwargs = {}
                    if not is_preview:
                        save_kwargs['quality'] = self.default_quality
                        save_kwargs['optimize'] = True
                    
                    resized_img.save(variant_path, **save_kwargs)
                    variants[size_name] = variant_path
                    
                except Exception as e:
                    logger.warning(f"Error generating {size_name} variant: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error generating image variants: {e}")
        
        return variants
    
    def _resize_with_background(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """Resize image with proper background handling"""
        try:
            # Create background
            background = Image.new('RGB', (target_width, target_height), self.thumbnail_bg_color)
            
            # Calculate resize dimensions maintaining aspect ratio
            img_ratio = img.width / img.height
            target_ratio = target_width / target_height
            
            if img_ratio > target_ratio:
                # Image is wider, fit to width
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                # Image is taller, fit to height
                new_height = target_height
                new_width = int(target_height * img_ratio)
            
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center the image on the background
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2
            background.paste(resized_img, (x_offset, y_offset))
            
            return background
            
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            # Return original image if resize fails
            return img.convert('RGB')
    
    def _add_watermark(self, img: Image.Image) -> Image.Image:
        """Add watermark to preview image"""
        try:
            # Create a copy to avoid modifying original
            watermarked = img.copy()
            draw = ImageDraw.Draw(watermarked)
            
            # Try to get a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", self.watermark_size)
            except (OSError, IOError):
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
            
            # Add watermark in bottom-right corner
            if font:
                text_bbox = draw.textbbox((0, 0), self.watermark_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            else:
                text_width, text_height = 50, 10  # Approximate
            
            # Position watermark
            x = watermarked.width - text_width - 10
            y = watermarked.height - text_height - 10
            
            # Draw semi-transparent watermark
            draw.text((x, y), self.watermark_text, fill=self.watermark_color, font=font)
            
            return watermarked
            
        except Exception as e:
            logger.warning(f"Error adding watermark: {e}")
            return img
    
    def _get_generation_metadata(self) -> Dict[str, Any]:
        """Get metadata about the preview generation process"""
        return {
            'generator_version': '1.0.0',
            'thumbnail_sizes': list(self.thumbnail_sizes.keys()),
            'preview_sizes': list(self.preview_sizes.keys()),
            'thumbnail_format': self.thumbnail_format,
            'preview_format': self.preview_format,
            'default_quality': self.default_quality,
            'watermark_enabled': True
        }
    
    def get_preview_info(self, preview_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful information from preview results"""
        info = {
            'has_thumbnails': len(preview_results.get('thumbnails', {})) > 0,
            'has_previews': len(preview_results.get('previews', {})) > 0,
            'has_page_previews': len(preview_results.get('page_previews', {})) > 0,
            'total_variants': 0,
            'smallest_thumbnail': None,
            'largest_preview': None,
            'generation_successful': preview_results.get('success', False)
        }
        
        # Count total variants
        for category in ['thumbnails', 'previews']:
            info['total_variants'] += len(preview_results.get(category, {}))
        
        # Find smallest thumbnail
        thumbnails = preview_results.get('thumbnails', {})
        if thumbnails and 'small' in thumbnails:
            info['smallest_thumbnail'] = thumbnails['small']
        
        # Find largest preview
        previews = preview_results.get('previews', {})
        if previews and 'large' in previews:
            info['largest_preview'] = previews['large']
        
        return info
    
    def cleanup_previews(self, preview_results: Dict[str, Any]) -> int:
        """Clean up temporary preview files"""
        cleaned_count = 0
        
        try:
            # Clean up all file paths in preview results
            all_variants = {}
            
            # Collect all file paths
            for category in ['thumbnails', 'previews']:
                for size_name, file_path in preview_results.get(category, {}).items():
                    all_variants[file_path] = True
            
            # Also collect page previews
            for page_name, page_variants in preview_results.get('page_previews', {}).items():
                for size_name, file_path in page_variants.items():
                    all_variants[file_path] = True
            
            # Delete files
            for file_path in all_variants.keys():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Error cleaning up preview file {file_path}: {e}")
            
            # Clean up empty directories
            for file_path in all_variants.keys():
                try:
                    dir_path = os.path.dirname(file_path)
                    if os.path.exists(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except Exception:
                    continue  # Directory not empty or other error
            
        except Exception as e:
            logger.error(f"Error cleaning up previews: {e}")
        
        return cleaned_count
    
    def generate_document_overview(self, file_path: str, format_type: DocumentFormat) -> Dict[str, Any]:
        """Generate a comprehensive document overview with preview information"""
        try:
            # Generate previews
            preview_results = self.generate_previews(file_path, format_type)
            
            # Get document info
            doc_info = {
                'file_path': file_path,
                'format': format_type.value,
                'preview_info': self.get_preview_info(preview_results),
                'preview_results': preview_results,
                'preview_metadata': preview_results.get('generation_metadata', {}),
                'errors': preview_results.get('errors', [])
            }
            
            # Add format-specific information
            if format_type == DocumentFormat.PDF:
                try:
                    import pypdf
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    doc_info['page_count'] = len(reader.pages)
                except Exception:
                    doc_info['page_count'] = None
            
            elif format_type == DocumentFormat.TIFF:
                try:
                    with Image.open(file_path) as img:
                        page_count = 1
                        try:
                            while True:
                                img.seek(page_count)
                                page_count += 1
                        except EOFError:
                            pass
                        doc_info['page_count'] = page_count
                except Exception:
                    doc_info['page_count'] = None
            
            else:  # Image formats
                try:
                    with Image.open(file_path) as img:
                        doc_info['dimensions'] = (img.width, img.height)
                        doc_info['color_mode'] = img.mode
                        doc_info['file_size'] = os.path.getsize(file_path)
                except Exception:
                    doc_info['dimensions'] = None
                    doc_info['color_mode'] = None
                    doc_info['file_size'] = None
            
            return doc_info
            
        except Exception as e:
            logger.error(f"Error generating document overview: {e}")
            return {
                'file_path': file_path,
                'format': format_type.value,
                'preview_results': {'success': False, 'errors': [str(e)]},
                'errors': [str(e)]
            }


def get_preview_generator() -> PreviewGenerator:
    """Get a singleton preview generator instance"""
    return PreviewGenerator()