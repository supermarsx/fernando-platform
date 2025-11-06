from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.services.export_import_service import ExportImportService
from app.models.enterprise import ExportJob

router = APIRouter(prefix="/export-import", tags=["export-import"])


@router.post("/exports")
async def create_export_job(
    export_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new export job"""
    service = ExportImportService(db)
    
    # Validate export type
    valid_types = ["jobs", "documents", "extractions", "audit_logs", "tenant_summary"]
    if export_data.get("export_type") not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export_type. Must be one of: {valid_types}"
        )
    
    # Validate export format
    valid_formats = ["csv", "excel", "json", "pdf"]
    if export_data.get("export_format") not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid export_format. Must be one of: {valid_formats}"
        )
    
    # Check permissions for different export types
    if export_data.get("export_type") == "audit_logs":
        if "admin" not in (current_user.roles or []) and "auditor" not in (current_user.roles or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or Auditor role required for audit log exports"
            )
    
    export_job = service.create_export(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        export_type=export_data["export_type"],
        export_format=export_data["export_format"],
        job_id=export_data.get("job_id"),
        filters=export_data.get("filters", {})
    )
    
    return {
        "export_id": export_job.export_id,
        "export_type": export_job.export_type,
        "export_format": export_job.export_format,
        "status": export_job.status,
        "created_at": export_job.created_at.isoformat()
    }


@router.get("/exports")
async def list_export_jobs(
    status: Optional[str] = Query(None),
    export_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List export jobs"""
    query = db.query(ExportJob).filter(ExportJob.tenant_id == current_user.tenant_id)
    
    if status:
        query = query.filter(ExportJob.status == status)
    
    if export_type:
        query = query.filter(ExportJob.export_type == export_type)
    
    exports = query.order_by(ExportJob.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "export_id": e.export_id,
            "export_type": e.export_type,
            "export_format": e.export_format,
            "status": e.status,
            "file_size_bytes": e.file_size_bytes,
            "records_count": e.records_count,
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat(),
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "error_message": e.error_message
        }
        for e in exports
    ]


@router.get("/exports/{export_id}")
async def get_export_job(
    export_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of an export job"""
    export_job = db.query(ExportJob).filter(
        ExportJob.export_id == export_id,
        ExportJob.tenant_id == current_user.tenant_id
    ).first()
    
    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )
    
    return {
        "export_id": export_job.export_id,
        "export_type": export_job.export_type,
        "export_format": export_job.export_format,
        "status": export_job.status,
        "file_size_bytes": export_job.file_size_bytes,
        "records_count": export_job.records_count,
        "filters": export_job.filters,
        "file_url": export_job.file_url,
        "created_by": export_job.created_by,
        "created_at": export_job.created_at.isoformat(),
        "completed_at": export_job.completed_at.isoformat() if export_job.completed_at else None,
        "error_message": export_job.error_message
    }


@router.post("/exports/{export_id}/execute")
async def execute_export_job(
    export_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute an export job"""
    service = ExportImportService(db)
    
    export_job = db.query(ExportJob).filter(
        ExportJob.export_id == export_id,
        ExportJob.tenant_id == current_user.tenant_id,
        ExportJob.created_by == current_user.user_id
    ).first()
    
    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found or access denied"
        )
    
    if export_job.status == "completed" and export_job.file_size_bytes:
        return {"message": "Export already completed"}
    
    result = service.execute_export(export_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {
        "message": "Export completed successfully",
        "filename": result["filename"],
        "file_size_bytes": result["file_data"] and len(result["file_data"]),
        "records_count": result["export_job"].records_count
    }


@router.get("/exports/{export_id}/download")
async def download_export_file(
    export_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download an exported file"""
    service = ExportImportService(db)
    
    export_job = db.query(ExportJob).filter(
        ExportJob.export_id == export_id,
        ExportJob.tenant_id == current_user.tenant_id
    ).first()
    
    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found"
        )
    
    if export_job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export job not completed yet"
        )
    
    # Re-execute to get file data
    result = service.execute_export(export_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    # Return file as streaming response
    return StreamingResponse(
        iter([result["file_data"]]),
        media_type=result["mime_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"'
        }
    )


@router.delete("/exports/{export_id}")
async def delete_export_job(
    export_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an export job"""
    export_job = db.query(ExportJob).filter(
        ExportJob.export_id == export_id,
        ExportJob.tenant_id == current_user.tenant_id,
        ExportJob.created_by == current_user.user_id
    ).first()
    
    if not export_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found or access denied"
        )
    
    db.delete(export_job)
    db.commit()
    
    return {"message": "Export job deleted successfully"}


@router.post("/imports")
async def import_data(
    import_type: str = Query(..., description="Type of data to import: jobs, users"),
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import data from uploaded file"""
    service = ExportImportService(db)
    
    # Validate import type
    valid_types = ["jobs", "users"]
    if import_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid import_type. Must be one of: {valid_types}"
        )
    
    # Check permissions for user imports
    if import_type == "users" and "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for user imports"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size (max 50MB)
    if len(file_content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit"
        )
    
    # Process import
    result = service.import_data(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        file_data=file_content,
        filename=file.filename,
        import_type=import_type
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {
        "import_type": import_type,
        "imported_count": result["imported_count"],
        "errors": result["errors"],
        "filename": file.filename
    }


@router.get("/templates/{template_type}")
async def get_import_template(
    template_type: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get import template for specific data type"""
    service = ExportImportService(db)
    
    if template_type == "jobs":
        template_data = [
            {
                "original_filename": "invoice_001.pdf",
                "priority": "0",
                "queue_name": "default",
                "metadata": '{"document_type": "invoice", "supplier": "ABC Corp"}'
            },
            {
                "original_filename": "receipt_002.pdf",
                "priority": "1",
                "queue_name": "urgent",
                "metadata": '{"document_type": "receipt", "supplier": "XYZ Ltd"}'
            }
        ]
        filename = "job_import_template.csv"
        content_type = "text/csv"
    elif template_type == "users":
        template_data = [
            {
                "email": "user1@company.com",
                "full_name": "John Doe",
                "status": "active"
            },
            {
                "email": "user2@company.com",
                "full_name": "Jane Smith",
                "status": "active"
            }
        ]
        filename = "user_import_template.csv"
        content_type = "text/csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template type: {template_type}"
        )
    
    # Generate CSV content
    import csv
    import io
    
    output = io.StringIO()
    if template_data:
        writer = csv.DictWriter(output, fieldnames=template_data[0].keys())
        writer.writeheader()
        writer.writerows(template_data)
    
    csv_content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        iter([csv_content.encode('utf-8')]),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/formats/supported")
async def get_supported_formats():
    """Get list of supported import/export formats"""
    return {
        "export_formats": [
            {
                "format": "csv",
                "description": "Comma-separated values",
                "mime_type": "text/csv"
            },
            {
                "format": "excel",
                "description": "Microsoft Excel spreadsheet",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
            {
                "format": "json",
                "description": "JavaScript Object Notation",
                "mime_type": "application/json"
            },
            {
                "format": "pdf",
                "description": "PDF Report",
                "mime_type": "application/pdf"
            }
        ],
        "import_formats": [
            {
                "format": "csv",
                "description": "Comma-separated values",
                "mime_type": "text/csv",
                "max_size_mb": 50
            },
            {
                "format": "json",
                "description": "JavaScript Object Notation",
                "mime_type": "application/json",
                "max_size_mb": 50
            },
            {
                "format": "excel",
                "description": "Microsoft Excel spreadsheet",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "max_size_mb": 50
            }
        ],
        "export_types": [
            {
                "type": "jobs",
                "description": "Export job records and metadata"
            },
            {
                "type": "documents",
                "description": "Export document metadata"
            },
            {
                "type": "extractions",
                "description": "Export extraction results"
            },
            {
                "type": "audit_logs",
                "description": "Export audit trail (Admin/Auditor only)"
            },
            {
                "type": "tenant_summary",
                "description": "Export tenant overview and statistics"
            }
        ]
    }


@router.get("/statistics")
async def get_export_import_statistics(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get export/import statistics for the tenant"""
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get export statistics
    exports = db.query(ExportJob).filter(
        ExportJob.tenant_id == current_user.tenant_id,
        ExportJob.created_at >= cutoff_date
    )
    
    export_stats = exports.with_entities(
        ExportJob.status,
        ExportJob.export_format,
        ExportJob.export_type,
        ExportJob.file_size_bytes
    ).all()
    
    # Get import statistics (would need to track imports separately)
    import_stats = []
    
    # Calculate totals
    total_exports = len(exports.all())
    completed_exports = len([e for e in exports.all() if e.status == "completed"])
    total_exported_bytes = sum(e.file_size_bytes or 0 for e in exports.all() if e.file_size_bytes)
    
    return {
        "period_days": days,
        "exports": {
            "total": total_exports,
            "completed": completed_exports,
            "failed": total_exports - completed_exports,
            "total_exported_bytes": total_exported_bytes,
            "by_format": {},
            "by_type": {}
        },
        "imports": {
            "total": len(import_stats),
            "completed": 0,  # Would track this
            "failed": 0      # Would track this
        },
        "average_file_size_bytes": total_exported_bytes / completed_exports if completed_exports > 0 else 0
    }
