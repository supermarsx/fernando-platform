"""
Image Document Processor

Handles PNG, JPEG, and JPG image processing with OCR-ready optimization.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageEnhance, ImageFilter
import logging

from .format_detector import DocumentFormat

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Service to process image documents (PNG, JPEG, JPG)"""
    
    def __init__(self):
        self.supported_formats = {DocumentFormat.PNG, DocumentFormat.JPEG, DocumentFormat.JPG}
        self.max_file_size = 25 * 1024 * 1024  # 25MB for images
        self.max_dimensions = (4000, 4000)  # Max width/height
        self.target_dpi = 300  # Target DPI for OCR
        
        # Image processing configuration
        self.enhance_for_ocr = True
        self.remove_noise = True
        self.enhance_contrast = True
        
        # Supported image modes for processing
        self.supported_modes = {'RGB', 'RGBA', 'L', 'P'}
    
    def process_image(self, file_path: str) -> Dict[str, Any]:
        """
        Process an image document
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Processing results including processed image and metadata
        """
        try:
            # Load and validate image
            image_info = self._load_and_validate_image(file_path)
            
            # Optimize for OCR if needed
            processed_image_path = None
            if self.enhance_for_ocr:
                processed_image_path = self._optimize_for_ocr(file_path, image_info)
            
            # Extract image features
            features = self._extract_image_features(processed_image_path or file_path, image_info)
            
            # Calculate processing statistics
            stats = self._calculate_processing_stats(image_info, features)
            
            return {
                'format': image_info['format'],
                'original_path': file_path,
                'processed_path': processed_image_path,
                'image_info': image_info,
                'features': features,
                'statistics': stats,
                'ocr_ready': self._is_ocr_ready(image_info),
                'confidence': stats.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            raise
    
    def _load_and_validate_image(self, file_path: str) -> Dict[str, Any]:
        """Load image and extract basic information"""
        try:
            with Image.open(file_path) as img:
                # Basic image information
                image_info = {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'has_transparency': False,
                    'color_mode': 'color',
                    'file_size_bytes': os.path.getsize(file_path),
                    'aspect_ratio': img.width / img.height if img.height > 0 else 0,
                    'dpi': self._get_image_dpi(img),
                    'color_count': self._get_color_count(img),
                    'is_grayscale': img.mode == 'L',
                    'is_indexed': img.mode == 'P'
                }
                
                # Check for transparency
                if img.mode in ('RGBA', 'LA') or 'transparency' in img.info:
                    image_info['has_transparency'] = True
                
                # Determine color mode
                if img.mode == 'L':
                    image_info['color_mode'] = 'grayscale'
                elif img.mode in ('1', 'L'):
                    image_info['color_mode'] = 'black_white'
                elif img.mode in ('RGB', 'RGBA'):
                    image_info['color_mode'] = 'color'
                
                # Validate image
                validation = self._validate_image_dimensions(image_info)
                image_info.update(validation)
                
                return image_info
                
        except Exception as e:
            logger.error(f"Error loading image {file_path}: {e}")
            raise
    
    def _get_image_dpi(self, img: Image.Image) -> Optional[tuple]:
        """Get image DPI information"""
        try:
            dpi = img.info.get('dpi')
            if dpi and len(dpi) >= 2:
                return dpi
        except Exception:
            pass
        return None
    
    def _get_color_count(self, img: Image.Image) -> int:
        """Get number of unique colors in image"""
        try:
            if img.mode in ('1', 'L'):
                return 2 if img.mode == '1' else 256
            elif img.mode == 'P':
                return len(img.getcolors())
            elif img.mode in ('RGB', 'RGBA'):
                # For large images, sample to get color count
                if img.width * img.height > 1000000:  # More than 1MP
                    # Resize and count colors
                    thumb = img.copy()
                    thumb.thumbnail((100, 100))
                    colors = len(thumb.getcolors() or [])
                    return colors * 16  # Rough estimate
                else:
                    colors = len(img.getcolors() or [])
                    return colors
            else:
                return 256  # Default for unknown modes
        except Exception as e:
            logger.warning(f"Error counting colors: {e}")
            return 256
    
    def _validate_image_dimensions(self, image_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate image dimensions and quality"""
        validation = {
            'dimensions_valid': True,
            'resolution_adequate': True,
            'size_appropriate': True,
            'warnings': [],
            'issues': []
        }
        
        width, height = image_info['width'], image_info['height']
        
        # Check dimensions
        if width > self.max_dimensions[0] or height > self.max_dimensions[1]:
            validation['dimensions_valid'] = False
            validation['warnings'].append(
                f"Image dimensions {width}x{height} exceed recommended maximum {self.max_dimensions}"
            )
        
        # Check resolution (DPI)
        dpi = image_info.get('dpi')
        if dpi:
            horizontal_dpi, vertical_dpi = dpi
            if horizontal_dpi < 150 or vertical_dpi < 150:
                validation['resolution_adequate'] = False
                validation['warnings'].append(
                    f"Image DPI {horizontal_dpi}x{vertical_dpi} may be too low for OCR"
                )
        
        # Check file size
        file_size = image_info['file_size_bytes']
        if file_size > self.max_file_size:
            validation['size_appropriate'] = False
            validation['issues'].append(
                f"Image file size {file_size} bytes exceeds maximum {self.max_file_size} bytes"
            )
        
        # Check minimum size
        if width < 100 or height < 100:
            validation['warnings'].append(
                "Image is very small and may not contain readable text"
            )
        
        return validation
    
    def _optimize_for_ocr(self, file_path: str, image_info: Dict[str, Any]) -> str:
        """
        Optimize image for OCR processing
        
        Args:
            file_path: Original image path
            image_info: Image information dictionary
            
        Returns:
            Path to optimized image
        """
        try:
            with Image.open(file_path) as img:
                # Start with original image
                optimized = img.copy()
                
                # Convert to appropriate mode
                if optimized.mode not in ('RGB', 'L'):
                    if optimized.mode == 'P':
                        optimized = optimized.convert('RGB')
                    elif optimized.mode == 'RGBA':
                        # Remove alpha channel for OCR
                        background = Image.new('RGB', optimized.size, (255, 255, 255))
                        background.paste(optimized, mask=optimized.split()[-1])
                        optimized = background
                    else:
                        optimized = optimized.convert('RGB')
                
                # Enhance contrast if requested
                if self.enhance_contrast:
                    try:
                        enhancer = ImageEnhance.Contrast(optimized)
                        optimized = enhancer.enhance(1.2)  # Increase contrast by 20%
                    except Exception as e:
                        logger.warning(f"Error enhancing contrast: {e}")
                
                # Apply noise reduction if requested
                if self.remove_noise:
                    try:
                        # Apply a mild blur to reduce noise
                        optimized = optimized.filter(ImageFilter.MedianFilter(size=3))
                    except Exception as e:
                        logger.warning(f"Error applying noise reduction: {e}")
                
                # Convert to grayscale if appropriate
                # Keep color for now as some OCR engines work better with color
                
                # Save optimized image
                temp_dir = tempfile.mkdtemp()
                optimized_path = os.path.join(temp_dir, 'ocr_optimized.png')
                
                optimized.save(optimized_path, 'PNG', dpi=(self.target_dpi, self.target_dpi))
                
                logger.info(f"Created OCR-optimized image: {optimized_path}")
                return optimized_path
                
        except Exception as e:
            logger.error(f"Error optimizing image for OCR: {e}")
            # Return original path if optimization fails
            return file_path
    
    def _extract_image_features(self, image_path: str, image_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features that might help with OCR and content analysis"""
        try:
            with Image.open(image_path) as img:
                features = {
                    'file_path': image_path,
                    'estimated_text_regions': self._estimate_text_regions(img),
                    'image_complexity': self._calculate_image_complexity(img, image_info),
                    'sharpness_estimate': self._estimate_sharpness(img),
                    'brightness_estimate': self._estimate_brightness(img),
                    'contrast_estimate': self._estimate_contrast(img)
                }
                
                return features
                
        except Exception as e:
            logger.error(f"Error extracting image features: {e}")
            return {}
    
    def _estimate_text_regions(self, img: Image.Image) -> int:
        """Estimate number of potential text regions"""
        try:
            # Simple heuristic: count distinct regions of similar colors
            # This is a basic implementation - in production, you might want
            # more sophisticated analysis using computer vision
            
            if img.mode == 'L':
                # For grayscale images, analyze histogram
                histogram = img.histogram()
                
                # Count peaks in histogram (potential text regions)
                peaks = 0
                threshold = len(histogram) * 0.01  # 1% of max count
                
                for i in range(1, len(histogram) - 1):
                    if (histogram[i] > histogram[i-1] and 
                        histogram[i] > histogram[i+1] and 
                        histogram[i] > threshold):
                        peaks += 1
                
                return min(peaks, 20)  # Cap at 20 regions
            else:
                # For color images, estimate based on size
                total_pixels = img.width * img.height
                return max(1, min(10, total_pixels // 100000))  # Rough estimate
                
        except Exception as e:
            logger.warning(f"Error estimating text regions: {e}")
            return 1
    
    def _calculate_image_complexity(self, img: Image.Image, image_info: Dict[str, Any]) -> str:
        """Calculate image complexity for OCR difficulty estimation"""
        try:
            color_count = image_info.get('color_count', 256)
            
            if color_count < 50:
                return 'low'
            elif color_count < 200:
                return 'medium'
            else:
                return 'high'
                
        except Exception:
            return 'medium'
    
    def _estimate_sharpness(self, img: Image.Image) -> str:
        """Estimate image sharpness"""
        try:
            # Simple sharpness estimation using edge detection
            edges = img.filter(ImageFilter.FIND_EDGES)
            
            # Calculate edge intensity
            if edges.mode == 'L':
                histogram = edges.histogram()
                high_values = sum(histogram[200:])  # Bright edges
                total_values = sum(histogram)
                
                edge_ratio = high_values / total_values if total_values > 0 else 0
                
                if edge_ratio > 0.1:
                    return 'sharp'
                elif edge_ratio > 0.05:
                    return 'moderate'
                else:
                    return 'blurry'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.warning(f"Error estimating sharpness: {e}")
            return 'unknown'
    
    def _estimate_brightness(self, img: Image.Image) -> str:
        """Estimate image brightness"""
        try:
            if img.mode == 'L':
                histogram = img.histogram()
                total_pixels = sum(histogram)
                
                # Calculate mean brightness
                mean_brightness = sum(i * count for i, count in enumerate(histogram)) / total_pixels
                
                if mean_brightness < 85:
                    return 'dark'
                elif mean_brightness > 170:
                    return 'bright'
                else:
                    return 'normal'
            else:
                return 'unknown'
                
        except Exception:
            return 'unknown'
    
    def _estimate_contrast(self, img: Image.Image) -> str:
        """Estimate image contrast"""
        try:
            if img.mode == 'L':
                histogram = img.histogram()
                
                # Calculate standard deviation (measure of contrast)
                total_pixels = sum(histogram)
                mean = sum(i * count for i, count in enumerate(histogram)) / total_pixels
                
                variance = sum(((i - mean) ** 2) * count for i, count in enumerate(histogram)) / total_pixels
                std_dev = variance ** 0.5
                
                if std_dev > 60:
                    return 'high'
                elif std_dev > 30:
                    return 'normal'
                else:
                    return 'low'
            else:
                return 'unknown'
                
        except Exception:
            return 'normal'
    
    def _calculate_processing_stats(self, image_info: Dict[str, Any], 
                                  features: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate processing statistics and confidence"""
        try:
            # Base confidence on image quality
            confidence = 0.5  # Base confidence
            
            # Adjust based on image size
            if image_info['width'] >= 300 and image_info['height'] >= 300:
                confidence += 0.1
            
            # Adjust based on file size (larger files often contain more content)
            file_size_mb = image_info['file_size_bytes'] / (1024 * 1024)
            if file_size_mb > 0.5:
                confidence += 0.1
            
            # Adjust based on sharpness
            sharpness = features.get('sharpness_estimate', 'unknown')
            if sharpness == 'sharp':
                confidence += 0.2
            elif sharpness == 'moderate':
                confidence += 0.1
            
            # Adjust based on contrast
            contrast = features.get('contrast_estimate', 'normal')
            if contrast == 'high':
                confidence += 0.1
            
            # Cap confidence at 1.0
            confidence = min(confidence, 1.0)
            
            return {
                'processing_quality': self._assess_processing_quality(image_info, features),
                'confidence': confidence,
                'ocr_suitability': self._assess_ocr_suitability(image_info, features),
                'estimated_processing_time': self._estimate_processing_time(image_info),
                'recommended_settings': self._get_recommended_settings(image_info, features)
            }
            
        except Exception as e:
            logger.error(f"Error calculating processing stats: {e}")
            return {'confidence': 0.5}
    
    def _assess_processing_quality(self, image_info: Dict[str, Any], 
                                 features: Dict[str, Any]) -> str:
        """Assess overall processing quality"""
        warnings = len(image_info.get('warnings', []))
        issues = len(image_info.get('issues', []))
        
        if issues > 0:
            return 'poor'
        elif warnings > 2:
            return 'fair'
        elif warnings > 0:
            return 'good'
        else:
            return 'excellent'
    
    def _assess_ocr_suitability(self, image_info: Dict[str, Any], 
                              features: Dict[str, Any]) -> str:
        """Assess suitability for OCR processing"""
        quality_score = 0
        
        # Check resolution
        dpi = image_info.get('dpi')
        if dpi:
            horizontal_dpi, _ = dpi
            if horizontal_dpi >= 300:
                quality_score += 2
            elif horizontal_dpi >= 200:
                quality_score += 1
        
        # Check dimensions
        if image_info['width'] >= 800 and image_info['height'] >= 600:
            quality_score += 1
        
        # Check sharpness
        sharpness = features.get('sharpness_estimate', 'unknown')
        if sharpness == 'sharp':
            quality_score += 2
        elif sharpness == 'moderate':
            quality_score += 1
        
        # Check contrast
        contrast = features.get('contrast_estimate', 'normal')
        if contrast == 'high':
            quality_score += 1
        
        if quality_score >= 4:
            return 'excellent'
        elif quality_score >= 2:
            return 'good'
        else:
            return 'poor'
    
    def _estimate_processing_time(self, image_info: Dict[str, Any]) -> str:
        """Estimate processing time based on image characteristics"""
        file_size_mb = image_info['file_size_bytes'] / (1024 * 1024)
        pixel_count = image_info['width'] * image_info['height']
        
        if file_size_mb < 1 and pixel_count < 500000:
            return 'fast'
        elif file_size_mb < 5 and pixel_count < 2000000:
            return 'normal'
        else:
            return 'slow'
    
    def _get_recommended_settings(self, image_info: Dict[str, Any], 
                                features: Dict[str, Any]) -> Dict[str, str]:
        """Get recommended processing settings"""
        settings = {
            'ocr_engine': 'tesseract',  # Default
            'preprocessing': 'enhanced'
        }
        
        # Adjust based on image characteristics
        if image_info['color_mode'] == 'grayscale':
            settings['ocr_engine'] = 'tesseract_grayscale'
        elif features.get('sharpness_estimate') == 'blurry':
            settings['preprocessing'] = 'maximum'
            settings['ocr_engine'] = 'enhanced_tesseract'
        
        return settings
    
    def _is_ocr_ready(self, image_info: Dict[str, Any]) -> bool:
        """Check if image is ready for OCR processing"""
        # Basic criteria for OCR readiness
        min_width = 100
        min_height = 100
        min_dpi = 72
        
        if (image_info['width'] < min_width or 
            image_info['height'] < min_height):
            return False
        
        dpi = image_info.get('dpi')
        if dpi and min(dpi) < min_dpi:
            return False
        
        # Check for critical issues
        issues = image_info.get('issues', [])
        if any('size' in issue.lower() for issue in issues):
            return False
        
        return True
    
    def validate_image(self, file_path: str) -> Dict[str, Any]:
        """Validate if image can be processed"""
        validation = {
            'is_valid_image': False,
            'is_processable': False,
            'is_ocr_ready': False,
            'issues': [],
            'warnings': [],
            'format': None,
            'file_size_bytes': 0,
            'dimensions': None,
            'recommended_actions': []
        }
        
        try:
            # Check file exists and size
            if not os.path.exists(file_path):
                validation['issues'].append("File does not exist")
                return validation
            
            file_size = os.path.getsize(file_path)
            validation['file_size_bytes'] = file_size
            
            if file_size == 0:
                validation['issues'].append("File is empty")
                return validation
            
            # Load and analyze image
            with Image.open(file_path) as img:
                validation['is_valid_image'] = True
                validation['format'] = img.format
                validation['dimensions'] = (img.width, img.height)
                
                # Check format support
                if img.format not in ('PNG', 'JPEG', 'JPG'):
                    validation['issues'].append(f"Format {img.format} not supported")
                    return validation
                
                # Check file size
                if file_size > self.max_file_size:
                    validation['issues'].append(
                        f"File size {file_size} bytes exceeds maximum {self.max_file_size}"
                    )
                    return validation
                
                # Check dimensions
                if img.width < 50 or img.height < 50:
                    validation['warnings'].append("Image is very small")
                
                validation['is_processable'] = True
                validation['is_ocr_ready'] = self._is_ocr_ready({
                    'width': img.width,
                    'height': img.height,
                    'dpi': img.info.get('dpi', (72, 72)),
                    'issues': []
                })
                
        except Exception as e:
            validation['issues'].append(f"Error validating image: {str(e)}")
        
        return validation


def get_image_processor() -> ImageProcessor:
    """Get a singleton image processor instance"""
    return ImageProcessor()