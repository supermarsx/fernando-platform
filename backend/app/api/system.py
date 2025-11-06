"""
System monitoring and health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.system_health import SystemHealthService

router = APIRouter(prefix="/api/v1/system", tags=["system"])

@router.get("/status")
async def system_status(db: Session = Depends(get_db)):
    """Get detailed system status including enterprise features and cache"""
    health_service = SystemHealthService(db)
    return await health_service.get_detailed_status()