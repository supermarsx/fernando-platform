"""
TIFF Document Processor

Handles TIFF format processing with multi-page support and various compression types.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageOps
import logging

from .format_detector import DocumentFormat
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)

class TIFFProcessor:
    """Service to process TIFF documents"""
    
    def __init__(self):
        self.supported = True  # PIL supports TIFF
        self.max_file_size = 100 * 1024 * 1024  # 100MB for TIFF
        self.max_pages = 100  # Maximum pages to process
        self.max_dimensions = (8000, 8000)  # Max width/height for TIFF
        
        # TIFF-specific settings
        self.compression_types = ['LZW', 'ZIP', 'CCITT', 'JPEG', 'None']
        self.supported_compressions = ['LZW', 'ZIP', 'None']  # Lossless compressions
        
        # Processing configuration
        self.extract_text_layers = True
        self.preserve_original_resolution = True
        self.convert_for_ocr = True
    
    def process_tiff(self, file_path: str) -> Dict[str, Any]:
        """
        Process a TIFF document
        
        Args:
            file_path: Path to the TIFF file
            
        Returns:
            Processing results including pages, metadata, and text content
        """
        try:
            # Load and validate TIFF
            tiff_info = self._load_and_validate_tiff(file_path)
            
            # Extract metadata
            metadata = self._extract_tiff_metadata(file_path, tiff_info)
            
            # Process pages
            pages = self._process_pages(file_path, tiff_info)
            
            # Extract text content if available
            text_content = ""
            if self.extract_text_layers:
                text_content = self._extract_text_layers(pages)
            
            # Calculate statistics
            stats = self._calculate_tiff_stats(tiff_info, pages, text_content)
            
            return {
                'format': DocumentFormat.TIFF.value,
                'file_path': file_path,
                'tiff_info': tiff_info,
                'metadata': metadata,
                'pages': pages,
                'text_content': text_content,
                'statistics': stats,
                'is_multi_page': tiff_info['is_multi_page'],
                'page_count': tiff_info['page_count'],
                'confidence': stats.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error processing TIFF {file_path}: {e}")
            raise
    
    def _load_and_validate_tiff(self, file_path: str) -> Dict[str, Any]:
        """Load TIFF and extract basic information"""
        try:
            with Image.open(file_path) as img:
                tiff_info = {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'is_multi_page': False,
                    'page_count': 1,
                    'compression': 'unknown',
                    'dpi': self._get_tiff_dpi(img),
                    'color_mode': self._determine_color_mode(img),
                    'bits_per_sample': self._get_bits_per_sample(img),
                    'samples_per_pixel': self._get_samples_per_pixel(img),
                    'file_size_bytes': os.path.getsize(file_path),
                    'has_transparency': False,
                    'photometric_interpretation': 'unknown',
                    'planar_configuration': 'unknown'
                }
                
                # Check if multi-page
                try:
                    img.seek(1)  # Try to seek to second page
                    tiff_info['is_multi_page'] = True
                    tiff_info['page_count'] = self._count_tiff_pages(file_path)
                    img.seek(0)  # Return to first page
                except EOFError:
                    tiff_info['is_multi_page'] = False
                
                # Extract TIFF-specific metadata
                self._extract_tiff_specific_metadata(img, tiff_info)
                
                # Validate TIFF
                validation = self._validate_tiff_structure(tiff_info)
                tiff_info.update(validation)
                
                return tiff_info
                
        except Exception as e:
            logger.error(f"Error loading TIFF {file_path}: {e}")
            raise
    
    def _get_tiff_dpi(self, img: Image.Image) -> Optional[tuple]:
        """Get TIFF DPI information"""
        try:
            dpi = img.info.get('dpi')
            if dpi and len(dpi) >= 2:
                return dpi
            
            # Check for resolution tags
            resolution = img.info.get('resolution')
            if resolution:
                return (resolution, resolution)
                
        except Exception as e:
            logger.debug(f"Error getting TIFF DPI: {e}")
        
        return None
    
    def _determine_color_mode(self, img: Image.Image) -> str:
        """Determine TIFF color mode"""
        if img.mode == '1':
            return 'black_white'
        elif img.mode == 'L':
            return 'grayscale'
        elif img.mode == 'P':
            return 'palette'
        elif img.mode == 'RGB':
            return 'rgb_color'
        elif img.mode == 'RGBA':
            return 'rgb_alpha'
        elif img.mode in ('CMYK', 'YCbCr', 'LAB'):
            return 'color_space'
        elif img.mode in ('I', 'F'):
            return 'continuous_tone'
        else:
            return 'unknown'
    
    def _get_bits_per_sample(self, img: Image.Image) -> Optional[int]:
        """Get bits per sample from TIFF info"""
        try:
            return img.info.get('bits_per_sample')
        except Exception:
            return None
    
    def _get_samples_per_pixel(self, img: Image.Image) -> Optional[int]:
        """Get samples per pixel from TIFF info"""
        try:
            return img.info.get('samples_per_pixel')
        except Exception:
            return None
    
    def _extract_tiff_specific_metadata(self, img: Image.Image, tiff_info: Dict[str, Any]):
        """Extract TIFF-specific metadata"""
        try:
            # Compression type
            compression = img.info.get('compression', 'raw')
            tiff_info['compression'] = compression
            
            # Photometric interpretation
            photometric = img.info.get('photometric')
            if photometric:
                photometric_map = {
                    0: 'white_is_zero',
                    1: 'black_is_zero',
                    2: 'rgb',
                    3: 'palette',
                    4: 'transparency_mask',
                    5: 'cmyk',
                    6: 'YCbCr',
                    7: 'cielab',
                    8: 'icclab',
                    9: 'itulab'
                }
                tiff_info['photometric_interpretation'] = photometric_map.get(photometric, 'unknown')
            
            # Planar configuration
            planar = img.info.get('planar_config')
            if planar:
                tiff_info['planar_configuration'] = 'planar' if planar == 2 else 'contiguous'
            
            # Transparency
            if img.mode in ('RGBA', 'LA') or 'transparency' in img.info:
                tiff_info['has_transparency'] = True
            
            # ICC Profile
            if 'icc_profile' in img.info:
                tiff_info['has_icc_profile'] = True
            
        except Exception as e:
            logger.debug(f"Error extracting TIFF metadata: {e}")
    
    def _count_tiff_pages(self, file_path: str) -> int:
        """Count number of pages in multi-page TIFF"""
        try:
            with Image.open(file_path) as img:
                page_count = 1
                try:
                    while True:
                        img.seek(page_count)
                        page_count += 1
                except EOFError:
                    pass
                return page_count
        except Exception:
            return 1
    
    def _validate_tiff_structure(self, tiff_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate TIFF structure and quality"""
        validation = {
            'is_valid_tiff': True,
            'is_processable': True,
            'issues': [],
            'warnings': [],
            'compression_supported': True,
            'dimensions_valid': True,
            'resolution_adequate': True
        }
        
        # Check compression support
        compression = tiff_info['compression']
        if compression.lower() not in [c.lower() for c in self.supported_compressions]:
            if compression.lower() != 'raw' and compression.lower() != 'none':
                validation['compression_supported'] = False
                validation['warnings'].append(
                    f"TIFF compression {compression} may not be fully supported"
                )
        
        # Check dimensions
        width, height = tiff_info['width'], tiff_info['height']
        if width > self.max_dimensions[0] or height > self.max_dimensions[1]:
            validation['dimensions_valid'] = False
            validation['issues'].append(
                f"TIFF dimensions {width}x{height} exceed maximum {self.max_dimensions}"
            )
        
        # Check resolution
        dpi = tiff_info['dpi']
        if dpi:
            horizontal_dpi, vertical_dpi = dpi
            if horizontal_dpi < 72 or vertical_dpi < 72:
                validation['resolution_adequate'] = False
                validation['warnings'].append(
                    f"TIFF resolution {horizontal_dpi}x{vertical_dpi} DPI may be too low"
                )
        
        # Check file size
        file_size = tiff_info['file_size_bytes']
        if file_size > self.max_file_size:
            validation['is_processable'] = False
            validation['issues'].append(
                f"TIFF file size {file_size} bytes exceeds maximum {self.max_file_size}"
            )
        
        # Check page count
        if tiff_info['page_count'] > self.max_pages:
            validation['warnings'].append(
                f"TIFF has {tiff_info['page_count']} pages, only first {self.max_pages} will be processed"
            )
        
        return validation
    
    def _extract_tiff_metadata(self, file_path: str, tiff_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive TIFF metadata"""
        try:
            metadata = {
                'file_info': {
                    'file_path': file_path,
                    'file_size_bytes': tiff_info['file_size_bytes'],
                    'creation_date': None,  # Would need additional library for EXIF
                    'modification_date': os.path.getmtime(file_path)
                },
                'technical_specs': {
                    'compression': tiff_info['compression'],
                    'bits_per_sample': tiff_info['bits_per_sample'],
                    'samples_per_pixel': tiff_info['samples_per_pixel'],
                    'color_mode': tiff_info['color_mode'],
                    'photometric_interpretation': tiff_info['photometric_interpretation'],
                    'planar_configuration': tiff_info['planar_configuration'],
                    'has_icc_profile': tiff_info.get('has_icc_profile', False)
                },
                'image_properties': {
                    'dimensions': (tiff_info['width'], tiff_info['height']),
                    'dpi': tiff_info['dpi'],
                    'color_space': self._map_color_space(tiff_info),
                    'has_transparency': tiff_info['has_transparency']
                },
                'processing_info': {
                    'is_multi_page': tiff_info['is_multi_page'],
                    'page_count': tiff_info['page_count'],
                    'max_pages_processed': min(tiff_info['page_count'], self.max_pages)
                }
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting TIFF metadata: {e}")
            return {}
    
    def _map_color_space(self, tiff_info: Dict[str, Any]) -> str:
        """Map TIFF color space to standard terminology"""
        color_modes = {
            'black_white': 'Monochrome',
            'grayscale': 'Grayscale',
            'palette': 'Palette Color',
            'rgb_color': 'RGB Color',
            'rgb_alpha': 'RGB with Alpha',
            'color_space': 'Special Color Space',
            'continuous_tone': 'Continuous Tone',
            'unknown': 'Unknown'
        }
        
        return color_modes.get(tiff_info['color_mode'], 'Unknown')
    
    def _process_pages(self, file_path: str, tiff_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process all pages of the TIFF document"""
        pages = []
        
        try:
            with Image.open(file_path) as img:
                max_pages = min(tiff_info['page_count'], self.max_pages)
                
                for page_num in range(max_pages):
                    try:
                        # Seek to page
                        img.seek(page_num)
                        
                        # Process page
                        page_info = self._process_single_page(img, page_num + 1)
                        pages.append(page_info)
                        
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num + 1}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error processing TIFF pages: {e}")
        
        return pages
    
    def _process_single_page(self, img: Image.Image, page_number: int) -> Dict[str, Any]:
        """Process a single TIFF page"""
        try:
            page_info = {
                'page_number': page_number,
                'dimensions': (img.width, img.height),
                'mode': img.mode,
                'format': img.format,
                'processed_image_path': None,
                'ocr_ready_path': None,
                'page_metadata': {}
            }
            
            # Get page-specific metadata
            if hasattr(img, 'tag_v2'):
                # Extract EXIF/TIFF tags
                tag_v2 = img.tag_v2
                page_info['page_metadata'] = {
                    'x_resolution': tag_v2.get(282),  # XResolution
                    'y_resolution': tag_v2.get(283),  # YResolution
                    'resolution_unit': tag_v2.get(296),  # ResolutionUnit
                    'software': tag_v2.get(305),  # Software
                    'date_time': tag_v2.get(306),  # DateTime
                }
            
            # Process image for OCR if needed
            if self.convert_for_ocr:
                page_info['ocr_ready_path'] = self._convert_page_for_ocr(img, page_number)
            
            return page_info
            
        except Exception as e:
            logger.error(f"Error processing page {page_number}: {e}")
            return {
                'page_number': page_number,
                'error': str(e),
                'processed_successfully': False
            }
    
    def _convert_page_for_ocr(self, img: Image.Image, page_number: int) -> str:
        """Convert TIFF page to OCR-ready format"""
        try:
            # Create a copy for processing
            processed_img = img.copy()
            
            # Convert to appropriate mode for OCR
            if processed_img.mode not in ('RGB', 'L'):
                if processed_img.mode == 'P':
                    processed_img = processed_img.convert('RGB')
                elif processed_img.mode == 'RGBA':
                    background = Image.new('RGB', processed_img.size, (255, 255, 255))
                    background.paste(processed_img, mask=processed_img.split()[-1])
                    processed_img = background
                else:
                    processed_img = processed_img.convert('RGB')
            
            # Enhance for OCR
            processed_img = self._enhance_for_ocr(processed_img)
            
            # Save processed image
            temp_dir = tempfile.mkdtemp()
            processed_path = os.path.join(temp_dir, f'tiff_page_{page_number}.png')
            
            processed_img.save(processed_path, 'PNG', dpi=(300, 300))
            
            return processed_path
            
        except Exception as e:
            logger.error(f"Error converting page {page_number} for OCR: {e}")
            return None
    
    def _enhance_for_ocr(self, img: Image.Image) -> Image.Image:
        """Enhance image for better OCR results"""
        try:
            # Convert to grayscale for better OCR
            if img.mode != 'L':
                img = ImageOps.grayscale(img)
            
            # Enhance contrast
            img = ImageOps.autocontrast(img)
            
            # Apply slight sharpening
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
            
            return img
            
        except Exception as e:
            logger.warning(f"Error enhancing image for OCR: {e}")
            return img
    
    def _extract_text_layers(self, pages: List[Dict[str, Any]]) -> str:
        """Extract text content from TIFF pages (if any)"""
        try:
            text_content = ""
            
            # Note: Standard TIFF doesn't contain text layers like PDF
            # This is a placeholder for potential future enhancements
            # or for TIFFs that might contain OCR text in metadata
            
            for page_info in pages:
                page_num = page_info.get('page_number', 0)
                text_content += f"\n--- Page {page_num} ---\n"
                text_content += "[TIFF pages typically contain images only, no embedded text]\n"
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting text layers: {e}")
            return ""
    
    def _calculate_tiff_stats(self, tiff_info: Dict[str, Any], 
                            pages: List[Dict[str, Any]], 
                            text_content: str) -> Dict[str, Any]:
        """Calculate TIFF processing statistics"""
        try:
            # Base confidence
            confidence = 0.6  # TIFFs typically require OCR
            
            # Adjust based on resolution
            dpi = tiff_info['dpi']
            if dpi:
                horizontal_dpi, _ = dpi
                if horizontal_dpi >= 300:
                    confidence += 0.2
                elif horizontal_dpi >= 200:
                    confidence += 0.1
            
            # Adjust based on dimensions
            if tiff_info['width'] >= 1000 and tiff_info['height'] >= 1000:
                confidence += 0.1
            
            # Adjust based on compression
            compression = tiff_info['compression'].lower()
            if compression in ['lzw', 'zip']:
                confidence += 0.1
            elif compression in ['jpeg']:
                confidence -= 0.1  # Lossy compression might reduce quality
            
            # Cap confidence
            confidence = min(confidence, 1.0)
            
            return {
                'total_pages': len(pages),
                'text_content_length': len(text_content),
                'has_text_content': len(text_content.strip()) > 50,
                'compression_type': tiff_info['compression'],
                'color_mode': tiff_info['color_mode'],
                'multi_page_processing': tiff_info['is_multi_page'],
                'average_confidence': confidence,
                'processing_difficulty': self._assess_processing_difficulty(tiff_info),
                'recommended_ocr_settings': self._get_ocr_recommendations(tiff_info)
            }
            
        except Exception as e:
            logger.error(f"Error calculating TIFF stats: {e}")
            return {'confidence': 0.6}
    
    def _assess_processing_difficulty(self, tiff_info: Dict[str, Any]) -> str:
        """Assess OCR processing difficulty"""
        difficulty_score = 0
        
        # Resolution factor
        dpi = tiff_info['dpi']
        if dpi:
            horizontal_dpi, _ = dpi
            if horizontal_dpi < 150:
                difficulty_score += 2
            elif horizontal_dpi < 200:
                difficulty_score += 1
        
        # Dimensions factor
        if tiff_info['width'] < 500 or tiff_info['height'] < 500:
            difficulty_score += 1
        
        # Color mode factor
        if tiff_info['color_mode'] == 'grayscale':
            difficulty_score -= 1  # Grayscale is easier than color
        elif tiff_info['color_mode'] == 'rgb_color':
            difficulty_score += 1
        
        # Compression factor
        compression = tiff_info['compression'].lower()
        if compression == 'jpeg':
            difficulty_score += 1
        
        if difficulty_score >= 3:
            return 'high'
        elif difficulty_score >= 1:
            return 'medium'
        else:
            return 'low'
    
    def _get_ocr_recommendations(self, tiff_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get OCR processing recommendations"""
        recommendations = {
            'engine': 'tesseract',
            'preprocessing': 'enhanced',
            'language': 'eng',
            'psm': 'auto',
            'oem': 'default'
        }
        
        # Adjust based on characteristics
        if tiff_info['color_mode'] == 'grayscale':
            recommendations['preprocessing'] = 'standard'
        elif tiff_info['color_mode'] == 'rgb_color':
            recommendations['preprocessing'] = 'enhanced'
        
        # Adjust based on compression
        compression = tiff_info['compression'].lower()
        if compression == 'jpeg':
            recommendations['preprocessing'] = 'maximum'
        
        return recommendations
    
    def validate_tiff(self, file_path: str) -> Dict[str, Any]:
        """Validate TIFF file for processing"""
        validation = {
            'is_valid_tiff': False,
            'is_processable': False,
            'is_ocr_suitable': False,
            'issues': [],
            'warnings': [],
            'compression_type': None,
            'page_count': 0,
            'dimensions': None,
            'file_size_bytes': 0
        }
        
        try:
            # Check file exists
            if not os.path.exists(file_path):
                validation['issues'].append("File does not exist")
                return validation
            
            file_size = os.path.getsize(file_path)
            validation['file_size_bytes'] = file_size
            
            if file_size == 0:
                validation['issues'].append("File is empty")
                return validation
            
            # Load and analyze TIFF
            with Image.open(file_path) as img:
                validation['is_valid_tiff'] = True
                validation['dimensions'] = (img.width, img.height)
                validation['compression_type'] = img.info.get('compression', 'unknown')
                
                # Count pages
                page_count = self._count_tiff_pages(file_path)
                validation['page_count'] = page_count
                
                # Check file size limits
                if file_size > self.max_file_size:
                    validation['issues'].append(
                        f"File size {file_size} bytes exceeds maximum {self.max_file_size}"
                    )
                    return validation
                
                # Check dimensions
                if img.width < 50 or img.height < 50:
                    validation['warnings'].append("TIFF dimensions are very small")
                
                # Check compression
                compression = validation['compression_type']
                if compression.lower() not in [c.lower() for c in self.supported_compressions + ['raw', 'none']]:
                    validation['warnings'].append(
                        f"Compression {compression} may not be fully supported"
                    )
                
                validation['is_processable'] = True
                
                # Check OCR suitability
                dpi = img.info.get('dpi')
                if dpi and min(dpi) >= 150:
                    validation['is_ocr_suitable'] = True
                elif img.width >= 800 and img.height >= 600:
                    validation['is_ocr_suitable'] = True
                
        except Exception as e:
            validation['issues'].append(f"Error validating TIFF: {str(e)}")
        
        return validation


def get_tiff_processor() -> TIFFProcessor:
    """Get a singleton TIFF processor instance"""
    return TIFFProcessor()