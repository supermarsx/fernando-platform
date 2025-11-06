"""
Enhanced Document Processing API

Multi-format document processing endpoints with intelligent pipelines,
format detection, validation, and preview generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import os
import tempfile
from pathlib import Path

from app.db.session import get_db
from app.models.user import User
from app.models.document import Document
from app.core.security import get_current_user
from app.core.config import settings

# Import enhanced processors
from app.services.enhanced_document_processor import get_enhanced_document_processor
from app.services.document_formats.format_detector import get_format_detector
from app.services.document_validator import get_document_validator
from app.services.document_converter import get_document_converter
from app.services.document_formats.preview_generator import get_preview_generator

# Import models for extended functionality
from app.models.document_extensions import (
    DocumentFormatInfo, DocumentPreview, DocumentConversion,
    DocumentValidation, DocumentProcessingPipeline, ProcessingStepRun,
    DocumentProcessingCache
)

router = APIRouter(prefix="/enhanced-documents", tags=["enhanced-documents"])


@router.post("/detect-format")
def detect_document_format(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect document format and basic metadata"""
    try:
        format_detector = get_format_detector()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Detect format
        detected_format, metadata = format_detector.detect_format(temp_file_path)
        
        # Validate format support
        validation = format_detector.validate_format_support(
            detected_format, 
            max_file_size=settings.MAX_FILE_SIZE,
            size_bytes=len(content)
        )
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        return {
            "detected_format": detected_format.value,
            "confidence": metadata["confidence"],
            "validation": validation,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Format detection failed: {str(e)}"
        )


@router.post("/validate")
def validate_document(
    file: UploadFile = File(...),
    tenant_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Comprehensive document validation including security scanning"""
    try:
        validator = get_document_validator()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Perform validation
        validation_result = validator.validate_document(
            temp_file_path, tenant_id, current_user.user_id
        )
        
        # Get summary
        summary = validator.get_validation_summary(validation_result)
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        return {
            "validation_result": validation_result,
            "summary": summary
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document validation failed: {str(e)}"
        )


@router.post("/convert")
async def convert_document(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    quality: str = Form("medium"),
    dpi: int = Form(300),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert document to different format"""
    try:
        converter = get_document_converter()
        format_detector = get_format_detector()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Detect source format
        source_format, _ = format_detector.detect_format(temp_file_path)
        from app.services.document_formats.format_detector import DocumentFormat
        
        target_format_enum = DocumentFormat(target_format.lower())
        
        # Check if conversion is supported
        if not converter.can_convert(source_format, target_format_enum):
            os.unlink(temp_file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conversion from {source_format.value} to {target_format} not supported"
            )
        
        # Perform conversion
        conversion_options = {
            "quality": quality,
            "dpi": dpi
        }
        
        conversion_result = converter.convert_document(
            temp_file_path, source_format, target_format_enum, **conversion_options
        )
        
        # Clean up original file
        os.unlink(temp_file_path)
        
        if conversion_result["success"]:
            # Return first converted file
            converted_files = conversion_result["converted_files"]
            if converted_files:
                return FileResponse(
                    converted_files[0],
                    media_type="application/octet-stream",
                    filename=f"converted_{target_format}.{target_format}",
                    background=converter.cleanup_conversion_files(conversion_result)
                )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=conversion_result.get("error", "Conversion failed")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document conversion failed: {str(e)}"
        )


@router.post("/preview/{document_id}")
def generate_document_preview(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate document preview and thumbnails"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.document_id == document_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if previews already exist
        existing_previews = db.query(DocumentPreview).filter(
            DocumentPreview.document_id == document_id
        ).all()
        
        if existing_previews:
            # Return existing previews
            preview_data = {
                "document_id": document_id,
                "previews": {
                    "thumbnails": {},
                    "previews": {},
                    "page_previews": {}
                }
            }
            
            for preview in existing_previews:
                size_category = preview.size_category
                preview_type = preview.preview_type
                
                if preview_type == "thumbnail":
                    preview_data["previews"]["thumbnails"][size_category] = preview.file_path
                elif preview_type == "preview":
                    preview_data["previews"]["previews"][size_category] = preview.file_path
                elif preview_type == "page_preview":
                    if f"page_{preview.page_number}" not in preview_data["previews"]["page_previews"]:
                        preview_data["previews"]["page_previews"][f"page_{preview.page_number}"] = {}
                    preview_data["previews"]["page_previews"][f"page_{preview.page_number}"][size_category] = preview.file_path
            
            return preview_data
        
        # Generate new previews
        preview_generator = get_preview_generator()
        format_detector = get_format_detector()
        
        # Detect format
        detected_format, _ = format_detector.detect_format(document.storage_url)
        
        # Generate previews
        preview_result = preview_generator.generate_previews(document.storage_url, detected_format)
        
        if preview_result["success"]:
            # Store preview information in database
            format_info = db.query(DocumentFormatInfo).filter(
                DocumentFormatInfo.document_id == document_id
            ).first()
            
            if not format_info:
                format_info = DocumentFormatInfo(
                    document_id=document_id,
                    detected_format=detected_format.value,
                    format_confidence=0.0,
                    format_metadata={}
                )
                db.add(format_info)
                db.commit()
                db.refresh(format_info)
            
            # Store preview images
            for size_category, file_path in preview_result.get("thumbnails", {}).items():
                preview = DocumentPreview(
                    document_id=document_id,
                    format_info_id=format_info.format_info_id,
                    preview_type="thumbnail",
                    size_category=size_category,
                    file_path=file_path,
                    file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0
                )
                db.add(preview)
            
            for size_category, file_path in preview_result.get("previews", {}).items():
                preview = DocumentPreview(
                    document_id=document_id,
                    format_info_id=format_info.format_info_id,
                    preview_type="preview",
                    size_category=size_category,
                    file_path=file_path,
                    file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0
                )
                db.add(preview)
            
            # Store page previews
            for page_name, page_variants in preview_result.get("page_previews", {}).items():
                page_number = int(page_name.split("_")[1])
                for size_category, file_path in page_variants.items():
                    preview = DocumentPreview(
                        document_id=document_id,
                        format_info_id=format_info.format_info_id,
                        preview_type="page_preview",
                        size_category=size_category,
                        file_path=file_path,
                        file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                        page_number=page_number
                    )
                    db.add(preview)
            
            db.commit()
        
        return preview_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview generation failed: {str(e)}"
        )


@router.post("/process/{document_id}")
def process_document_enhanced(
    document_id: str,
    processing_options: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process document using enhanced multi-format pipeline"""
    try:
        # Get document
        document = db.query(Document).filter(
            Document.document_id == document_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check permissions
        if document.uploaded_by != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to process this document"
            )
        
        # Get enhanced processor
        processor = get_enhanced_document_processor(db)
        
        # Process document
        processing_result = processor.process_document(
            document, current_user.user_id, processing_options or {}
        )
        
        return processing_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced processing failed: {str(e)}"
        )


@router.get("/statistics")
def get_processing_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document processing statistics"""
    try:
        processor = get_enhanced_document_processor(db)
        stats = processor.get_processing_statistics()
        
        # Add database statistics
        total_documents = db.query(Document).count()
        processed_documents = db.query(Document).filter(
            Document.processed_at.isnot(None)
        ).count()
        
        # Format distribution from database
        format_distribution = {}
        format_info_records = db.query(DocumentFormatInfo).all()
        for record in format_info_records:
            format_type = record.detected_format
            if format_type not in format_distribution:
                format_distribution[format_type] = 0
            format_distribution[format_type] += 1
        
        stats["database_stats"] = {
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "format_distribution": format_distribution
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/conversions/{document_id}")
def get_conversion_history(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document conversion history"""
    try:
        # Check document exists and user has access
        document = db.query(Document).filter(
            Document.document_id == document_id,
            Document.uploaded_by == current_user.user_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get conversion history
        conversions = db.query(DocumentConversion).filter(
            DocumentConversion.document_id == document_id
        ).order_by(DocumentConversion.conversion_started_at.desc()).all()
        
        conversion_data = []
        for conversion in conversions:
            conversion_data.append({
                "conversion_id": conversion.conversion_id,
                "source_format": conversion.source_format,
                "target_format": conversion.target_format,
                "conversion_method": conversion.conversion_method,
                "conversion_successful": conversion.conversion_successful,
                "conversion_time_seconds": conversion.conversion_time_seconds,
                "output_files": conversion.output_files,
                "error_message": conversion.error_message,
                "started_at": conversion.conversion_started_at,
                "completed_at": conversion.conversion_completed_at
            })
        
        return {
            "document_id": document_id,
            "conversion_history": conversion_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversion history: {str(e)}"
        )


@router.delete("/cache")
def clear_processing_cache(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear processing cache (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Clear expired cache entries
        from datetime import datetime
        expired_count = db.query(DocumentProcessingCache).filter(
            DocumentProcessingCache.expires_at <= datetime.utcnow()
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "message": f"Cleared {expired_count} expired cache entries"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/formats/support")
def get_supported_formats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get supported document formats based on user license tier"""
    try:
        # Determine supported formats based on user role/tier
        user_formats = settings.BASIC_FORMATS  # Default
        
        if hasattr(current_user, 'subscription_tier'):
            if current_user.subscription_tier == "professional":
                user_formats = settings.PROFESSIONAL_FORMATS
            elif current_user.subscription_tier == "enterprise":
                user_formats = settings.ENTERPRISE_FORMATS
        
        # Format the response
        supported_formats = []
        for ext in user_formats:
            format_info = {
                "extension": ext,
                "name": ext.upper().replace('.', ''),
                "description": get_format_description(ext),
                "max_size_mb": get_max_size_for_format(ext),
                "features": get_format_features(ext)
            }
            supported_formats.append(format_info)
        
        return {
            "user_tier": getattr(current_user, 'subscription_tier', 'basic'),
            "supported_formats": supported_formats,
            "processing_features": {
                "format_detection": True,
                "validation": settings.DOCUMENT_VALIDATION_ENABLED,
                "preview_generation": settings.PREVIEW_GENERATION_ENABLED,
                "format_conversion": settings.FORMAT_CONVERSION_ENABLED,
                "parallel_processing": settings.PARALLEL_PROCESSING_ENABLED
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported formats: {str(e)}"
        )


def get_format_description(extension: str) -> str:
    """Get description for file format"""
    descriptions = {
        ".pdf": "PDF documents with text and image support",
        ".tiff": "TIFF images with multi-page and compression support",
        ".png": "PNG images with transparency and high quality",
        ".jpeg": "JPEG images with compression optimization",
        ".jpg": "JPEG images with compression optimization"
    }
    return descriptions.get(extension, "Document format")


def get_max_size_for_format(extension: str) -> int:
    """Get maximum file size for format in MB"""
    sizes = {
        ".pdf": settings.MAX_PDF_SIZE // (1024 * 1024),
        ".tiff": settings.MAX_TIFF_SIZE // (1024 * 1024),
        ".png": settings.MAX_IMAGE_SIZE // (1024 * 1024),
        ".jpeg": settings.MAX_IMAGE_SIZE // (1024 * 1024),
        ".jpg": settings.MAX_IMAGE_SIZE // (1024 * 1024)
    }
    return sizes.get(extension, 50)


def get_format_features(extension: str) -> List[str]:
    """Get features available for format"""
    features = {
        ".pdf": ["text_extraction", "image_extraction", "encryption_support", "multi_page"],
        ".tiff": ["multi_page", "compression", "high_resolution", "color_modes"],
        ".png": ["transparency", "high_quality", "lossless_compression"],
        ".jpeg": ["compression", "photo_optimization", "progressive_loading"],
        ".jpg": ["compression", "photo_optimization", "progressive_loading"]
    }
    return features.get(extension, [])